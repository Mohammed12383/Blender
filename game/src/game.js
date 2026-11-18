// Deepwater Crew: main game - player, stations, hands, interactions, HUD, audio and the loop.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Sim, TELEGRAPH_NAMES, ROOMS, PERISCOPE_DEPTH, TEST_DEPTH } from './sim.js';
import { Exterior } from './exterior.js';
import { Interior } from './interior.js';
import { Sound } from './sound.js';
import { Net } from './net.js';
import { DROP } from './exterior.js';
const DROP_TEX = () => DROP;

const $ = (id) => document.getElementById(id);
const ROLE_FILE = { navigator: 'Navigator', weapons_officer: 'Gunner', torpedo_loader: 'Loader', cook: 'Cook' };
const PARAMS = new URLSearchParams(location.search);
const EYE = 1.65;

const canvas = $('view');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;
const loader = new GLTFLoader();

const sim = new Sim();
const ext = new Exterior(renderer, loader);
const inn = new Interior(renderer, loader);
const sound = new Sound();
let net = null;

const camera = new THREE.PerspectiveCamera(72, 1, 0.03, 200);
camera.rotation.order = 'YXZ';
inn.scene.add(camera);

const player = {
  pos: new THREE.Vector3(14.6, 0, 0.6), yaw: Math.PI / 2, pitch: -0.05, stamina: 100, hunger: 100,
  carry: null, mode: 'walk', station: null, role: 'navigator', hold: 0, shake: 0, transition: 0,
  camFrom: new THREE.Vector3(), quatFrom: new THREE.Quaternion(),
};
const keys = new Set();
let mouseDX = 0, mouseDY = 0, wheel = 0, clicked = false;
const griddle = { power: false, slots: [null, null, null, null] };   // {state:'raw'|'cooked'|'burnt', t}

// --------------------------------------------------------------- loading
const extReady = ext.load();
let menuCine = true;
extReady.then(() => {
  const t0 = performance.now();
  const cine = () => {
    if (!menuCine) return;
    const t = (performance.now() - t0) / 1000;
    sim.update(1 / 60);
    sim.events.length = 0;
    ext.sync(sim, 1 / 60);
    ext.orbit.yaw = 2.2 + t * 0.05; ext.orbit.pitch = 0.12 + Math.sin(t * 0.1) * 0.06; ext.orbit.dist = 60;
    renderer.setSize(innerWidth, innerHeight, false);
    ext.chaseCamera(sim, innerWidth / innerHeight);
    ext.render();
    requestAnimationFrame(cine);
  };
  sim.setTelegraph(2);
  cine();
});

async function start(role) {
  player.role = role;
  $('loading').textContent = 'Loading the submarine...';
  await Promise.all([inn.load(), extReady, loadHands(role), loadFood()]);
  menuCine = false;
  sim.setTelegraph(0);
  $('menu').classList.add('hidden');
  $('hud').classList.remove('hidden');
  const url = $('server').value.trim();
  if (url) { net = new Net(url, $('pname').value || 'Sailor', role, sim, inn, loader); net.connect(); }
  sound.start();
  sim.message(`You are the ${role.replace('_', ' ').toUpperCase()}. Press E to use stations. Any crew member can run any station.`);
  if (PARAMS.get('station')) enterStation(PARAMS.get('station'));
  if (PARAMS.get('mode')) player.mode = PARAMS.get('mode');
  if (PARAMS.get('test')) applyTest(PARAMS.get('test'));
  requestAnimationFrame(loop);
}

let fp = null;
async function loadHands(role) {
  const g = await loader.loadAsync(`../submarine/models/characters/FPArms_${ROLE_FILE[role]}.glb`);
  const rig = g.scene;
  const holder = new THREE.Group();
  holder.add(rig);
  rig.rotation.y = Math.PI;
  rig.position.set(0, -1.69, 0.08);
  camera.add(holder);
  rig.traverse((o) => { if (o.isMesh) { o.frustumCulled = false; o.renderOrder = 2; } });
  const bone = (n) => rig.getObjectByName(n);
  fp = { rig, holder, sides: {} };
  for (const [s, sd] of [[1, 'L'], [-1, 'R']]) {
    const up = bone(`UpperArm${sd}`), lo = bone(`LowerArm${sd}`), hand = bone(`Hand${sd}`);
    if (!up) continue;
    const fingers = [];
    for (const f of ['Thumb', 'Index', 'Middle', 'Ring', 'Pinky']) for (let k = 1; k <= 3; k++) { const b = bone(`${f}${k}${sd}`); if (b) fingers.push({ b, f, k, rest: b.quaternion.clone() }); }
    fp.sides[sd] = { s, up, lo, hand, fingers, rest: [up.quaternion.clone(), lo.quaternion.clone(), hand.quaternion.clone()],
      target: new THREE.Vector3(), pose: 'relax', cur: new THREE.Vector3() };
  }
  const a = new THREE.Vector3(), b = new THREE.Vector3(), c = new THREE.Vector3();
  rig.updateMatrixWorld(true);
  for (const sd of ['L', 'R']) {
    const S = fp.sides[sd]; if (!S) continue;
    S.up.getWorldPosition(a); S.lo.getWorldPosition(b); S.hand.getWorldPosition(c);
    S.L1 = a.distanceTo(b); S.L2 = b.distanceTo(c);
  }
  // carried items
  fp.torpedo = null; fp.wrench = null;
}

let food = {};
async function loadFood() {
  for (const n of ['SteakRaw', 'SteakCooked']) food[n] = (await loader.loadAsync(`../submarine/models/props/${n}.glb`)).scene;
  griddle.views = [null, null, null, null];
}

// ------------------------------------------------------------ hands (IK)
const _v1 = new THREE.Vector3(), _v2 = new THREE.Vector3(), _v3 = new THREE.Vector3(), _q1 = new THREE.Quaternion(), _q2 = new THREE.Quaternion();
const CURL = { relax: [0.35, 0.3], grip: [1.15, 0.7], pinch: [0.9, 0.6], press: [1.3, 0.9], palm: [0.08, 0.1], carry: [1.0, 0.6] };

