// Deepwater Crew: main game - player, stations, hands, interactions, HUD, audio and the loop.
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Sim, TELEGRAPH_NAMES, ROOMS, R as RI, PERISCOPE_DEPTH, TEST_DEPTH, SNORKEL_DEPTH, ENGINE_FAULTS } from './sim.js';
import { Exterior } from './exterior.js';
import { Interior, dial } from './interior.js';
import { Sound } from './sound.js';
import { Net, poseAvatar } from './net.js';
import { STATUS_PAGES } from './consoles.js';
import { DROP } from './exterior.js';
const DROP_TEX = () => DROP;

const $ = (id) => document.getElementById(id);
const ROLE_FILE = { navigator: 'Navigator', weapons_officer: 'Gunner', torpedo_loader: 'Loader', cook: 'Cook' };
const PARAMS = new URLSearchParams(location.search);
// ?capture=1: the page does not run its own loop; a recorder calls __game.tick(dt) once per video frame
const CAPTURE = PARAMS.has('capture');
let clockMs = 0;
const nowMs = () => (CAPTURE ? clockMs : performance.now());
const EYE = 1.65;

const canvas = $('view');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.0;
renderer.outputColorSpace = THREE.SRGBColorSpace;
const loader = new GLTFLoader();

const sim = new Sim();
// player actions on shared machinery: run locally (instant feedback) and, as a guest, forward to the host
sim.act = (fn, ...args) => {
  const r = sim[fn](...args);
  if (net && !net.isHost) net.send({ t: 'act', ev: { type: 'call', fn, args } });
  return r;
};
const ext = new Exterior(renderer, loader);
const inn = new Interior(renderer, loader);
const sound = new Sound();
let net = null;

const camera = new THREE.PerspectiveCamera(72, 1, 0.03, 200);
camera.rotation.order = 'YXZ';
inn.scene.add(camera);

const player = {
  pos: new THREE.Vector3(14.6, 0, 0.6), yaw: Math.PI / 2, pitch: -0.05, stamina: 100, hunger: 100, health: 100, breath: 100,
  carry: null, mode: 'walk', station: null, role: 'navigator', hold: 0, shake: 0, transition: 0, swim: false, vy: 0,
  camFrom: new THREE.Vector3(), quatFrom: new THREE.Quaternion(), carriedObj: null, task: null, down: 0,
};
const CARRY_NAMES = { torpedo: 'TORPEDO', wrench: 'WRENCH', extinguisher: 'EXTINGUISHER', fuel_can: 'JERRYCAN', oil_can: 'OIL CAN', first_aid: 'FIRST-AID KIT',
  food_raw: 'RAW STEAK', food_cooked: 'COOKED STEAK', food_burnt: 'BURNT STEAK' };
const keys = new Set();
// pointer lock needs a user gesture; never let a refused request become an unhandled error
const lockPointer = () => { try { const p = canvas.requestPointerLock?.(); if (p && p.catch) p.catch(() => {}); } catch { /* ignore */ } };
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
  if (!CAPTURE) requestAnimationFrame(loop);
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
  fp = { rig, holder, sides: {} }; window.__fp = fp;
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
const CURL = { relax: [0.35, 0.3], grip: [1.15, 0.7], bar: [1.25, 0.85], knob: [1.0, 0.75], pinch: [0.9, 0.6], press: [1.3, 0.9], palm: [0.08, 0.1], carry: [1.0, 0.6], swim: [0.12, 0.15] };

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
const ROLL = { relax: 0.5, grip: 1.25, bar: 0.2, knob: -0.8, pinch: 0.9, press: 0.35, palm: 0.0, carry: Math.PI, swim: 1.45 };
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
  camera.updateWorldMatrix(true, false);
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
      if (poses[side] === 'bar') targets[side].y += 0.045;      // sideways bars (periscope handles): the wrist sits over the top
      if (stationInput.press && side === 'R') targets[side].add(camera.getWorldDirection(new THREE.Vector3()).multiplyScalar(0.03));
    }
    if (periHand.part && nowMs() < periHand.until) {
      targets.R = periHand.part.getWorldPosition(new THREE.Vector3()).add(camera.getWorldDirection(new THREE.Vector3()).multiplyScalar(-0.06));
      poses.R = periHand.pose;
    }
  }
  const bob = Math.sin(nowMs() / 160) * (keys.size ? 0.01 : 0.003);
  if (player.swim && player.mode === 'walk') {
    // breaststroke: reach forward together, sweep out and back, tuck in, glide
    const moving = ['w', 'a', 's', 'd', ' ', 'c'].some((k) => keys.has(k));
    player.stroke = (player.stroke || 0) + dt * (moving ? 1.25 : 0.45);
    const ph = player.stroke % 1;
    const K = [[0.0, 0.06, -0.12, -0.62], [0.35, 0.42, -0.18, -0.48], [0.62, 0.3, -0.36, -0.2], [0.82, 0.1, -0.3, -0.3], [1.0, 0.06, -0.12, -0.62]];
    let a = K[0], b = K[1];
    for (let i = 0; i < K.length - 1; i++) if (ph >= K[i][0] && ph <= K[i + 1][0]) { a = K[i]; b = K[i + 1]; }
    const t = (ph - a[0]) / Math.max(1e-3, b[0] - a[0]), e = t * t * (3 - 2 * t);
    const x = a[1] + (b[1] - a[1]) * e, y = a[2] + (b[2] - a[2]) * e, z = a[3] + (b[3] - a[3]) * e;
    targets.L = camLocal(-x, y, z); targets.R = camLocal(x, y, z); poses.L = poses.R = 'swim';
  }
  if (player.carry === 'torpedo') { targets.L ||= camLocal(-0.22, -0.42 + bob, -0.55); targets.R ||= camLocal(0.22, -0.42 + bob, -0.55); poses.L = poses.R = 'carry'; }
  if (player.carry === 'wrench') { targets.R ||= camLocal(0.24, -0.3 + bob, -0.42); poses.R = 'grip'; }
  if (player.carry && player.carry.startsWith('food')) { targets.L ||= camLocal(-0.2, -0.3 + bob, -0.4); poses.L = 'palm'; }
  if (player.carry === 'extinguisher') { targets.L ||= camLocal(-0.12, -0.36 + bob, -0.5); targets.R ||= camLocal(0.14, -0.3 + bob, -0.48); poses.L = poses.R = 'grip'; }
  if (player.carry === 'fuel_can' || player.carry === 'oil_can') { targets.R ||= camLocal(0.22, -0.42 + bob, -0.42); poses.R = 'grip'; }
  if (player.carry === 'first_aid') { targets.L ||= camLocal(-0.2, -0.36 + bob, -0.42); poses.L = 'grip'; }
  if (player.task) {   // pouring / topping up / fixing: the hand goes to the job
    const it = player.task.it;
    if (it) { targets.R = it.pos.clone(); poses.R = 'grip'; if (player.carry === 'fuel_can') targets.L = it.pos.clone().add(new THREE.Vector3(0, 0.1, 0)); }
  }
  if (player.repairing) targets.R = inn.interactables.find((i) => i.kind === 'leak' && i.data === player.repairing)?.pos.clone() || targets.R;
  // reaching: when a control is further than arm's reach the shoulder joint slides towards it (the torso stays
  // put, and the shoulder stays below the bottom of the view), like leaning in over a desk
  const tanHalf = Math.tan(THREE.MathUtils.degToRad(camera.fov / 2));
  for (const sd of ['L', 'R']) {
    const S = fp.sides[sd]; if (!S) continue;
    if (!S.sh0) { S.upPos0 = S.up.position.clone(); fp.rig.updateMatrixWorld(true); S.sh0 = fp.holder.worldToLocal(S.up.getWorldPosition(new THREE.Vector3())); S.lean = new THREE.Vector3(); }
    const off = _v2.set(0, 0, 0);
    if (targets[sd]) {
      const tl = camera.worldToLocal(targets[sd].clone()), reach = 0.94 * (S.L1 + S.L2);
      for (let it = 0; it < 4; it++) {
        const sh = _v1.copy(S.sh0).add(off), d = tl.distanceTo(sh);
        if (d <= reach) break;
        off.addScaledVector(tl.clone().sub(sh).normalize(), d - reach);
        const y = S.sh0.y + off.y, maxY = -(tanHalf + 0.5) * Math.max(0, -(S.sh0.z + off.z)) - 0.08;
        if (y > maxY) off.y += maxY - y;
      }
      off.clampLength(0, 0.8);
    }
    S.lean.lerp(off, Math.min(1, dt * 6));
    const w = fp.holder.localToWorld(S.sh0.clone().add(S.lean));
    S.up.position.copy(S.up.parent.worldToLocal(w));
  }
  fp.rig.updateMatrixWorld(true);
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
    const turn = player.repairing ? Math.sin(nowMs() / 90) * 0.6 : 0;
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
  // jerrycans, oil cans and first-aid kits: carry the real prop in the hand
  const held = ['fuel_can', 'oil_can', 'first_aid'].includes(player.carry) ? player.carriedObj : null;
  if (held !== fp.heldSrc) {
    if (fp.held) camera.remove(fp.held);
    fp.held = held ? held.clone() : null; fp.heldSrc = held;
    if (fp.held) { fp.held.visible = true; fp.held.position.set(0, 0, 0); fp.held.traverse((o) => { if (o.isMesh) { o.renderOrder = 2; o.frustumCulled = false; } }); camera.add(fp.held); }
  }
  if (fp.held) {
    const pour = player.task && (player.task.kind === 'filler' || player.task.kind === 'oil');
    if (player.carry === 'first_aid') { fp.held.position.set(-0.2, -0.42 + bob, -0.45); fp.held.rotation.set(0.3, 0.4, 0); }
    else { fp.held.position.set(0.2, -0.62 + bob + (pour ? 0.18 : 0), -0.46); fp.held.rotation.set(pour ? -1.1 : 0, Math.PI * 0.5, pour ? 0.3 : 0); }
  }
}

