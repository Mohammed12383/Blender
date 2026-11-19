// Game simulation: the submarine, the world, enemies, creatures, weapons and damage.
// Pure logic (no rendering) so it can run in the browser or on the multiplayer host.
//
// World axes: x/z horizontal (metres), y up. Heading 0 = +X, increasing counter-clockwise
// seen from above (towards -Z). Depth is metres below the surface (positive down).

export const TELEGRAPH = { '-2': -3.0, '-1': -1.5, '0': 0, '1': 2.0, '2': 4.0, '3': 6.0, '4': 8.0 };
export const TELEGRAPH_NAMES = { '-2': 'FULL ASTERN', '-1': 'HALF ASTERN', '0': 'ALL STOP', '1': 'SLOW AHEAD',
  '2': 'HALF AHEAD', '3': 'FULL AHEAD', '4': 'FLANK' };
// Interior compartments (three.js coordinates: x along the boat from the bow, y up, z = -port).
// floor = height of the walking surface, bottom = lowest point (pit floor), height = floor-to-deckhead.
export const LOWER = -2.9;
const room = (name, label, x0, x1, floor, opts = {}) => {
  const w = floor < -1 ? 4.8 : 5.0;
  const bottom = floor - (opts.pit || 0);
  const height = (floor < -1 ? 2.9 : 2.9) + (opts.pit || 0);
  return { name, label, x0, x1, floor, bottom, height, area: (x1 - x0) * w, halfW: w / 2, deck: floor < -1 ? 'lower' : 'upper', ...opts };
};
export const ROOMS = [
  room('FwdQuarters', 'FORWARD QUARTERS', 0.0, 7.0, 0),
  room('ControlRoom', 'CONTROL ROOM', 7.3, 16.3, 0),
  room('CrewMess', 'CREW MESS', 16.6, 22.6, 0),
  room('Galley', 'GALLEY', 22.9, 27.4, 0),
  room('Passageway', 'ENGINE PASSAGE', 27.7, 31.7, 0, { pit: 0.6 }),
  room('EngineRoom', 'ENGINE ROOM', 32.0, 44.0, 0, { pit: 1.2 }),
  room('TorpedoRoom', 'TORPEDO ROOM', 0.0, 7.0, LOWER),
  room('BatteryRoom', 'BATTERY ROOM', 7.3, 16.3, LOWER),
];
export const R = Object.fromEntries(ROOMS.map((r, i) => [r.name, i]));
// watertight doors (index = sim.doors index); x = forward face of the bulkhead plate
export const DOORS = [
  { a: R.FwdQuarters, b: R.ControlRoom, x: 7.0, sill: 0 },
  { a: R.ControlRoom, b: R.CrewMess, x: 16.3, sill: 0 },
  { a: R.CrewMess, b: R.Galley, x: 22.6, sill: 0 },
  { a: R.Galley, b: R.Passageway, x: 27.4, sill: 0 },
  { a: R.Passageway, b: R.EngineRoom, x: 31.7, sill: 0 },
  { a: R.TorpedoRoom, b: R.BatteryRoom, x: 7.0, sill: LOWER },
];
// the open stairwell joins the forward quarters (above) and the torpedo room (below)
export const STAIRWELL = { upper: R.FwdQuarters, lower: R.TorpedoRoom };
export const PUMP_ROOMS = [R.TorpedoRoom, R.BatteryRoom, R.EngineRoom];   // rooms with a hand bilge pump
export const TEST_DEPTH = 180;   // beyond this the hull starts to fail
export const PERISCOPE_DEPTH = 14;
export const SNORKEL_DEPTH = 12;  // the diesels need air: surfaced or snorkelling
export const DAY_TANK = 100;      // litres
export const ENGINE_FAULTS = { injector: 'injector fault', overheat: 'overheated', oil: 'low oil pressure' };

const rand = (a, b) => a + Math.random() * (b - a);

// Sea floor depth (m) at a world position: rolling plains, ridges and the odd trench.
export function seabed(x, z) {
  const n = Math.sin(x * 0.0021) * Math.cos(z * 0.0017) * 45 + Math.sin((x + z) * 0.0063) * 14 + Math.cos(x * 0.011 - z * 0.007) * 6;
  const ridge = Math.max(0, Math.sin(x * 0.0011 + z * 0.0009) - 0.75) * 260;
  return 215 + n - ridge;
}
const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));
const dist2 = (a, b) => Math.hypot(a.x - b.x, a.z - b.z);

export class Sim {
  constructor() {
    this.time = 0;
    this.events = [];          // drained by the renderer each frame: {type, ...}
    this.sub = {
      x: 0, z: 0, heading: 0, speed: 0, vy: 0, depth: 0, pitch: 0, roll: 0,
      telegraph: 0, rudder: 0, planes: 0, ballast: 0.35, valve: 'hold', air: 100,
      hull: 100, battery: 100, oxygen: 100, periscopeUp: false, periscopeBearing: 0, periscopePitch: 0, periscopeZoom: 1,
      noise: 0, lost: false, lostReason: '', countermeasures: 4, shockCooldown: 0, sonarPingCooldown: 0,
    };
    this.tubes = [1, 2, 3, 4].map((n) => ({ n, loaded: n <= 2, flooded: false, outerOpen: false, breechOpen: false }));
    this.weapons = { selected: 1, armed: false, guardOpen: false, lock: null, gyro: 0, aim: 0 };   // aim: course offset from our heading (AIM stick)
    this.tags = {};            // periscope contact tags: number (1..8) -> entity id
    this.route = [];           // chart-table waypoints [{x, z}] in order
    this.autopilot = false;    // helm steers along the route
    this.alarm = false;        // general alarm (ship status console)
    this.noiseLevel = 0;       // how loud we are right now (0 silent .. ~20 very loud)
    this.torpedoStock = 6;     // spares in the racks
    this.water = ROOMS.map(() => 0);   // flood depth per room above its lowest point (m)
    this.smoke = ROOMS.map(() => 0);   // smoke density per room 0..1
    this.vents = ROOMS.map(() => false);   // SMOKE EXTRACT fans per room
    this.doors = DOORS.map(() => true);    // watertight doors between rooms (open = water, smoke and crew pass)
    this.leaks = [];           // {id, room, x, y, side, severity, fixed}
    this.fires = [];           // {id, room, x, y, z, intensity, out}
    this.power = true;
    this.breakers = [true, true, true, true, true, true, true, true];   // switchboard breakers (main = this.power)
    this.engines = [1, 2].map((id) => ({ id, running: false, crank: 0, rpm: 0, temp: 24, oil: 100, coolant: true, fault: null,
      faultTimer: rand(120, 260) }));
    this.fuel = { day: 70, main: 420 };   // litres: engine-room day tank and the main bunkers
    this.contacts = new Map(); // id -> {bearing, range, known, lastSeen}
    this.entities = [];        // ships, subs, creatures
    this.torpedoes = [];       // {id, owner, x, z, depth, heading, speed, life, target, homing}
    this.charges = [];         // depth charges {x, z, depth, fuse}
    this.score = { sunk: 0, wave: 0 };
    this.nextId = 1;
    this.message('Dive to periscope depth and find the enemy convoy.');
    this.spawnWave();
  }