function aimBone(bone, from, to, childWorld) {
  // rotate `bone` so the direction from its head (from) to childWorld points at `to`
  const cur = _v1.copy(childWorld).sub(from).normalize();
  const want = _v2.copy(to).sub(from).normalize();
  _q1.setFromUnitVectors(cur, want);
  bone.getWorldQuaternion(_q2);
  _q2.premultiply(_q1);
  const parentQ = new THREE.Quaternion();
  bone.parent.getWorldQuaternion(parentQ);
  bone.quaternion.copy(parentQ.invert().multiply(_q2));
  bone.updateMatrixWorld(true);
}

function solveArm(S, target, pose, dt) {
  S.up.quaternion.copy(S.rest[0]); S.lo.quaternion.copy(S.rest[1]); S.hand.quaternion.copy(S.rest[2]);
  fp.rig.updateMatrixWorld(true);
  S.cur.lerp(target, Math.min(1, dt * 10));
  const sh = S.up.getWorldPosition(new THREE.Vector3());
  const T = S.cur.clone();
  const d = Math.min(S.L1 + S.L2 - 1e-3, Math.max(1e-3, T.distanceTo(sh)));
  const dir = T.clone().sub(sh).normalize();
  T.copy(sh).addScaledVector(dir, d);
  const a = (S.L1 * S.L1 - S.L2 * S.L2 + d * d) / (2 * d), h = Math.sqrt(Math.max(0, S.L1 * S.L1 - a * a));
  const pole = camera.localToWorld(new THREE.Vector3(S.s * -0.8, -1.2, 0.4)).sub(camera.getWorldPosition(new THREE.Vector3()));
  const perp = pole.sub(dir.clone().multiplyScalar(pole.dot(dir))).normalize();
  const elbow = sh.clone().addScaledVector(dir, a).addScaledVector(perp, h);
  aimBone(S.up, sh, elbow, S.lo.getWorldPosition(new THREE.Vector3()));
  const el = S.lo.getWorldPosition(new THREE.Vector3());
  aimBone(S.lo, el, T, S.hand.getWorldPosition(new THREE.Vector3()));
  orientHand(S, pose);
  const [c1, c2] = CURL[pose] || CURL.relax;
  for (const f of S.fingers) {
    let amt = f.f === 'Thumb' ? c2 : c1;
    if (pose === 'press' && f.f === 'Index') amt = 0.05;
    if (pose === 'pinch' && (f.f === 'Ring' || f.f === 'Pinky')) amt = 1.3;
    f.b.quaternion.copy(f.rest).multiply(_q1.setFromAxisAngle(_v3.set(1, 0, 0), amt * (f.k === 1 ? 0.8 : 1)));
  }
}

// Point the hand along the view with the palm facing the control.
const ROLL = { relax: 0.5, grip: 1.25, pinch: 0.9, press: 0.35, palm: 0.0, carry: Math.PI };
function orientHand(S, pose) {
  const fwd = camera.getWorldDirection(new THREE.Vector3());
  const up = new THREE.Vector3(0, 1, 0).applyQuaternion(camera.getWorldQuaternion(new THREE.Quaternion()));
  const side = new THREE.Vector3().crossVectors(fwd, up).normalize().multiplyScalar(S.s * -1);
  const y = fwd.clone().multiplyScalar(0.85).addScaledVector(up, -0.35).addScaledVector(side, 0.15).normalize();
  const roll = (ROLL[pose] ?? 0.5) * S.s;
  let z = up.clone().applyAxisAngle(y, roll);
  z.sub(y.clone().multiplyScalar(z.dot(y))).normalize();
  const x = new THREE.Vector3().crossVectors(y, z).normalize();
  const want = new THREE.Quaternion().setFromRotationMatrix(new THREE.Matrix4().makeBasis(x, y, z));
  const parentQ = S.hand.parent.getWorldQuaternion(new THREE.Quaternion());
  S.hand.quaternion.copy(parentQ.invert().multiply(want));
  S.hand.updateMatrixWorld(true);
}