// --------------------------------------------------------------- stations
const HELP = {
  helm: ['HELM', 'W / S   engine telegraph (ahead / astern)\nA / D   rudder (hold)    X centre rudder\nT       autopilot along the chart route\nC       captain\'s external 3D view\nEsc     leave'],
  chart: ['CHART TABLE - ROUTE PLANNING', 'W A S D  move the cursor (CURSOR stick)\nSpace   ADD WPT at the cursor    Backspace  DEL WPT\nZ / X or wheel  zoom      R  cursor back to the boat\nContacts: red = warships, green = merchants, purple = creatures.\nThe helm screen shows the course to the next waypoint;\nthe helmsman presses T for the autopilot.\nC external view    Esc leave'],
  status: ['SHIP STATUS', '1-8 or Q / E  page: NOISE  AIR  ENGINES  POWER\n                    LEAKS  FLOOD  FIRE  CREW\nA page key blinks red when that system needs help.\nG  GENERAL ALARM (flip the guard, press)\nEsc leave'],
  ballast: ['BALLAST & DIVE PLANES', 'F  FLOOD tanks (dive)     B  BLOW tanks (surface)\nH  HOLD (close valves)\nW / S  planes rise / dive (hold)    X level planes\nPeriscope depth is ' + PERISCOPE_DEPTH + ' m. Hull limit ' + TEST_DEPTH + ' m.\nEsc leave'],
  periscope: ['PERISCOPE', 'A / D or mouse  train left & right (you turn with it)\nW / S  tilt (TILT knob)    Wheel / Z X  zoom (ZOOM knob)\n1-8 or Q / E  move the tag slider\nSpace / Click  MARK the contact in the crosshair\nC  CLEAR that tag    V or right-click  eye to the eyepiece\nR  raise / lower      Esc  leave'],
  sonar: ['SONAR', 'A / D  turn the TRAIN wheel: aim the hydrophone and listen\nThe SIGNAL meter rises when something is out there\nW / S  GAIN slider    L  LOCK what you hear for fire control\nP  active PING (shows everything, but they hear you)\nN  next known contact      Esc leave'],
  mission: ['MISSION MAP', 'The big map: islands, shallows, contacts, tags and the route.\nThe MISSION board: goal, next action, stealth, crew.\nBOW and STERN cameras on the left.\nZ / X or wheel  zoom the map    Esc leave'],
  cameras: ['CAMERAS', '1-6 or Q / E  TORPEDO  BATTERY  ENGINES  GALLEY  MESS  QUARTERS\nWatch every compartment from the control room.\nEsc leave'],
  weapons: ['FIRE CONTROL', '1-4 or Q / E (TUBE - / +)  select tube\nF  flood / drain tube     O  open / close outer door\nK  ARM key                G  lift guard\nA / D  AIM stick: torpedo course when nothing is locked\nSPACE  FIRE           N  DECOY (noisemaker)\nEsc leave'],
  griddle: ['GRIDDLE', 'P  power on / off\nE  put raw food on / take cooked food off\nCook ~8 s. Leave it too long and it burns!\nEsc leave'],
};
for (let n = 1; n <= 4; n++) HELP[`tube${n}`] = [`TUBE ${n} BREECH`, 'E  open / close the breech door\nCarry a torpedo here with the door open to load\nEsc leave'];
HELP.engines = ['ENGINE CONTROLS', `1 / 2   start / stop DIESEL 1 / 2\nThe diesels charge the battery but need air:\nsurface or snorkel at ${SNORKEL_DEPTH} m or shallower.\nWatch TEMP (coolant valves on the engines),\nOIL (oil cans) and the DAY TANK (fuel pump).\nEsc leave`];
HELP.fuel = ['FUEL TRANSFER PUMP', 'CLICK (or W / S)  pump the lever up and down\nEvery stroke lifts diesel from the main bunkers\ninto the day tank (sight glass on the left).\nNo fuel left? Pour JERRYCANS into the filler on top.\nEsc leave'];
for (const n of [1, 2]) HELP[`motor${n}`] = [`DIESEL ${n} PANEL`, `P or POWER  start / stop this diesel\nThe screen shows its revs, load and warnings (HOT, OIL,\nCOOLANT, INJECTOR, FUEL, FIRE).\nT  TALK: report to the control room\nEsc leave`];
HELP.switchboard = ['MAIN SWITCHBOARD', '1 - 8   close / open the breakers\nM or CLICK   MAIN BREAKER (restores power once\n        every tripped breaker is closed)\nEsc leave'];
for (const r of [RI.TorpedoRoom, RI.BatteryRoom, RI.EngineRoom]) HELP[`bilge${r}`] = [`BILGE PUMP - ${ROOMS[r].label}`, 'CLICK (or W / S)  pump the handle up and down\nEvery stroke lifts water out of this compartment.\nFix the leaks first or you will never keep up!\nEsc leave'];
const stationInput = { press: false };

function enterStation(key) {
  const st = inn.stations[key];
  if (!st) return;
  player.mode = 'station'; player.station = key; player.transition = 0;
  camera.getWorldPosition(player.camFrom); camera.getWorldQuaternion(player.quatFrom);
  $('station').classList.remove('hidden');
  $('stationtitle').textContent = HELP[key][0];
  $('stationhelp').textContent = HELP[key][1];
  $('station').classList.remove('collapsed'); player.helpUntil = nowMs() + 9000;
  $('crosshair').classList.add('hidden');
  if (document.pointerLockElement) document.exitPointerLock();
  if (key === 'periscope' && !sim.sub.periscopeUp) sim.togglePeriscope();
  if (net) net.claim(key);
  player.swim = false;
}

function leaveStation() {
  if (player.mode === 'lie') { player.mode = 'walk'; $('crosshair').classList.remove('hidden'); lockPointer(); return; }
  if (player.mode === 'bridge' || player.mode === 'chase') { player.mode = player.station ? 'station' : 'walk'; if (!player.station) $('crosshair').classList.remove('hidden'); return; }
  player.mode = 'walk'; player.station = null;
  $('station').classList.add('hidden'); $('scope').classList.add('hidden');
  $('crosshair').classList.remove('hidden');
  lockPointer();
  if (net) net.claim(null);
}