  message(text, level = 'info') { this.events.push({ type: 'message', text, level }); }

  // ---------------------------------------------------------------- spawning
  spawnWave() {
    const s = this.sub;
    this.score.wave += 1;
    const w = this.score.wave;
    const ang = s.heading + rand(-0.6, 0.6);
    const cx = s.x + Math.cos(ang) * rand(700, 1000), cz = s.z - Math.sin(ang) * rand(700, 1000);
    const course = rand(0, Math.PI * 2);
    for (let i = 0; i < 1 + Math.min(w, 3); i++) {
      this.add({ kind: 'freighter', x: cx + i * 70 * Math.cos(course + 1.57), z: cz - i * 70 * Math.sin(course + 1.57),
        heading: course, speed: 4, hp: 2, length: 46, draft: 6 });
    }
    for (let i = 0; i < Math.min(w, 2); i++) {
      this.add({ kind: 'frigate', x: cx + rand(-120, 120), z: cz + rand(-120, 120), heading: course, speed: 6, hp: 3,
        length: 38, draft: 4, state: 'patrol', chargeTimer: 0, gunTimer: 0 });
    }
    if (w >= 2) this.add({ kind: 'enemySub', x: s.x + rand(-800, 800), z: s.z + rand(-800, 800), depth: 70,
      heading: rand(0, 6.28), speed: 4, hp: 2, length: 34, state: 'patrol', fireTimer: 10 });
    this.add({ kind: 'shark', x: s.x + rand(-150, 150), z: s.z + rand(-150, 150), depth: 20, heading: 0, speed: 5,
      hp: 2, length: 5, state: 'circle', ramTimer: 8 });
    this.message(`Wave ${w}: convoy contact reported to the ${this.bearingWord(Math.atan2(-(cz - s.z), cx - s.x))}.`, 'alert');
  }

  add(e) { e.id = this.nextId++; e.alive = true; e.depth = e.depth ?? 0; e.sinking = 0; this.entities.push(e); return e; }

  bearingWord(a) {
    const rel = wrap(a - this.sub.heading);
    if (Math.abs(rel) < 0.4) return 'bow';
    if (Math.abs(rel) > 2.7) return 'stern';
    return rel > 0 ? 'port' : 'starboard';
  }

