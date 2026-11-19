// Inside the boat: loads the two-deck interior, finds stations / doors / hand targets / cameras from the
// glTF extras, builds the walkable decks, live screens, leaks with spray, flood water, smoke, fire and alarms.
import * as THREE from 'three';
import { ROOMS, R as RI, DOORS, ENGINE_FAULTS } from './sim.js';
import { DROP } from './exterior.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { Nav } from './nav.js';
import { Particles } from './particles.js';

const MODELS = '../submarine/models/';
const LIGHT_POOL = 8;          // real point lights, moved to the lamps nearest the camera
const FIRE_LIGHTS = 3;
const Y_AXIS = new THREE.Vector3(0, 1, 0), X_AXIS = new THREE.Vector3(1, 0, 0), NZ_AXIS = new THREE.Vector3(0, 0, -1);
// GLTFLoader drops the '.' from Blender's duplicate suffixes ("Lever.001" -> "Lever001"): compare base names
export const baseName = (n) => n.replace(/\d{3}$/, '');
// Needles turn about the dial's axis; their rest pose is already turned by restDeg. f = 0..1 of full scale.
export function dial(o, restDeg, f) {
  if (!o) return;
  o.userData.rest ||= o.quaternion.clone();
  const deg = -135 + 270 * Math.max(0, Math.min(1, f)) - restDeg;
  o.quaternion.copy(o.userData.rest).multiply(new THREE.Quaternion().setFromAxisAngle(NZ_AXIS, deg * Math.PI / 180));
}

function cloudTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 256;
  const g = c.getContext('2d');
  for (let i = 0; i < 70; i++) {
    const x = Math.random() * 256, y = Math.random() * 256, r = 20 + Math.random() * 50;
    for (const [ox, oy] of [[0, 0], [256, 0], [-256, 0], [0, 256], [0, -256]]) {
      const gr = g.createRadialGradient(x + ox, y + oy, 0, x + ox, y + oy, r);
      gr.addColorStop(0, 'rgba(255,255,255,0.32)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
    }
  }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

export class Interior {
  constructor(renderer, loader) {
    this.renderer = renderer;
    this.loader = loader;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0b0f12);
    this.stations = {};           // key -> {root, cam, hands:[], parts}
    this.interactables = [];      // {pos, radius, label, kind, data}
    this.leakViews = new Map();
    this.fireViews = new Map();
    this.screens = {};
    this.time = 0;
    this.levers = {};             // station key -> current lever angle (rad) for pumps
  }

  async load() {
    const [gltf, navData, normals] = await Promise.all([
      this.loader.loadAsync(`${MODELS}Submarine_Interior.glb`),
      fetch(`${MODELS}nav.json`).then((r) => r.json()),
      new THREE.TextureLoader().loadAsync('assets/waternormals.png'),
    ]);
    this.nav = new Nav(navData);
    this.normals = normals; normals.wrapS = normals.wrapT = THREE.RepeatWrapping;
    this.root = gltf.scene;
    this.scene.add(this.root);
    this.scene.add(new THREE.HemisphereLight(0xfff1dd, 0x34302a, 0.55));
    this.alarm = new THREE.PointLight(0xff2010, 0, 14, 1.2);
    this.scene.add(this.alarm);
    // lamps: keep their positions, drive a small pool of real lights from them
    this.lamps = [];
    const lights = [];
    this.root.traverse((o) => { if (o.isLight) lights.push(o); if (o.isMesh) o.frustumCulled = true; });
    this.root.updateMatrixWorld(true);
    for (const l of lights) {
      const p = l.getWorldPosition(new THREE.Vector3());
      this.lamps.push({ pos: p, color: l.color.clone(), base: l.intensity * 0.0035, distance: l.distance || 9 });
      l.parent.remove(l);
    }
    this.pool = [];
    for (let i = 0; i < LIGHT_POOL; i++) { const l = new THREE.PointLight(0xffffff, 0, 9, 2); this.scene.add(l); this.pool.push(l); }
    this.fireLights = [];
    for (let i = 0; i < FIRE_LIGHTS; i++) { const l = new THREE.PointLight(0xff6418, 0, 6, 1.8); this.scene.add(l); this.fireLights.push(l); }
    this.indexScene();
    this.setupScreens();
    this.mergeStatic();
    this.makeWater();
    this.makeSmoke();
    const [wrench, crack, patch, torpedo] = await Promise.all(['Wrench', 'HullCrack', 'HullPatch', 'Torpedo']
      .map((n) => this.loader.loadAsync(`${MODELS}props/${n}.glb`)));
    this.tpl = { wrench: wrench.scene, crack: crack.scene, patch: patch.scene, torpedo: torpedo.scene };
    // wrenches: torpedo room workbench, control room, galley counter, engine room platform
    this.wrenches = [];
    for (const p of [[6.35, -1.97, 1.95], [9.9, 0.02, -1.6], [23.95, 0.93, 2.05], [42.95, 0.03, 1.75]]) {
      const w = wrench.scene.clone();
      w.position.set(...p); w.rotation.y = Math.random() * 6;
      this.scene.add(w);
      this.wrenches.push(w);
      this.interactables.push({ pos: w.position.clone().add(new THREE.Vector3(0, 0.05, 0)), radius: 0.6, label: 'Pick up WRENCH', kind: 'wrench', data: w });
    }
  }

  // ---------------------------------------------------------- scene index
  indexScene() {
    const box = new THREE.Box3();
    const tops = this.root.children;
    const byStation = {};
    const passable = /Door|Hatch|Lamp|Stool|Torpedo$|Torpedo\.|Poster|Sign|Clock|Extinguisher|Intercom|Monitor|Box|Speaker|Board|Mug|Plate|Steak|Drum|Patty|Tray|Checkers|Toolbox|Junction|Ladder|LoadingCradle|ChainHoist|Stairs|Catwalk|Platform|Rail|PipeBank|DuctFan|Jerrycan|OilCan|FirstAid|SPAWN|Shaft|Beacon/;
    for (const r of tops) {
      const ud = r.userData || {};
      const name = r.name;
      if (ud.station) (byStation[ud.station] ||= []).push(r);
      if (/_Shell|^Bulkhead|CableLooms/.test(name)) continue;
      box.setFromObject(r);
      if (box.isEmpty()) continue;
      const thin = (box.max.x - box.min.x) < 0.05 || (box.max.z - box.min.z) < 0.05;
      if (!thin && !passable.test(name)) this.nav.colliders.push({ minX: box.min.x, maxX: box.max.x, minY: box.min.y, maxY: box.max.y, minZ: box.min.z, maxZ: box.max.z, name });
    }
    // under the stairs on the lower deck (the treads are too low to walk beneath)
    for (const s of this.nav.stairs) {
      this.nav.colliders.push({ minX: s.tx, maxX: s.tx + (s.bx - s.tx) * 0.78, minY: -2.9, maxY: -2.3, minZ: s.zc - 0.56, maxZ: s.zc + 0.56, name: 'UnderStairs' });
    }
    const find = (root, test) => { let f = null; root.traverse((o) => { if (!f && test(o)) f = o; }); return f; };
    const all = (root, test) => { const out = []; root.traverse((o) => { if (test(o)) out.push(o); }); return out; };
    const center = (r) => new THREE.Box3().setFromObject(r).getCenter(new THREE.Vector3());
    const floorOf = (p) => (p.y < -1.45 ? -2.9 : 0);
    const station = (key, root, label, radius = 1.3) => {
      const cam = find(root, (o) => o.isCamera && !/back/.test(o.name));
      const hands = all(root, (o) => o.userData && o.userData.interaction === 'hand_target');
      const parts = {};
      root.traverse((o) => { if (o.userData && (o.userData.interact || o.userData.interaction)) parts[baseName(o.name).replace(baseName(root.name) + '_', '')] = o; });
      // hands that work a moving control ride along with it
      for (const h of hands) {
        const ctl = h.userData.control && parts[h.userData.control];
        if (ctl && /Lever|Breaker/.test(h.userData.control)) ctl.attach(h);
      }
      this.stations[key] = { key, root, cam, hands, parts };
      const c = center(root);
      if (label) this.interactables.push({ pos: new THREE.Vector3(c.x, Math.min(floorOf(c) + 1.3, c.y + 0.2), c.z), radius, label, kind: 'station', data: key });
      return this.stations[key];
    };
    const stationDefs = [
      ['helm', 'navigation', /^NavConsole/, 'Use HELM (throttle & rudder)'],
      ['chart', 'navigation', /^NavTable/, 'Use CHART TABLE'],
      ['weapons', 'weapons', /^FireControl/, 'Use FIRE CONTROL'],
      ['periscope', 'periscope', /^Periscope/, 'Use PERISCOPE'],
      ['sonar', 'sonar', /^SonarStation/, 'Use SONAR'],
      ['ballast', 'ballast', /^BallastPanel/, 'Use BALLAST & DIVE PLANES'],
      ['griddle', 'cooking', /^Griddle/, 'Use GRIDDLE'],
      ['engines', 'engine_control', /^EngineConsole/, 'Use ENGINE CONTROLS (start / stop diesels)'],
      ['fuel', 'fuel', /^FuelStation/, 'Use FUEL TRANSFER PUMP'],
      ['switchboard', 'switchboard', /^MainSwitchboard/, 'Use MAIN SWITCHBOARD (breakers / power)'],
    ];
    for (const [key, st, re, label] of stationDefs) {
      const root = (byStation[st] || []).find((r) => re.test(r.name));
      if (root) station(key, root, label);
    }
    // hand bilge pumps (one per low compartment) and smoke-extract panels (one per room)
    this.pumps = [];
    for (const root of byStation.bilge || []) {
      const room = this.roomAt(root.position.x, root.position.y);
      const st = station(`bilge${room}`, root, `Use BILGE PUMP (${ROOMS[room]?.label || ''})`);
      st.room = room; this.pumps.push(st);
    }
    this.vents = [];
    for (const root of byStation.vent || []) {
      const room = this.roomAt(root.position.x, root.position.y);
      const sw = find(root, (o) => o.userData && o.userData.interact === 'vent_switch');
      const p = new THREE.Vector3(); (sw || root).getWorldPosition(p);
      this.vents.push({ room, root, sw, rest: sw ? sw.quaternion.clone() : null, k: 0 });
      this.interactables.push({ pos: p, radius: 0.8, label: 'SMOKE EXTRACT fans on / off', kind: 'vent', data: room });
    }
    this.fans = tops.filter((r) => /^DuctFan/.test(r.name)).map((r) => ({ room: this.roomAt(r.position.x, r.position.y - 2.4), fan: find(r, (o) => baseName(o.name).endsWith('_Fan')) }));
    // engines
    this.engines = [];
    for (const [i, re] of [[0, /^DieselEngineP/], [1, /^DieselEngineS/]]) {
      const root = tops.find((r) => re.test(r.name)); if (!root) continue;
      const part = (n) => find(root, (o) => baseName(o.name).endsWith(`_${n}`) && !/_HAND_/.test(o.name));
      const v = { root, rest: root.position.clone(), fly: part('Flywheel'), lamp: part('FaultLamp'), valve: part('CoolantValve'),
        gauges: { oil: part('OilGaugeNeedle'), temp: part('TempGaugeNeedle'), rpm: part('RpmGaugeNeedle') }, start: part('StartButton') };
      for (const g of Object.values(v.gauges)) if (g) g.userData.rest = g.quaternion.clone();
      if (v.valve) v.valve.userData.rest = v.valve.quaternion.clone();
      if (v.lamp) v.lamp.traverse((o) => { if (o.isMesh) { o.material = o.material.clone(); v.lampMat = o.material; } });
      const at = (o) => (o ? o.getWorldPosition(new THREE.Vector3()) : null);
      const fault = find(root, (o) => o.userData && o.userData.interaction === 'fault_point');
      if (v.start) this.interactables.push({ pos: at(v.start), radius: 0.6, label: `Diesel ${i + 1}: START / STOP`, kind: 'engine_button', data: i });
      if (v.valve) this.interactables.push({ pos: at(v.valve), radius: 0.7, label: `Diesel ${i + 1}: COOLANT VALVE (open / shut)`, kind: 'coolant', data: i });
      const oil = part('OilFiller');
      if (oil) this.interactables.push({ pos: at(oil), radius: 0.7, label: `Diesel ${i + 1}: OIL FILLER (hold E with an oil can)`, kind: 'oil', data: i });
      if (fault) this.interactables.push({ pos: at(fault), radius: 0.8, label: `Diesel ${i + 1}: INJECTORS (hold E with a wrench)`, kind: 'engine_fault', data: i });
      this.engines.push(v);
    }
    this.spinners = tops.filter((r) => /^Motor[PS]|^ShaftLine/.test(r.name)).map((r) => ({ root: r, engine: r.position.z > 0 ? 1 : 0,
      part: find(r, (o) => baseName(o.name).endsWith('_Shaft')) }));
    // fuel station filler and level glass
    const fuel = this.stations.fuel;
    if (fuel) {
      const cap = find(fuel.root, (o) => o.userData && o.userData.interact === 'fuel_filler');
      if (cap) this.interactables.push({ pos: cap.getWorldPosition(new THREE.Vector3()), radius: 0.9, label: 'DAY TANK FILLER (hold E with a jerrycan)', kind: 'filler', data: null });
      fuel.level = find(fuel.root, (o) => o.userData && o.userData.interact === 'fuel_level');
    }
    // switchboard breakers
    const sb = this.stations.switchboard;
    if (sb) {
      sb.breakers = [];
      for (const side of ['L', 'R']) for (let k = 1; k <= 4; k++) { const b = find(sb.root, (o) => o.userData?.interact === 'breaker' && baseName(o.name).endsWith(`_Breaker${side}${k}`)); sb.breakers.push(b); if (b) b.userData.rest = b.quaternion.clone(); }
      sb.main = find(sb.root, (o) => o.userData && o.userData.interact === 'main_breaker'); if (sb.main) sb.main.userData.rest = sb.main.quaternion.clone();
    }
    // console parts
    const ec = this.stations.engines;
    if (ec) for (const o of Object.values(ec.parts)) if (o.quaternion) o.userData.rest = o.quaternion.clone();
    if (ec) for (const n of ['Fault1', 'Fault2']) ec.parts[n]?.traverse((o) => { if (o.isMesh) { o.material = o.material.clone(); ec.parts[n].userData.mat = o.material; } });
    // torpedo tubes (breech doors) and racks
    const tubes = tops.find((r) => /^TorpedoTubes/.test(r.name));
    this.tubes = [];
    if (tubes) {
      for (let n = 1; n <= 4; n++) {
        const door = find(tubes, (o) => baseName(o.name) === `TorpedoTubes_Door${n}`);
        const wheel = find(tubes, (o) => baseName(o.name) === `TorpedoTubes_Door${n}Wheel`);
        const p = new THREE.Vector3(); (wheel || door).getWorldPosition(p);
        const hands = all(tubes, (o) => o.userData && o.userData.control === `Door${n}Wheel`);
        const cam = find(tubes, (o) => o.isCamera && o.name.includes(`tube${n}`));
        this.tubes.push({ n, door, wheel, rest: door ? door.quaternion.clone() : null, open: 0 });
        this.stations[`tube${n}`] = { key: `tube${n}`, root: tubes, cam, hands, parts: { wheel } };
        this.interactables.push({ pos: p, radius: 0.9, label: `TUBE ${n}`, kind: 'tube', data: n });
      }
    }
    for (const r of tops.filter((o) => /^TorpedoRack/.test(o.name))) {
      const c = center(r);
      this.interactables.push({ pos: c.setY(floorOf(c) + 0.9), radius: 1.4, label: 'Take TORPEDO from rack', kind: 'rack', data: r });
    }
    this.rackTorpedoes = tops.filter((o) => /^Torpedo\d*$/.test(o.name) && Math.abs(o.position.z) > 1.2);
    // watertight doors, matched to the simulation's door list by position
    this.doors = DOORS.map(() => null);
    for (const r of tops.filter((o) => /^WatertightDoor|^EngineRoomDoor/.test(o.name))) {
      const i = DOORS.findIndex((d) => Math.abs(r.position.x - (d.x + 0.15)) < 0.3 && Math.abs(r.position.y - d.sill) < 0.5);
      if (i < 0) continue;
      const leaf = find(r, (o) => baseName(o.name).endsWith('_Leaf'));
      this.interactables.push({ pos: r.position.clone().setY(DOORS[i].sill + 1.0), radius: 1.0, label: 'Open/close WATERTIGHT DOOR', kind: 'door', data: i });
      this.doors[i] = { root: r, leaf, rest: leaf ? leaf.quaternion.clone() : null, open: 1 };
    }
    // medical
    this.medbed = tops.find((r) => /^MedBed/.test(r.name));
    if (this.medbed) {
      const lie = find(this.medbed, (o) => o.userData && o.userData.interaction === 'lie');
      this.medbed.userData.lie = lie ? lie.getWorldPosition(new THREE.Vector3()) : center(this.medbed).setY(0.9);
      this.interactables.push({ pos: center(this.medbed).setY(0.7), radius: 1.3, label: 'Lie on the MED BED (heals you)', kind: 'medbed', data: null });
    }
    this.cabinet = tops.find((r) => /^MedicalCabinet/.test(r.name));
    if (this.cabinet) {
      this.cabinet.userData.kits = 3;
      this.cabinet.userData.doors = all(this.cabinet, (o) => /_Door[LR]$/.test(baseName(o.name))).map((d) => ({ d, rest: d.quaternion.clone() }));
      this.interactables.push({ pos: center(this.cabinet), radius: 1.0, label: 'MEDICAL CABINET: take a first-aid kit', kind: 'medcab', data: this.cabinet });
    }
    const spawn = find(this.root, (o) => /SPAWN_Medical/.test(o.name));
    this.medSpawn = spawn ? spawn.getWorldPosition(new THREE.Vector3()) : new THREE.Vector3(1.35, 0, 0.55);
    // pickups
    const ITEMS = [[/^Jerrycan/, 'fuel_can', 'Pick up JERRYCAN (20 L diesel)'], [/^OilCan/, 'oil_can', 'Pick up OIL CAN'], [/^FirstAidKit/, 'first_aid', 'Pick up FIRST-AID KIT']];
    for (const [re, item, label] of ITEMS) {
      for (const r of tops.filter((o) => re.test(o.name))) {
        const c = center(r);
        this.interactables.push({ pos: c, radius: 0.6, label, kind: 'pickup', data: { obj: r, item } });
      }
    }
    // misc
    const add = (re, label, kind, dy = 1.1, radius = 1.2) => {
      for (const r of tops.filter((o) => re.test(o.name))) {
        const c = center(r);
        this.interactables.push({ pos: c.setY(floorOf(c) + dy), radius, label, kind, data: r });
      }
    };
    add(/^Ladder/, 'Climb to the BRIDGE (when surfaced)', 'ladder', 1.4);
    add(/^ElectricalCabinet/, 'HULL SHOCK (shake off creatures)', 'shock', 1.2, 1.0);
    add(/^FireExtinguisher/, 'Take FIRE EXTINGUISHER', 'extinguisher', 0.6, 0.8);
    add(/^Fridge|^WireShelf/, 'Take RAW FOOD', 'food', 1.1, 1.0);
    add(/^CoffeeStation/, 'Drink COFFEE (stamina)', 'coffee', 1.0, 1.0);
    add(/^WallMonitor/, 'EXTERNAL CAMERA view', 'chase', 1.8, 1.0);
    add(/^MessTable/, 'EAT cooked food', 'eat', 0.8, 1.4);
    add(/^BunkBed/, 'Rest (restore stamina)', 'rest', 0.6, 1.2);
    // the quarters' wire shelf holds first-aid kits, not food
    this.interactables = this.interactables.filter((it) => !(it.kind === 'food' && it.pos.x < 7.2));
  }

  // Merge every non-moving mesh by material per room and deck: ~1500 draw calls -> ~200.
  mergeStatic() {
    const keep = (o) => {
      for (let p = o; p; p = p.parent) {
        const ud = p.userData || {};
        const n = baseName(p.name || '');
        if (ud.interact || ud.item || /^Torpedo$/.test(n) || /Leaf|Door\d|Head$|Joystick|Wheel|^DieselEngine|^Motor[PS]|^ShaftLine|^Jerrycan|^OilCan|^FirstAidKit/.test(n)) return true;
      }
      return false;
    };
    const groups = new Map();
    const remove = [];
    this.root.updateMatrixWorld(true);
    this.root.traverse((o) => {
      if (!o.isMesh || o.isSkinnedMesh || Array.isArray(o.material) || keep(o)) return;
      const g = o.geometry.clone().applyMatrix4(o.matrixWorld);
      for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'uv', 'tangent'].includes(k)) g.deleteAttribute(k);
      if (!g.attributes.uv) return;
      g.computeBoundingBox();
      const c = g.boundingBox.getCenter(new THREE.Vector3());
      const room = Math.max(0, this.roomAt(c.x, c.y));
      const key = o.material.uuid + (g.index ? 'i' : 'n') + (g.attributes.tangent ? 't' : '') + room;
      if (!groups.has(key)) groups.set(key, { mat: o.material, geos: [] });
      groups.get(key).geos.push(g);
      remove.push(o);
    });
    for (const o of remove) o.parent.remove(o);
    for (const { mat, geos } of groups.values()) {
      const merged = mergeGeometries(geos, false);
      if (!merged) continue;
      const m = new THREE.Mesh(merged, mat);
      m.matrixAutoUpdate = false;
      this.scene.add(m);
    }
  }

  // --------------------------------------------------------------- screens
  setupScreens() {
    const mats = new Map();
    this.root.traverse((o) => {
      if (!o.isMesh) return;
      for (const m of [].concat(o.material)) if (m && /^screen_/.test(m.name)) mats.set(m.name, (mats.get(m.name) || []).concat(m));
    });
    const make = (name, w, h) => {
      const canvas = document.createElement('canvas'); canvas.width = w; canvas.height = h;
      const tex = new THREE.CanvasTexture(canvas); tex.colorSpace = THREE.SRGBColorSpace; tex.flipY = false;
      for (const m of mats.get(name) || []) { m.emissiveMap = tex; m.map = tex; m.emissive = new THREE.Color(1, 1, 1); m.emissiveIntensity = 1.4; m.needsUpdate = true; }
      return { canvas, ctx: canvas.getContext('2d'), tex };
    };
    for (const n of ['screen_chart', 'screen_nav_scope', 'screen_sonar', 'screen_fire_control', 'screen_ballast', 'screen_target_id', 'screen_engine']) {
      this.screens[n] = make(n, n === 'screen_chart' ? 768 : 512, n === 'screen_chart' ? 512 : n === 'screen_target_id' ? 256 : 512);
    }
    this.camTargets = {};
    for (const n of ['screen_cam_fwd', 'screen_cam_aft']) {
      const rt = new THREE.WebGLRenderTarget(384, 288);
      for (const m of mats.get(n) || []) { m.emissiveMap = rt.texture; m.map = rt.texture; m.emissive = new THREE.Color(1, 1, 1); m.emissiveIntensity = 1.2; m.needsUpdate = true; }
      this.camTargets[n] = { rt, cam: new THREE.PerspectiveCamera(60, 4 / 3, 0.5, 3000) };
    }
  }

  drawScreens(sim) {
    const s = sim.sub;
    const deg = (a) => sim.deg(a);
    for (const key of ['screen_chart', 'screen_nav_scope']) {
      const sc = this.screens[key]; if (!sc) continue;
      const { ctx, canvas } = sc, W = canvas.width, H = canvas.height, round = key === 'screen_nav_scope';
      const scale = key === 'screen_chart' ? 0.22 : 0.3;
      ctx.fillStyle = round ? '#1a0e02' : '#cfe3e6'; ctx.fillRect(0, 0, W, H);
      ctx.save(); ctx.translate(W / 2, H / 2);
      ctx.strokeStyle = round ? '#ffae2e55' : '#5b7d8a55'; ctx.lineWidth = 1;
      for (let g = -2000; g <= 2000; g += 200) {
        ctx.beginPath(); ctx.moveTo((g - s.x % 200) * scale, -H); ctx.lineTo((g - s.x % 200) * scale, H); ctx.stroke();
        ctx.beginPath(); ctx.moveTo(-W, (g - s.z % 200) * scale); ctx.lineTo(W, (g - s.z % 200) * scale); ctx.stroke();
      }
      for (const [id, c] of sim.contacts) {
        const e = sim.entities.find((q) => q.id === id);
        if (!e || !e.alive || sim.time - c.lastSeen > 30) continue;
        const px = (e.x - s.x) * scale, pz = (e.z - s.z) * scale;
        ctx.fillStyle = e.kind === 'freighter' ? '#2e7d32' : e.kind === 'squid' || e.kind === 'shark' ? '#8e24aa' : '#d32f2f';
        if (round) ctx.fillStyle = '#ffcc66';
        ctx.beginPath(); ctx.arc(px, pz, e.id === sim.weapons.lock ? 9 : 6, 0, 7); ctx.fill();
        ctx.font = '16px monospace'; ctx.fillText(e.kind.toUpperCase(), px + 9, pz - 6);
      }
      const lk = sim.entities.find((q) => q.id === sim.weapons.lock && q.alive);
      if (lk) { ctx.setLineDash([8, 6]); ctx.strokeStyle = round ? '#ffe0a0' : '#c62828'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo((lk.x - s.x) * scale, (lk.z - s.z) * scale); ctx.stroke(); ctx.setLineDash([]); }
      for (const tp of sim.torpedoes) { ctx.fillStyle = tp.owner === 'player' ? '#1565c0' : '#ff1744'; ctx.fillRect((tp.x - s.x) * scale - 2, (tp.z - s.z) * scale - 2, 4, 4); }
      ctx.rotate(-s.heading); ctx.fillStyle = round ? '#ffe0a0' : '#0d47a1';
      ctx.beginPath(); ctx.moveTo(14, 0); ctx.lineTo(-10, -7); ctx.lineTo(-10, 7); ctx.fill();
      ctx.restore();
      ctx.fillStyle = round ? '#ffae2e' : '#102030'; ctx.font = 'bold 22px monospace';
      ctx.fillText(`HDG ${deg(s.heading)}°  SPD ${s.speed.toFixed(1)}  DEPTH ${s.depth.toFixed(0)}m`, 16, H - 18);
      sc.tex.needsUpdate = true;
    }
    const so = this.screens.screen_sonar;
    if (so) {
      const { ctx } = so, R = 230;
      ctx.fillStyle = 'rgba(0,12,4,0.25)'; ctx.fillRect(0, 0, 512, 512);
      ctx.save(); ctx.translate(256, 256);
      ctx.strokeStyle = '#1f8f4a'; for (const r of [R / 3, 2 * R / 3, R]) { ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.stroke(); }
      const sweep = (sim.time * 1.6) % (Math.PI * 2);
      ctx.strokeStyle = '#53ff8a'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(sweep) * R, Math.sin(sweep) * R); ctx.stroke();
      for (const [id] of sim.contacts) {
        const e = sim.entities.find((q) => q.id === id); if (!e || !e.alive) continue;
        const rel = Math.atan2(-(e.z - s.z), e.x - s.x) - s.heading;
        const rng = Math.min(1, Math.hypot(e.x - s.x, e.z - s.z) / 1500) * R;
        const x = Math.sin(rel) * -rng, y = -Math.cos(rel) * rng;
        ctx.fillStyle = e.id === sim.weapons.lock ? '#ffffff' : '#7dffb0'; ctx.beginPath(); ctx.arc(x, y, 5, 0, 7); ctx.fill();
      }
      ctx.restore();
      so.tex.needsUpdate = true;
    }
    const fc = this.screens.screen_fire_control;
    if (fc) {
      const { ctx } = fc;
      ctx.fillStyle = '#080a08'; ctx.fillRect(0, 0, 512, 512);
      ctx.fillStyle = '#ffb52e'; ctx.font = 'bold 30px monospace'; ctx.fillText('FIRE CONTROL', 20, 44);
      ctx.font = '22px monospace';
      const lock = sim.entities.find((e) => e.id === sim.weapons.lock && e.alive);
      ctx.fillText(lock ? `TGT ${lock.kind.toUpperCase()} BRG ${deg(Math.atan2(-(lock.z - s.z), lock.x - s.x))}` : 'NO TARGET LOCK', 20, 84);
      ctx.fillText(lock ? `RNG ${Math.hypot(lock.x - s.x, lock.z - s.z).toFixed(0)} m` : 'MARK ONE AT PERISCOPE/SONAR', 20, 114);
      sim.tubes.forEach((t, i) => {
        const x = 20 + i * 122, y = 150, sel = sim.weapons.selected === t.n;
        ctx.strokeStyle = '#ffb52e'; ctx.lineWidth = sel ? 5 : 2; ctx.strokeRect(x, y, 110, 210);
        ctx.fillStyle = '#ffb52e'; ctx.fillText(`TUBE ${t.n}`, x + 8, y + 30);
        ctx.fillStyle = t.loaded ? '#7dff7d' : '#ff5d5d'; ctx.fillText(t.loaded ? 'LOADED' : 'EMPTY', x + 8, y + 70);
        ctx.fillStyle = t.flooded ? '#64b5f6' : '#777'; ctx.fillText(t.flooded ? 'FLOODED' : 'DRY', x + 8, y + 110);
        ctx.fillStyle = t.outerOpen ? '#7dff7d' : '#777'; ctx.fillText(t.outerOpen ? 'DOOR OPEN' : 'DOOR SHUT', x + 4, y + 150);
        ctx.fillStyle = t.breechOpen ? '#ff5d5d' : '#777'; ctx.fillText(t.breechOpen ? 'BREECH!' : '', x + 8, y + 190);
      });
      ctx.fillStyle = sim.weapons.armed ? '#ff5d5d' : '#777'; ctx.fillText(sim.weapons.armed ? 'ARMED' : 'SAFE', 20, 410);
      ctx.fillStyle = '#ffb52e'; ctx.fillText(`SPARES ${sim.torpedoStock}  DECOYS ${s.countermeasures}`, 20, 450);
      fc.tex.needsUpdate = true;
    }
    const bl = this.screens.screen_ballast;
    if (bl) {
      const { ctx } = bl;
      ctx.fillStyle = '#04100a'; ctx.fillRect(0, 0, 512, 512);
      ctx.fillStyle = '#7dffb0'; ctx.font = 'bold 30px monospace'; ctx.fillText('DIVE STATUS', 20, 44);
      ctx.font = '24px monospace';
      [`DEPTH  ${s.depth.toFixed(1)} m`, `RATE   ${(s.vy * 60).toFixed(0)} m/min`, `BALLAST ${(s.ballast * 100).toFixed(0)} %`,
        `PLANES ${s.planes > 0.05 ? 'RISE' : s.planes < -0.05 ? 'DIVE' : 'LEVEL'}`, `VALVE  ${s.valve.toUpperCase()}`, `AIR    ${s.air.toFixed(0)} %`,
        `HULL   ${s.hull.toFixed(0)} %`, `FLOOD  ${(sim.floodFraction() * 100).toFixed(0)} %`].forEach((l, i) => ctx.fillText(l, 20, 96 + i * 44));
      bl.tex.needsUpdate = true;
    }
    const en = this.screens.screen_engine;
    if (en) {
      const { ctx } = en;
      ctx.fillStyle = '#06100c'; ctx.fillRect(0, 0, 512, 512);
      ctx.fillStyle = '#7dffb0'; ctx.font = 'bold 30px monospace'; ctx.fillText('ENGINES', 20, 44);
      ctx.font = '21px monospace';
      sim.engines.forEach((e, i) => {
        const y = 88 + i * 150;
        ctx.fillStyle = e.fault ? '#ff5d5d' : e.running ? '#7dff7d' : e.crank ? '#ffe07d' : '#9aa';
        ctx.fillText(`DIESEL ${e.id}  ${e.fault ? 'FAULT' : e.running ? 'RUNNING' : e.crank ? 'CRANKING' : 'STOPPED'}`, 20, y);
        ctx.fillStyle = '#bfe';
        ctx.fillText(`RPM ${e.rpm.toFixed(0).padStart(4)}  TEMP ${e.temp.toFixed(0)}°C`, 20, y + 32);
        ctx.fillText(`OIL ${e.oil.toFixed(0)}%  COOLANT ${e.coolant ? 'OPEN' : 'SHUT!'}`, 20, y + 62);
        if (e.fault) { ctx.fillStyle = '#ff5d5d'; ctx.fillText(ENGINE_FAULTS[e.fault].toUpperCase(), 20, y + 92); }
      });
      ctx.fillStyle = '#ffe07d';
      ctx.fillText(`DAY TANK ${sim.fuel.day.toFixed(0)} L  MAIN ${sim.fuel.main.toFixed(0)} L`, 20, 410);
      ctx.fillText(`BATTERY ${s.battery.toFixed(0)}%  ${s.charging ? 'CHARGING +' + (s.charging * 60).toFixed(0) + '%/min' : 'DISCHARGING'}`, 20, 446);
      ctx.fillStyle = s.depth > 12 ? '#ff5d5d' : '#7dff7d';
      ctx.fillText(s.depth > 12 ? `SNORKEL UNDER (${s.depth.toFixed(0)} m)` : 'SNORKEL CLEAR - AIR OK', 20, 482);
      en.tex.needsUpdate = true;
    }
  }

  renderMonitors(ext, sim) {
    for (const [n, m] of Object.entries(this.camTargets)) {
      ext.monitorCamera(sim, m.cam, n.endsWith('aft'));
      const prev = ext.camera; ext.camera = m.cam; ext.setUnderwater(); ext.camera = prev;
      ext.render(m.rt, m.cam);
    }
  }

  // ------------------------------------------------------------ flooding
  makeWater() {
    const vert = (shader) => {
      shader.uniforms.uTime = this.waterTime;
      shader.vertexShader = 'uniform float uTime;\n' + shader.vertexShader.replace('#include <begin_vertex>',
        '#include <begin_vertex>\ntransformed.z += sin(position.x * 2.3 + uTime * 1.9) * 0.018 + cos(position.y * 3.1 + uTime * 1.4) * 0.014 + sin((position.x + position.y) * 5.0 + uTime * 3.0) * 0.006;');
      // clear when you look straight down, mirror-like at a glancing angle (Fresnel), with moving caustic glints
      shader.fragmentShader = 'uniform float uTime;\n' + shader.fragmentShader.replace('#include <opaque_fragment>',
        `float fres = pow(1.0 - clamp(abs(dot(normalize(vViewPosition), normal)), 0.0, 1.0), 2.5);
         diffuseColor.a = mix(0.42, 0.94, fres);
         outgoingLight *= mix(0.75, 1.15, fres);
         #include <opaque_fragment>`);
    };
    this.waterTime = { value: 0 };
    this.waterMeshes = ROOMS.map((r) => {
      const g = new THREE.Group();
      const surf = new THREE.Mesh(new THREE.PlaneGeometry(r.x1 - r.x0 + 0.02, r.halfW * 2 - 0.02, 48, 12),
        new THREE.MeshStandardMaterial({ color: 0x1a6474, transparent: true, opacity: 0.6, roughness: 0.03, metalness: 0.05,
          normalMap: this.normals, normalScale: new THREE.Vector2(0.5, 0.5), side: THREE.DoubleSide, depthWrite: false }));
      surf.material.onBeforeCompile = vert;
      surf.rotation.x = -Math.PI / 2;
      surf.renderOrder = 1;
      const body = new THREE.Mesh(new THREE.BoxGeometry(r.x1 - r.x0 - 0.04, 1, r.halfW * 2 - 0.06),
        new THREE.MeshBasicMaterial({ color: 0x06323d, transparent: true, opacity: 0.5, depthWrite: false, side: THREE.BackSide }));
      body.position.y = -0.5;
      g.add(body); g.add(surf);
      g.position.set((r.x0 + r.x1) / 2, r.bottom, 0); g.visible = false;
      g.userData = { surf, body };
      this.scene.add(g);
      return g;
    });
    // splashes where leak jets hit the water / floor
    this.splash = new Particles(500, { kind: 'drop', additive: false });
    this.scene.add(this.splash.points);
  }

  makeSmoke() {
    const tex = cloudTexture();
    this.smokeLayers = ROOMS.map((r, i) => {
      const g = new THREE.Group();
      const top = r.deck === 'lower' ? -0.18 : 2.75;
      for (let k = 0; k < 4; k++) {
        const t = tex.clone(); t.needsUpdate = true; t.repeat.set((r.x1 - r.x0) / 3.5, 1.3);
        const m = new THREE.Mesh(new THREE.PlaneGeometry(r.x1 - r.x0, r.halfW * 2),
          new THREE.MeshBasicMaterial({ map: t, color: 0x27241f, transparent: true, opacity: 0, depthWrite: false, side: THREE.DoubleSide }));
        m.rotation.x = -Math.PI / 2;
        m.position.set((r.x0 + r.x1) / 2, top - k * 0.38, 0);
        m.userData = { k, t, room: i };
        g.add(m);
      }
      g.visible = false;
      this.scene.add(g);
      return g;
    });
    // fire particle systems (shared, positioned per fire)
    this.flames = new Particles(900, { kind: 'flame', premul: true, cover: 0.6 });
    this.embers = new Particles(300, { kind: 'ember', premul: true, cover: 0.3 });
    this.smokeFx = new Particles(700, { kind: 'smoke', additive: false });
    for (const p of [this.flames, this.embers, this.smokeFx]) this.scene.add(p.points);
    this.fanFx = new Particles(240, { kind: 'smoke', additive: false });
    this.scene.add(this.fanFx.points);
    this.steamFx = new Particles(260, { kind: 'smoke', additive: false });     // engine steam and exhaust leaks
    this.bubbles = new Particles(200, { kind: 'drop', additive: false });      // your breath underwater
    this.scene.add(this.steamFx.points); this.scene.add(this.bubbles.points);
  }

  spawnLeak(l) {
    const g = new THREE.Group();
    const crack = this.tpl.crack.clone();
    crack.rotation.y = l.side > 0 ? 0 : Math.PI;    // the model faces +Z (into the room) for a port-side leak
    g.add(crack);
    const r = ROOMS[l.room];
    g.position.set(l.x, l.y, l.z ?? -l.side * (r.halfW - 0.47));
    const n = 260, geo = new THREE.BufferGeometry(), pos = new Float32Array(n * 3), vel = [];
    for (let i = 0; i < n; i++) vel.push(new THREE.Vector3());
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const spray = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xd8f3fb, size: 0.07, map: DROP, transparent: true, opacity: 0.8, depthWrite: false }));
    spray.frustumCulled = false;
    this.scene.add(g); this.scene.add(spray);
    const age = new Float32Array(n).map(() => Math.random());
    this.leakViews.set(l.id, { g, spray, vel, age, leak: l });
    this.interactables.push({ pos: g.position.clone(), radius: 1.1, label: 'FIX LEAK (hold E with a wrench)', kind: 'leak', data: l.id });
  }

  spawnFire(f) {
    const base = new THREE.Vector3(f.x, f.y ?? 0.05, f.z ?? 0);
    this.fireViews.set(f.id, { base, fire: f, light: null });
    this.interactables.push({ pos: base.clone().add(new THREE.Vector3(0, 0.6, 0)), radius: 1.6, label: 'PUT OUT FIRE (hold E with an extinguisher)', kind: 'fire', data: f.id });
  }

  removeFire(f) {
    this.fireViews.delete(f.id);
    this.interactables = this.interactables.filter((i) => !(i.kind === 'fire' && i.data === f.id));
  }

  fixLeakView(l) {
    const v = this.leakViews.get(l.id); if (!v) return;
    this.scene.remove(v.spray); v.g.clear();
    const patch = this.tpl.patch.clone(); patch.rotation.y = l.side > 0 ? 0 : Math.PI;
    v.g.add(patch);
    this.leakViews.delete(l.id);
    this.interactables = this.interactables.filter((i) => !(i.kind === 'leak' && i.data === l.id));
  }

  update(sim, dt, camera) {
    this.time += dt;
    const camPos = camera.getWorldPosition(new THREE.Vector3());
    const H = this.renderer.domElement.height;
    for (const p of [this.flames, this.embers, this.smokeFx, this.splash, this.fanFx, this.steamFx, this.bubbles]) p.setScale(H);
    // leaks: high pressure spray, stronger with depth; splashes where it lands
    for (const v of this.leakViews.values()) {
      const p = v.spray.geometry.attributes.position, o = v.g.position, inward = -Math.sign(o.z);
      const speed = 3 + sim.sub.depth / 25;
      const floor = Math.max(sim.surface(v.leak.room), ROOMS[v.leak.room].floor);
      for (let i = 0; i < v.age.length; i++) {
        v.age[i] += dt * (1.2 + Math.random());
        if (v.age[i] > 1) {
          v.age[i] = 0;
          p.array.set([o.x, o.y, o.z], i * 3);
          v.vel[i].set((Math.random() - 0.5) * 1.2, (Math.random() - 0.3) * 1.5, inward * speed * (0.7 + Math.random() * 0.6));
        }
        v.vel[i].y -= 9.8 * dt;
        p.array[i * 3] += v.vel[i].x * dt; p.array[i * 3 + 1] += v.vel[i].y * dt; p.array[i * 3 + 2] += v.vel[i].z * dt;
        if (p.array[i * 3 + 1] < floor) {
          if (Math.random() < 0.25) this.splash.emit([p.array[i * 3], floor + 0.01, p.array[i * 3 + 2]], [(Math.random() - 0.5) * 1.4, 1 + Math.random() * 1.5, (Math.random() - 0.5) * 1.4], 0.45, 0.05, 0.02);
          v.age[i] = 2;
          p.array[i * 3 + 1] = -100;
        }
      }
      p.needsUpdate = true;
    }
    this.splash.update(dt, (i, t) => [0.85, 0.95, 1.0, 0.7 * (1 - t)], (i) => { this.splash.vel[i * 3 + 1] -= 9.8 * dt; });
    const bb = this.bubbles;
    bb.update(dt, (i, t) => [0.8, 0.95, 1.0, 0.75 * (1 - t * t)], (i, dt2) => { bb.vel[i * 3] += Math.sin(this.time * 11 + i) * dt2 * 0.8; });
    // fires: flames, embers and smoke plumes
    const fires = [...this.fireViews.values()];
    fires.sort((a, b) => a.base.distanceTo(camPos) - b.base.distanceTo(camPos));
    this.fireLights.forEach((l, i) => {
      const v = fires[i];
      if (!v) { l.intensity = 0; return; }
      l.position.copy(v.base).add(new THREE.Vector3(0, 0.8, 0));
      l.intensity = (2.2 + Math.random() * 2.2) * Math.max(0.15, v.fire.intensity);
    });
    for (const v of fires) {
      const k = Math.max(0.1, v.fire.intensity), b = v.base, room = ROOMS[v.fire.room];
      const ceil = room.deck === 'lower' ? -0.2 : 2.8;
      for (let j = 0; j < Math.round(dt * 420 * k + Math.random()); j++) {
        const a = Math.random() * 6.28, r = Math.sqrt(Math.random()) * 0.45 * (0.5 + k * 0.6);
        const centre = 1 - r / 0.6;                    // tongues in the middle burn taller
        this.flames.emit([b.x + Math.cos(a) * r, b.y + Math.random() * 0.08, b.z + Math.sin(a) * r * 0.8],
          [(Math.random() - 0.5) * 0.25, (1.2 + Math.random() * 1.4) * (0.6 + 0.6 * k) * (0.7 + centre * 0.6), (Math.random() - 0.5) * 0.25],
          0.3 + Math.random() * 0.45, 0.32 + 0.3 * k, 0.04);
      }
      if (Math.random() < dt * 30 * k) this.embers.emit([b.x + (Math.random() - 0.5) * 0.6, b.y + 0.2, b.z + (Math.random() - 0.5) * 0.5],
        [(Math.random() - 0.5) * 0.8, 1.8 + Math.random() * 1.8, (Math.random() - 0.5) * 0.8], 1.2 + Math.random(), 0.07, 0.03);
      for (let j = 0; j < Math.round(dt * 40 * k + Math.random()); j++) {
        this.smokeFx.emit([b.x + (Math.random() - 0.5) * 0.5, b.y + 0.9 + Math.random() * 0.4, b.z + (Math.random() - 0.5) * 0.5],
          [(Math.random() - 0.5) * 0.4, 0.6 + Math.random() * 0.5, (Math.random() - 0.5) * 0.4], 4 + Math.random() * 3, 0.45, 2.8);
        this.smokeFx.ceil = ceil;
      }
      v.ceil = ceil;
    }
    const t0 = this.time;
    this.flames.update(dt, (i, t) => {
      const w = 1 - t;
      const g = t < 0.25 ? 0.78 - t * 0.9 : Math.max(0.08, 0.56 - (t - 0.25) * 0.75);
      return [1.0 - t * 0.25, g, Math.max(0.0, 0.32 - t * 0.6), Math.min(1, t * 7) * w * 0.95];
    }, (i, dt2) => { const v = this.flames.vel; v[i * 3] += Math.sin(t0 * 9 + i) * dt2 * 1.2; v[i * 3 + 2] += Math.cos(t0 * 7 + i * 1.7) * dt2 * 1.2; });
    this.embers.update(dt, (i, t) => [1, 0.55, 0.15, (1 - t) * (0.6 + Math.random() * 0.4)], (i, dt2) => { const v = this.embers.vel; v[i * 3] += (Math.random() - 0.5) * dt2 * 6; v[i * 3 + 2] += (Math.random() - 0.5) * dt2 * 6; });
    const smk = this.smokeFx;
    smk.update(dt, (i, t) => [0.16 + t * 0.08, 0.15 + t * 0.08, 0.14 + t * 0.08, Math.min(1, t * 4) * (1 - t) * 0.42], (i, dt2) => {
      // rise, then mushroom out under the deckhead
      const y = smk.pos[i * 3 + 1], c = (y > 0.8 ? 2.8 : -0.2);
      if (y > c - 0.3) { smk.vel[i * 3 + 1] *= 0.8; smk.vel[i * 3] += (Math.random() - 0.5) * dt2 * 3; smk.vel[i * 3 + 2] += (Math.random() - 0.5) * dt2 * 3; }
    });
    // flood water: one sloshing surface per compartment
    this.waterTime.value = this.time;
    this.normals.offset.set(this.time * 0.02, this.time * 0.013);
    sim.water.forEach((w, i) => {
      const g = this.waterMeshes[i], r = ROOMS[i];
      g.visible = w > 0.015;
      if (!g.visible) return;
      g.position.y = r.bottom + w;
      g.userData.body.scale.y = Math.max(0.01, w - 0.02);
      g.userData.body.position.y = -w / 2 + 0.01;
      g.userData.body.material.opacity = Math.min(0.66, 0.32 + w * 0.2);
      g.rotation.x = -sim.sub.roll * 0.5;
      g.rotation.z = Math.sin(this.time * 0.6 + i) * 0.004 + sim.sub.pitch * 0.4;
    });
    // smoke layers under the deckheads
    sim.smoke.forEach((s, i) => {
      const g = this.smokeLayers[i];
      g.visible = s > 0.02;
      if (!g.visible) return;
      for (const m of g.children) {
        const k = m.userData.k;
        m.material.opacity = Math.min(0.85, s * (1.3 - k * 0.25));
        m.userData.t.offset.set(this.time * (0.01 + k * 0.006) * (k % 2 ? -1 : 1), this.time * 0.004 * k);
      }
    });
    // doors
    sim.doors.forEach((open, i) => {
      const d = this.doors[i]; if (!d || !d.leaf) return;
      d.open += ((open ? 1 : 0) - d.open) * Math.min(1, dt * 3);
      d.leaf.quaternion.copy(d.rest).multiply(new THREE.Quaternion().setFromAxisAngle(Y_AXIS, -1.75 * d.open));
    });
    // tube breech doors
    sim.tubes.forEach((t, i) => {
      const v = this.tubes[i]; if (!v || !v.door) return;
      v.open += ((t.breechOpen ? 1 : 0) - v.open) * Math.min(1, dt * 3);
      v.door.quaternion.copy(v.rest).multiply(new THREE.Quaternion().setFromAxisAngle(Y_AXIS, -1.8 * v.open));
    });
    this.rackTorpedoes.forEach((t, i) => { t.visible = i < sim.torpedoStock; });
    this.animateMachinery(sim, dt);
    // alarm: rotating red light in the compartment you are in
    const danger = sim.leaks.some((l) => !l.fixed) || sim.sub.hull < 40 || sim.torpedoes.some((t) => t.owner !== 'player') || sim.sub.lost;
    const ci = this.roomAt(camPos.x, camPos.y - 1.6);
    if (ci >= 0) { const r = ROOMS[ci]; this.alarm.position.set(Math.max(r.x0 + 0.5, Math.min(r.x1 - 0.5, camPos.x + 1.5)), r.deck === 'lower' ? -0.5 : 2.5, 0); }
    this.alarm.intensity = danger || !sim.power || sim.fires.some((f) => !f.out) ? (Math.sin(this.time * 6) > 0 ? 18 : 2) : 0;
    // lamps: the nearest ones (same deck first) get the real lights
    this.flicker = Math.max(0, (this.flicker || 0) - dt);
    const dim = (0.55 + 0.45 * sim.sub.hull / 100) * (sim.power ? 1 : 0.04);
    this._lampT = (this._lampT || 0) - dt;
    if (this._lampT <= 0) {
      this._lampT = 0.2;
      const deckOf = (y) => (y < -0.6 ? 0 : 1);
      const cd = deckOf(camPos.y - 1.0);
      this.lamps.forEach((l) => { l.score = l.pos.distanceTo(camPos) + (deckOf(l.pos.y - 2.0) === cd ? 0 : 7); });
      this.nearLamps = [...this.lamps].sort((a, b) => a.score - b.score).slice(0, LIGHT_POOL);
    }
    this.pool.forEach((pl, i) => {
      const l = this.nearLamps?.[i];
      if (!l) { pl.intensity = 0; return; }
      pl.position.copy(l.pos); pl.color.copy(l.color); pl.distance = l.distance;
      pl.intensity = l.base * dim * (this.flicker > 0 && Math.random() < 0.5 ? Math.random() * 0.3 : 1);
    });
  }

  animateMachinery(sim, dt) {
    const set = (o, axis, ang) => { if (!o) return; o.userData.rest ||= o.quaternion.clone(); o.quaternion.copy(o.userData.rest).multiply(new THREE.Quaternion().setFromAxisAngle(axis, ang)); };
    // diesels: flywheel, gauges, fault lamp, a little shudder while running
    sim.engines.forEach((e, i) => {
      const v = this.engines[i]; if (!v) return;
      v.spin = (v.spin || 0) + dt * e.rpm / 60 * 6.283;
      set(v.fly, X_AXIS, v.spin);
      dial(v.gauges.rpm, -120, e.rpm / 900);
      dial(v.gauges.temp, -60, (e.temp - 20) / 120);
      dial(v.gauges.oil, -30, e.oil / 100);
      v.valveAng = (v.valveAng || 0) + ((e.coolant ? 0 : -2.6) - (v.valveAng || 0)) * Math.min(1, dt * 4);
      set(v.valve, Y_AXIS, v.valveAng);
      if (v.lampMat) { const on = e.fault || !e.coolant || e.temp > 105; v.lampMat.emissive?.setHex(on && Math.sin(this.time * 8) > -0.3 ? 0xff2010 : 0x000000); if (v.lampMat.emissive) v.lampMat.emissiveIntensity = 3; }
      // a sick diesel shows it: black smoke from the injectors, steam when it overheats
      const top = v.root.position;
      if (e.running && e.fault === 'injector' && Math.random() < dt * 14) {
        const i = this.steamFx.emit([top.x + (Math.random() - 0.5) * 4.5, top.y + 2.3, top.z + (Math.random() - 0.5) * 0.4], [(Math.random() - 0.5) * 0.3, 0.5 + Math.random() * 0.4, (Math.random() - 0.5) * 0.3], 3.5, 0.3, 1.6);
        this.steamFx.kind[i] = 1;
      }
      if (e.temp > 100 && Math.random() < dt * (e.temp - 95) * 0.6) {
        const i = this.steamFx.emit([top.x - 2.6 + Math.random() * 0.4, top.y + 2.35, top.z + (Math.random() - 0.5) * 0.3], [(Math.random() - 0.5) * 0.4, 1.2 + Math.random() * 0.8, (Math.random() - 0.5) * 0.4], 1.6, 0.15, 1.1);
        this.steamFx.kind[i] = 0;
      }
      const shake = e.running ? 0.0025 : e.crank ? 0.006 : 0;
      v.root.position.set(v.rest.x + (Math.random() - 0.5) * shake, v.rest.y + (Math.random() - 0.5) * shake, v.rest.z + (Math.random() - 0.5) * shake);
    });
    for (const s of this.spinners) {
      const e = sim.engines[s.engine];
      s.spin = (s.spin || 0) + dt * (e ? e.rpm : 0) / 60 * 6.283;
      set(s.part, X_AXIS, s.spin);
    }
    // engine console
    const ec = this.stations.engines;
    if (ec) {
      const p = ec.parts;
      sim.engines.forEach((e, i) => {
        const n = i + 1;
        dial(p[`Rpm${n}Needle`], -120, e.rpm / 900);
        dial(p[`Temp${n}Needle`], -60, (e.temp - 20) / 120);
        dial(p[`Oil${n}Needle`], -40, e.oil / 100);
        set(p[`Throttle${n}`], X_AXIS, e.running ? -0.45 : 0.2);
        const m = p[`Fault${n}`]?.userData.mat;
        if (m && m.emissive) { m.emissive.setHex(e.fault ? 0xff2010 : e.running ? 0x20ff40 : 0x000000); m.emissiveIntensity = 2.5; }
        const pressed = (this.pressed?.[`engine${i}`] || 0) > this.time;
        const b = p[`Start${n}`]; if (b) { b.userData.restPos ||= b.position.clone(); b.position.copy(b.userData.restPos); if (pressed) b.translateZ(0.012); }
      });
      dial(p.ChargeAmmeterNeedle, 20, 0.5 + Math.min(0.5, (sim.sub.charging || 0) * 0.5) - (sim.sub.charging ? 0 : Math.min(0.4, Math.abs(sim.sub.speed) * 0.05)));
    }
    // fuel day tank sight glass and transfer pump lever
    const fu = this.stations.fuel;
    if (fu) {
      if (fu.level) fu.level.scale.set(1, Math.max(0.01, sim.fuel.day / 100), 1);
      set(fu.parts.PumpLever, X_AXIS, this.leverAngle('fuel', dt));
    }
    for (const st of this.pumps) set(st.parts.Lever, X_AXIS, this.leverAngle(st.key, dt));
    // vent switches and duct fans
    for (const v of this.vents) {
      v.k += ((sim.vents[v.room] ? 1 : 0) - v.k) * Math.min(1, dt * 8);
      if (v.sw) v.sw.quaternion.copy(v.rest).multiply(new THREE.Quaternion().setFromAxisAngle(NZ_AXIS, (v.k - 0.5) * 1.4));
    }
    for (const f of this.fans) {
      const on = f.room >= 0 && sim.vents[f.room] && sim.power;
      f.speed = (f.speed || 0) + ((on ? 14 : 0) - (f.speed || 0)) * Math.min(1, dt * 1.5);
      f.ang = (f.ang || 0) + f.speed * dt;
      set(f.fan, Y_AXIS, f.ang);
      if (on && sim.smoke[f.room] > 0.05 && f.fan) {
        const p = f.fan.getWorldPosition(new THREE.Vector3());
        if (Math.random() < dt * 30 * sim.smoke[f.room]) this.fanFx.emit([p.x + (Math.random() - 0.5) * 1.6, p.y - 0.6 - Math.random() * 0.4, p.z + (Math.random() - 0.5) * 1.6], [0, 0, 0], 0.9, 0.6, 0.15);
      }
    }
    const st = this.steamFx;
    st.update(dt, (i, t) => (st.kind[i] ? [0.1, 0.1, 0.1, Math.min(1, t * 5) * (1 - t) * 0.5] : [0.92, 0.94, 0.95, Math.min(1, t * 6) * (1 - t) * 0.45]));
    const ff = this.fanFx, fans = this.fans;
    ff.update(dt, (i, t) => [0.16, 0.15, 0.14, Math.sin(t * Math.PI) * 0.4], (i, dt2) => {
      // drawn up into the nearest fan
      const x = ff.pos[i * 3];
      const fan = fans.reduce((a, f) => (f.fan && Math.abs(f.fan.getWorldPosition(new THREE.Vector3()).x - x) < Math.abs((a?.fan?.getWorldPosition(new THREE.Vector3()).x ?? 1e9) - x) ? f : a), null);
      if (!fan?.fan) return;
      const p = fan.fan.getWorldPosition(new THREE.Vector3());
      ff.vel[i * 3] = (p.x - x) * 1.6; ff.vel[i * 3 + 1] = (p.y - ff.pos[i * 3 + 1]) * 1.6; ff.vel[i * 3 + 2] = (p.z - ff.pos[i * 3 + 2]) * 1.6;
    });
    // switchboard: breakers up = closed, down = tripped; the main breaker follows the power
    const sb = this.stations.switchboard;
    if (sb) {
      sb.breakers.forEach((b, k) => set(b, X_AXIS, sim.breakers[k] ? 0 : 0.9));
      set(sb.main, X_AXIS, sim.power ? 0 : 1.05);
    }
    // medical cabinet doors swing open while someone is close
    if (this.cabinet) {
      const open = this.cabinetOpen > this.time ? 1 : 0;
      this.cabinet.userData.k = (this.cabinet.userData.k || 0) + (open - (this.cabinet.userData.k || 0)) * Math.min(1, dt * 4);
      this.cabinet.userData.doors.forEach(({ d, rest }, j) => d.quaternion.copy(rest).multiply(new THREE.Quaternion().setFromAxisAngle(Y_AXIS, (j ? 1 : -1) * 1.9 * this.cabinet.userData.k)));
    }
  }

  // pump-lever stations: the lever chases the target the player sets with clicks
  leverAngle(key, dt) {
    const L = (this.levers[key] ||= { target: -0.42, angle: -0.42 });
    L.angle += (L.target - L.angle) * Math.min(1, dt * 14);
    return L.angle;
  }

  // breath bubbles rising from the swimmer to the surface
  breathe(pos, surface, dt) {
    if (Math.random() < dt * 6) {
      const i = this.bubbles.emit([pos.x + (Math.random() - 0.5) * 0.15, pos.y - 0.1, pos.z + (Math.random() - 0.5) * 0.15],
        [(Math.random() - 0.5) * 0.15, 0.9 + Math.random() * 0.5, (Math.random() - 0.5) * 0.15], Math.max(0.3, (surface - pos.y) / 1.1), 0.03 + Math.random() * 0.03, 0.05);
      this.bubbles.top = surface;
    }
  }

  roomAt(x, y) {
    return ROOMS.findIndex((r) => (r.deck === 'lower') === (y < -1.45) && x >= r.x0 - 0.16 && x <= r.x1 + 0.16);
  }

  // water surface at the camera, smoke density there
  envAt(sim, pos) {
    const i = this.roomAt(pos.x, pos.y - 1.6);
    if (i < 0) return { room: -1, surface: -99, smoke: 0 };
    return { room: i, surface: sim.surface(i), smoke: sim.smoke[i] };
  }
}