function stationKey(k, down) {
  const s = sim.sub, key = player.station;
  if (!down) return;
  if (k === 'i') { const c = $('station').classList.toggle('collapsed'); player.helpUntil = c ? 0 : Infinity; return; }
  if (k === 'c' && (key === 'helm' || key === 'chart')) { player.mode = 'chase'; return; }
  if (key === 'helm') {
    if (k === 'w') { sim.setTelegraph(s.telegraph + 1); sound.bell(); }
    if (k === 's') { sim.setTelegraph(s.telegraph - 1); sound.bell(); }
    if (k === 'x') { sim.setRudder(0); if (sim.autopilot) sim.act('setAutopilot', false); }
    if (k === 't') sim.act('setAutopilot', !sim.autopilot);
    sound.click();
  } else if (key === 'ballast') {
    if (k === 'f') { if (s.valve !== 'flood') sound.klaxon(); sim.setValve('flood'); }
    if (k === 'b') sim.setValve('blow');
    if (k === 'h') sim.setValve('hold');
    if (k === 'x') sim.setPlanes(0);
    sound.click();
  } else if (key === 'periscope') {
    if (k === 'r') { sim.togglePeriscope(); if (!sim.sub.periscopeUp) player.mode = 'station'; }
    if (k === ' ') periscopeMark();
    if (k === 'c' || k === 'backspace') periscopeClear();
    if (k.length === 1 && '12345678'.includes(k)) periscopeTag(+k);
    if (k === 'q') periscopeTag(inn.periTag - 1);
    if (k === 'e') periscopeTag(inn.periTag + 1);
    if (k === 'v' && sim.sub.periscopeUp) player.mode = player.mode === 'scope' ? 'station' : 'scope';
  } else if (key === 'sonar') {
    if (k === 'p') { sim.sonarPing(); inn.pressed = { ...inn.pressed, ping: inn.time + 0.25 }; reach('PingButton'); }
    if (k === 'l') { sim.act('lockBeam'); inn.pressed = { ...inn.pressed, lock: inn.time + 0.25 }; reach('LockButton'); }
    if (k === 'n') {
      const ids = [...sim.contacts.keys()].filter((id) => sim.entities.some((e) => e.id === id && e.alive));
      if (ids.length) { const i = (ids.indexOf(sim.weapons.lock) + 1) % ids.length; sim.weapons.lock = ids[i]; const e = sim.entities.find((q) => q.id === ids[i]); sim.message(`Fire control locked on ${e.kind.toUpperCase()}.`); }
    }
  } else if (key === 'weapons') {
    const w = sim.weapons;
    if (k.length === 1 && '1234'.includes(k)) w.selected = +k;
    if (k === 'q') { w.selected = ((w.selected + 2) % 4) + 1; inn.pressed = { ...inn.pressed, tubedown: inn.time + 0.2 }; reach('TubeDown'); }
    if (k === 'e') { w.selected = (w.selected % 4) + 1; inn.pressed = { ...inn.pressed, tubeup: inn.time + 0.2 }; reach('TubeUp'); }
    if (k === 'f') sim.floodTube(w.selected);
    if (k === 'o') sim.openOuter(w.selected);
    if (k === 'k') w.armed = !w.armed;
    if (k === 'g') w.guardOpen = !w.guardOpen;
    if (k === 'n') { sim.countermeasure(); inn.pressed = { ...inn.pressed, decoy: inn.time + 0.25 }; reach('DecoyButton'); }
    if (k === ' ') { stationInput.press = true; later(200, () => { stationInput.press = false; }); sim.fire(); }
    sound.click();
  } else if (key === 'status') {
    const i = STATUS_PAGES.indexOf(inn.statusPage);
    let n = -1;
    if (k.length === 1 && '12345678'.includes(k)) n = +k - 1;
    if (k === 'q') n = (i + 7) % 8;
    if (k === 'e') n = (i + 1) % 8;
    if (n >= 0) { inn.statusPage = STATUS_PAGES[n]; inn.pressed = { ...inn.pressed, [`page${n}`]: inn.time + 0.2 }; reach(`Page${n + 1}`); sound.click(); }
    if (k === 'g') {
      sim.act('setAlarm', !sim.alarm); inn.pressed = { ...inn.pressed, alarm: inn.time + 0.25 }; reach('AlarmButton', 'palm', 700);
      if (sim.alarm) sound.klaxon(); else sound.click();
    }
  } else if (key === 'cameras') {
    let n = -1;
    if (k.length === 1 && '123456'.includes(k)) n = +k - 1;
    if (k === 'q') n = (inn.cctvSel + 5) % 6;
    if (k === 'e') n = (inn.cctvSel + 1) % 6;
    if (n >= 0) { inn.cctvSel = n; reach(`Cam${n + 1}`); sound.click(); cctvTimer = 0; }
  } else if (key === 'mission') {
    if (k === 'z') inn.mapZoom = Math.min(4, inn.mapZoom * 1.25);
    if (k === 'x') inn.mapZoom = Math.max(0.5, inn.mapZoom / 1.25);
    if (k === 'z' || k === 'x') reach('MapZoom', 'knob');
  } else if (key.startsWith('motor')) {
    const i = +key.slice(5) - 1;
    if (k === 'p' || k === ' ') { sim.act('toggleEngine', i); inn.pressed = { ...inn.pressed, [`engine${i}`]: inn.time + 0.25 }; reach('PowerButton'); sound.click(); }
    if (k === 't') {
      const e = sim.engines[i];
      sim.message(`DIESEL ${i + 1} to control room: ${e.fault ? 'FAULT - ' + ENGINE_FAULTS[e.fault] : e.running ? `running ${e.rpm.toFixed(0)} rpm, ${e.temp.toFixed(0)} degrees` : 'stopped'}.`, 'alert');
      reach('TalkButton'); sound.bell();
    }
  } else if (key === 'chart') {
    const c = inn.chartCursor;
    if (k === ' ') { sim.act('addWaypoint', s.x + c.x, s.z + c.z); inn.pressed = { ...inn.pressed, addwpt: inn.time + 0.2 }; reach('AddWaypoint'); sound.click(); }
    if (k === 'backspace' || k === 'delete') { sim.act('delWaypoint'); inn.pressed = { ...inn.pressed, delwpt: inn.time + 0.2 }; reach('DelWaypoint'); sound.click(); }
    if (k === 'r') { c.x = 0; c.z = 0; }
  } else if (key === 'griddle') {
    if (k === 'p') { griddle.power = !griddle.power; sim.message(griddle.power ? 'Griddle on.' : 'Griddle off.'); }
    if (k === 'e') griddleUse();
  } else if (key === 'engines') {
    if (k === '1' || k === '2') { const i = +k - 1; sim.act('toggleEngine', i); inn.pressed = { ...inn.pressed, [`engine${i}`]: inn.time + 0.25 }; sound.click(); }
  } else if (key === 'fuel' || key.startsWith('bilge')) {
    if (k === 'w' || k === 's') pumpStroke(k === 'w' ? 1 : -1);
  } else if (key === 'switchboard') {
    if ('12345678'.includes(k) && k.length === 1) { const b = +k - 1; sim.act('setBreaker', b, !sim.breakers[b]); sound.clunk(); }
    if (k === 'm' || k === ' ') { sim.act('mainBreaker'); sound.clunk(); player.shake = 0.3; }
  } else if (key.startsWith('tube')) {
    const n = +key.slice(4);
    if (k === 'e') {
      if (player.carry === 'torpedo' && sim.tubes[n - 1].breechOpen && sim.loadTube(n)) { player.carry = null; sound.clunk(); }
      else if (sim.toggleBreech(n)) sound.clunk();
    }
  }
  if (net) net.sendControls();
}

// periscope controls: tag slider, MARK and CLEAR buttons (the right hand reaches for them)
const periHand = { part: null, until: 0 };
// the right hand goes to a control on the current station for a moment (button presses, slider moves)
function reach(name, pose = 'press', ms = 450) { periHand.part = inn.stations[player.station]?.parts?.[name] || null; periHand.pose = pose; periHand.until = nowMs() + ms; }
const periscopeReach = reach;
function periscopeTag(n) {
  inn.periTag = Math.max(1, Math.min(8, n)); periscopeReach('TagSlider', 'pinch'); sound.click();
}
function periscopeMark() {
  const s = sim.sub;
  if (!s.periscopeUp) return sim.message('Raise the periscope first (R).', 'warn');
  inn.pressed = { ...inn.pressed, mark: inn.time + 0.2 }; periscopeReach('MarkButton'); sound.clunk();
  sim.act('tagTarget', inn.periTag, s.heading + s.periscopeBearing);
}
function periscopeClear() {
  inn.pressed = { ...inn.pressed, clear: inn.time + 0.2 }; periscopeReach('ClearButton'); sound.click();
  sim.act('clearTag', inn.periTag);
}

// pump levers: each click throws the handle to the other end; a completed throw is one stroke
function pumpStroke(dir) {
  const key = player.station;
  const L = (inn.levers[key] ||= { target: -0.42, angle: -0.42 });
  const want = dir ? (dir > 0 ? -0.42 : 0.42) : (L.target < 0 ? 0.42 : -0.42);
  if (want === L.target) return;
  const now = nowMs();
  if (now - (L.last || 0) < 170) return;          // the handle has to travel: no machine-gun clicking
  L.last = now;
  L.target = want;
  stationInput.press = true; later(150, () => { stationInput.press = false; });
  later(120, () => {
    if (key === 'fuel') sim.act('fuelStroke');
    else sim.act('bilgeStroke', +key.slice(5));
    sound.pump(key === 'fuel');
  }, 120);
  player.stamina = Math.max(0, player.stamina - 0.6);
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
    case 'shock': sim.hullShock(); break;
    case 'vent': sim.act('setVent', it.data, !sim.vents[it.data]); sound.clunk(); break;
    case 'engine_button': sim.act('toggleEngine', it.data); sound.click(); break;
    case 'coolant': sim.act('setCoolant', it.data, !sim.engines[it.data].coolant); sound.clunk(); break;
    case 'oil': if (player.carry !== 'oil_can') sim.message('You need an OIL CAN (stores, battery room / engine room).', 'warn'); break;
    case 'filler': if (player.carry !== 'fuel_can') sim.message('Bring a JERRYCAN to pour into the day tank - or pump fuel up with the transfer pump.', 'warn'); break;
    case 'engine_fault':
      if (sim.engines[it.data].fault !== 'injector') sim.message(sim.engines[it.data].fault ? `Diesel ${it.data + 1}: ${ENGINE_FAULTS[sim.engines[it.data].fault]} - no injector work needed.` : `Diesel ${it.data + 1} injectors look fine.`);
      else if (player.carry !== 'wrench') sim.message('You need a WRENCH to fix the injectors.', 'warn');
      break;
    case 'pickup': {
      if (player.carry) return sim.message('Your hands are full (Q to drop).', 'warn');
      const { obj, item } = it.data;
      obj.visible = false; player.carry = item; player.carriedObj = obj;
      inn.interactables = inn.interactables.filter((q) => q !== it);
      sim.message({ fuel_can: 'Jerrycan of diesel: pour it into the DAY TANK filler (engine room).', oil_can: 'Oil can: top up a diesel at its OIL FILLER.', first_aid: 'First-aid kit: press F to patch yourself up.' }[item]);
      break;
    }
    case 'medcab':
      inn.cabinetOpen = inn.time + 2.5;
      if (player.carry) return sim.message('Your hands are full (Q to drop).', 'warn');
      if (it.data.userData.kits <= 0) return sim.message('The medical cabinet is empty.', 'warn');
      it.data.userData.kits -= 1;
      const tpl = inn.root.children.find((o) => /^FirstAidKit/.test(o.name));
      player.carry = 'first_aid'; player.carriedObj = tpl ? tpl.clone() : null;   // a fresh kit, not one from the shelf
      sim.message(`Took a first-aid kit (${it.data.userData.kits} left). Press F to use it.`);
      break;
    case 'medbed':
      player.mode = 'lie'; player.station = null; player.transition = 0;
      camera.getWorldPosition(player.camFrom); camera.getWorldQuaternion(player.quatFrom);
      sim.message('Resting on the med bed... (E or Esc to get up)');
      break;
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
  if (player.carry === 'first_aid') {
    player.health = Math.min(100, player.health + 45); player.carry = null; player.carriedObj = null;
    sim.message('Patched up with the first-aid kit. +45 health.'); return;
  }
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
  if (k === 'tab') { toggleHandbook(); return; }
  if (!$('handbook').classList.contains('hidden') && k === 'escape') { toggleHandbook(false); return; }
  if (k === 'm') sound.toggle();
  if (player.mode === 'down') return;
  if (k === 'escape' || (player.mode === 'lie' && k === 'e')) { leaveStation(); return; }
  if (player.mode === 'station' || player.mode === 'scope') { stationKey(k, true); return; }
  if (player.mode === 'walk') {
    if (k === 'e') {
      const it = nearest();
      if (it && it.kind === 'leak' && player.carry === 'wrench') { player.repairing = it.data; player.hold = 0; }
      else if (it && it.kind === 'fire' && player.carry === 'extinguisher') player.spraying = it.data;
      else if (it && it.kind === 'filler' && player.carry === 'fuel_can') player.task = { kind: 'filler', it, t: 0, need: 2.2 };
      else if (it && it.kind === 'oil' && player.carry === 'oil_can') player.task = { kind: 'oil', it, t: 0, need: 2.0 };
      else if (it && it.kind === 'engine_fault' && player.carry === 'wrench' && sim.engines[it.data].fault === 'injector') player.task = { kind: 'injector', it, t: 0, need: 3.0 };
      else interact(it);
    }
    if (k === 'q') drop();
    if (k === 'f') eat();
  }
});
addEventListener('keyup', (e) => { const k = e.key.toLowerCase(); keys.delete(k); if (k === 'e') { player.repairing = null; player.hold = 0; player.spraying = null; player.task = null; } });
addEventListener('mousemove', (e) => {
  if (document.pointerLockElement === canvas || player.mode === 'scope' || player.mode === 'bridge' || player.mode === 'chase'
    || (player.mode === 'station' && ['periscope', 'chart', 'weapons', 'sonar'].includes(player.station) && e.buttons & 1)) { mouseDX += e.movementX; mouseDY += e.movementY; }
});
addEventListener('wheel', (e) => { wheel += Math.sign(e.deltaY); });
// clicking a control on a station panel works like its key (page keys, alarm, waypoint keys, FIRE, ARM, tube switches...)
const CLICK_KEYS = { AlarmButton: 'g', AlarmGuard: 'g', AddWaypoint: ' ', DelWaypoint: 'backspace', FireButton: ' ', ArmKey: 'k',
  FireGuard: 'g', DecoyButton: 'n', MarkButton: ' ', ClearButton: 'c', Start1: '1', Start2: '2' };