function updateHands(dt) {
  if (!fp) return;
  const show = player.mode === 'walk' || player.mode === 'station';
  fp.holder.visible = show;
  if (!show) return;
  const targets = { L: null, R: null }, poses = { L: 'relax', R: 'relax' };
  const camLocal = (x, y, z) => camera.localToWorld(new THREE.Vector3(x, y, z));
  if (player.mode === 'station' && player.station && player.transition >= 1) {
    const st = inn.stations[player.station];
    for (const h of st.hands) {
      const side = h.userData.hand;
      const p = h.getWorldPosition(new THREE.Vector3());
      // back the wrist off the control so the fingers land on it
      targets[side] = p.add(camera.getWorldDirection(new THREE.Vector3()).multiplyScalar(-0.07));
      poses[side] = h.userData.hand_pose;
      if (stationInput.press && side === 'R') targets[side].add(camera.getWorldDirection(new THREE.Vector3()).multiplyScalar(0.03));
    }
  }
  const bob = Math.sin(performance.now() / 160) * (keys.size ? 0.01 : 0.003);
  if (player.carry === 'torpedo') { targets.L ||= camLocal(-0.22, -0.42 + bob, -0.55); targets.R ||= camLocal(0.22, -0.42 + bob, -0.55); poses.L = poses.R = 'carry'; }
  if (player.carry === 'wrench') { targets.R ||= camLocal(0.24, -0.3 + bob, -0.42); poses.R = 'grip'; }
  if (player.carry && player.carry.startsWith('food')) { targets.L ||= camLocal(-0.2, -0.3 + bob, -0.4); poses.L = 'palm'; }
  if (player.carry === 'extinguisher') { targets.L ||= camLocal(-0.12, -0.36 + bob, -0.5); targets.R ||= camLocal(0.14, -0.3 + bob, -0.48); poses.L = poses.R = 'grip'; }
  if (player.repairing) targets.R = inn.interactables.find((i) => i.kind === 'leak' && i.data === player.repairing)?.pos.clone() || targets.R;
  targets.L ||= camLocal(-0.32, -0.75, -0.25);
  targets.R ||= camLocal(0.32, -0.75, -0.25);
  for (const sd of ['L', 'R']) if (fp.sides[sd]) solveArm(fp.sides[sd], targets[sd], poses[sd], dt);
  // carried props follow the hands
  if (player.carry === 'torpedo') {
    if (!fp.torpedo) { fp.torpedo = inn.tpl.torpedo.clone(); fp.torpedo.scale.setScalar(0.55); camera.add(fp.torpedo); }
    fp.torpedo.position.set(0, -0.48 + bob, -0.85); fp.torpedo.rotation.set(0, Math.PI / 2, 0);
  } else if (fp.torpedo) { camera.remove(fp.torpedo); fp.torpedo = null; }
  if (player.carry === 'wrench') {
    if (!fp.wrench) { fp.wrench = inn.tpl.wrench.clone(); camera.add(fp.wrench); }
    const turn = player.repairing ? Math.sin(performance.now() / 90) * 0.6 : 0;
    fp.wrench.position.set(0.2, -0.24 + bob, -0.5); fp.wrench.rotation.set(0.2, -1.2 + turn, 0.3);
  } else if (fp.wrench) { camera.remove(fp.wrench); fp.wrench = null; }
  if (player.carry === 'extinguisher') {
    if (!fp.ext) {
      const src = inn.root.children.find((o) => /^FireExtinguisher/.test(o.name));
      fp.ext = src ? src.clone() : new THREE.Group(); camera.add(fp.ext);
      fp.spray = new THREE.Points(new THREE.BufferGeometry().setAttribute('position', new THREE.BufferAttribute(new Float32Array(300), 3)),
        new THREE.PointsMaterial({ color: 0xffffff, size: 0.12, map: DROP_TEX(), transparent: true, opacity: 0.8, depthWrite: false }));
      fp.spray.frustumCulled = false; camera.add(fp.spray);
    }
    fp.ext.position.set(0.02, -0.75 + bob, -0.62); fp.ext.rotation.set(0.25, Math.PI, 0);
    const a = fp.spray.geometry.attributes.position;
    for (let i = 0; i < 100; i++) { const t = Math.random(); a.array.set([0.05 + (Math.random() - 0.5) * t * 0.5, -0.22 + (Math.random() - 0.5) * t * 0.4, -0.6 - t * 2.2], i * 3); }
    a.needsUpdate = true; fp.spray.visible = !!player.spraying;
  } else if (fp.ext) { camera.remove(fp.ext); camera.remove(fp.spray); fp.ext = null; }
  if (player.carry && player.carry.startsWith('food')) {
    if (!fp.food) { fp.food = food[player.carry === 'food_raw' ? 'SteakRaw' : 'SteakCooked'].clone(); camera.add(fp.food); }
    fp.food.position.set(-0.2, -0.27 + bob, -0.42);
  } else if (fp.food) { camera.remove(fp.food); fp.food = null; }
}

// --------------------------------------------------------------- stations
const HELP = {
  helm: ['HELM', 'W / S   engine telegraph (ahead / astern)\nA / D   rudder (hold)    X centre rudder\nC       captain\'s external 3D view\nEsc     leave'],
  chart: ['CHART TABLE', 'The chart shows every contact found by\nperiscope or sonar. Red = warships, green = merchants,\npurple = creatures.\nC external view    Esc leave'],
  ballast: ['BALLAST & DIVE PLANES', 'F  FLOOD tanks (dive)     B  BLOW tanks (surface)\nH  HOLD (close valves)\nW / S  planes rise / dive (hold)    X level planes\nPeriscope depth is ' + PERISCOPE_DEPTH + ' m. Hull limit ' + TEST_DEPTH + ' m.\nEsc leave'],
  periscope: ['PERISCOPE', 'Mouse / A D  train left & right    W S  tilt\nWheel / Z  zoom      Click / Space  MARK target\nR  raise / lower      Esc  leave'],
  sonar: ['SONAR', 'P  active PING (reveals everything, but they hear you)\nN  lock next contact for fire control\nEsc leave'],
  weapons: ['FIRE CONTROL', '1-4  select tube     F  flood / drain tube\nO    open / close outer door\nK    ARM key          G  lift guard\nSPACE  FIRE           N  launch noisemaker (decoy)\nEsc leave'],
  griddle: ['GRIDDLE', 'P  power on / off\nE  put raw food on / take cooked food off\nCook ~8 s. Leave it too long and it burns!\nEsc leave'],
};
for (let n = 1; n <= 4; n++) HELP[`tube${n}`] = [`TUBE ${n} BREECH`, 'E  open / close the breech door\nCarry a torpedo here with the door open to load\nEsc leave'];
const stationInput = { press: false };

function enterStation(key) {
  const st = inn.stations[key];
  if (!st) return;
  player.mode = 'station'; player.station = key; player.transition = 0;
  camera.getWorldPosition(player.camFrom); camera.getWorldQuaternion(player.quatFrom);
  $('station').classList.remove('hidden');
  $('stationtitle').textContent = HELP[key][0];
  $('stationhelp').textContent = HELP[key][1];
  $('crosshair').classList.add('hidden');
  if (document.pointerLockElement) document.exitPointerLock();
  if (key === 'periscope') {
    if (!sim.sub.periscopeUp) sim.togglePeriscope();
    if (sim.sub.periscopeUp) setTimeout(() => { if (player.station === 'periscope') player.mode = 'scope'; }, 450);
  }
  if (net) net.claim(key);
}

function leaveStation() {
  if (player.mode === 'bridge' || player.mode === 'chase') { player.mode = player.station ? 'station' : 'walk'; if (!player.station) $('crosshair').classList.remove('hidden'); return; }
  player.mode = 'walk'; player.station = null;
  $('station').classList.add('hidden'); $('scope').classList.add('hidden');
  $('crosshair').classList.remove('hidden');
  canvas.requestPointerLock?.();
  if (net) net.claim(null);
}

