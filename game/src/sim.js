// Game simulation: the submarine, the world, enemies, creatures, weapons and damage.
// Pure logic (no rendering) so it can run in the browser or on the multiplayer host.
//
// World axes: x/z horizontal (metres), y up. Heading 0 = +X, increasing counter-clockwise
// seen from above (towards -Z). Depth is metres below the surface (positive down).

export const TELEGRAPH = { '-2': -3.0, '-1': -1.5, '0': 0, '1': 2.0, '2': 4.0, '3': 6.0, '4': 8.0 };
export const TELEGRAPH_NAMES = { '-2': 'FULL ASTERN', '-1': 'HALF ASTERN', '0': 'ALL STOP', '1': 'SLOW AHEAD',
  '2': 'HALF AHEAD', '3': 'FULL AHEAD', '4': 'FLANK' };
export const ROOMS = [
  { name: 'TorpedoRoom', label: 'TORPEDO ROOM', x0: 0.0, x1: 7.0 },
  { name: 'ControlRoom', label: 'CONTROL ROOM', x0: 7.3, x1: 16.3 },
  { name: 'CrewMess', label: 'CREW MESS', x0: 16.6, x1: 22.6 },
  { name: 'Galley', label: 'GALLEY', x0: 22.9, x1: 27.4 },
];
export const TEST_DEPTH = 180;   // beyond this the hull starts to fail
export const PERISCOPE_DEPTH = 14;

const rand = (a, b) => a + Math.random() * (b - a);
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
    this.weapons = { selected: 1, armed: false, guardOpen: false, lock: null, gyro: 0 };
    this.torpedoStock = 6;     // spares in the racks
    this.water = ROOMS.map(() => 0);   // flood level per room (m)
    this.doors = [true, true, true];   // watertight doors between rooms (open = water and crew can pass)
    this.leaks = [];           // {id, room, x, y, side, severity, fixed}
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
    let heading = s.periscopeUp ? s.heading + s.periscopeBearing : s.heading;   // manual aim: along the periscope
    const target = this.entities.find((e) => e.id === w.lock && e.alive);
    if (target) heading = Math.atan2(-(target.z - s.z), target.x - s.x);
    const bowX = s.x + Math.cos(s.heading) * 17, bowZ = s.z - Math.sin(s.heading) * 17;
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

  reveal(e, ranged) {
    const s = this.sub;
    const c = this.contacts.get(e.id) || {};
    c.bearing = Math.atan2(-(e.z - s.z), e.x - s.x);
    c.range = ranged ? dist2(e, s) : c.range;
    c.known = true; c.kind = e.kind; c.lastSeen = this.time;
    this.contacts.set(e.id, c);
  }

  // ------------------------------------------------------------------ damage
  damage(amount, source, hitAlongHull = Math.random()) {
    const s = this.sub;
    if (s.lost) return;
    s.hull = Math.max(0, s.hull - amount);
    const room = Math.min(3, Math.max(0, Math.floor(hitAlongHull * 4)));
    const leaks = amount >= 20 ? 3 : amount >= 8 ? 2 : 1;
    for (let i = 0; i < leaks; i++) this.addLeak(Math.random() < 0.7 ? room : Math.floor(Math.random() * 4), amount / 20);
    this.events.push({ type: 'hit', amount, source });
    this.message(`HIT! ${source}. Hull ${Math.round(s.hull)}%`, 'danger');
    if (s.hull <= 0) this.lose('The hull gave way.');
  }
  addLeak(room, severity = 1) {
    const r = ROOMS[room];
    const l = { id: this.nextId++, room, x: rand(r.x0 + 0.6, r.x1 - 0.6), y: rand(0.5, 1.9), side: Math.random() < 0.5 ? -1 : 1,
      severity: Math.min(1.5, 0.6 + severity * 0.6), fixed: false };
    this.leaks.push(l);
    this.events.push({ type: 'leak', leak: l });
  }
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

    // power: electric motors drain the battery submerged; the diesels recharge it on the surface
    const surfaced = s.depth < 2;
    if (surfaced) { s.battery = Math.min(100, s.battery + dt * 1.5); s.oxygen = Math.min(100, s.oxygen + dt * 6); }
    else {
      s.battery = Math.max(0, s.battery - dt * (0.02 + Math.abs(s.speed) * Math.abs(s.speed) * 0.004));
      s.oxygen = Math.max(0, s.oxygen - dt * 0.12);
    }
    if (s.battery <= 0 && !surfaced && s.telegraph > 1) { s.telegraph = 1; this.message('Battery flat! Only SLOW AHEAD until we surface to recharge.', 'warn'); }
    if (s.oxygen < 15 && !this._o2warn) { this._o2warn = true; this.message('Oxygen is running low - surface soon!', 'danger'); }
    if (s.oxygen > 30) this._o2warn = false;
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
    const flooded = this.water.reduce((a, b) => a + b, 0) / 4;
    const buoy = (s.ballast - 0.5) * 1.2 + flooded * 0.6;           // >0 sinks
    const planeLift = -s.planes * Math.abs(s.speed) * 0.09;           // planes up (+) climbs
    s.vy += (buoy + planeLift - s.vy * 0.6) * dt;
    s.depth = Math.max(0, s.depth + s.vy * dt);
    if (s.depth === 0 && s.vy < 0) s.vy = 0;
    s.pitch += ((-s.vy * 0.06 + s.planes * 0.05 * Math.min(1, Math.abs(s.speed) / 4)) - s.pitch) * Math.min(1, dt * 1.5);
    if (s.periscopeUp && s.depth > PERISCOPE_DEPTH + 2) { s.periscopeUp = false; this.message('Periscope lowered: too deep.', 'warn'); this.events.push({ type: 'periscope', up: false }); }

    // crush depth
    if (s.depth > TEST_DEPTH) {
      this._creak = (this._creak || 0) - dt;
      if (this._creak <= 0) { this._creak = Math.max(1.5, 6 - (s.depth - TEST_DEPTH) / 10); this.damage(4 + (s.depth - TEST_DEPTH) / 15, 'Hull crushing under pressure'); }
    }

    // noise (how easy we are to detect)
    s.noise = Math.max(0, s.noise - dt * 0.8);
    const noise = Math.abs(s.speed) * 0.6 + s.noise + (s.periscopeUp ? 2 : 0) + (s.valve === 'blow' ? 2 : 0) + (s.depth < 3 ? 4 : 0);
    s.sonarPingCooldown = Math.max(0, s.sonarPingCooldown - dt);
    s.shockCooldown = Math.max(0, s.shockCooldown - dt);

    // flooding and pumps
    for (let r = 0; r < 4; r++) {
      const inflow = this.leaks.filter((l) => !l.fixed && l.room === r).reduce((a, l) => a + l.severity, 0) * 0.006 * (1 + s.depth / 80);
      this.water[r] = Math.max(0, this.water[r] + (inflow - 0.0025) * dt);
    }
    for (let i = 0; i < 3; i++) if (this.doors[i]) {   // water equalises through open doors
      const a = this.water[i], b = this.water[i + 1], f = (a - b) * Math.min(1, dt * 0.5);
      this.water[i] -= f; this.water[i + 1] += f;
    }
    if (Math.min(...this.water) > 1.5) this.lose('The boat flooded.');

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