Object.assign(CLICK_KEYS, { PingButton: 'p', LockButton: 'l', TubeUp: 'e', TubeDown: 'q', PowerButton: 'p', TalkButton: 't', MapZoom: 'z' });
for (let n = 1; n <= 6; n++) CLICK_KEYS[`Cam${n}`] = String(n);
for (let n = 1; n <= 8; n++) CLICK_KEYS[`Page${n}`] = String(n);
for (let n = 1; n <= 4; n++) CLICK_KEYS[`TubeSelect${n}`] = String(n);
const raycaster = new THREE.Raycaster();
function controlUnder(e) {
  const st = inn.stations[player.station]; if (!st || player.transition < 1) return null;
  st.partNames ||= new Map(Object.entries(st.parts).map(([k, v]) => [v, k]));
  const r = canvas.getBoundingClientRect();
  raycaster.setFromCamera(new THREE.Vector2(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1), camera);
  const hit = raycaster.intersectObject(st.root, true)[0];
  for (let o = hit?.object; o && o !== st.root; o = o.parent) { const nm = st.partNames.get(o); if (nm && CLICK_KEYS[nm]) return nm; }
  // small controls sit in their panels: otherwise take the nearest one within a few pixels of the click
  let best = null, bd = Math.max(18, r.height * 0.035);
  for (const [nm, o] of Object.entries(st.parts)) {
    if (!CLICK_KEYS[nm]) continue;
    const q = o.getWorldPosition(new THREE.Vector3()).project(camera);
    const d = Math.hypot((q.x + 1) / 2 * r.width - (e.clientX - r.left), (1 - q.y) / 2 * r.height - (e.clientY - r.top));
    if (q.z < 1 && d < bd) { bd = d; best = nm; }
  }
  return best;
}
canvas.addEventListener('mousedown', (e) => {
  if (player.mode === 'walk' && document.pointerLockElement !== canvas) lockPointer();
  if (player.mode === 'station' && e.button === 0) {
    const nm = controlUnder(e);
    if (nm) { stationKey(CLICK_KEYS[nm], true); return; }
  }
  if (player.mode === 'station' && e.button === 0 && (player.station === 'fuel' || player.station?.startsWith('bilge'))) pumpStroke(0);
  if (player.mode === 'station' && e.button === 0 && player.station === 'switchboard') { sim.act('mainBreaker'); sound.clunk(); }
  if ((player.mode === 'scope' || (player.mode === 'station' && player.station === 'periscope')) && e.button === 0) periscopeMark();
  if (player.station === 'periscope' && e.button === 2 && sim.sub.periscopeUp) player.mode = player.mode === 'scope' ? 'station' : 'scope';
  if (player.mode === 'bridge' && e.button === 2) ext.look.zoom = true;
});
canvas.addEventListener('mouseup', () => { ext.look.zoom = false; });
// a pointer lock asked for while walking can arrive after you've stepped up to a station: let the mouse go again
document.addEventListener('pointerlockchange', () => { if (document.pointerLockElement && player.mode !== 'walk') document.exitPointerLock(); });
canvas.addEventListener('contextmenu', (e) => e.preventDefault());

// ------------------------------------------------------------------ TAB handbook: how the boat works
const HANDBOOK = `<h1>CREW HANDBOOK</h1>
<p class="lead">Everything on the boat is a real control. Walk up to a station and press <kbd>E</kbd>; your hands go to its controls.
Use the keys shown in the corner, or click the buttons on the panel. Any crew member can run any station. <kbd>TAB</kbd> closes this book.</p>
<section><h2>HOW A PATROL GOES</h2><ol>
<li><b>Dive</b> at the BALLAST panel to periscope depth (${PERISCOPE_DEPTH} m).</li>
<li><b>Find</b> ships with the PERISCOPE (MARK them with a tag number) or listen on SONAR.</li>
<li><b>Plan</b> a route at the CHART TABLE; the helmsman follows it or turns on the autopilot.</li>
<li><b>Attack</b> at FIRE CONTROL: choose a tube, flood it, open the outer door, turn the ARM key, lift the guard, FIRE.</li>
<li><b>Reload</b> in the torpedo room: carry a torpedo from the racks to an open breech.</li>
<li><b>Survive</b>: stay quiet (SHIP STATUS - NOISE), fix leaks, pump water, fight fires, keep the power and air up.</li></ol></section>
<section><h2>HELM (navigation console)</h2><p>Engine telegraph <kbd>W</kbd>/<kbd>S</kbd>, rudder <kbd>A</kbd>/<kbd>D</kbd> (the steering wheel turns with it), centre <kbd>X</kbd>.
<kbd>T</kbd> autopilot steers along the chart route. The round scope shows contacts, the route and the course to the next waypoint.</p></section>
<section><h2>BALLAST &amp; TRIM</h2><p><kbd>F</kbd> flood the tanks to dive, <kbd>B</kbd> blow them to surface, <kbd>H</kbd> hold.
Dive planes <kbd>W</kbd>/<kbd>S</kbd>. The DIVE PROFILE screen shows the sea floor ahead, the periscope depth and the hull limit (${TEST_DEPTH} m).</p></section>
<section><h2>PERISCOPE</h2><p>Only at ${PERISCOPE_DEPTH} m or shallower. Train it with the handles (<kbd>A</kbd>/<kbd>D</kbd> or drag), ZOOM and TILT knobs,
pick a tag 1-8 on the slider and press MARK on the ship in the crosshair. The TARGET IDENTIFICATION screen names it.</p></section>
<section><h2>SONAR</h2><p>Turn the TRAIN wheel (<kbd>A</kbd>/<kbd>D</kbd>) to aim the hydrophone and listen: the SIGNAL meter rises when a ship is out
there, and after a moment it shows up as a contact. <kbd>W</kbd>/<kbd>S</kbd> GAIN, <kbd>L</kbd> LOCK what you hear for fire control.
<kbd>P</kbd> sends an active PING: it shows everything around you, but every enemy hears it.</p></section>
<section><h2>MISSION MAP</h2><p>The big wall screen: islands, shallows, every contact, periscope tags and the route. Beside it the MISSION board
(goal, next action, how loud you are, whether you have been detected, the crew) and the BOW and STERN cameras.</p></section>
<section><h2>CAMERAS</h2><p>The CCTV console shows any compartment: TORPEDO, BATTERY, ENGINES, GALLEY, MESS, QUARTERS (<kbd>1</kbd>-<kbd>6</kbd>).
Check on a fire or the flooding without leaving the control room.</p></section>
<section><h2>ISLANDS</h2><p>The sea is dotted with islands and a shoal. Ships steer round them; you run aground if you try to sail through,
and a rock wall stops a deep boat too. Torpedoes that hit land just blow up on the rocks. Use them to hide.</p></section>
<section><h2>FIRE CONTROL</h2><p>Tube switches 1-4 or TUBE +/- (<kbd>Q</kbd>/<kbd>E</kbd>), <kbd>F</kbd> flood, <kbd>O</kbd> outer door, <kbd>K</kbd> ARM key, <kbd>G</kbd> guard, <kbd>Space</kbd> FIRE.
With a lock the torpedo homes in; without one it runs along the course set with the AIM stick (<kbd>A</kbd>/<kbd>D</kbd>).
DECOY (<kbd>N</kbd>) throws a noisemaker to spoil an enemy torpedo.</p></section>
<section><h2>CHART TABLE - ROUTE PLANNING</h2><p>Move the cursor with the CURSOR stick (<kbd>WASD</kbd> or drag), ADD WPT (<kbd>Space</kbd>) drops a waypoint,
DEL WPT (<kbd>Backspace</kbd>) removes the last. Zoom <kbd>Z</kbd>/<kbd>X</kbd>.</p></section>
<section><h2>SHIP STATUS</h2><p>Eight pages: NOISE, AIR, ENGINES, POWER, LEAKS, FLOOD, FIRE, HEAT (<kbd>1</kbd>-<kbd>8</kbd>). A page key flashes red when that
system needs help. The guarded GENERAL ALARM (<kbd>G</kbd>) sounds the klaxon and lights the beacons for the whole crew.</p></section>
<section><h2>NOISE &amp; STEALTH</h2><p>Speed, running diesels, a raised periscope, blowing tanks, being on the surface, pings and launches all make noise.
The louder you are, the further away a frigate hears you. Go slow and deep to slip away.</p></section>
<section><h2>AIR, BATTERY &amp; DIESELS</h2><p>Submerged, the oxygen slowly runs down and the motors drain the battery. Surface, or snorkel at ${SNORKEL_DEPTH} m
with a diesel running, to refresh the air and charge. Diesels need fuel in the DAY TANK (fuel transfer pump, jerrycans), oil, and their
coolant valves open.</p></section>
<section><h2>DIESEL PANELS &amp; HEAT</h2><p>Each diesel has its own panel on the catwalk: POWER, a status screen with its revs, load and warnings,
and TALK to report to the control room. Running diesels and fires heat the compartments: a hot room saps your stamina and makes
the engines run hotter. Switch on the room's fans (SMOKE EXTRACT) - the HEAT page on SHIP STATUS shows every room.</p></section>
<section><h2>POWER</h2><p>Big hits trip the breakers. At the MAIN SWITCHBOARD (battery room) close the tripped breakers, then the MAIN BREAKER.</p></section>
<section><h2>LEAKS &amp; FLOODING</h2><p>Hits tear the hull. The deeper you are, the harder the sea jets in. Take a wrench from the tool board and hold <kbd>E</kbd> on the leak.
Water spreads through open doors and down the stairs; work the hand BILGE PUMPS (click up and down). Chest deep, you swim.</p></section>
<section><h2>FIRE &amp; SMOKE</h2><p>Take an extinguisher off the wall and hold <kbd>E</kbd> at the flames. Then switch on that room's SMOKE EXTRACT fans (they need power).</p></section>
<section><h2>CREW CARE</h2><p>Hunger and stamina drain. Cook at the galley griddle and eat (<kbd>F</kbd>). Hurt? Lie on the med bed or use a first-aid kit.</p></section>`;
function toggleHandbook(show = $('handbook').classList.contains('hidden')) {
  const hb = $('handbook');
  if (!hb.innerHTML) hb.innerHTML = HANDBOOK;
  hb.classList.toggle('hidden', !show);
  if (show && document.pointerLockElement) document.exitPointerLock();
  if (!show && player.mode === 'walk') lockPointer();
}