  // ----------------------------------------------------------------- controls
  setTelegraph(v) { this.sub.telegraph = Math.max(-2, Math.min(4, v)); }
  setRudder(v) { this.sub.rudder = Math.max(-1, Math.min(1, v)); }
  setPlanes(v) { this.sub.planes = Math.max(-1, Math.min(1, v)); }
  setAim(a) { this.weapons.aim = Math.max(-Math.PI * 0.75, Math.min(Math.PI * 0.75, a)); }
  // route planning (chart table)
  addWaypoint(x, z) {
    if (this.route.length >= 9) return this.message('The route is full (9 waypoints).', 'warn');
    this.route.push({ x, z }); this.message(`Waypoint ${this.route.length} added.`);
  }
  delWaypoint() { if (this.route.pop()) this.message(this.route.length ? `Waypoint ${this.route.length + 1} removed.` : 'Route cleared.'); if (!this.route.length) this.autopilot = false; }
  setAutopilot(on) {
    if (on && !this.route.length) return this.message('No route: plot waypoints at the chart table first.', 'warn');
    this.autopilot = on; this.message(on ? 'Autopilot: steering along the route.' : 'Autopilot off - hand steering.');
  }
  waypointInfo() {
    const w = this.route[0], s = this.sub; if (!w) return null;
    const brg = Math.atan2(-(w.z - s.z), w.x - s.x);
    return { n: 1, brg, rng: Math.hypot(w.x - s.x, w.z - s.z), off: wrap(brg - s.heading) };
  }
  setAlarm(on) { this.alarm = on; this.events.push({ type: 'alarm', on }); if (on) this.message('GENERAL ALARM! All hands to stations!', 'danger'); }
  setValve(v) { this.sub.valve = v; }
  togglePeriscope() {
    const s = this.sub;
    if (!s.periscopeUp && s.depth > PERISCOPE_DEPTH) { this.message(`Too deep for the periscope (max ${PERISCOPE_DEPTH} m).`, 'warn'); return; }
    s.periscopeUp = !s.periscopeUp;
    this.events.push({ type: 'periscope', up: s.periscopeUp });
  }
  sonarPing() {
    const s = this.sub;
    if (s.sonarPingCooldown > 0) return;
    s.sonarPingCooldown = 6;
    s.noise += 3;
    for (const e of this.entities) if (e.alive && dist2(e, s) < 2500) this.reveal(e, true);
    this.events.push({ type: 'ping' });
    for (const e of this.entities) if (e.alive && (e.kind === 'frigate' || e.kind === 'enemySub') && dist2(e, s) < 1500) e.state = 'hunt';
  }
  markTarget(bearing) {
    // lock the closest contact near this bearing
    let best = null, bd = 0.25;
    for (const e of this.entities) {
      if (!e.alive || e.sinking) continue;
      const b = Math.atan2(-(e.z - this.sub.z), e.x - this.sub.x);
      const d = Math.abs(wrap(b - bearing));
      if (d < bd) { bd = d; best = e; }
    }
    this.weapons.lock = best ? best.id : null;
    if (best) { this.reveal(best, true); this.message(`Target locked: ${best.kind.toUpperCase()} bearing ${this.deg(Math.atan2(-(best.z - this.sub.z), best.x - this.sub.x))}°.`); }
    else this.message('No target on that bearing.', 'warn');
    return best;
  }
  // the contact nearest a bearing (within `width` radians), or null
  contactAt(bearing, width = 0.12) {
    let best = null, bd = width;
    for (const e of this.entities) {
      if (!e.alive || e.sinking) continue;
      const d = Math.abs(wrap(Math.atan2(-(e.z - this.sub.z), e.x - this.sub.x) - bearing));
      if (d < bd && Math.hypot(e.x - this.sub.x, e.z - this.sub.z) < 2500) { bd = d; best = e; }
    }
    return best;
  }
  tagTarget(n, bearing) {
    const e = this.contactAt(bearing);
    if (!e) { this.message('Nothing under the crosshair to tag.', 'warn'); return null; }
    for (const k of Object.keys(this.tags)) if (this.tags[k] === e.id) delete this.tags[k];
    this.tags[n] = e.id;
    this.weapons.lock = e.id;
    this.reveal(e, true);
    this.message(`Tagged ${e.kind.toUpperCase()} as contact ${n} - fire control locked on.`);
    return e;
  }
  clearTag(n) {
    if (!this.tags[n]) { this.message(`No contact ${n} to clear.`, 'warn'); return; }
    if (this.weapons.lock === this.tags[n]) this.weapons.lock = null;
    delete this.tags[n];
    this.message(`Contact ${n} cleared.`);
  }
  deg(a) { return Math.round(((90 - a * 180 / Math.PI) % 360 + 360) % 360); }   // compass bearing
  floodTube(n) { const t = this.tubes[n - 1]; if (t.breechOpen) { this.message('Close the breech door first!', 'warn'); return; } t.flooded = !t.flooded; if (!t.flooded) t.outerOpen = false; }
  openOuter(n) { const t = this.tubes[n - 1]; if (!t.flooded) { this.message(`Flood tube ${n} before opening the outer door.`, 'warn'); return; } t.outerOpen = !t.outerOpen; }
  toggleBreech(n) {
    const t = this.tubes[n - 1];
    if (!t.breechOpen && t.flooded) { this.message(`Tube ${n} is flooded - drain it at fire control first.`, 'warn'); return false; }
    t.breechOpen = !t.breechOpen;
    return true;
  }
  loadTube(n) {
    const t = this.tubes[n - 1];
    if (!t.breechOpen || t.loaded) return false;
    t.loaded = true;
    this.message(`Tube ${n} loaded.`);
    return true;
  }
  takeTorpedo() { if (this.torpedoStock <= 0) { this.message('No torpedoes left in the racks!', 'warn'); return false; } this.torpedoStock -= 1; return true; }
  fire() {
    const w = this.weapons, t = this.tubes[w.selected - 1], s = this.sub;
    if (!w.armed) return this.message('Turn the ARM key first.', 'warn');
    if (!w.guardOpen) return this.message('Lift the guard over the FIRE button.', 'warn');
    if (!t.loaded) return this.message(`Tube ${t.n} is empty - the loader must reload it.`, 'warn');
    if (!t.flooded || !t.outerOpen) return this.message(`Tube ${t.n}: flood it and open the outer door.`, 'warn');
    t.loaded = false;
    let heading = s.heading + (w.aim || 0);           // manual aim: the course set with the AIM stick
    const target = this.entities.find((e) => e.id === w.lock && e.alive);
    if (target) heading = Math.atan2(-(target.z - s.z), target.x - s.x);
    const bowX = s.x + Math.cos(s.heading) * 25, bowZ = s.z - Math.sin(s.heading) * 25;
    this.torpedoes.push({ id: this.nextId++, owner: 'player', x: bowX, z: bowZ, depth: Math.max(4, s.depth), heading, speed: 22,
      life: 95, target: target ? target.id : null, homing: target ? 0.25 : 0 });
    s.noise += 2;
    this.events.push({ type: 'launch', tube: t.n });
    this.message(`Tube ${t.n} fired!${target ? ' Running to target.' : ''}`, 'alert');
  }
  countermeasure() {
    const s = this.sub;
    if (s.countermeasures <= 0) return this.message('No noisemakers left.', 'warn');
    s.countermeasures -= 1;
    let n = 0;
    for (const tp of this.torpedoes) if (tp.owner !== 'player' && Math.random() < 0.8) { tp.target = null; tp.homing = 0; tp.heading += rand(-1, 1); n++; }
    this.events.push({ type: 'noisemaker' });
    this.message(n ? 'Noisemaker away - the torpedo lost lock!' : 'Noisemaker away.');
  }
  hullShock() {
    const s = this.sub;
    if (s.shockCooldown > 0 || s.battery < 15) return this.message('Hull shock not ready.', 'warn');
    s.shockCooldown = 25; s.battery -= 15;
    this.events.push({ type: 'shock' });
    for (const e of this.entities) {
      if (!e.alive) continue;
      if (dist2(e, s) < 30 && Math.abs(e.depth - s.depth) < 20 && (e.kind === 'squid' || e.kind === 'shark')) {
        e.hp -= 1; e.state = 'flee'; e.attached = false; e.fleeTimer = 15;
        this.message(e.hp <= 0 ? `The ${e.kind} is dead!` : `The ${e.kind} lets go!`, 'alert');
        if (e.hp <= 0) { e.alive = false; this.events.push({ type: 'creatureDead', id: e.id }); }
      }
    }
  }
  fixLeak(id) {
    const l = this.leaks.find((q) => q.id === id);
    if (l && !l.fixed) { l.fixed = true; this.events.push({ type: 'leakFixed', leak: l }); this.message(`Leak sealed in the ${ROOMS[l.room].label}.`); }
  }
  toggleDoor(i) { this.doors[i] = !this.doors[i]; this.events.push({ type: 'door', index: i, open: this.doors[i] }); }

  // ------------------------------------------------------------ compartments
  surface(r) { return ROOMS[r].bottom + this.water[r]; }          // water surface height (y) in a room
  roomAt(x, y = 0) {
    const lower = y < -1.45;
    return ROOMS.findIndex((r) => (r.deck === 'lower') === lower && x >= r.x0 - 0.16 && x <= r.x1 + 0.16);
  }
  floodFraction() {
    let v = 0, vmax = 0;
    ROOMS.forEach((r, i) => { v += this.water[i] * r.area; vmax += r.height * r.area; });
    return v / vmax;
  }
  bilgeStroke(r) {
    // one half-stroke of a hand bilge pump lifts ~0.3 m3 of water overboard
    if (!PUMP_ROOMS.includes(r)) return;
    this.water[r] = Math.max(0, this.water[r] - 0.3 / ROOMS[r].area);
    this.events.push({ type: 'stroke', room: r });
  }
  setVent(r, on) {
    this.vents[r] = on;
    if (on && !this.power) this.message('SMOKE EXTRACT switched on, but there is no power for the fans!', 'warn');
    else this.message(`Smoke extract ${on ? 'ON' : 'OFF'} in the ${ROOMS[r].label}.`);
  }