function stationKey(k, down) {
  const s = sim.sub, key = player.station;
  if (!down) return;
  if (k === 'c' && (key === 'helm' || key === 'chart')) { player.mode = 'chase'; return; }
  if (key === 'helm') {
    if (k === 'w') sim.setTelegraph(s.telegraph + 1);
    if (k === 's') sim.setTelegraph(s.telegraph - 1);
    if (k === 'x') sim.setRudder(0);
    sound.click();
  } else if (key === 'ballast') {
    if (k === 'f') sim.setValve('flood');
    if (k === 'b') sim.setValve('blow');
    if (k === 'h') sim.setValve('hold');
    if (k === 'x') sim.setPlanes(0);
    sound.click();
  } else if (key === 'periscope') {
    if (k === 'r') { sim.togglePeriscope(); player.mode = sim.sub.periscopeUp ? 'scope' : 'station'; }
    if (k === ' ') sim.markTarget(s.heading + s.periscopeBearing);
  } else if (key === 'sonar') {
    if (k === 'p') sim.sonarPing();
    if (k === 'n') {
      const ids = [...sim.contacts.keys()].filter((id) => sim.entities.some((e) => e.id === id && e.alive));
      if (ids.length) { const i = (ids.indexOf(sim.weapons.lock) + 1) % ids.length; sim.weapons.lock = ids[i]; const e = sim.entities.find((q) => q.id === ids[i]); sim.message(`Fire control locked on ${e.kind.toUpperCase()}.`); }
    }
  } else if (key === 'weapons') {
    const w = sim.weapons;
    if ('1234'.includes(k)) w.selected = +k;
    if (k === 'f') sim.floodTube(w.selected);
    if (k === 'o') sim.openOuter(w.selected);
    if (k === 'k') w.armed = !w.armed;
    if (k === 'g') w.guardOpen = !w.guardOpen;
    if (k === 'n') sim.countermeasure();
    if (k === ' ') { stationInput.press = true; setTimeout(() => { stationInput.press = false; }, 200); sim.fire(); }
    sound.click();
  } else if (key === 'griddle') {
    if (k === 'p') { griddle.power = !griddle.power; sim.message(griddle.power ? 'Griddle on.' : 'Griddle off.'); }
    if (k === 'e') griddleUse();
  } else if (key.startsWith('tube')) {
    const n = +key.slice(4);
    if (k === 'e') {
      if (player.carry === 'torpedo' && sim.tubes[n - 1].breechOpen && sim.loadTube(n)) { player.carry = null; sound.clunk(); }
      else if (sim.toggleBreech(n)) sound.clunk();
    }
  }
  if (net) net.sendControls();
}

function griddleUse() {
  const i = griddle.slots.findIndex((x) => x && x.state !== 'raw');
  if (i >= 0 && !player.carry) {
    player.carry = griddle.slots[i].state === 'burnt' ? 'food_burnt' : 'food_cooked';
    griddle.slots[i] = null; sim.message(player.carry === 'food_burnt' ? 'Burnt... still edible, barely.' : 'Cooked! Take it to someone hungry (F to eat).');
    return;
  }
  if (player.carry === 'food_raw') {
    const j = griddle.slots.indexOf(null);
    if (j >= 0) { griddle.slots[j] = { state: 'raw', t: 0 }; player.carry = null; sim.message(griddle.power ? 'Sizzling...' : 'Turn the griddle on (P)!'); }
  }
}

function updateGriddle(dt) {
  const st = inn.stations.griddle; if (!st) return;
  const base = new THREE.Vector3(); st.root.getWorldPosition(base);
  griddle.slots.forEach((sl, i) => {
    if (sl && griddle.power) { sl.t += dt; sl.state = sl.t > 20 ? 'burnt' : sl.t > 8 ? 'cooked' : 'raw'; }
    const want = sl ? (sl.state === 'raw' ? 'SteakRaw' : 'SteakCooked') : null;
    const v = griddle.views[i];
    if (v && v.userData.kind !== want) { inn.scene.remove(v); griddle.views[i] = null; }
    if (want && !griddle.views[i]) {
      const m = food[want].clone(); m.userData.kind = want;
      const local = new THREE.Vector3(-0.45 + i * 0.3, 0.925, -0.4);   // along the plate (the griddle faces -Z, into the galley)
      m.position.copy(base).add(local);
      if (sl && sl.state === 'burnt') m.traverse((o) => { if (o.isMesh) { o.material = o.material.clone(); o.material.color.setHex(0x222222); } });
      inn.scene.add(m); griddle.views[i] = m;
    }
  });
}

// ------------------------------------------------------------ interaction
function nearest() {
  if (player.mode !== 'walk') return null;
  const eye = camera.getWorldPosition(new THREE.Vector3()), fwd = camera.getWorldDirection(new THREE.Vector3());
  let best = null, bestScore = 1e9;
  for (const it of inn.interactables) {
    const d = it.pos.distanceTo(eye);
    if (d > it.radius + 1.3) continue;
    const ang = fwd.angleTo(it.pos.clone().sub(eye));
    if (ang > 0.55 && d > 0.9) continue;
    const score = ang * 2 + d * 0.3;
    if (score < bestScore) { bestScore = score; best = it; }
  }
  return best;
}