function drop() {
  if (!player.carry) return;
  if (player.carry === 'wrench' && player.wrenchObj) {
    player.wrenchObj.position.set(player.pos.x, player.pos.y + 0.02, player.pos.z); player.wrenchObj.visible = true;
    inn.interactables.push({ pos: player.wrenchObj.position.clone().add(new THREE.Vector3(0, 0.08, 0)), radius: 0.6, label: 'Pick up WRENCH', kind: 'wrench', data: player.wrenchObj });
  }
  if (player.carry === 'torpedo') sim.torpedoStock += 1;
  if (['fuel_can', 'oil_can', 'first_aid'].includes(player.carry) && player.carriedObj) {
    const o = player.carriedObj, item = player.carry;
    if (!o.parent) inn.scene.add(o);
    o.position.set(player.pos.x + -Math.sin(player.yaw) * 0.5, player.pos.y + 0.01, player.pos.z - Math.cos(player.yaw) * 0.5); o.visible = true;
    inn.interactables.push({ pos: o.position.clone().add(new THREE.Vector3(0, 0.2, 0)), radius: 0.6, label: `Pick up ${CARRY_NAMES[item]}`, kind: 'pickup', data: { obj: o, item } });
  }
  player.carry = null; player.carriedObj = null;
}

// -------------------------------------------------------------------- loop
let last = nowMs(), monitorTimer = 0, screenTimer = 0, cctvTimer = 0;
// short delays on the game clock (in capture mode setTimeout would follow the slow real clock instead)
const timers = [];
function later(ms, fn) { if (!CAPTURE) setTimeout(fn, ms); else timers.push({ at: nowMs() + ms, fn }); }
function runTimers() {
  for (let i = timers.length - 1; i >= 0; i--) if (nowMs() >= timers[i].at) { const t = timers.splice(i, 1)[0]; t.fn(); }
}
function loop(now) {
  const dt = Math.min(0.05, (now - last) / 1000);
  last = now;
  tick(dt);
  requestAnimationFrame(loop);
}

// what the SHIP STATUS console shows: which pages need attention, and where the crew are
function updateStatusInfo() {
  const s = sim.sub;
  const hostileHunting = sim.entities.some((e) => e.alive && e.state === 'hunt' && (e.kind === 'frigate' || e.kind === 'enemySub'));
  inn.statusInfo.alerts = {
    noise: sim.noiseLevel > 11 || hostileHunting,
    air: s.oxygen < 30 || sim.smoke.some((v) => v > 0.35),
    engines: sim.engines.some((e) => e.fault || e.temp > 100 || !e.coolant) || sim.fuel.day < 8,
    power: !sim.power,
    leaks: sim.leaks.some((l) => !l.fixed),
    flood: sim.floodFraction() > 0.02,
    fire: sim.fires.some((f) => !f.out),
    heat: sim.heat.some((h) => h > 42),
  };
  const where = (st, x, y) => (st ? (HELP[st]?.[0] || st.toUpperCase()) : ROOMS[sim.roomAt(x, y)]?.label || 'ON DECK');
  const crew = [{ name: `YOU - ${$('pname')?.value || 'Sailor'}`, role: player.role.replace('_', ' ').toUpperCase(), where: where(player.station, player.pos.x, player.pos.y),
    health: player.health, hunger: player.hunger }];
  if (net) for (const p of net.peers.values()) crew.push({ name: p.name || 'Sailor', role: (p.role || '').replace('_', ' ').toUpperCase(), where: where(p.station, p.x || 0, p.y || 0) });
  inn.statusInfo.crew = crew.slice(0, 4);
  inn.statusInfo.objective = objective();
}

// one frame of the game (the recorder calls this directly with a fixed dt)
function tick(dt) {
  clockMs += dt * 1000;
  runTimers();
  const w = innerWidth, h = innerHeight;
  if (canvas.width !== Math.floor(w * renderer.getPixelRatio()) || canvas.height !== Math.floor(h * renderer.getPixelRatio())) renderer.setSize(w, h, false);
  camera.aspect = w / h; camera.updateProjectionMatrix();

  if (!net || net.isHost) sim.update(dt);
  if (net) { net.update(dt, player); net.animate(dt); }
  continuousInput(dt);
  updatePlayer(dt);
  handleEvents();
  inn.update(sim, dt, camera);
  updateEnvironment(dt);
  ext.sync(sim, dt);
  updateGriddle(dt);
  updateHands(dt);
  sound.update(sim, player, dt);

  screenTimer -= dt;
  if (screenTimer <= 0) { screenTimer = 0.1; updateStatusInfo(); inn.drawScreens(sim); }
  monitorTimer -= dt;
  cctvTimer -= dt;
  const m = player.mode;
  if (window.__noRender) { updateHud(); return; }      // recorder dry runs: simulate only
  inn.lensOn.value = sim.sub.periscopeUp ? 1 : 0;
  if (m === 'station' && player.station === 'periscope' && sim.sub.periscopeUp) {
    ext.updateTags(sim, true); ext.periscopeCamera(sim, 2.02); ext.render(inn.lensRT); ext.updateTags(sim, false);
  }
  if (m === 'scope') { ext.updateTags(sim, true); ext.periscopeCamera(sim, w / h); ext.render(); ext.updateTags(sim, false); }
  else if (m === 'bridge') { ext.bridgeCamera(sim, w / h); ext.render(); }
  else if (m === 'chase') { ext.chaseCamera(sim, w / h); ext.render(); }
  else {
    if (monitorTimer <= 0) { monitorTimer = CAPTURE ? 1.5 : 0.3; inn.renderMonitors(ext, sim); }
    if (cctvTimer <= 0) {
      const near = player.station === 'cameras' || Math.hypot(player.pos.x - 10.3, player.pos.z + 2.0) < 5;
      cctvTimer = near ? (CAPTURE ? 0.2 : 0.12) : 3; inn.renderCCTV(renderer, fp?.holder);
    }
    renderer.render(inn.scene, camera);
  }
  updateHud();
}