  // --------------------------------------------------------------- engines
  startEngine(i) {
    const e = this.engines[i], s = this.sub, n = `Diesel ${e.id}`;
    if (e.running || e.crank > 0) return false;
    if (e.fault) { this.message(`${n}: ${ENGINE_FAULTS[e.fault]} - fix it first.`, 'warn'); return false; }
    if (this.fuel.day <= 0.5) { this.message('Day tank empty! Pump fuel up from the main tanks (fuel transfer pump).', 'warn'); return false; }
    if (e.oil < 12) { this.message(`${n} is out of oil - top it up with an oil can.`, 'warn'); return false; }
    if (s.depth > SNORKEL_DEPTH) { this.message(`The diesels need air: rise to snorkel depth (${SNORKEL_DEPTH} m) or surface.`, 'warn'); return false; }
    e.crank = 2.2;
    this.events.push({ type: 'engineCrank', id: e.id });
    return true;
  }
  stopEngine(i, why) {
    const e = this.engines[i];
    if (!e.running && !e.crank) return;
    e.running = false; e.crank = 0;
    this.events.push({ type: 'engineStop', id: e.id });
    this.message(why ? `Diesel ${e.id} stopped: ${why}` : `Diesel ${e.id} stopped.`, why ? 'warn' : 'info');
  }
  toggleEngine(i) { const e = this.engines[i]; if (e.running || e.crank) this.stopEngine(i); else this.startEngine(i); }
  setCoolant(i, open) {
    const e = this.engines[i];
    e.coolant = open;
    this.message(`Diesel ${e.id} coolant valve ${open ? 'OPEN' : 'SHUT'}.`, open ? 'info' : 'warn');
  }
  addOil(i) {
    const e = this.engines[i];
    e.oil = 100;
    if (e.fault === 'oil') e.fault = null;
    this.message(`Diesel ${e.id} topped up with oil.`);
  }
  fixEngine(i) {
    const e = this.engines[i];
    if (e.fault === 'injector') { e.fault = null; e.faultTimer = rand(140, 300); this.message(`Diesel ${e.id}: injector fixed. She runs sweet again.`); return true; }
    return false;
  }
  fuelStroke() {
    // fuel transfer pump: one half-stroke moves 1.5 litres from the main bunkers to the day tank
    if (this.fuel.main <= 0) { this.message('Main fuel bunkers are dry! Use the jerrycans from the stores.', 'warn'); return; }
    const q = Math.min(1.5, this.fuel.main, DAY_TANK - this.fuel.day);
    this.fuel.main -= q; this.fuel.day += q;
    this.events.push({ type: 'fuelStroke' });
  }
  pourFuel(litres = 20) {
    const q = Math.min(litres, DAY_TANK - this.fuel.day);
    this.fuel.day += q;
    this.message(`Poured ${q.toFixed(0)} litres into the day tank.`);
    return q;
  }

  // -------------------------------------------------------------- switchboard
  setBreaker(k, on) {
    this.breakers[k] = on;
    this.events.push({ type: 'breaker', k, on });
  }
  mainBreaker() {
    if (this.power) return;
    const open = this.breakers.map((b, k) => (b ? null : k + 1)).filter(Boolean);
    if (open.length) { this.message(`Close the tripped breakers first: ${open.join(', ')}.`, 'warn'); return; }
    this.power = true; this.events.push({ type: 'power', on: true }); this.message('MAIN BREAKER closed - power restored.');
  }
  tripPower() {
    if (!this.power) return;
    this.power = false;
    const n = 2 + Math.floor(Math.random() * 3);
    for (let i = 0; i < n; i++) this.breakers[Math.floor(Math.random() * 8)] = false;
    this.events.push({ type: 'power', on: false });
    this.message('POWER FAILURE! Close the tripped breakers and the MAIN BREAKER (battery room, lower deck).', 'danger');
  }

  reveal(e, ranged) {
    const s = this.sub;
    const c = this.contacts.get(e.id) || {};
    c.bearing = Math.atan2(-(e.z - s.z), e.x - s.x);
    c.range = ranged ? dist2(e, s) : c.range;
    c.known = true; c.kind = e.kind; c.lastSeen = this.time;
    this.contacts.set(e.id, c);
  }