function interact(it) {
  if (!it) return;
  const s = sim.sub;
  switch (it.kind) {
    case 'station': enterStation(it.data); break;
    case 'tube': enterStation(`tube${it.data}`); break;
    case 'rack':
      if (player.carry) return sim.message('Your hands are full (Q to drop).', 'warn');
      if (sim.takeTorpedo()) { player.carry = 'torpedo'; sim.message('Carrying a torpedo - take it to an open tube breech.'); sound.clunk(); }
      break;
    case 'door': sim.toggleDoor(it.data); sound.clunk(); break;
    case 'wrench':
      if (player.carry) return sim.message('Your hands are full (Q to drop).', 'warn');
      it.data.visible = false; player.carry = 'wrench'; player.wrenchObj = it.data;
      inn.interactables = inn.interactables.filter((q) => q !== it);
      sim.message('Got a wrench. Find the leaks and hold E on them.');
      break;
    case 'leak': if (player.carry !== 'wrench') sim.message('You need a WRENCH to fix leaks.', 'warn'); break;
    case 'food': if (!player.carry) { player.carry = 'food_raw'; sim.message('Raw steak. Cook it at the GRIDDLE in the galley.'); } break;
    case 'coffee': player.stamina = Math.min(100, player.stamina + 40); sim.message('Hot coffee. Stamina up!'); break;
    case 'rest': player.stamina = 100; sim.message('A quick nap. Fully rested.'); break;
    case 'eat': eat(); break;
    case 'shock': if (!sim.power) sim.resetPower(); else sim.hullShock(); break;
    case 'extinguisher':
      if (player.carry) return sim.message('Your hands are full (Q to drop).', 'warn');
      player.carry = 'extinguisher'; sim.message('Fire extinguisher ready: hold E at a fire.');
      break;
    case 'fire': if (player.carry !== 'extinguisher') sim.message('Get a FIRE EXTINGUISHER (red, on the bulkheads).', 'warn'); break;
    case 'ladder':
      if (s.depth > 1.5) sim.message('The hatch is underwater - surface first (BLOW at the ballast panel).', 'warn');
      else { player.mode = 'bridge'; ext.look.yaw = 0; ext.look.pitch = 0; sim.message('On the bridge. Mouse to look, right-click to use binoculars, Esc to go below.'); }
      break;
    case 'chase': player.mode = 'chase'; sim.message('External camera. Mouse to orbit, wheel to zoom, Esc to return.'); break;
  }
}

function eat() {
  if (player.carry === 'food_cooked' || player.carry === 'food_burnt') {
    player.hunger = Math.min(100, player.hunger + (player.carry === 'food_cooked' ? 50 : 20));
    player.carry = null; sim.message('Delicious. Hunger restored.');
  } else sim.message('Nothing cooked to eat. Ask the cook!', 'warn');
}

// ------------------------------------------------------------------- input
addEventListener('keydown', (e) => {
  const k = e.key.toLowerCase();
  if (k === 'tab') e.preventDefault();
  if (keys.has(k)) return;
  keys.add(k);
  if (k === 'm') sound.toggle();
  if (k === 'escape') { leaveStation(); return; }
  if (player.mode === 'station' || player.mode === 'scope') { stationKey(k, true); return; }
  if (player.mode === 'walk') {
    if (k === 'e') {
      const it = nearest();
      if (it && it.kind === 'leak' && player.carry === 'wrench') { player.repairing = it.data; player.hold = 0; }
      else if (it && it.kind === 'fire' && player.carry === 'extinguisher') player.spraying = it.data;
      else interact(it);
    }
    if (k === 'q') drop();
    if (k === 'f') eat();
  }
});
addEventListener('keyup', (e) => { const k = e.key.toLowerCase(); keys.delete(k); if (k === 'e') { player.repairing = null; player.hold = 0; player.spraying = null; } });
addEventListener('mousemove', (e) => {
  if (document.pointerLockElement === canvas || player.mode === 'scope' || player.mode === 'bridge' || player.mode === 'chase') { mouseDX += e.movementX; mouseDY += e.movementY; }
});
addEventListener('wheel', (e) => { wheel += Math.sign(e.deltaY); });
canvas.addEventListener('mousedown', (e) => {
  if (player.mode === 'walk' && document.pointerLockElement !== canvas) canvas.requestPointerLock?.();
  if (player.mode === 'scope' && e.button === 0) sim.markTarget(sim.sub.heading + sim.sub.periscopeBearing);
  if (player.mode === 'bridge' && e.button === 2) ext.look.zoom = true;
});
canvas.addEventListener('mouseup', () => { ext.look.zoom = false; });
canvas.addEventListener('contextmenu', (e) => e.preventDefault());

function drop() {
  if (!player.carry) return;
  if (player.carry === 'wrench' && player.wrenchObj) {
    player.wrenchObj.position.set(player.pos.x, 0.02, player.pos.z); player.wrenchObj.visible = true;
    inn.interactables.push({ pos: player.wrenchObj.position.clone().setY(0.1), radius: 0.6, label: 'Pick up WRENCH', kind: 'wrench', data: player.wrenchObj });
  }
  if (player.carry === 'torpedo') sim.torpedoStock += 1;
  player.carry = null;
}

// -------------------------------------------------------------------- loop
let last = performance.now(), monitorTimer = 0, screenTimer = 0;
function loop(now) {
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  const w = innerWidth, h = innerHeight;
  if (canvas.width !== Math.floor(w * renderer.getPixelRatio()) || canvas.height !== Math.floor(h * renderer.getPixelRatio())) renderer.setSize(w, h, false);
  camera.aspect = w / h; camera.updateProjectionMatrix();

  if (!net || net.isHost) sim.update(dt);
  if (net) net.update(dt, player);
  continuousInput(dt);
  updatePlayer(dt);
  handleEvents();
  inn.update(sim, dt);
  ext.sync(sim, dt);
  updateGriddle(dt);
  updateHands(dt);
  sound.update(sim, player, dt);

  screenTimer -= dt;
  if (screenTimer <= 0) { screenTimer = 0.1; inn.drawScreens(sim); }
  monitorTimer -= dt;
  const m = player.mode;
  if (m === 'scope') { ext.periscopeCamera(sim, w / h); ext.render(); }
  else if (m === 'bridge') { ext.bridgeCamera(sim, w / h); ext.render(); }
  else if (m === 'chase') { ext.chaseCamera(sim, w / h); ext.render(); }
  else {
    if (monitorTimer <= 0) { monitorTimer = 0.3; inn.renderMonitors(ext, sim); }
    renderer.render(inn.scene, camera);
  }
  updateHud();
  requestAnimationFrame(loop);
}