// gauges, wheels and other instruments follow the simulation
const Z_AXIS = new THREE.Vector3(0, 0, -1);
function animateInstruments(dt) {
  const s = sim.sub, bp = inn.stations.ballast;
  if (!bp) return;
  const set = (o, axis, ang) => { if (!o) return; o.userData.rest ||= o.quaternion.clone(); o.quaternion.copy(o.userData.rest).multiply(new THREE.Quaternion().setFromAxisAngle(axis, ang)); };
  dial(bp.parts.DepthGaugeNeedle, -80, s.depth / 250);
  dial(bp.parts.PressureGaugeNeedle, 10, s.ballast);
  dial(bp.parts.AirGaugeNeedle, -20, s.air / 100);
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
    if (js) { js.userData.rest ||= js.quaternion.clone(); js.quaternion.copy(js.userData.rest).multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(-s.telegraph * 0.06, 0, -s.rudder * 0.3))); }
  }
  if (player.mode === 'station' && player.station === 'chart') {
    const c = inn.chartCursor, z = inn.chartZoom, v = 260 / z;
    const mx = (keys.has('d') ? 1 : 0) - (keys.has('a') ? 1 : 0), mz = (keys.has('s') ? 1 : 0) - (keys.has('w') ? 1 : 0);
    c.x += (mx * v * dt) + mouseDX * 2 / z; c.z += (mz * v * dt) + mouseDY * 2 / z;
    const lx = 384 / (0.22 * z) - 30 / z, lz = 256 / (0.22 * z) - 30 / z;
    c.x = Math.max(-lx, Math.min(lx, c.x)); c.z = Math.max(-lz, Math.min(lz, c.z));
    inn.cursorMove = { x: mx, z: mz };
    if (wheel) inn.chartZoom = Math.max(0.5, Math.min(4, inn.chartZoom * (wheel < 0 ? 1.25 : 0.8)));
    if (keys.has('z')) inn.chartZoom = Math.min(4, inn.chartZoom * (1 + dt * 1.5));
    if (keys.has('x')) inn.chartZoom = Math.max(0.5, inn.chartZoom / (1 + dt * 1.5));
    if (mx || mz) reach('CursorStick', 'grip', 150);
  } else inn.cursorMove = null;
  if (player.mode === 'station' && player.station === 'sonar') {
    const a = (keys.has('a') ? 1 : 0) - (keys.has('d') ? 1 : 0), g = (keys.has('w') ? 1 : 0) - (keys.has('s') ? 1 : 0);
    if (a || mouseDX) { sim.setHydro((s.hydro || 0) + a * dt * 0.7 - mouseDX * 0.004); reach('TrainWheel', 'grip', 150); }
    if (g) sim.setGain(s.gain + g * dt * 3);
    if ((a || g || mouseDX) && net) net.sendControls();
  }
  if (player.mode === 'station' && player.station === 'mission' && wheel) inn.mapZoom = Math.max(0.5, Math.min(4, inn.mapZoom * (wheel < 0 ? 1.25 : 0.8)));
  if (player.mode === 'station' && player.station === 'weapons') {
    const a = (keys.has('a') ? 1 : 0) - (keys.has('d') ? 1 : 0);
    if (a || mouseDX) { sim.setAim((sim.weapons.aim || 0) + a * dt * 0.7 - mouseDX * 0.003); if (net) net.sendControls(); }
  }
  if (player.mode === 'station' && player.station === 'ballast') {
    if (keys.has('w')) sim.setPlanes(s.planes + dt * 1.0);
    if (keys.has('s')) sim.setPlanes(s.planes - dt * 1.0);
  }
  if (player.mode === 'scope' || (player.mode === 'station' && player.station === 'periscope' && player.transition >= 1)) {
    s.periscopeBearing -= mouseDX * 0.0025 / s.periscopeZoom;
    if (keys.has('a')) s.periscopeBearing += dt * 0.8 / s.periscopeZoom;
    if (keys.has('d')) s.periscopeBearing -= dt * 0.8 / s.periscopeZoom;
    s.periscopePitch = Math.max(-0.35, Math.min(0.5, s.periscopePitch - mouseDY * 0.002 + (keys.has('w') ? dt * 0.4 : 0) - (keys.has('s') ? dt * 0.4 : 0)));
    if (wheel) s.periscopeZoom = Math.max(1, Math.min(6, s.periscopeZoom * (wheel < 0 ? 1.25 : 0.8)));
    if (keys.has('z')) s.periscopeZoom = Math.min(6, s.periscopeZoom + dt * 3);
    if (keys.has('x')) s.periscopeZoom = Math.max(1, s.periscopeZoom - dt * 3);
    if (!s.periscopeUp && player.mode === 'scope') player.mode = 'station';
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

const STATION_FOV = { periscope: 80 };   // a little wider at the periscope so both hands show on the grips
function updatePlayer(dt) {
  if (player.mode !== 'station' && camera.fov !== 72) { camera.fov = 72; camera.updateProjectionMatrix(); }
  // hunger / stamina / health
  player.hunger = Math.max(0, player.hunger - dt * 100 / 480);
  const moving = player.mode === 'walk' && ['w', 'a', 's', 'd'].some((k) => keys.has(k));
  const sprint = moving && !player.swim && keys.has('shift') && player.stamina > 5 && player.carry !== 'torpedo';
  const regen = player.hunger > 0 && sim.sub.oxygen > 15 ? 7 : 1;
  player.stamina = Math.max(0, Math.min(100, player.stamina + (sprint ? -14 : player.swim && moving ? -2 : regen) * dt));
  // a hot compartment saps you; an oven-hot one hurts
  const hr = sim.roomAt(player.pos.x, player.pos.y), heat = hr >= 0 ? sim.heat[hr] : 24;
  if (heat > 40) {
    player.stamina = Math.max(0, player.stamina - (heat - 40) * 0.6 * dt);
    if (heat > 52) player.health = Math.max(0, player.health - (heat - 52) * 0.15 * dt);
    if (!player.heatWarn || nowMs() - player.heatWarn > 20000) { player.heatWarn = nowMs(); sim.message(`It's ${heat.toFixed(0)}°C in the ${ROOMS[hr].label}: switch on its fans (SMOKE EXTRACT).`, 'warn'); }
  }
  if (player.mode === 'down') {
    player.down -= dt;
    if (player.down <= 0) respawn();
    return;
  }
  if (player.mode === 'walk') {
    player.yaw -= mouseDX * 0.0022; player.pitch = Math.max(-1.4, Math.min(1.4, player.pitch - mouseDY * 0.0022));
    const room = sim.roomAt(player.pos.x, player.pos.y);
    const surface = room >= 0 ? sim.surface(room) : -99;
    // water above the feet (only real water: halfway down the stairs your feet are below the upper deck's dry floor)
    const depthHere = room >= 0 && sim.water[room] > 0.02 ? surface - player.pos.y : 0;
    // swim once the water is chest deep (or when there is no floor under us)
    if (!player.swim && depthHere > 1.25) { player.swim = true; player.vy = 0; sim.message('Swimming! SPACE swim up, C dive. Watch your breath.', 'warn'); }
    if (player.swim && depthHere < 1.05) player.swim = false;
    let speed = sprint ? 4.6 : 2.6;
    if (player.carry === 'torpedo') speed = 1.5;
    if (player.hunger <= 0) speed *= 0.7;
    if (!player.swim && depthHere > 0.3) speed *= Math.max(0.45, 1 - depthHere * 0.5);   // wading
    if (player.swim) speed = keys.has('shift') && player.stamina > 5 ? 2.2 : 1.5;
    const f = new THREE.Vector3(-Math.sin(player.yaw), 0, -Math.cos(player.yaw)), r = new THREE.Vector3(Math.cos(player.yaw), 0, -Math.sin(player.yaw));
    const mv = new THREE.Vector3();
    if (keys.has('w')) mv.add(f); if (keys.has('s')) mv.sub(f); if (keys.has('d')) mv.add(r); if (keys.has('a')) mv.sub(r);
    if (mv.lengthSq()) mv.normalize().multiplyScalar(speed * dt);
    const floor = inn.nav.move(player.pos, mv.x, mv.z, sim.doors, player.swim);
    if (player.swim) {
      // float with the head just out of the water; SPACE swims up, C dives
      const ceil = inn.nav.ceilingAt(player.pos.x, player.pos.z, player.pos.y);
      const top = Math.min(surface - EYE + 0.1, ceil - EYE - 0.05);
      const want = keys.has('c') ? -1.6 : keys.has(' ') ? 1.3 : (top - player.pos.y) * 2.5;
      player.vy += (want - player.vy) * Math.min(1, dt * 3);
      player.pos.y += player.vy * dt;
      player.pos.y = Math.min(player.pos.y, ceil - EYE - 0.05, surface - 0.4);
      if (floor !== null) player.pos.y = Math.max(player.pos.y, floor);
    } else if (floor !== null) {
      player.pos.y += (floor - player.pos.y) * Math.min(1, dt * 18);
      if (Math.abs(floor - player.pos.y) < 0.01) player.pos.y = floor;
    }
    const bob = moving ? Math.sin(nowMs() / (sprint ? 90 : 140)) * (player.swim ? 0.05 : 0.03) : player.swim ? Math.sin(nowMs() / 600) * 0.04 : 0;
    camera.position.set(player.pos.x, player.pos.y + EYE + bob, player.pos.z);
    camera.rotation.set(player.pitch, player.yaw, player.swim ? Math.sin(nowMs() / 700) * 0.03 : 0);
    // fighting a fire
    if (player.spraying) {
      sim.extinguish(player.spraying, dt);
      if (net && !net.isHost) net.send({ t: 'act', ev: { type: 'extinguish', id: player.spraying, dt } });
      if (!sim.fires.some((q) => q.id === player.spraying && !q.out)) player.spraying = null;
    }
    // repairing a leak
    if (player.repairing) {
      const it = inn.interactables.find((i) => i.kind === 'leak' && i.data === player.repairing);
      if (!it || it.pos.distanceTo(camera.position) > 2.4) { player.repairing = null; }
      else { player.hold += dt; if (player.hold > 2.5) { sim.fixLeak(player.repairing); player.repairing = null; player.hold = 0; sound.clunk(); } }
    }
    // pouring fuel, topping up oil, fixing injectors
    if (player.task) {
      const t = player.task;
      if (t.it.pos.distanceTo(camera.position) > 2.6) player.task = null;
      else {
        t.t += dt;
        if (t.kind === 'filler' && Math.random() < dt * 8) sound.glug();
        if (t.t >= t.need) {
          if (t.kind === 'filler') { sim.act('pourFuel', 20); player.carry = null; player.carriedObj = null; }
          if (t.kind === 'oil') { sim.act('addOil', t.it.data); player.carry = null; player.carriedObj = null; }
          if (t.kind === 'injector') { sim.act('fixEngine', t.it.data); sound.clunk(); }
          player.task = null;
        }
      }
    }
  } else if (player.mode === 'station' && player.station) {
    const st = inn.stations[player.station];
    player.transition = Math.min(1, player.transition + dt * 2.2);
    const k = player.transition * player.transition * (3 - 2 * player.transition);
    const p = new THREE.Vector3(), q = new THREE.Quaternion();
    if (st.cam) { st.cam.getWorldPosition(p); st.cam.getWorldQuaternion(q); }
    camera.position.lerpVectors(player.camFrom, p, k);
    camera.quaternion.slerpQuaternions(player.quatFrom, q, k);
    const fov = STATION_FOV[player.station] || 72;
    if (Math.abs(camera.fov - (72 + (fov - 72) * k)) > 0.01) { camera.fov = 72 + (fov - 72) * k; camera.updateProjectionMatrix(); }
  } else if (player.mode === 'lie') {
    // on the med bed: look up at the deckhead and heal
    player.transition = Math.min(1, player.transition + dt * 1.5);
    const k = player.transition * player.transition * (3 - 2 * player.transition);
    const lie = inn.medbed?.userData.lie || new THREE.Vector3(1.35, 0.9, 1.97);
    const p = lie.clone().add(new THREE.Vector3(0, 0.25, 0));
    const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(1.35, Math.PI / 2, 0, 'YXZ'));
    camera.position.lerpVectors(player.camFrom, p, k);
    camera.quaternion.slerpQuaternions(player.quatFrom, q, k);
    player.health = Math.min(100, player.health + dt * 12);
    player.stamina = Math.min(100, player.stamina + dt * 15);
    if (player.health >= 100 && !player._healedMsg) { player._healedMsg = true; sim.message('Fully healed. Press E to get up.'); }
    if (player.health < 100) player._healedMsg = false;
  }
  updateHealth(dt);
  // the boat's motion and explosions shake the view
  player.shake = Math.max(0, player.shake - dt * 1.5);
  if (player.mode === 'walk' || player.mode === 'station') {
    camera.rotation.z += sim.sub.roll * 0.6;
    if (player.shake > 0) { camera.position.x += (Math.random() - 0.5) * player.shake * 0.08; camera.position.y += (Math.random() - 0.5) * player.shake * 0.08; }
  }
}