  // ------------------------------------------------------------------ damage
  roomsAlongHull(t) {
    // compartments at a fraction t (0 bow .. 1 stern) of the pressure hull
    const x = Math.max(0, Math.min(1, t)) * 44;
    const hit = ROOMS.map((r, i) => i).filter((i) => x >= ROOMS[i].x0 - 0.3 && x <= ROOMS[i].x1 + 0.3);
    return hit.length ? hit : [R.ControlRoom];
  }
  damage(amount, source, hitAlongHull = Math.random()) {
    const s = this.sub;
    if (s.lost) return;
    s.hull = Math.max(0, s.hull - amount);
    const near = this.roomsAlongHull(hitAlongHull);
    const room = near[Math.floor(Math.random() * near.length)];
    const leaks = amount >= 20 ? 3 : amount >= 8 ? 2 : 1;
    for (let i = 0; i < leaks; i++) this.addLeak(Math.random() < 0.7 ? room : Math.floor(Math.random() * ROOMS.length), amount / 20);
    this.events.push({ type: 'hit', amount, source, room });
    if (amount >= 12 && Math.random() < 0.35) this.addFire(room);
    if (amount >= 18 && this.power && Math.random() < 0.45) this.tripPower();
    this.message(`HIT! ${source}. Hull ${Math.round(s.hull)}%`, 'danger');
    if (s.hull <= 0) this.lose('The hull gave way.');
  }
  leakSpot(room) {
    // somewhere on the hull plating a crewman can reach
    const r = ROOMS[room];
    if (r.name === 'EngineRoom') return Math.random() < 0.7 ? { x: rand(42.0, 43.7), y: rand(0.5, 1.8) } : { x: rand(32.1, 32.5), y: rand(0.5, 1.8) };
    if (r.name === 'Passageway') return { x: rand(r.x0 + 0.5, r.x1 - 0.5), y: rand(1.05, 1.9) };
    if (r.name === 'FwdQuarters') return { x: rand(0.6, 3.2), y: rand(0.5, 1.8) };
    return { x: rand(r.x0 + 0.6, r.x1 - 0.6), y: r.floor + rand(0.5, 1.9) };
  }
  addLeak(room, severity = 1) {
    const r = ROOMS[room];
    const spot = this.leakSpot(room);
    const side = r.name === 'FwdQuarters' ? 1 : Math.random() < 0.5 ? -1 : 1;    // quarters: starboard (clear of the stairwell)
    const l = { id: this.nextId++, room, x: spot.x, y: spot.y, side, z: -side * (r.halfW - 0.47),
      severity: Math.min(1.5, 0.6 + severity * 0.6), fixed: false };
    this.leaks.push(l);
    this.events.push({ type: 'leak', leak: l });
  }
  fireSpot(room) {
    const r = ROOMS[room], side = Math.random() < 0.5 ? -1 : 1;
    if (r.name === 'EngineRoom') {
      if (Math.random() < 0.6) return { x: rand(33.2, 38.8), y: 0.25, z: side * 1.0 };     // on top of a diesel
      return { x: rand(42.1, 43.6), y: 0.05, z: rand(-2.0, 2.0) };
    }
    if (r.name === 'Passageway') return { x: rand(r.x0 + 0.5, r.x1 - 0.5), y: 0.05, z: rand(-0.4, 0.4) };
    return { x: rand(r.x0 + 0.8, r.x1 - 0.8), y: r.floor + 0.05, z: -side * (r.halfW - 0.65) };
  }
  addFire(room) {
    const r = ROOMS[room];
    const f = { id: this.nextId++, room, ...this.fireSpot(room), intensity: 0.3, out: false };
    this.fires.push(f);
    this.events.push({ type: 'fire', fire: f });
    this.message(`FIRE in the ${r.label}! Grab an extinguisher!`, 'danger');
  }
  neighbours(room) {
    const out = [];
    DOORS.forEach((d, i) => { if (this.doors[i]) { if (d.a === room) out.push(d.b); if (d.b === room) out.push(d.a); } });
    if (room === STAIRWELL.upper) out.push(STAIRWELL.lower);
    if (room === STAIRWELL.lower) out.push(STAIRWELL.upper);
    return out;
  }
  extinguish(id, dt) {
    const f = this.fires.find((q) => q.id === id && !q.out);
    if (!f) return;
    f.intensity -= dt * 0.45;
    if (f.intensity <= 0) { f.out = true; this.events.push({ type: 'fireOut', fire: f }); this.message(`Fire out in the ${ROOMS[f.room].label}.`); }
  }
  resetPower() { this.breakers.fill(true); this.mainBreaker(); }

  lose(reason) {
    const s = this.sub;
    if (s.lost) return;
    s.lost = true; s.lostReason = reason;
    this.events.push({ type: 'lost', reason });
    this.message(`SUBMARINE LOST: ${reason}`, 'danger');
  }