// gauges, wheels and other instruments follow the simulation
const Z_AXIS = new THREE.Vector3(0, 0, -1);
function animateInstruments(dt) {
  const s = sim.sub, bp = inn.stations.ballast;
  if (!bp) return;
  const set = (o, axis, ang) => { if (!o) return; o.userData.rest ||= o.quaternion.clone(); o.quaternion.copy(o.userData.rest).multiply(new THREE.Quaternion().setFromAxisAngle(axis, ang)); };
  set(bp.parts.DepthGaugeNeedle, Z_AXIS, (Math.min(300, s.depth) / 300) * 4.7 - 2.35 + 1.4);
  set(bp.parts.PressureGaugeNeedle, Z_AXIS, s.air / 100 * 3 - 1.5);
  bp.spin = (bp.spin || 0) + dt * (s.valve === 'flood' ? 3 : s.valve === 'blow' ? -3 : 0);
  set(bp.parts.FloodValve, Z_AXIS, s.valve === 'flood' ? bp.spin : 0);
  set(bp.parts.BlowValve, Z_AXIS, s.valve === 'blow' ? bp.spin : 0);
  set(bp.parts.TrimLever1, new THREE.Vector3(0, 0, 1), s.planes * 0.5);
}

function continuousInput(dt) {
  const s = sim.sub;
  animateInstruments(dt);
  if (player.mode === 'station' && player.station === 'helm') {
    if (keys.has('a')) sim.setRudder(s.rudder + dt * 1.2);
    if (keys.has('d')) sim.setRudder(s.rudder - dt * 1.2);
    const js = inn.stations.helm?.parts?.Joystick;
    if (js) { js.rotation.x = -s.telegraph * 0.06; js.rotation.z = -s.rudder * 0.3; }
  }
  if (player.mode === 'station' && player.station === 'ballast') {
    if (keys.has('w')) sim.setPlanes(s.planes + dt * 1.0);
    if (keys.has('s')) sim.setPlanes(s.planes - dt * 1.0);
  }
  if (player.mode === 'scope') {
    s.periscopeBearing -= mouseDX * 0.0025 / s.periscopeZoom;
    if (keys.has('a')) s.periscopeBearing += dt * 0.8 / s.periscopeZoom;
    if (keys.has('d')) s.periscopeBearing -= dt * 0.8 / s.periscopeZoom;
    s.periscopePitch = Math.max(-0.35, Math.min(0.5, s.periscopePitch - mouseDY * 0.002 + (keys.has('w') ? dt * 0.4 : 0) - (keys.has('s') ? dt * 0.4 : 0)));
    if (wheel) s.periscopeZoom = Math.max(1, Math.min(6, s.periscopeZoom * (wheel < 0 ? 1.25 : 0.8)));
    if (keys.has('z')) s.periscopeZoom = Math.min(6, s.periscopeZoom + dt * 3);
    if (!s.periscopeUp) player.mode = 'station';
    const head = inn.stations.periscope?.parts?.Head;
    if (head) head.rotation.y = s.periscopeBearing;
  }
  if (player.mode === 'bridge') {
    ext.look.yaw -= mouseDX * 0.0025; ext.look.pitch = Math.max(-0.6, Math.min(0.6, ext.look.pitch - mouseDY * 0.0025));
    if (sim.sub.depth > 2) { player.mode = 'walk'; sim.message('Diving! You slid back down the ladder.', 'warn'); }
  }
  if (player.mode === 'chase') {
    ext.orbit.yaw -= mouseDX * 0.004; ext.orbit.pitch = Math.max(-0.8, Math.min(1.2, ext.orbit.pitch + mouseDY * 0.003));
    if (wheel) ext.orbit.dist = Math.max(20, Math.min(160, ext.orbit.dist * (wheel > 0 ? 1.12 : 0.89)));
  }
  mouseDX = mouseDY = 0; wheel = 0;
}

function updatePlayer(dt) {
  // hunger / stamina
  player.hunger = Math.max(0, player.hunger - dt * 100 / 480);
  const moving = player.mode === 'walk' && ['w', 'a', 's', 'd'].some((k) => keys.has(k));
  const sprint = moving && keys.has('shift') && player.stamina > 5 && player.carry !== 'torpedo';
  const regen = player.hunger > 0 && sim.sub.oxygen > 15 ? 7 : 1;
  player.stamina = Math.max(0, Math.min(100, player.stamina + (sprint ? -14 : regen) * dt));
  if (player.mode === 'walk') {
    player.yaw -= mouseDX * 0.0022; player.pitch = Math.max(-1.4, Math.min(1.4, player.pitch - mouseDY * 0.0022));
    let speed = sprint ? 4.6 : 2.6;
    if (player.carry === 'torpedo') speed = 1.5;
    if (player.hunger <= 0) speed *= 0.7;
    const room = inn.roomAt(player.pos.x);
    if (room >= 0 && sim.water[room] > 0.4) speed *= 0.6;
    const f = new THREE.Vector3(-Math.sin(player.yaw), 0, -Math.cos(player.yaw)), r = new THREE.Vector3(Math.cos(player.yaw), 0, -Math.sin(player.yaw));
    const mv = new THREE.Vector3();
    if (keys.has('w')) mv.add(f); if (keys.has('s')) mv.sub(f); if (keys.has('d')) mv.add(r); if (keys.has('a')) mv.sub(r);
    if (mv.lengthSq()) player.pos.addScaledVector(mv.normalize(), speed * dt);
    inn.collide(player.pos, 0.28, sim);
    const bob = moving ? Math.sin(performance.now() / (sprint ? 90 : 140)) * 0.03 : 0;
    camera.position.set(player.pos.x, EYE + bob, player.pos.z);
    camera.rotation.set(player.pitch, player.yaw, 0);
    // fighting a fire
    if (player.spraying) {
      sim.extinguish(player.spraying, dt);
      if (net && !net.isHost) net.send({ t: 'act', ev: { type: 'extinguish', id: player.spraying, dt } });
      if (!sim.fires.some((f) => f.id === player.spraying && !f.out)) player.spraying = null;
    }
    // repairing a leak
    if (player.repairing) {
      const it = inn.interactables.find((i) => i.kind === 'leak' && i.data === player.repairing);
      if (!it || it.pos.distanceTo(camera.position) > 2.4) { player.repairing = null; }
      else { player.hold += dt; if (player.hold > 2.5) { sim.fixLeak(player.repairing); player.repairing = null; player.hold = 0; sound.clunk(); } }
    }
  } else if (player.mode === 'station' && player.station) {
    const st = inn.stations[player.station];
    player.transition = Math.min(1, player.transition + dt * 2.2);
    const k = player.transition * player.transition * (3 - 2 * player.transition);
    const p = new THREE.Vector3(), q = new THREE.Quaternion();
    if (st.cam) { st.cam.getWorldPosition(p); st.cam.getWorldQuaternion(q); }
    camera.position.lerpVectors(player.camFrom, p, k);
    camera.quaternion.slerpQuaternions(player.quatFrom, q, k);
  }
  // the boat's motion and explosions shake the view
  player.shake = Math.max(0, player.shake - dt * 1.5);
  if (player.mode === 'walk' || player.mode === 'station') {
    camera.rotation.z += sim.sub.roll * 0.6;
    if (player.shake > 0) { camera.position.x += (Math.random() - 0.5) * player.shake * 0.08; camera.position.y += (Math.random() - 0.5) * player.shake * 0.08; }
  }
}