// drowning, smoke and flames hurt; food slowly heals
function updateHealth(dt) {
  if (player.mode === 'down') return;
  const eye = camera.getWorldPosition(new THREE.Vector3());
  const env = inn.envAt(sim, eye);
  const under = eye.y < env.surface - 0.02;
  player.underwater = under;
  player.breath = Math.max(0, Math.min(100, player.breath + (under ? -9 : 30) * dt));
  let hurt = 0;
  if (under && player.breath <= 0) hurt += 14;
  if (env.smoke > 0.35 && !under) hurt += (env.smoke - 0.35) * 16;
  for (const f of sim.fires) if (!f.out && Math.hypot(f.x - player.pos.x, f.z - player.pos.z) < 1.0 && Math.abs((f.y ?? 0) - player.pos.y) < 1.2) hurt += 10 * f.intensity;
  if (sim.sub.oxygen < 8) hurt += 2;
  if (hurt > 0) { player.health -= hurt * dt; player.hurtT = 0.4; }
  else if (player.hunger > 40 && player.health < 100) player.health = Math.min(100, player.health + dt * 0.4);
  player.hurtT = Math.max(0, (player.hurtT || 0) - dt);
  if (player.health <= 0) blackout(under ? 'You drowned' : env.smoke > 0.35 ? 'You passed out in the smoke' : 'You were badly burnt');
}

function blackout(why) {
  player.health = 0; player.mode = 'down'; player.down = 4; player.swim = false;
  player.repairing = player.spraying = player.task = null;
  if (player.station) { player.station = null; $('station').classList.add('hidden'); $('scope').classList.add('hidden'); }
  drop();
  sim.message(`${why}! Your crewmates carry you to the sick bay...`, 'danger');
  $('blackout').classList.remove('hidden');
}

function respawn() {
  const p = inn.medSpawn;
  player.pos.set(p.x, 0, p.z); player.yaw = Math.PI / 2; player.pitch = -0.1;
  player.health = 55; player.breath = 100; player.mode = 'walk'; player.vy = 0;
  $('blackout').classList.add('hidden');
  sim.message('You wake up in the sick bay. Lie on the MED BED to heal fully.');
}

// fog from smoke, a blue murk underwater, and the water-line overlay
const FOG_SMOKE = new THREE.Color(0x2a2724), FOG_WATER = new THREE.Color(0x0d4656), FOG_CLEAR = new THREE.Color(0x0b0f12);
function updateEnvironment(dt) {
  const eye = camera.getWorldPosition(new THREE.Vector3());
  const env = inn.envAt(sim, eye);
  const under = eye.y < env.surface - 0.02;
  if (!inn.scene.fog) inn.scene.fog = new THREE.FogExp2(0x0b0f12, 0.01);
  const fog = inn.scene.fog;
  if (under) { fog.color.copy(FOG_WATER); fog.density = 0.32; }
  else {
    const sm = Math.max(0, env.smoke);
    fog.color.copy(FOG_CLEAR).lerp(FOG_SMOKE, Math.min(1, sm * 2.5));
    fog.density = 0.008 + sm * sm * 0.55 + sm * 0.12;
  }
  inn.scene.background = fog.color;
  $('underwater').classList.toggle('hidden', !under);
  if (under) inn.breathe(eye, env.surface, dt);
  // splashing about in the flood water
  const wet = env.surface - player.pos.y;
  if (player.mode === 'walk' && wet > 0.15 && ['w', 'a', 's', 'd'].some((k) => keys.has(k))) {
    player.splashT = (player.splashT || 0) - dt;
    if (player.splashT <= 0) {
      player.splashT = player.swim ? 0.7 : 0.42; sound.splash(player.swim ? 0.6 : Math.min(1, wet));
      inn.ripple(player.pos.x, env.surface, player.pos.z, player.swim ? 1.3 : 0.9);
    }
  }
  $('smokeveil').style.opacity = under ? 0 : Math.min(0.55, env.smoke * 0.6);
  sound.setUnderwater(under);
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
    if (ev.type === 'engineCrank') sound.crank();
    if (ev.type === 'engineFault') { sound.alarm(); }
    if (ev.type === 'breaker') sound.clunk();
    if (ev.type === 'lost') { setTimeout(() => { $('lost').classList.remove('hidden'); $('lostreason').textContent = `${ev.reason} Ships sunk: ${sim.score.sunk}.`; document.exitPointerLock?.(); }, 3500); }
    if (net && !ev.remote) net.event(ev);
  }
}

function flash(color = '#ffffff') { const f = $('flash'); f.style.background = color; f.style.transition = 'none'; f.style.opacity = 0.6; requestAnimationFrame(() => { f.style.transition = 'opacity .6s'; f.style.opacity = 0; }); }
function pushMessage(text, level = 'info') {
  const d = document.createElement('div'); d.className = level; d.textContent = text;
  d.dataset.born = nowMs();
  if (CAPTURE) d.style.animation = 'none';           // the recorder fades them on game time instead
  $('messages').prepend(d);
  while ($('messages').children.length > 5) $('messages').lastChild.remove();
  if (!CAPTURE) setTimeout(() => d.remove(), 7000);
}
function ageMessages() {
  for (const d of [...$('messages').children]) {
    const age = nowMs() - +d.dataset.born;
    if (age > 7000) d.remove(); else if (age > 5600) d.style.opacity = String(1 - (age - 5600) / 1400);
  }
}