  // ------------------------------------------------------------------ update
  update(dt) {
    if (dt <= 0) return;
    this.time += dt;
    const s = this.sub;
    if (s.lost) { s.depth += dt * 6; s.pitch = Math.min(0.5, s.pitch + dt * 0.05); return; }

    // power: the electric motors drain the battery; the diesels (surfaced or snorkelling) recharge it
    const surfaced = s.depth < 2;
    this.updateEngines(dt);
    const charging = this.engines.reduce((a, e) => a + (e.running ? (e.fault === 'injector' ? 0.25 : 0.5) : 0), 0);
    s.charging = charging;
    s.battery = Math.max(0, Math.min(100, s.battery + dt * (charging - 0.02 - Math.abs(s.speed) * Math.abs(s.speed) * 0.004)));
    if (surfaced) s.oxygen = Math.min(100, s.oxygen + dt * 6);
    else if (charging > 0 && s.depth <= SNORKEL_DEPTH) s.oxygen = Math.min(100, s.oxygen + dt * 1.5);   // the snorkel draws fresh air
    else s.oxygen = Math.max(0, s.oxygen - dt * 0.12);
    if (s.battery < 20 && !this._battWarn) { this._battWarn = true; this.message('Battery below 20% - run the diesels at snorkel depth to recharge.', 'warn'); }
    if (s.battery > 30) this._battWarn = false;
    // fires burn oxygen, scorch the hull, fill the room with smoke and spread
    for (const f of this.fires) {
      if (f.out) continue;
      f.intensity = Math.min(1.2, f.intensity + dt * 0.025);
      s.oxygen = Math.max(0, s.oxygen - dt * 0.25 * f.intensity);
      s.hull = Math.max(0, s.hull - dt * 0.05 * f.intensity);
      this.smoke[f.room] = Math.min(1, this.smoke[f.room] + dt * 0.08 * f.intensity * 35 / ROOMS[f.room].area);
      if (this.water[f.room] + ROOMS[f.room].bottom > f.y + 0.15) { f.intensity -= dt * 0.6; if (f.intensity <= 0) { f.out = true; this.events.push({ type: 'fireOut', fire: f }); this.message(`The flood water put out the fire in the ${ROOMS[f.room].label}.`); } }
      if (f.intensity > 0.9 && Math.random() < dt * 0.02 && this.fires.filter((q) => !q.out).length < 6) {
        const nb = this.neighbours(f.room);
        this.addFire(Math.random() < 0.7 || !nb.length ? f.room : nb[Math.floor(Math.random() * nb.length)]);
      }
    }
    this.updateSmoke(dt);
    if (s.hull <= 0) this.lose('Fire gutted the boat.');
    if (!this.power && s.telegraph > 1) { s.telegraph = 1; }
    if (s.battery <= 0 && !surfaced && s.telegraph > 1) { s.telegraph = 1; this.message('Battery flat! Only SLOW AHEAD until we surface to recharge.', 'warn'); }
    if (s.oxygen < 15 && !this._o2warn) { this._o2warn = true; this.message('Oxygen is running low - surface soon!', 'danger'); }
    if (s.oxygen > 30) this._o2warn = false;
    // autopilot: rudder towards the next waypoint; drop it once we pass within 60 m
    if (this.autopilot && this.route.length) {
      const wi = this.waypointInfo();
      s.rudder = Math.max(-1, Math.min(1, wi.off * 2.5));
      if (wi.rng < 60) {
        this.route.shift();
        this.message(this.route.length ? `Waypoint reached - steering for the next (${this.route.length} left).` : 'Final waypoint reached. Autopilot off.');
        if (!this.route.length) { this.autopilot = false; s.rudder = 0; }
      }
    }
    // propulsion and steering
    const target = TELEGRAPH[s.telegraph];
    s.speed += Math.sign(target - s.speed) * Math.min(Math.abs(target - s.speed), dt * 0.6);
    const steer = Math.min(1, 0.25 + Math.abs(s.speed) / 5);
    s.heading = wrap(s.heading + s.rudder * 0.09 * steer * Math.sign(s.speed || 1) * dt);
    s.roll += ((-s.rudder * Math.abs(s.speed) * 0.012) - s.roll) * Math.min(1, dt * 2);
    s.x += Math.cos(s.heading) * s.speed * dt;
    s.z -= Math.sin(s.heading) * s.speed * dt;

    // ballast and planes
    if (s.valve === 'flood') s.ballast = Math.min(1, s.ballast + dt * 0.05);
    if (s.valve === 'blow') { if (s.air > 0) { s.ballast = Math.max(0, s.ballast - dt * 0.09); s.air = Math.max(0, s.air - dt * 2.5); } else s.valve = 'hold'; }
    if (s.valve !== 'blow') s.air = Math.min(100, s.air + dt * 0.4);
    const flooded = this.floodFraction();
    const buoy = (s.ballast - 0.5) * 1.2 + flooded * 1.6;           // >0 sinks
    const planeLift = -s.planes * Math.abs(s.speed) * 0.09;           // planes up (+) climbs
    s.vy += (buoy + planeLift - s.vy * 0.6) * dt;
    s.depth = Math.max(0, s.depth + s.vy * dt);
    if (s.depth === 0 && s.vy < 0) s.vy = 0;
    s.pitch += ((-s.vy * 0.06 + s.planes * 0.05 * Math.min(1, Math.abs(s.speed) / 4)) - s.pitch) * Math.min(1, dt * 1.5);
    if (s.periscopeUp && s.depth > PERISCOPE_DEPTH + 2) { s.periscopeUp = false; this.message('Periscope lowered: too deep.', 'warn'); this.events.push({ type: 'periscope', up: false }); }

    // the sea floor
    const floor = seabed(s.x, s.z) - 4;
    if (s.depth > floor) {
      s.depth = floor; if (s.vy > 0) { if (s.vy > 1.2) this.damage(Math.round(s.vy * 6), 'Ran aground on the sea floor', 0.5); s.vy = -0.2; }
      if (Math.abs(s.speed) > 2 && Math.random() < dt * 0.5) this.damage(3, 'Scraping along the bottom', Math.random());
    }
    s.belowKeel = Math.max(0, floor - s.depth);
    // crush depth
    if (s.depth > TEST_DEPTH) {
      this._creak = (this._creak || 0) - dt;
      if (this._creak <= 0) { this._creak = Math.max(1.5, 6 - (s.depth - TEST_DEPTH) / 10); this.damage(4 + (s.depth - TEST_DEPTH) / 15, 'Hull crushing under pressure'); }
    }

    // noise (how easy we are to detect)
    s.noise = Math.max(0, s.noise - dt * 0.8);
    const noise = Math.abs(s.speed) * 0.6 + s.noise + (s.periscopeUp ? 2 : 0) + (s.valve === 'blow' ? 2 : 0) + (s.depth < 3 ? 4 : 0)
      + this.engines.filter((e) => e.running).length * 2.5;
    this.noiseLevel = noise;
    s.sonarPingCooldown = Math.max(0, s.sonarPingCooldown - dt);
    s.shockCooldown = Math.max(0, s.shockCooldown - dt);

    this.updateFlooding(dt);
    if (this.floodFraction() > 0.55) this.lose('The boat flooded.');

    this.updateEntities(dt, noise);
    this.updateWeapons(dt);
    if (this.entities.filter((e) => e.alive && (e.kind === 'freighter' || e.kind === 'frigate' || e.kind === 'enemySub')).length === 0) {
      this.message('All targets destroyed! Next wave incoming...', 'alert');
      this.spawnWave();
    }
    // creature encounters by depth
    if (s.depth > 60 && !this.entities.some((e) => e.alive && e.kind === 'squid') && Math.random() < dt / 25) {
      this.add({ kind: 'squid', x: s.x + rand(-120, 120), z: s.z + rand(-120, 120), depth: s.depth + rand(10, 30), heading: 0, speed: 3,
        hp: 2, length: 13, state: 'stalk', grabTimer: 0 });
      this.message('Sonar: something huge is moving below us...', 'alert');
    }
  }

  updateFlooding(dt) {
    const s = this.sub;
    // leaks pour water in (harder the deeper we are); the electric bilge pumps fight back while there is power
    ROOMS.forEach((r, i) => {
      const inflow = this.leaks.filter((l) => !l.fixed && l.room === i).reduce((a, l) => a + l.severity, 0) * 0.2 * (1 + s.depth / 80);
      const pumps = this.power ? 0.05 : 0;
      this.water[i] = Math.max(0, Math.min(r.height, this.water[i] + (inflow - pumps) * dt / r.area));
    });
    // water runs through open doors over the sill towards the lower side
    DOORS.forEach((d, i) => {
      if (!this.doors[i]) return;
      const sa = this.surface(d.a), sb = this.surface(d.b);
      const [hiR, loR] = sa >= sb ? [d.a, d.b] : [d.b, d.a];
      const hi = Math.max(sa, sb), lo = Math.max(Math.min(sa, sb), d.sill);
      if (hi <= d.sill + 1e-4 || hi - lo < 1e-4) return;
      const A = ROOMS[hiR].area, B = ROOMS[loR].area;
      const eq = (hi - lo) / (1 / A + 1 / B);
      const dv = Math.min(eq, Math.min(1, dt * 0.8) * eq, (hi - d.sill) * A);
      this.water[hiR] -= dv / A; this.water[loR] = Math.min(ROOMS[loR].height, this.water[loR] + dv / B);
    });
    // the stairwell: the quarters drain straight down into the torpedo room until it is full
    const up = STAIRWELL.upper, dn = STAIRWELL.lower, ru = ROOMS[up], rd = ROOMS[dn];
    const room = (ru.floor - this.surface(dn)) * rd.area;            // spare volume below the upper deck
    if (this.water[up] > 0 && room > 0) {
      const dv = Math.min(this.water[up] * ru.area, room, dt * 4.0);
      this.water[up] -= dv / ru.area; this.water[dn] += dv / rd.area;
    } else if (room < 0) {                                           // torpedo room overflowing: it backs up the stairs
      this.water[dn] += room / rd.area; this.water[up] += -room / ru.area;
    }
  }