function handleEvents() {
  for (const ev of sim.events.splice(0)) {
    if (ev.type === 'message') pushMessage(ev.text, ev.level);
    if (ev.type === 'leak') { inn.spawnLeak(ev.leak); }
    if (ev.type === 'leakFixed') inn.fixLeakView(ev.leak);
    if (ev.type === 'fire') inn.spawnFire(ev.fire);
    if (ev.type === 'fireOut') inn.removeFire(ev.fire);
    if (ev.type === 'power') { sound.clunk(); if (!ev.on) flash('#000000'); }
    if (ev.type === 'hit') { player.shake = Math.min(2, 0.6 + ev.amount / 15); flash(); sound.boom(1); inn.flicker = 1.2; }
    if (ev.type === 'explosion') {
      ext.explosion(ev.x, -ev.depth, ev.z, ev.surface, ev.surface ? 1.2 : 0.8);
      if (ev.charge) { player.shake = Math.max(player.shake, Math.max(0, 1.2 - ev.dist / 80)); sound.boom(Math.max(0.2, 1 - ev.dist / 120)); }
      else sound.boom(0.5);
    }
    if (ev.type === 'ping') sound.ping();
    if (ev.type === 'chargeDropped') sound.noise(0.4, 500, 0.25, 'bandpass');
    if (ev.type === 'launch') sound.launch();
    if (ev.type === 'enemyLaunch') sound.alarm();
    if (ev.type === 'shock') { flash('#7fd9ff'); sound.zap(); }
    if (ev.type === 'grab') { player.shake = 1.5; sound.boom(0.6); }
    if (ev.type === 'lost') { setTimeout(() => { $('lost').classList.remove('hidden'); $('lostreason').textContent = `${ev.reason} Ships sunk: ${sim.score.sunk}.`; document.exitPointerLock?.(); }, 3500); }
    if (net && !ev.remote) net.event(ev);
  }
}

function flash(color = '#ffffff') { const f = $('flash'); f.style.background = color; f.style.transition = 'none'; f.style.opacity = 0.6; requestAnimationFrame(() => { f.style.transition = 'opacity .6s'; f.style.opacity = 0; }); }
function pushMessage(text, level = 'info') {
  const d = document.createElement('div'); d.className = level; d.textContent = text;
  $('messages').prepend(d);
  while ($('messages').children.length > 5) $('messages').lastChild.remove();
  setTimeout(() => d.remove(), 7000);
}