function updateHud() {
  const s = sim.sub;
  if (CAPTURE) ageMessages();
  $('stamina').style.width = `${player.stamina}%`;
  $('hunger').style.width = `${player.hunger}%`;
  $('hullbar').style.width = `${s.hull}%`;
  $('healthbar').style.width = `${Math.max(0, player.health)}%`;
  $('breathrow').classList.toggle('hidden', player.breath >= 99.5 && !player.swim);
  $('breathbar').style.width = `${player.breath}%`;
  $('hurt').style.opacity = player.hurtT > 0 ? 0.35 + (1 - player.health / 100) * 0.4 : Math.max(0, (35 - player.health) / 70);
  const room = sim.roomAt(player.pos.x, player.pos.y);
  const leaks = sim.leaks.filter((l) => !l.fixed);
  const eng = sim.engines.map((e) => `${e.id}:${e.fault ? '<span style="color:#ff6b5b">FAULT</span>' : e.running ? '<span style="color:#63e08f">RUN</span>' : e.crank ? 'START' : 'OFF'}`).join(' ');
  $('status').innerHTML = [
    `${room >= 0 ? ROOMS[room].label + (ROOMS[room].deck === 'lower' ? ' · LOWER DECK' : '') : 'BULKHEAD'}`,
    `DEPTH ${s.depth.toFixed(0)} m ${s.depth > TEST_DEPTH ? '<span style="color:#ff6b5b">CRUSH!</span>' : ''} · <span style="color:${(s.belowKeel ?? 99) < 15 ? '#ff6b5b' : 'inherit'}">${(s.belowKeel ?? 0).toFixed(0)} m under keel</span>`,
    `${TELEGRAPH_NAMES[s.telegraph]} · ${s.speed.toFixed(1)} m/s`,
    `HEADING ${sim.deg(s.heading)}° · RUDDER ${s.rudder > 0.05 ? 'PORT' : s.rudder < -0.05 ? 'STBD' : 'MID'}`,
    `BALLAST ${s.valve.toUpperCase()} ${(s.ballast * 100).toFixed(0)}% · PERISCOPE ${s.periscopeUp ? 'UP' : 'DOWN'}`,
    `BATTERY ${s.battery.toFixed(0)}%${s.charging ? ' ⚡' : ''} · O₂ <span style="color:${s.oxygen < 20 ? '#ff6b5b' : 'inherit'}">${s.oxygen.toFixed(0)}%</span>`,
    `DIESELS ${eng} · FUEL ${sim.fuel.day.toFixed(0)}/${sim.fuel.main.toFixed(0)} L`,
    sim.power ? '' : '<span style="color:#ff6b5b">NO POWER</span>',
    leaks.length ? `<span style="color:#ff6b5b">LEAKS: ${[...new Set(leaks.map((l) => ROOMS[l.room].label))].join(', ')}</span>` : 'NO LEAKS',
    sim.water.some((w) => w > 0.05) ? `<span style="color:#64b5f6">FLOODING ${(sim.floodFraction() * 100).toFixed(0)}% · ${ROOMS.map((r, i) => sim.water[i] > 0.05 ? `${r.label} ${sim.water[i].toFixed(1)}m` : '').filter(Boolean).join(', ')}</span>` : '',
    sim.smoke.some((q) => q > 0.08) ? `<span style="color:#c9b9a0">SMOKE: ${ROOMS.map((r, i) => sim.smoke[i] > 0.08 ? `${r.label} ${(sim.smoke[i] * 100).toFixed(0)}%` : '').filter(Boolean).join(', ')}</span>` : '',
  ].filter(Boolean).join('<br>');
  $('score').style.top = `${$('status').offsetTop + $('status').offsetHeight + 8}px`;
  $('score').innerHTML = `WAVE ${sim.score.wave} · SHIPS SUNK ${sim.score.sunk}<br><span style="color:#f2ead6;font-weight:500">${objective()}</span>`;
  $('carry').textContent = player.carry ? `CARRYING: ${CARRY_NAMES[player.carry] || player.carry.toUpperCase()} (Q drop${player.carry.startsWith('food_c') || player.carry === 'food_burnt' ? ', F eat' : player.carry === 'first_aid' ? ', F use' : ''})` : '';
  const it = nearest();
  $('prompt').textContent = it ? `[E] ${it.label}` : '';
  const prog = player.repairing ? player.hold / 2.5 : player.task ? player.task.t / player.task.need : null;
  $('progress').classList.toggle('hidden', prog === null);
  $('progressfill').style.width = `${Math.min(100, (prog || 0) * 100)}%`;
  const scope = player.mode === 'scope';
  $('scope').classList.toggle('hidden', !scope);
  if (scope) {
    const lock = sim.entities.find((e) => e.id === sim.weapons.lock && e.alive);
    $('scopeinfo').innerHTML = `BRG ${sim.deg(s.heading + s.periscopeBearing)}° · ZOOM ${s.periscopeZoom.toFixed(1)}x<br>${lock ? `LOCKED: ${lock.kind.toUpperCase()} ${Math.hypot(lock.x - s.x, lock.z - s.z).toFixed(0)} m` : 'CLICK TO MARK A TARGET'}`;
  }
  $('crosshair').classList.toggle('hidden', player.mode !== 'walk');
  // at a station its own screens tell the story: hide the big status panel and fold the help away after a while
  const atStation = player.mode === 'station' || player.mode === 'scope';
  $('status').classList.toggle('hidden', atStation);
  $('score').classList.toggle('hidden', atStation);
  if (atStation && player.helpUntil && nowMs() > player.helpUntil) { $('station').classList.add('collapsed'); player.helpUntil = 0; }
  if (net) {
    const st = { helm: 'HELM', chart: 'CHART', weapons: 'FIRE CONTROL', periscope: 'PERISCOPE', sonar: 'SONAR', ballast: 'BALLAST', griddle: 'GRIDDLE',
      engines: 'ENGINES', fuel: 'FUEL PUMP', switchboard: 'SWITCHBOARD', bilge5: 'BILGE PUMP', bilge6: 'BILGE PUMP', bilge7: 'BILGE PUMP' };
    $('carry').title = '';
    $('crew').innerHTML = ['<b>CREW</b>', `${$('pname').value} (you) · ${st[player.station] || 'walking'}`,
      ...[...net.peers.values()].map((p) => `${p.name} · ${p.role.replace('_', ' ')} · ${st[p.station] || (p.carry ? 'carrying ' + p.carry : 'walking')}`)].join('<br>');
  }
  // labels over ships in the outside views; numbered name tags over crewmates inside the boat
  const labels = $('labels');
  labels.innerHTML = '';
  if (net && !m3d()) {
    let n = 1;
    for (const [id, p] of net.peers) {
      n += 1;
      const a = net.avatars[id]; if (!a || a === 'loading' || !a.visible) continue;
      const q = a.getWorldPosition(new THREE.Vector3()).add(new THREE.Vector3(0, 2.05, 0));
      if (q.distanceTo(camera.position) > 14) continue;
      q.project(camera);
      if (q.z > 1 || Math.abs(q.x) > 1 || Math.abs(q.y) > 1) continue;
      const d = document.createElement('div');
      d.className = 'crewtag';
      d.style.left = `${(q.x + 1) / 2 * 100}%`; d.style.top = `${(1 - q.y) / 2 * 100}%`;
      d.innerHTML = `<b style="background:${['#ffcf4a', '#58c2f0', '#4cff8a', '#ff8a5a'][(n - 1) % 4]}">${n}</b>${(p.name || 'Sailor').replace(/[<>&]/g, '')}`;
      labels.appendChild(d);
    }
  }
  if (m3d()) {
    for (const e of sim.entities) {
      if (!e.alive || !sim.contacts.has(e.id)) continue;
      const p = new THREE.Vector3(e.x, -(e.depth || 0) + 8, e.z).project(ext.camera);
      if (p.z > 1 || Math.abs(p.x) > 1 || Math.abs(p.y) > 1) continue;
      if (player.mode === 'scope' && Math.hypot(p.x * innerWidth / 2, p.y * innerHeight / 2) > Math.min(innerWidth, innerHeight) * 0.37) continue;
      const d = document.createElement('div');
      d.className = 'tag' + (e.id === sim.weapons.lock ? ' locked' : '');
      d.style.left = `${(p.x + 1) / 2 * 100}%`; d.style.top = `${(1 - p.y) / 2 * 100}%`;
      d.textContent = `${e.kind.toUpperCase()} ${Math.hypot(e.x - s.x, e.z - s.z).toFixed(0)}m`;
      labels.appendChild(d);
    }
  }
}
const m3d = () => player.mode === 'chase' || player.mode === 'bridge' || player.mode === 'scope';

function objective() {
  const s = sim.sub;
  if (player.health < 30) return '▸ You are badly hurt: lie on the MED BED (forward quarters) or use a first-aid kit';
  const fires = sim.fires.filter((f) => !f.out);
  if (fires.length) return `▸ FIRE in the ${ROOMS[fires[0].room].label}: grab an extinguisher`;
  if (!sim.power) return '▸ Power out: close the tripped breakers + MAIN BREAKER (battery room, lower deck)';
  const open = sim.leaks.filter((l) => !l.fixed);
  if (open.length) return `▸ Fix ${open.length} leak${open.length > 1 ? 's' : ''} with a wrench (${ROOMS[open[0].room].label})`;
  const wet = ROOMS.map((r, i) => i).filter((i) => sim.water[i] > 0.25).sort((a, b) => sim.water[b] - sim.water[a]);
  if (wet.length) return `▸ Water in the ${ROOMS[wet[0]].label}: work the BILGE PUMPS (torpedo room, battery room, engine room)`;
  const smoky = ROOMS.map((r, i) => i).filter((i) => sim.smoke[i] > 0.25 && !sim.vents[i]);
  if (smoky.length) return `▸ Smoke in the ${ROOMS[smoky[0]].label}: switch on its SMOKE EXTRACT fans`;
  if (sim.entities.some((e) => e.alive && e.attached)) return '▸ Squid on the hull! HULL SHOCK in the control room';
  if (sim.torpedoes.some((t) => t.owner !== 'player')) return '▸ Incoming torpedo: turn hard, noisemaker at fire control';
  const faulty = sim.engines.find((e) => e.fault || (e.running && !e.coolant));
  if (faulty) return `▸ Diesel ${faulty.id}: ${faulty.fault === 'injector' ? 'fix the injectors with a wrench' : faulty.fault === 'oil' ? 'top up the oil (oil can)' : faulty.fault === 'overheat' ? 'open the coolant valve and let it cool' : 'open the coolant valve!'}`;
  if (s.battery < 25 && !sim.engines.some((e) => e.running)) return s.depth > SNORKEL_DEPTH ? `▸ Battery low: rise to ${SNORKEL_DEPTH} m and start the diesels (engine room)` : '▸ Battery low: start the diesels at the ENGINE CONTROLS (engine room)';
  if (sim.fuel.day < 15) return '▸ Day tank nearly dry: pump fuel up at the FUEL TRANSFER PUMP (engine room)';
  if (player.hunger < 25) return '▸ You are starving: cook and eat (galley)';
  if (!sim.tubes.some((t) => t.loaded)) return '▸ All tubes empty: reload in the torpedo room (lower deck, stairs in the forward quarters)';
  if (!sim.weapons.lock) return s.depth > PERISCOPE_DEPTH ? '▸ Rise to periscope depth (14 m) or use sonar to find targets' : '▸ Find a target: periscope or sonar, then mark it';
  return '▸ Target locked: flood, open door, arm and FIRE at fire control';
}

function applyTest(name) {
  // deterministic scenarios for automated screenshots
  const s = sim.sub;
  if (name === 'leaks') { sim.damage(18, 'Test depth charge', 0.25); player.pos.set(10.5, 0, 0.4); player.yaw = 0; }
  if (name === 'jet') {   // one leak at depth, seen from across the control room
    s.depth = 60; s.ballast = 0.5;
    sim.entities.forEach((e) => { if (e.kind === 'shark') e.alive = false; });
    const l = { id: sim.nextId++, room: RI.ControlRoom, x: 11.4, y: 1.35, side: 1, z: -2.03, severity: 1.3, fixed: false };
    sim.leaks.push(l); sim.events.push({ type: 'leak', leak: l });
    player.pos.set(12.3, 0, 0.9); player.yaw = 0.35; player.pitch = -0.1;
  }
  if (name === 'flood') {   // the torpedo room deep in water
    sim.doors[5] = false; sim.water[RI.TorpedoRoom] = 2.45; sim.addLeak(RI.TorpedoRoom, 1.0);
    player.pos.set(4.6, -2.9, 0.2); player.yaw = Math.PI / 2;
  }
  if (name === 'engines') { s.depth = 8; s.ballast = 0.42; player.pos.set(42.6, 0, -0.2); player.yaw = Math.PI / 2; }
  if (name === 'fire') { sim.addFire(RI.CrewMess); sim.fires[sim.fires.length - 1].intensity = 1; sim.smoke[RI.CrewMess] = 0.5; player.pos.set(17.4, 0, 0.3); player.yaw = -Math.PI / 2; }
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
window.__game = { sim, player, inn, ext, camera, enterStation, leaveStation, interact, keys, pumpStroke, loader, poseAvatar, tick, drop, eat, controlUnder, stationKey,
  periscopeMark, periscopeClear, periscopeTag, nearest, griddle, get net() { return net; } };