  updateSmoke(dt) {
    // smoke drifts through open doors, rises up the stairwell and is sucked out by the vent fans (with power)
    const sm = this.smoke;
    DOORS.forEach((d, i) => {
      if (!this.doors[i]) return;
      const f = (sm[d.a] - sm[d.b]) * Math.min(1, dt * 0.12);
      sm[d.a] -= f; sm[d.b] += f;
    });
    const up = STAIRWELL.upper, dn = STAIRWELL.lower;
    const rise = sm[dn] * Math.min(1, dt * 0.12) - sm[up] * Math.min(1, dt * 0.03);
    sm[dn] -= rise; sm[up] += rise;
    this.engines.forEach((e) => { if (e.running && e.fault === 'injector') sm[R.EngineRoom] += dt * 0.012; });
    for (let i = 0; i < sm.length; i++) {
      const fan = this.vents[i] && this.power ? 0.12 : 0;
      sm[i] = Math.max(0, Math.min(1, sm[i] - dt * (0.004 + fan)));
    }
  }

  updateEngines(dt) {
    const s = this.sub;
    for (const [i, e] of this.engines.entries()) {
      if (e.crank > 0) {
        e.crank -= dt; e.rpm = 180 + Math.random() * 60;
        if (e.crank <= 0) { e.crank = 0; e.running = true; this.events.push({ type: 'engineStart', id: e.id }); this.message(`Diesel ${e.id} running - charging the battery.`); }
      }
      if (e.running) {
        e.rpm += ((e.fault === 'injector' ? 480 + Math.random() * 120 : 720) - e.rpm) * Math.min(1, dt * 1.5);
        this.fuel.day = Math.max(0, this.fuel.day - dt * 0.07);
        e.oil = Math.max(0, e.oil - dt * 0.05);
        e.temp += ((e.coolant ? 82 : 140) - e.temp) * dt * 0.035;
        e.faultTimer -= dt;
        if (e.faultTimer <= 0 && !e.fault) {
          e.faultTimer = rand(120, 280);
          if (Math.random() < 0.55) { e.fault = 'injector'; this.message(`Diesel ${e.id} is running rough and smoking - INJECTOR FAULT! Fix it with a wrench.`, 'danger'); }
          else { e.coolant = false; this.message(`Diesel ${e.id} is overheating - the coolant valve has shaken shut!`, 'danger'); }
          this.events.push({ type: 'engineFault', id: e.id });
        }
        if (e.temp > 118) { e.fault = 'overheat'; this.stopEngine(i, 'OVERHEATED. Open the coolant valve and let it cool.'); }
        else if (e.oil < 10) { e.fault = 'oil'; this.stopEngine(i, 'LOW OIL PRESSURE. Top up the oil.'); }
        else if (this.fuel.day <= 0) this.stopEngine(i, 'the day tank is empty. Pump up more fuel!');
        else if (s.depth > SNORKEL_DEPTH) this.stopEngine(i, 'the snorkel went under - no air for the diesels.');
      } else if (!e.crank) {
        e.rpm = Math.max(0, e.rpm - dt * 400);
        e.temp += (24 - e.temp) * dt * 0.02;
        if (e.fault === 'overheat' && e.temp < 70) { e.fault = null; this.message(`Diesel ${e.id} has cooled down and can be restarted.`); }
      }
    }
  }

