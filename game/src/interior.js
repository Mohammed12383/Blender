// Inside the boat: loads the two-deck interior, finds stations / doors / hand targets / cameras from the
// glTF extras, builds the walkable decks, live screens, leaks with spray, flood water, smoke, fire and alarms.
import * as THREE from 'three';
import { ROOMS, R as RI, DOORS, ENGINE_FAULTS } from './sim.js';
import { DROP } from './exterior.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { Nav } from './nav.js';
import { Particles } from './particles.js';
import { drawStatus, drawDiveProfile, drawFireScope, drawRoute, STATUS_PAGES } from './consoles.js';

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

// Long thin streaks: the alpha map that makes the jet and the wall run-off look like flowing water
function streakTexture() {
  const c = document.createElement('canvas'); c.width = 64; c.height = 256;
  const g = c.getContext('2d');
  g.fillStyle = 'rgb(70,70,70)'; g.fillRect(0, 0, 64, 256);
  for (let i = 0; i < 90; i++) {
    const x = Math.random() * 64, y = Math.random() * 256, len = 20 + Math.random() * 120, w = 1 + Math.random() * 3;
    const b = 120 + Math.random() * 135;
    const gr = g.createLinearGradient(0, y, 0, y + len);
    gr.addColorStop(0, `rgba(${b},${b},${b},0)`); gr.addColorStop(0.5, `rgba(${b},${b},${b},1)`); gr.addColorStop(1, `rgba(${b},${b},${b},0)`);
    g.fillStyle = gr;
    for (const oy of [0, -256, 256]) g.fillRect(x, y + oy, w, len);
  }
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

// Tapered tube along a list of points (the glassy core of a water jet). v runs along the jet for the flow texture.
function jetGeometry(pts, r0, r1, radial = 8) {
  const n = pts.length, pos = [], uv = [], idx = [];
  const up = new THREE.Vector3(0, 1, 0), t = new THREE.Vector3(), a = new THREE.Vector3(), b = new THREE.Vector3();
  let len = 0;
  for (let i = 0; i < n; i++) {
    if (i) len += pts[i].distanceTo(pts[i - 1]);
    t.subVectors(pts[Math.min(n - 1, i + 1)], pts[Math.max(0, i - 1)]).normalize();
    a.crossVectors(t, up); if (a.lengthSq() < 1e-6) a.set(1, 0, 0); a.normalize();
    b.crossVectors(t, a).normalize();
    const r = r0 + (r1 - r0) * (i / (n - 1)) + Math.sin(i * 1.7) * r0 * 0.12;
    for (let k = 0; k <= radial; k++) {
      const ang = (k / radial) * Math.PI * 2;
      pos.push(pts[i].x + (a.x * Math.cos(ang) + b.x * Math.sin(ang)) * r, pts[i].y + (a.y * Math.cos(ang) + b.y * Math.sin(ang)) * r,
        pts[i].z + (a.z * Math.cos(ang) + b.z * Math.sin(ang)) * r);
      uv.push(k / radial, len * 1.5);
    }
  }
  for (let i = 0; i < n - 1; i++) for (let k = 0; k < radial; k++) {
    const p0 = i * (radial + 1) + k, p1 = p0 + radial + 1;
    idx.push(p0, p1, p0 + 1, p1, p1 + 1, p0 + 1);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx); g.computeVertexNormals();
  return g;
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
    // the torpedo-room wrench hangs on its painted outline on the tool board behind the workbench
    let hook = null;
    this.root.traverse((o) => { if (!hook && /wrench_hook$/.test(baseName(o.name))) hook = o; });
    const hookPos = hook ? hook.getWorldPosition(new THREE.Vector3()) : null;
    for (const p of [hookPos ? hookPos.toArray() : [6.35, -1.97, 1.95], [9.9, 0.02, -1.6], [23.95, 0.93, 2.05], [42.95, 0.03, 1.75]]) {
      const w = wrench.scene.clone();
      w.position.set(...p); w.rotation.y = Math.random() * 6;
      if (hookPos && p[0] === hookPos.x) { w.rotation.set(-Math.PI / 2, 0, 0); w.position.z -= 0.012; }
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
    // (the space under the stairs is cut out of the lower deck in nav.js, so no extra collider is needed)
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
      ['status', 'status', /^ShipStatus/, 'Use SHIP STATUS (diagnostics, general alarm)'],
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
    this.fans = tops.filter((r) => /^DuctFan/.test(r.name)).map((r) => {
      const fan = find(r, (o) => baseName(o.name).endsWith('_Fan'));
      return { room: this.roomAt(r.position.x, r.position.y - 2.4), fan, pos: (fan || r).getWorldPosition(new THREE.Vector3()) };
    });
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
    for (const n of ['screen_chart', 'screen_nav_scope', 'screen_sonar', 'screen_target_id', 'screen_engine']) {
      this.screens[n] = make(n, n === 'screen_chart' ? 768 : 512, n === 'screen_chart' ? 512 : n === 'screen_target_id' ? 256 : 512);
    }
    // canvases in the same proportions as their screens
    this.screens.screen_fire_control = make('screen_fire_control', 640, 480);
    this.screens.screen_ballast = make('screen_ballast', 544, 400);
    this.screens.screen_status = make('screen_status', 640, 412);
    this.statusPage = 'noise';
    // some groups of panel indicator lamps blink (each group at its own pace); the rest stay lit.
    // (the export merges a prop's lamps of one colour into one mesh, so a group blinks together)
    this.blinkers = [];
    this.root.traverse((o) => {
      if (!o.isMesh || !o.material || !/^Lamp(Green|Red|Amber|Blue)$/.test(o.material.name) || /Fault|Start|Button|Lamp_/.test(o.name)) return;
      for (let p = o.parent, k = 0; p && k < 3; p = p.parent, k++) if (p.userData && (p.userData.interact || p.userData.interaction)) return;
      const h = Math.abs(Math.sin(o.getWorldPosition(new THREE.Vector3()).dot(new THREE.Vector3(12.9898, 78.233, 37.719))) * 43758.5453) % 1;
      if (h > 0.55) return;
      o.material = o.material.clone();
      this.blinkers.push({ mat: o.material, base: o.material.emissiveIntensity || 1, rate: 0.8 + h * 6, phase: h * 40, duty: h < 0.2 ? 0.7 : -0.5 });
    });
    this.statusInfo = { alerts: {}, crew: [] };
    this.chartCursor = { x: 0, z: 0 };     // chart-table cursor, metres from the boat
    this.chartZoom = 1;
    // the periscope eyepiece: the live view is rendered into lensRT; the shader adds the reticle, ranging scales and vignette
    this.lensRT = new THREE.WebGLRenderTarget(768, 380, { type: THREE.HalfFloatType, generateMipmaps: true,   // HDR sky; mipmaps stop shimmer
      minFilter: THREE.LinearMipmapLinearFilter });
    this.lensOn = { value: 0 };
    const lens = new THREE.MeshBasicMaterial({ map: this.lensRT.texture });
    lens.onBeforeCompile = (sh) => {
      sh.uniforms.uOn = this.lensOn;
      sh.fragmentShader = 'uniform float uOn;\n' + sh.fragmentShader.replace('#include <map_fragment>', `
        vec2 q = vMapUv;
        diffuseColor *= texture2D(map, q);
        vec2 p = vec2((q.x - 0.5) * 0.436, (q.y - 0.5) * 0.216);
        float d = min(length(p - vec2(-0.11, 0.0)), length(p - vec2(0.11, 0.0))) / 0.108;
        float lw = 0.0011;
        float ink = (1.0 - smoothstep(0.0, lw, abs(p.x))) + (1.0 - smoothstep(0.0, lw, abs(p.y)));
        for (int k = -1; k <= 1; k += 2) {
          float x = float(k) * 0.168;
          float inBand = step(abs(p.y), 0.085);
          ink += (1.0 - smoothstep(0.0, lw, abs(p.x - x))) * inBand;
          float tickLen = mod(floor(p.y / 0.0085 + 0.5), 5.0) < 0.5 ? 0.012 : 0.006;
          ink += (1.0 - smoothstep(0.0, lw * 0.8, abs(fract(p.y / 0.0085 + 0.5) - 0.5) * 0.0085)) * step(abs(p.x - x), tickLen) * inBand;
        }
        ink += (1.0 - smoothstep(0.0, lw, abs(p.y + 0.004))) * step(abs(p.x), 0.012) * 0.0;
        diffuseColor.rgb = mix(diffuseColor.rgb, vec3(0.02, 0.03, 0.03), clamp(ink, 0.0, 1.0) * 0.8);
        diffuseColor.rgb *= smoothstep(1.02, 0.6, d) * (0.92 + 0.08 * smoothstep(0.0, 0.004, abs(p.x)));
        if (uOn < 0.5) diffuseColor.rgb = vec3(0.01, 0.014, 0.018) + vec3(0.03, 0.04, 0.045) * smoothstep(1.0, 0.2, d);
      `);
    };
    this.root.traverse((o) => { if (o.isMesh && [].concat(o.material).some((m) => m && m.name === 'screen_periscope')) o.material = lens; });
    this.periTag = 1;
    this.camTargets = {};
    for (const n of ['screen_cam_fwd', 'screen_cam_aft']) {
      const rt = new THREE.WebGLRenderTarget(384, 288, { type: THREE.HalfFloatType });
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
      const scale = key === 'screen_chart' ? 0.22 * this.chartZoom : 0.3;
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
      drawRoute(ctx, s, sim, scale, key === 'screen_chart' ? this.chartCursor : null, round);
      ctx.rotate(-s.heading); ctx.fillStyle = round ? '#ffe0a0' : '#0d47a1';
      ctx.beginPath(); ctx.moveTo(14, 0); ctx.lineTo(-10, -7); ctx.lineTo(-10, 7); ctx.fill();
      ctx.restore();
      ctx.fillStyle = round ? '#ffae2e' : '#102030'; ctx.font = 'bold 22px monospace';
      ctx.fillText(`HDG ${deg(s.heading)}°  SPD ${s.speed.toFixed(1)}  DEPTH ${s.depth.toFixed(0)}m`, 16, H - 18);
      const wi = sim.waypointInfo();
      if (wi) {
        ctx.fillStyle = round ? '#ffe0a0' : '#b34700'; ctx.font = 'bold 20px monospace';
        ctx.fillText(`WPT 1/${sim.route.length}  ${String(deg(wi.brg)).padStart(3, '0')}°  ${wi.rng.toFixed(0)} m${sim.autopilot ? '  AUTO' : ''}`, 16, round ? 40 : H - 46);
      }
      if (key === 'screen_chart') { ctx.fillStyle = '#102030'; ctx.font = 'bold 16px monospace'; ctx.fillText(`ZOOM x${this.chartZoom.toFixed(1)}`, W - 120, 28); }
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
    if (fc) { drawFireScope(fc.ctx, 640, 480, sim); fc.tex.needsUpdate = true; }
    const bl = this.screens.screen_ballast;
    if (bl) { drawDiveProfile(bl.ctx, 544, 400, sim); bl.tex.needsUpdate = true; }
    const ss = this.screens.screen_status;
    if (ss) { drawStatus(ss.ctx, 640, 412, sim, this.statusPage, this.statusInfo); ss.tex.needsUpdate = true; }
    const id = this.screens.screen_target_id;
    if (id) this.drawTargetId(sim, id);
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

  // TARGET IDENTIFICATION screen on the periscope: silhouette, class, range and bearing of what is in the crosshair
  drawTargetId(sim, sc) {
    const { ctx, canvas } = sc, W = canvas.width, H = canvas.height, s = sim.sub;
    ctx.fillStyle = '#05170f'; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = '#1d4a34'; ctx.lineWidth = 1;
    for (let x = 0; x < W; x += 32) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (let y = 0; y < H; y += 32) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    const brg = s.heading + s.periscopeBearing;
    const e = s.periscopeUp ? sim.contactAt(brg, 0.45 / s.periscopeZoom) : null;
    ctx.font = 'bold 26px monospace'; ctx.fillStyle = '#9dffc4';
    if (!s.periscopeUp) { ctx.fillText('PERISCOPE DOWN', 120, 120); ctx.font = '20px monospace'; ctx.fillText('press R to raise', 160, 160); }
    else if (!e) {
      ctx.fillText('NO CONTACT', 160, 110);
      ctx.font = '20px monospace'; ctx.fillText(`BRG ${String(sim.deg(brg)).padStart(3, '0')}°  ZOOM ${s.periscopeZoom.toFixed(1)}x`, 120, 160);
    } else {
      const hostile = e.kind !== 'freighter';
      const name = { frigate: 'Enemy Frigate', freighter: 'Cargo Freighter', enemySub: 'Enemy Submarine', shark: 'Shark', squid: 'Giant Squid' }[e.kind] || e.kind;
      ctx.fillStyle = hostile ? '#ff4d3a' : '#5fd47a';
      this.silhouette(ctx, e.kind, 18, 14, 64, 34, true);
      ctx.fillStyle = '#eafff2'; ctx.font = 'bold 28px sans-serif'; ctx.fillText(name, 100, 42);
      ctx.strokeStyle = '#eafff2'; ctx.lineWidth = 2.5;
      this.silhouette(ctx, e.kind, 150, 70, 300, 92, false);
      this.silhouette(ctx, e.kind + '_front', 50, 74, 76, 88, false);
      const rng = Math.hypot(e.x - s.x, e.z - s.z);
      const tag = Object.entries(sim.tags || {}).find(([, v]) => v === e.id)?.[0];
      ctx.fillStyle = '#9dffc4'; ctx.font = 'bold 20px monospace';
      ctx.fillText(`RNG ${rng.toFixed(0)} m   BRG ${String(sim.deg(Math.atan2(-(e.z - s.z), e.x - s.x))).padStart(3, '0')}°`, 18, 200);
      ctx.fillStyle = tag ? '#ffd34d' : '#6fae8a';
      ctx.fillText(tag ? `TAG ${tag}${sim.weapons.lock === e.id ? '  LOCKED' : ''}` : `SELECT ${this.periTag} + MARK`, 18, 232);
    }
    ctx.fillStyle = 'rgba(0,0,0,0.18)'; for (let y = 0; y < H; y += 4) ctx.fillRect(0, y, W, 2);
    sc.tex.needsUpdate = true;
  }

  // simple line-art (or filled icon) silhouettes of everything at sea
  silhouette(ctx, kind, x, y, w, h, fill) {
    const P = (pts) => { ctx.beginPath(); pts.forEach(([u, v], i) => (i ? ctx.lineTo(x + u * w, y + v * h) : ctx.moveTo(x + u * w, y + v * h))); ctx.closePath(); fill ? ctx.fill() : ctx.stroke(); };
    const L = (a, b, c, d) => { ctx.beginPath(); ctx.moveTo(x + a * w, y + b * h); ctx.lineTo(x + c * w, y + d * h); ctx.stroke(); };
    switch (kind) {
      case 'frigate':
        P([[0, 0.72], [0.9, 0.72], [1, 0.55], [0.02, 0.6]]);
        P([[0.3, 0.6], [0.3, 0.42], [0.42, 0.42], [0.42, 0.3], [0.55, 0.3], [0.55, 0.42], [0.66, 0.42], [0.66, 0.6]]);
        P([[0.46, 0.3], [0.48, 0.05], [0.5, 0.3]]); if (!fill) { L(0.42, 0.14, 0.56, 0.14); L(0.75, 0.55, 0.88, 0.5); }
        P([[0.72, 0.6], [0.72, 0.52], [0.8, 0.52], [0.8, 0.6]]); P([[0.14, 0.6], [0.14, 0.5], [0.24, 0.5], [0.24, 0.6]]);
        break;
      case 'frigate_front':
        P([[0.3, 0.95], [0.7, 0.95], [0.8, 0.6], [0.2, 0.6]]); P([[0.32, 0.6], [0.32, 0.35], [0.68, 0.35], [0.68, 0.6]]);
        P([[0.46, 0.35], [0.5, 0.0], [0.54, 0.35]]); if (!fill) L(0.3, 0.12, 0.7, 0.12);
        break;
      case 'freighter':
        P([[0, 0.75], [0.95, 0.75], [1, 0.5], [0.0, 0.55]]);
        for (let k = 0; k < 6; k++) P([[0.22 + k * 0.11, 0.55], [0.22 + k * 0.11, 0.32 - (k % 2) * 0.1], [0.31 + k * 0.11, 0.32 - (k % 2) * 0.1], [0.31 + k * 0.11, 0.55]]);
        P([[0.04, 0.55], [0.04, 0.2], [0.17, 0.2], [0.17, 0.55]]); P([[0.08, 0.2], [0.08, 0.05], [0.13, 0.05], [0.13, 0.2]]);
        break;
      case 'freighter_front':
        P([[0.2, 0.95], [0.8, 0.95], [0.85, 0.55], [0.15, 0.55]]); P([[0.22, 0.55], [0.22, 0.25], [0.78, 0.25], [0.78, 0.55]]);
        break;
      case 'enemySub':
        P([[0, 0.62], [0.08, 0.5], [0.9, 0.48], [1, 0.58], [0.9, 0.7], [0.08, 0.7]]); P([[0.42, 0.48], [0.45, 0.22], [0.58, 0.22], [0.6, 0.48]]);
        if (!fill) { L(0.5, 0.22, 0.5, 0.06); L(0.0, 0.62, -0.03, 0.45); }
        break;
      case 'enemySub_front':
        ctx.beginPath(); ctx.ellipse(x + 0.5 * w, y + 0.62 * h, 0.3 * w, 0.3 * h, 0, 0, 7); fill ? ctx.fill() : ctx.stroke();
        P([[0.44, 0.33], [0.45, 0.1], [0.55, 0.1], [0.56, 0.33]]);
        break;
      case 'shark': case 'shark_front':
        P([[0, 0.55], [0.3, 0.4], [0.45, 0.1], [0.55, 0.4], [0.85, 0.48], [1, 0.3], [0.95, 0.55], [1, 0.8], [0.85, 0.62], [0.3, 0.7]]);
        break;
      default:   // squid
        ctx.beginPath(); ctx.ellipse(x + 0.3 * w, y + 0.45 * h, 0.28 * w, 0.18 * h, 0, 0, 7); fill ? ctx.fill() : ctx.stroke();
        for (let k = 0; k < 6; k++) L(0.55, 0.4 + k * 0.03, 1, 0.2 + k * 0.12);
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
    this.splash = new Particles(700, { kind: 'drop', additive: false });
    this.scene.add(this.splash.points);
    // leak jets: droplets thrown by the jet, and mist where the plate is torn
    this.drops = new Particles(2400, { kind: 'drop', additive: false });
    this.mist = new Particles(500, { kind: 'smoke', additive: false });
    this.scene.add(this.drops.points); this.scene.add(this.mist.points);
    this.streakTex = streakTexture();
    this.streamMat = new THREE.MeshStandardMaterial({ color: 0xd9f2fa, transparent: true, opacity: 0.85, roughness: 0.04, metalness: 0.1,
      alphaMap: this.streakTex, emissive: 0x16323a, depthWrite: false, side: THREE.DoubleSide });
    this.sheetMat = new THREE.MeshStandardMaterial({ color: 0xbfe2ee, transparent: true, opacity: 0.55, roughness: 0.05, metalness: 0.1,
      alphaMap: this.streakTex.clone(), depthWrite: false, side: THREE.DoubleSide });
    this.sheetMat.alphaMap.needsUpdate = true;
    this.sheetMat.alphaMap.wrapS = this.sheetMat.alphaMap.wrapT = THREE.RepeatWrapping;
    // expanding ripple rings on the water surface (wading, swimming, leak jets)
    const ringGeo = new THREE.RingGeometry(0.42, 0.5, 40);
    ringGeo.rotateX(-Math.PI / 2);
    this.ripples = Array.from({ length: 24 }, () => {
      const m = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: 0xdff6ff, transparent: true, opacity: 0, depthWrite: false }));
      m.visible = false; m.renderOrder = 2; m.userData = { t: 1, life: 1, size: 1 };
      this.scene.add(m);
      return m;
    });
    this.rippleNext = 0;
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
    this.scene.add(g);
    const inward = -Math.sign(g.position.z) || 1;
    // the glassy core of the jet, and a sheet of water running down the plating under the crack
    const stream = new THREE.Mesh(new THREE.BufferGeometry(), this.streamMat);
    stream.frustumCulled = false; stream.renderOrder = 3;
    const sheet = new THREE.Mesh(new THREE.PlaneGeometry(0.22, 1), this.sheetMat);
    sheet.rotation.y = inward > 0 ? 0 : Math.PI; sheet.renderOrder = 3;
    this.scene.add(stream); this.scene.add(sheet);
    // the crack is ragged: each leak squirts in its own slightly random direction
    const aim = new THREE.Vector3((Math.random() - 0.5) * 0.35, -0.05 - Math.random() * 0.25, inward).normalize();
    this.leakViews.set(l.id, { g, leak: l, inward, aim, stream, sheet, speed: -1, acc: 0, mistAcc: 0 });
    this.interactables.push({ pos: g.position.clone(), radius: 1.1, label: 'FIX LEAK (hold E with a wrench)', kind: 'leak', data: l.id });
  }

  // Jet speed from the sea pressure at our depth (v = sqrt(2 g h), scaled down so it stays playable), and hole size
  jetSpeed(depth, severity) {
    return Math.min(11, 2.4 + Math.sqrt(2 * 9.81 * Math.max(0, depth)) * 0.3) * (0.75 + 0.25 * severity);
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
    this.scene.remove(v.stream); this.scene.remove(v.sheet); v.stream.geometry.dispose(); v.g.clear();
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
    // leaks: a pressurised jet. Core stream -> breaks up into droplets (gravity + air drag) -> splashes; mist at the hole;
    // water sheeting down the plating; once the hole is under water, a turbulent bubbling plume instead.
    const G = -9.81;
    this.streakTex.offset.y -= dt * 4.5;
    this.sheetMat.alphaMap.offset.y += dt * 1.6;
    for (const v of this.leakViews.values()) {
      const l = v.leak, o = v.g.position, room = ROOMS[l.room];
      const surface = sim.surface(l.room), floor = Math.max(surface, room.floor);
      const under = surface > o.y + 0.03;
      const speed = this.jetSpeed(sim.sub.depth, l.severity);
      const v0 = v.aim.clone().multiplyScalar(speed);
      // rebuild the core stream when the pressure changes noticeably
      if (!under && Math.abs(speed - v.speed) > 0.15) {
        v.speed = speed;
        const breakT = Math.min(0.16, (0.55 + l.severity * 0.35) / speed), pts = [];
        for (let k = 0; k <= 14; k++) { const t = breakT * k / 14; pts.push(new THREE.Vector3(o.x + v0.x * t, o.y + v0.y * t + 0.5 * G * t * t, o.z + v0.z * t)); }
        v.stream.geometry.dispose();
        v.stream.geometry = jetGeometry(pts, 0.018 + l.severity * 0.012, 0.032 + l.severity * 0.016);
        v.breakT = breakT;
      }
      v.stream.visible = !under;
      // run-off sheet from the crack down to the floor or the water line
      const sh = Math.max(0.05, o.y - floor - 0.02);
      v.sheet.visible = sh > 0.08 && !under;
      v.sheet.scale.set(0.7 + l.severity * 0.4, sh, 1);
      v.sheet.position.set(o.x, floor + 0.01 + sh / 2, o.z + v.inward * 0.035);
      if (under) {
        // flooding in under the water line: a churning plume of bubbles pushing into the room
        if (Math.random() < dt * 45 * l.severity) {
          this.bubbles.emit([o.x + (Math.random() - 0.5) * 0.12, o.y + (Math.random() - 0.5) * 0.1, o.z + v.inward * 0.05],
            [(Math.random() - 0.5) * 0.6, 0.4 + Math.random() * 0.6, v.inward * speed * (0.25 + Math.random() * 0.25)],
            Math.max(0.4, (surface - o.y) / 0.8), 0.04 + Math.random() * 0.05, 0.09);
        }
        if (Math.random() < dt * 4 * l.severity) this.ripple(o.x + (Math.random() - 0.5) * 0.4, surface, o.z + v.inward * (0.3 + Math.random() * 0.5), 0.8);
        continue;
      }
      // droplets: from the hole (a cone) and from where the stream breaks apart (wider spray)
      v.acc += dt * (260 + 220 * l.severity) * Math.min(1.6, speed / 6);
      const bt = v.breakT || 0.1;
      while (v.acc >= 1) {
        v.acc -= 1;
        const fromBreak = Math.random() < 0.65, spread = fromBreak ? 0.16 : 0.06, t = fromBreak ? bt : Math.random() * 0.02;
        const sp = 0.85 + Math.random() * 0.3;
        const vel = [v0.x * sp + (Math.random() - 0.5) * speed * spread, v0.y * sp + G * t + (Math.random() - 0.5) * speed * spread,
          v0.z * sp + (Math.random() - 0.5) * speed * spread];
        const p = [o.x + v0.x * t, o.y + v0.y * t + 0.5 * G * t * t, o.z + v0.z * t];
        const i = this.drops.emit(p, vel, 2.5, 0.03 + Math.random() * 0.045, 0.04);
        this.drops.kind[i] = l.room;
      }
      v.mistAcc += dt * 40 * l.severity;
      while (v.mistAcc >= 1) {
        v.mistAcc -= 1;
        this.mist.emit([o.x + (Math.random() - 0.5) * 0.1, o.y + (Math.random() - 0.5) * 0.1, o.z + v.inward * 0.06],
          [(Math.random() - 0.5) * 0.5, (Math.random() - 0.4) * 0.4, v.inward * (0.4 + Math.random() * 0.8)], 1.0 + Math.random() * 0.6, 0.08, 0.55);
      }
    }
    // droplet physics: gravity and air drag; they splash on the floor / water or against the far wall
    const dr = this.drops;
    dr.update(dt, (i, t) => [0.86, 0.95, 1.0, 0.85], (i, h) => {
      dr.vel[i * 3 + 1] += G * h;
      const drag = Math.max(0, 1 - 0.35 * h);
      dr.vel[i * 3] *= drag; dr.vel[i * 3 + 1] *= drag; dr.vel[i * 3 + 2] *= drag;
      const r = ROOMS[dr.kind[i]], y = dr.pos[i * 3 + 1], z = dr.pos[i * 3 + 2];
      if (!r) return;
      const fl = Math.max(sim.surface(dr.kind[i]), r.floor);
      const wallHit = Math.abs(z) > r.halfW - 0.32 && Math.sign(dr.vel[i * 3 + 2]) === Math.sign(z);
      if (y < fl || wallHit) {
        const px = dr.pos[i * 3];
        if (Math.random() < 0.2) this.mist.emit([px, Math.max(y, fl) + 0.03, z], [(Math.random() - 0.5) * 0.4, 0.25, (Math.random() - 0.5) * 0.4], 0.45, 0.12, 0.3);
        if (Math.random() < 0.6) {
          const k = Math.min(1.5, Math.hypot(dr.vel[i * 3], dr.vel[i * 3 + 1], dr.vel[i * 3 + 2]) * 0.18);
          this.splash.emit([px, Math.max(y, fl) + 0.01, z], [(Math.random() - 0.5) * 1.6 * k, (0.6 + Math.random() * 1.4) * k, (Math.random() - 0.5) * 1.6 * k - (wallHit ? Math.sign(z) * 0.8 : 0)],
            0.35 + Math.random() * 0.2, 0.05, 0.02);
        }
        if (!wallHit && sim.water[dr.kind[i]] > 0.04 && Math.random() < 0.015) this.ripple(px, fl, z, 0.5);
        dr.age[i] = 1;
      }
    });
    this.mist.update(dt, (i, t) => [0.92, 0.96, 0.98, Math.sin(t * Math.PI) * 0.22]);
    this.splash.update(dt, (i, t) => [0.85, 0.95, 1.0, 0.7 * (1 - t)], (i) => { this.splash.vel[i * 3 + 1] -= 9.8 * dt; });
    for (const m of this.ripples) {
      if (!m.visible) continue;
      const u = m.userData; u.t += dt / u.life;
      if (u.t >= 1) { m.visible = false; continue; }
      m.scale.setScalar(0.2 + u.t * 1.6 * u.size);
      m.material.opacity = (1 - u.t) * 0.5;
    }
    const bb = this.bubbles;
    bb.update(dt, (i, t) => [0.8, 0.95, 1.0, 0.75 * (1 - t * t)], (i, h) => {
      // water drag slows them, buoyancy lifts them, and they wobble on the way up
      const d = Math.max(0, 1 - 2.2 * h);
      bb.vel[i * 3] = bb.vel[i * 3] * d + Math.sin(this.time * 11 + i) * h * 0.8;
      bb.vel[i * 3 + 2] *= d;
      bb.vel[i * 3 + 1] = bb.vel[i * 3 + 1] * d + 2.4 * h;
    });
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
    const danger = sim.alarm || sim.leaks.some((l) => !l.fixed) || sim.sub.hull < 40 || sim.torpedoes.some((t) => t.owner !== 'player') || sim.sub.lost;
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
        const p = f.pos;
        if (Math.random() < dt * 30 * sim.smoke[f.room]) {
          const i = this.fanFx.emit([p.x + (Math.random() - 0.5) * 1.6, p.y - 0.6 - Math.random() * 0.4, p.z + (Math.random() - 0.5) * 1.6], [0, 0, 0], 0.9, 0.6, 0.15);
          this.fanFx.kind[i] = this.fans.indexOf(f);
        }
      }
    }
    const st = this.steamFx;
    st.update(dt, (i, t) => (st.kind[i] ? [0.1, 0.1, 0.1, Math.min(1, t * 5) * (1 - t) * 0.5] : [0.92, 0.94, 0.95, Math.min(1, t * 6) * (1 - t) * 0.45]));
    const ff = this.fanFx, fans = this.fans;
    ff.update(dt, (i, t) => [0.16, 0.15, 0.14, Math.sin(t * Math.PI) * 0.4], (i) => {
      // drawn up into the fan that is sucking it out
      const p = fans[ff.kind[i]]?.pos;
      if (!p) return;
      ff.vel[i * 3] = (p.x - ff.pos[i * 3]) * 1.6; ff.vel[i * 3 + 1] = (p.y - ff.pos[i * 3 + 1]) * 1.6; ff.vel[i * 3 + 2] = (p.z - ff.pos[i * 3 + 2]) * 1.6;
    });
    // periscope: the head trains with the bearing (and you with it), compass card, knobs, tag slider, buttons
    const ps = this.stations.periscope;
    if (ps) {
      const P = ps.parts, s = sim.sub;
      set(P.Head, Y_AXIS, Math.PI / 2 + s.periscopeBearing);
      set(P.CompassCard, NZ_AXIS, -sim.deg(s.heading + s.periscopeBearing) * Math.PI / 180);
      set(P.ZoomKnob, NZ_AXIS, (s.periscopeZoom - 1) * 1.2);
      set(P.TiltKnob, NZ_AXIS, s.periscopePitch * 3.5);
      if (P.TagSlider) {
        P.TagSlider.userData.restPos ||= P.TagSlider.position.clone();
        const want = P.TagSlider.userData.restPos.x + (this.periTag - 1) * 0.0425;
        P.TagSlider.position.x += (want - P.TagSlider.position.x) * Math.min(1, dt * 14);
      }
      for (const [nm, key] of [['MarkButton', 'mark'], ['ClearButton', 'clear']]) {
        const b = P[nm]; if (!b) continue;
        b.userData.restPos ||= b.position.clone();
        b.position.copy(b.userData.restPos);
        if ((this.pressed?.[key] || 0) > this.time) b.position.z -= 0.007;
      }
    }
    // ship status console: the selected page key stays pushed in, the alarm button and its flip-up guard
    const stc = this.stations.status;
    if (stc) {
      const P = stc.parts;
      STATUS_PAGES.forEach((pg, k) => {
        const b = P[`Page${k + 1}`]; if (!b) return;
        b.userData.restPos ||= b.position.clone();
        b.position.copy(b.userData.restPos);
        if (pg === this.statusPage || (this.pressed?.[`page${k}`] || 0) > this.time) b.position.z -= pg === this.statusPage ? 0.005 : 0.008;
      });
      this.alarmGuard = (this.alarmGuard || 0) + (((this.pressed?.alarm || 0) > this.time - 1.2 ? 1 : 0) - (this.alarmGuard || 0)) * Math.min(1, dt * 6);
      set(P.AlarmGuard, X_AXIS, this.alarmGuard * 1.8);
      if (P.AlarmButton) { P.AlarmButton.userData.restPos ||= P.AlarmButton.position.clone(); P.AlarmButton.position.copy(P.AlarmButton.userData.restPos); if ((this.pressed?.alarm || 0) > this.time) P.AlarmButton.position.z -= 0.01; }
    }
    // fire control: AIM stick leans with the course offset; DECOY button
    const wc = this.stations.weapons;
    if (wc) {
      set(wc.parts.AimStick, NZ_AXIS, -(sim.weapons.aim || 0) / 2.35 * 0.35);
      const b = wc.parts.DecoyButton;
      if (b) { b.userData.restPos ||= b.position.clone(); b.position.copy(b.userData.restPos); if ((this.pressed?.decoy || 0) > this.time) b.position.y -= 0.007; }
    }
    // chart table route pod: the cursor stick leans the way the cursor is moving, waypoint keys
    const ct = this.stations.chart;
    if (ct) {
      const m = this.cursorMove || { x: 0, z: 0 };
      const st2 = ct.parts.CursorStick;
      if (st2) {
        st2.userData.rest ||= st2.quaternion.clone();
        st2.quaternion.copy(st2.userData.rest).multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(m.z * 0.3, 0, -m.x * 0.3)));
      }
      set(ct.parts.ChartZoom, Y_AXIS, (this.chartZoom - 1) * 1.5);
      for (const [nm, key] of [['AddWaypoint', 'addwpt'], ['DelWaypoint', 'delwpt']]) {
        const b = ct.parts[nm]; if (!b) continue;
        b.userData.restPos ||= b.position.clone(); b.position.copy(b.userData.restPos);
        if ((this.pressed?.[key] || 0) > this.time) b.position.y -= 0.006;
      }
    }
    // indicator lamps that blink (racks, cabinets, consoles)
    for (const b of this.blinkers || []) {
      const on = Math.sin(this.time * b.rate + b.phase) > b.duty;
      b.mat.emissiveIntensity = on ? b.base : b.base * 0.08;
    }
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

  ripple(x, y, z, size = 1) {
    const m = this.ripples[this.rippleNext]; this.rippleNext = (this.rippleNext + 1) % this.ripples.length;
    m.position.set(x, y + 0.012, z); m.userData = { t: 0, life: 0.9 + size * 0.5, size }; m.visible = true;
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