function updateHud() {
  const s = sim.sub;
  $('stamina').style.width = `${player.stamina}%`;
  $('hunger').style.width = `${player.hunger}%`;
  $('hullbar').style.width = `${s.hull}%`;
  const room = inn.roomAt(player.pos.x);
  const leaks = sim.leaks.filter((l) => !l.fixed);
  $('status').innerHTML = [
    `${room >= 0 ? ROOMS[room].label : 'BULKHEAD'}`,
    `DEPTH ${s.depth.toFixed(0)} m ${s.depth > TEST_DEPTH ? '<span style="color:#ff6b5b">CRUSH!</span>' : ''} · <span style="color:${(s.belowKeel ?? 99) < 15 ? '#ff6b5b' : 'inherit'}">${(s.belowKeel ?? 0).toFixed(0)} m under keel</span>`,
    `${TELEGRAPH_NAMES[s.telegraph]} · ${s.speed.toFixed(1)} m/s`,
    `HEADING ${sim.deg(s.heading)}° · RUDDER ${s.rudder > 0.05 ? 'PORT' : s.rudder < -0.05 ? 'STBD' : 'MID'}`,
    `BALLAST ${s.valve.toUpperCase()} ${(s.ballast * 100).toFixed(0)}% · PERISCOPE ${s.periscopeUp ? 'UP' : 'DOWN'}`,
    `BATTERY ${s.battery.toFixed(0)}% · O₂ <span style="color:${s.oxygen < 20 ? '#ff6b5b' : 'inherit'}">${s.oxygen.toFixed(0)}%</span>`,
    leaks.length ? `<span style="color:#ff6b5b">LEAKS: ${leaks.map((l) => ROOMS[l.room].label).join(', ')}</span>` : 'NO LEAKS',
    sim.water.some((w) => w > 0.05) ? `<span style="color:#64b5f6">FLOODING ${sim.water.map((w) => w.toFixed(1)).join(' / ')} m</span>` : '',
  ].filter(Boolean).join('<br>');
  $('score').innerHTML = `WAVE ${sim.score.wave} · SHIPS SUNK ${sim.score.sunk}<br><span style="color:#f2ead6;font-weight:500">${objective()}</span>`;
  $('carry').textContent = player.carry ? `CARRYING: ${player.carry.replace('food_', '').toUpperCase()} (Q drop${player.carry.startsWith('food_c') || player.carry === 'food_burnt' ? ', F eat' : ''})` : '';
  const it = nearest();
  $('prompt').textContent = it ? `[E] ${it.label}` : '';
  $('progress').classList.toggle('hidden', !player.repairing);
  $('progressfill').style.width = `${Math.min(100, player.hold / 2.5 * 100)}%`;
  const scope = player.mode === 'scope';
  $('scope').classList.toggle('hidden', !scope);
  if (scope) {
    const lock = sim.entities.find((e) => e.id === sim.weapons.lock && e.alive);
    $('scopeinfo').innerHTML = `BRG ${sim.deg(s.heading + s.periscopeBearing)}° · ZOOM ${s.periscopeZoom.toFixed(1)}x<br>${lock ? `LOCKED: ${lock.kind.toUpperCase()} ${Math.hypot(lock.x - s.x, lock.z - s.z).toFixed(0)} m` : 'CLICK TO MARK A TARGET'}`;
  }
  $('crosshair').classList.toggle('hidden', player.mode !== 'walk');
  if (net) {
    const st = { helm: 'HELM', chart: 'CHART', weapons: 'FIRE CONTROL', periscope: 'PERISCOPE', sonar: 'SONAR', ballast: 'BALLAST', griddle: 'GRIDDLE' };
    $('carry').title = '';
    $('crew').innerHTML = ['<b>CREW</b>', `${$('pname').value} (you) · ${st[player.station] || 'walking'}`,
      ...[...net.peers.values()].map((p) => `${p.name} · ${p.role.replace('_', ' ')} · ${st[p.station] || (p.carry ? 'carrying ' + p.carry : 'walking')}`)].join('<br>');
  }
  // labels over ships in the outside views
  const labels = $('labels');
  labels.innerHTML = '';
  if (m3d()) {
    for (const e of sim.entities) {
      if (!e.alive || !sim.contacts.has(e.id)) continue;
      const p = new THREE.Vector3(e.x, -(e.depth || 0) + 8, e.z).project(ext.camera);
      if (p.z > 1 || Math.abs(p.x) > 1 || Math.abs(p.y) > 1) continue;
      const d = document.createElement('div');
      d.className = 'tag' + (e.id === sim.weapons.lock ? ' locked' : '');
      d.style.left = `${(p.x + 1) / 2 * 100}%`; d.style.top = `${(1 - p.y) / 2 * 100}%`;
      d.textContent = `${e.kind.toUpperCase()} ${Math.hypot(e.x - s.x, e.z - s.z).toFixed(0)}m`;
      labels.appendChild(d);
    }
  }
}
const m3d = () => player.mode === 'chase' || player.mode === 'bridge';

function objective() {
  const s = sim.sub;
  const fires = sim.fires.filter((f) => !f.out);
  if (fires.length) return `▸ FIRE in the ${ROOMS[fires[0].room].label}: grab an extinguisher`;
  if (!sim.power) return '▸ Power out: reset the breakers (electrical cabinet, control room)';
  const open = sim.leaks.filter((l) => !l.fixed);
  if (open.length) return `▸ Fix ${open.length} leak${open.length > 1 ? 's' : ''} with a wrench (${ROOMS[open[0].room].label})`;
  if (sim.entities.some((e) => e.alive && e.attached)) return '▸ Squid on the hull! HULL SHOCK in the control room';
  if (sim.torpedoes.some((t) => t.owner !== 'player')) return '▸ Incoming torpedo: turn hard, noisemaker at fire control';
  if (player.hunger < 25) return '▸ You are starving: cook and eat (galley)';
  if (!sim.tubes.some((t) => t.loaded)) return '▸ All tubes empty: reload in the torpedo room';
  if (!sim.weapons.lock) return s.depth > PERISCOPE_DEPTH ? '▸ Rise to periscope depth (14 m) or use sonar to find targets' : '▸ Find a target: periscope or sonar, then mark it';
  return '▸ Target locked: flood, open door, arm and FIRE at fire control';
}

function applyTest(name) {
  // deterministic scenarios for automated screenshots
  const s = sim.sub;
  if (name === 'leaks') { sim.damage(18, 'Test depth charge', 0.4); player.pos.set(10.5, 0, 0.4); player.yaw = 0; }
  if (name === 'surface') { s.depth = 0; s.ballast = 0.3; }
  if (name === 'deep') { s.depth = 90; s.ballast = 0.5; }
  if (name === 'convoy') {
    for (const [i, e] of sim.entities.filter((q) => q.kind === 'freighter' || q.kind === 'frigate').entries()) {
      e.x = s.x + 380 + i * 90; e.z = s.z - 60 + i * 50; e.heading = Math.PI / 2;
    }
  }
  if (name === 'squid') {
    s.depth = 80; s.ballast = 0.5;
    const q = sim.add({ kind: 'squid', x: s.x - 6, z: s.z + 3, depth: 83, heading: 0, speed: 0, hp: 2, length: 13, state: 'stalk', grabTimer: 2, attached: true });
    sim.add({ kind: 'shark', x: s.x + 25, z: s.z - 12, depth: 78, heading: 2, speed: 5, hp: 2, length: 5, state: 'circle', ramTimer: 30 });
    player.mode = 'chase'; ext.orbit.dist = 40; ext.orbit.yaw = 2.2; ext.orbit.pitch = 0.15;
  }
}

document.querySelectorAll('#roles button').forEach((b) => b.addEventListener('click', () => start(b.dataset.role)));
if (PARAMS.get('role')) start(PARAMS.get('role'));
window.__game = { sim, player, inn, ext, enterStation, leaveStation, interact, keys, get net() { return net; } };