  updateEntities(dt, noise) {
    const s = this.sub;
    for (const e of this.entities) {
      if (!e.alive) continue;
      const d = dist2(e, s);
      const bearingToSub = Math.atan2(-(s.z - e.z), s.x - e.x);
      if (e.sinking) {
        e.sinking += dt;
        e.depth += dt * (e.kind === 'enemySub' ? 3 : 0.8 + e.sinking * 0.05);
        if (e.sinking > 40) { e.alive = false; this.events.push({ type: 'removed', id: e.id }); }
        continue;
      }
      // passive detection both ways
      if (d < 250 + noise * 120) this.reveal(e, d < 600);
      const steerTo = (a, rate) => { e.heading = wrap(e.heading + Math.max(-rate * dt, Math.min(rate * dt, wrap(a - e.heading)))); };
      if (e.kind === 'freighter') {
        if (e.state === 'flee') { steerTo(bearingToSub + Math.PI + Math.sin(this.time * 0.3) * 0.6, 0.08); e.speed = 7; }
        else e.heading = wrap(e.heading + Math.sin(this.time * 0.05 + e.id) * 0.004 * dt);
      } else if (e.kind === 'frigate') {
        const detect = d < 180 + noise * 90 + (s.depth < 15 ? 250 : 0);
        if (detect && e.state !== 'hunt') { e.state = 'hunt'; this.message('Enemy frigate is hunting us! Go deep and run silent.', 'danger'); }
        if (e.state === 'hunt') {
          const lost = d > 700 + noise * 100;
          if (lost) e.state = 'search';
          steerTo(bearingToSub, 0.14); e.speed = d < 80 ? 6 : 9;
          e.chargeTimer -= dt;
          if (d < 70 && e.chargeTimer <= 0 && s.depth > 6) {
            e.chargeTimer = 3.5;
            this.charges.push({ x: e.x + rand(-15, 15), z: e.z + rand(-15, 15), depth: 0, target: s.depth + rand(-14, 14), fuse: 0 });
            this.events.push({ type: 'chargeDropped' });
            if (!this._dcMsg || this.time - this._dcMsg > 15) { this._dcMsg = this.time; this.message('Splashes overhead - DEPTH CHARGES! Change depth and course!', 'danger'); }
          }
          e.gunTimer -= dt;
          if (s.depth < 3 && d < 900 && e.gunTimer <= 0) {
            e.gunTimer = 4;
            this.events.push({ type: 'gunfire', from: e.id });
            if (Math.random() < 0.45) this.damage(6, 'Shellfire from the frigate', 0.2 + Math.random() * 0.6);
          }
        } else if (e.state === 'search') {
          steerTo(e.heading + Math.sin(this.time * 0.2) * 0.5, 0.05); e.speed = 5;
          if (d < 200 + noise * 80) e.state = 'hunt';
        }
      } else if (e.kind === 'enemySub') {
        e.depth += (60 - e.depth) * dt * 0.1;
        const detect = d < 300 + noise * 100;
        if (detect && e.state !== 'hunt') { e.state = 'hunt'; this.message('Sonar: enemy submarine has our scent!', 'danger'); }
        if (e.state === 'hunt') {
          steerTo(bearingToSub + 0.5, 0.06); e.speed = 5;
          e.fireTimer -= dt;
          if (e.fireTimer <= 0 && d < 900) {
            e.fireTimer = 28;
            const lead = bearingToSub + rand(-0.08, 0.08);
            this.torpedoes.push({ id: this.nextId++, owner: e.id, x: e.x, z: e.z, depth: e.depth, heading: lead, speed: 16, life: 80, target: 'sub', homing: 0.18 });
            this.events.push({ type: 'enemyLaunch' });
            this.message('TORPEDO IN THE WATER! Evade or launch a noisemaker!', 'danger');
          }
        } else steerTo(e.heading + 0.2, 0.02);
      } else if (e.kind === 'shark') {
        e.depth += (s.depth + Math.sin(this.time + e.id) * 3 - e.depth) * dt * 0.4;
        if (e.state === 'flee') { steerTo(bearingToSub + Math.PI, 0.6); e.speed = 9; e.fleeTimer -= dt; if (e.fleeTimer <= 0) e.state = 'circle'; }
        else {
          e.ramTimer -= dt;
          if (e.ramTimer <= 0 && d < 60) { steerTo(bearingToSub, 1.0); e.speed = 10; if (d < 9) { e.ramTimer = rand(12, 20); this.damage(4, 'A shark rammed the hull'); e.state = 'flee'; e.fleeTimer = 4; } }
          else { steerTo(bearingToSub + 1.3, 0.5); e.speed = 6; }
        }
      } else if (e.kind === 'squid') {
        if (e.state === 'flee') { steerTo(bearingToSub + Math.PI, 0.4); e.speed = 8; e.depth += dt * 3; e.fleeTimer -= dt; if (e.fleeTimer <= 0) e.state = 'stalk'; }
        else if (e.attached) {
          e.x = s.x - Math.cos(s.heading) * 4; e.z = s.z + Math.sin(s.heading) * 4; e.depth = s.depth + 3; e.heading = s.heading;
          e.grabTimer -= dt;
          if (e.grabTimer <= 0) { e.grabTimer = 7; this.damage(5, 'The giant squid is crushing the hull', Math.random()); }
          if (s.depth < 25) { e.attached = false; e.state = 'flee'; e.fleeTimer = 20; this.message('The squid lets go in the shallows!'); }
        } else {
          steerTo(bearingToSub, 0.3); e.speed = 4.5;
          e.depth += (s.depth + 4 - e.depth) * dt * 0.3;
          if (d < 14 && Math.abs(e.depth - s.depth) < 10) { e.attached = true; e.grabTimer = 3; this.events.push({ type: 'grab' }); this.message('GIANT SQUID ON THE HULL! Use HULL SHOCK at the electrical cabinet or surface!', 'danger'); }
        }
      }
      e.x += Math.cos(e.heading) * e.speed * dt;
      e.z -= Math.sin(e.heading) * e.speed * dt;
    }
  }

  updateWeapons(dt) {
    const s = this.sub;
    for (const tp of this.torpedoes) {
      tp.life -= dt;
      let tgt = null;
      if (tp.target === 'sub') tgt = { x: s.x, z: s.z, depth: s.depth };
      else if (tp.target) tgt = this.entities.find((e) => e.id === tp.target && e.alive);
      if (tgt && tp.homing) {
        const want = Math.atan2(-(tgt.z - tp.z), tgt.x - tp.x);
        tp.heading = wrap(tp.heading + Math.max(-tp.homing * dt, Math.min(tp.homing * dt, wrap(want - tp.heading))));
        tp.depth += Math.sign((tgt.depth ?? 3) - tp.depth) * Math.min(Math.abs((tgt.depth ?? 3) - tp.depth), dt * 4);
      }
      tp.x += Math.cos(tp.heading) * tp.speed * dt;
      tp.z -= Math.sin(tp.heading) * tp.speed * dt;
      if (tp.owner === 'player') {
        for (const e of this.entities) {
          if (!e.alive || e.sinking || e.kind === 'shark' || e.kind === 'squid' && !e.attached) continue;
          const reach = (e.length || 20) / 2;
          if (dist2(tp, e) < reach && Math.abs(tp.depth - (e.depth || 0)) < (e.draft || 10) + 4) {
            tp.life = 0;
            e.hp -= 1;
            this.events.push({ type: 'explosion', x: tp.x, z: tp.z, depth: tp.depth, surface: (e.depth || 0) < 5 });
            if (e.kind === 'freighter') { this.entities.filter((q) => q.kind === 'freighter' && q.alive).forEach((q) => { q.state = 'flee'; }); }
            this.entities.filter((q) => q.kind === 'frigate' && q.alive).forEach((q) => { q.state = 'hunt'; });
            if (e.hp <= 0) { e.sinking = 0.01; this.score.sunk += 1; this.events.push({ type: 'sunk', id: e.id, kind: e.kind }); this.message(`${e.kind.toUpperCase()} SUNK! (${this.score.sunk} total)`, 'alert'); }
            else this.message(`Hit on the ${e.kind}!`, 'alert');
          }
        }
      } else if (Math.hypot(tp.x - s.x, tp.z - s.z) < 12 && Math.abs(tp.depth - s.depth) < 8) {
        tp.life = 0;
        this.events.push({ type: 'explosion', x: tp.x, z: tp.z, depth: tp.depth, surface: false, onSub: true });
        this.damage(24, 'Enemy torpedo hit', Math.random());
      }
    }
    this.torpedoes = this.torpedoes.filter((t) => t.life > 0);
    for (const c of this.charges) {
      c.depth += dt * 5;
      if (c.depth >= c.target) {
        c.done = true;
        const d = Math.hypot(c.x - s.x, c.z - s.z, (c.depth - s.depth) * 1.2);
        this.events.push({ type: 'explosion', x: c.x, z: c.z, depth: c.depth, surface: false, charge: true, dist: d });
        if (d < 45) this.damage(Math.round((45 - d) * 0.8), 'Depth charge', 0.1 + Math.random() * 0.8);
      }
    }
    this.charges = this.charges.filter((c) => !c.done);
  }
}
