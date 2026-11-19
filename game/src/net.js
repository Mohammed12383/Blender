// Co-op networking: one browser (the first to join) hosts the simulation; others send their
// station inputs and receive the boat/world state. The relay server just forwards messages.
import * as THREE from 'three';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

const ROLE_FILE = { navigator: 'Navigator', weapons_officer: 'Gunner', torpedo_loader: 'Loader', cook: 'Cook' };

// ---- procedural poses for crewmates: arms down with a walk cycle, a breaststroke when swimming
const _a = new THREE.Vector3(), _b = new THREE.Vector3(), _c = new THREE.Vector3();
const _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _q3 = new THREE.Quaternion();
function aim(bone, child, dirWorld) {
  // turn `bone` so the segment from it to `child` points along dirWorld (works whatever the bone's local axes)
  bone.getWorldPosition(_a); child.getWorldPosition(_b);
  _q.setFromUnitVectors(_b.sub(_a).normalize(), _c.copy(dirWorld).normalize());
  bone.getWorldQuaternion(_q2).premultiply(_q);
  bone.parent.getWorldQuaternion(_q3);
  bone.quaternion.copy(_q3.invert().multiply(_q2));
  bone.updateMatrixWorld(true);
}
const LIMBS = [['UpperArmL', 'LowerArmL', 'HandL'], ['UpperArmR', 'LowerArmR', 'HandR'], ['UpperLegL', 'LowerLegL', 'FootL'], ['UpperLegR', 'LowerLegR', 'FootR']];
export function poseAvatar(a, { swim = false, moving = false, t = 0 } = {}) {
  if (!a.userData.limbs) {
    a.userData.limbs = LIMBS.map((names) => names.map((n) => a.getObjectByName(n)));
    a.userData.rest = a.userData.limbs.flat().filter(Boolean).map((b) => [b, b.quaternion.clone()]);
  }
  for (const [b, q] of a.userData.rest) b.quaternion.copy(q);
  a.updateMatrixWorld(true);
  const W = (x, y, z) => new THREE.Vector3(x, y, z).applyQuaternion(a.quaternion);   // avatar-local direction -> world
  const [armL, armR, legL, legR] = a.userData.limbs;
  const limb = (L, up, lo) => { if (L[0] && L[1] && L[2]) { aim(L[0], L[1], up); aim(L[1], L[2], lo); } };
  // avatar-local axes: +Z faces forward, +Y up, +X is the character's left
  if (swim) {
    // breaststroke: reach ahead together, sweep out and round, tuck in, glide; frog kick
    const ph = (t * 0.9) % 1, k = Math.sin(ph * Math.PI * 2);
    const out = Math.max(0, Math.sin(ph * Math.PI));            // 0 reach .. 1 wide sweep
    for (const [L, sx] of [[armL, 1], [armR, -1]]) {
      const up = W(sx * (0.15 + out * 0.9), 1.0 - out * 0.7, 0.35 + out * 0.2);
      const lo = W(sx * (0.05 + out * 0.4), 1.0 - out * 1.1, 0.5 + out * 0.6);
      limb(L, up, lo);
    }
    for (const [L, sx] of [[legL, 1], [legR, -1]]) {
      const bend = Math.max(0, -k);
      limb(L, W(sx * (0.12 + bend * 0.35), -1, -0.15 - bend * 0.5), W(sx * 0.08, -1 + bend * 0.9, -0.2 - bend * 1.2));
    }
  } else {
    const sw = moving ? Math.sin(t * 7.5) : 0;
    for (const [L, sx, ph] of [[armL, 1, 1], [armR, -1, -1]]) {
      limb(L, W(sx * 0.18, -1, sw * ph * 0.45), W(sx * 0.1, -1, 0.25 + Math.max(0, sw * ph) * 0.4));
    }
    for (const [L, sx, ph] of [[legL, 1, -1], [legR, -1, 1]]) {
      const s2 = sw * ph;
      limb(L, W(sx * 0.06, -1, s2 * 0.5), W(sx * 0.04, -1, s2 * 0.2 - Math.max(0, -s2) * 0.6));
    }
  }
}

export class Net {
  constructor(url, name, role, sim, inn, loader) {
    Object.assign(this, { url, name, role, sim, inn, loader });
    this.isHost = false; this.id = null; this.peers = new Map(); this.sendT = 0; this.avatars = {};
  }
  connect() {
    this.ws = new WebSocket(this.url);
    this.ws.onopen = () => this.send({ t: 'hello', name: this.name, role: this.role });
    this.ws.onmessage = (m) => this.receive(JSON.parse(m.data));
    this.ws.onclose = () => this.sim.message('Disconnected from the server.', 'warn');
  }
  send(o) { if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(o)); }
  claim(station) { this.send({ t: 'claim', station }); }
  sendControls() {
    const s = this.sim.sub, w = this.sim.weapons;
    if (!this.isHost) this.send({ t: 'ctl', sub: { telegraph: s.telegraph, rudder: s.rudder, planes: s.planes, valve: s.valve,
      periscopeBearing: s.periscopeBearing, periscopePitch: s.periscopePitch, periscopeUp: s.periscopeUp },
      weapons: { selected: w.selected, armed: w.armed, guardOpen: w.guardOpen, lock: w.lock }, tubes: this.sim.tubes });
  }
  event(ev) {
    // guests forward actions that change the shared world to the host
    if (this.isHost) return;
    if (['launch', 'leakFixed', 'door', 'ping', 'shock', 'noisemaker'].includes(ev.type)) this.send({ t: 'act', ev: { ...ev, leak: ev.leak ? { id: ev.leak.id } : undefined, fire: undefined } });
  }
  async avatar(peer) {
    if (this.avatars[peer.id]) return this.avatars[peer.id];
    this.avatars[peer.id] = 'loading';
    const g = await this.loader.loadAsync(`../submarine/models/characters/Crew_${ROLE_FILE[peer.role] || 'Navigator'}.glb`);
    const a = SkeletonUtils.clone(g.scene);
    this.inn.scene.add(a);
    this.avatars[peer.id] = a;
    return a;
  }
  receive(m) {
    const sim = this.sim;
    if (window.__netlog && m.t !== 'state' && m.t !== 'pos') console.log('net <-', m.t, JSON.stringify(m).slice(0, 120));
    if (m.t === 'welcome') { this.id = m.id; this.isHost = m.host; sim.message(this.isHost ? 'You are hosting the boat.' : 'Joined the crew!'); }
    if (m.t === 'host') { this.isHost = m.id === this.id; if (this.isHost) sim.message('You are now hosting the boat.'); }
    if (m.t === 'players') {
      for (const p of m.players) if (p.id !== this.id) this.peers.set(p.id, { ...this.peers.get(p.id), ...p });
      for (const id of [...this.peers.keys()]) if (!m.players.some((p) => p.id === id)) { const a = this.avatars[id]; if (a && a !== 'loading') this.inn.scene.remove(a); this.peers.delete(id); delete this.avatars[id]; }
    }
    if (m.t === 'pos') { const p = this.peers.get(m.id); if (p) Object.assign(p, m); }
    if (m.t === 'state' && !this.isHost) {
      Object.assign(sim.sub, m.sub);
      sim.entities = m.entities; sim.torpedoes = m.torpedoes; sim.charges = m.charges; sim.tubes = m.tubes;
      sim.water = m.water; sim.doors = m.doors; sim.score = m.score; sim.torpedoStock = m.torpedoStock;
      if (m.smoke) sim.smoke = m.smoke;
      if (m.vents) sim.vents = m.vents;
      if (m.breakers) sim.breakers = m.breakers;
      if (m.fuel) sim.fuel = m.fuel;
      if (m.engines) m.engines.forEach((e, i) => Object.assign(sim.engines[i], e));
      Object.assign(sim.weapons, m.weapons);
      sim.contacts = new Map(m.contacts);
      for (const l of m.leaks) if (!sim.leaks.some((q) => q.id === l.id)) { sim.leaks.push(l); sim.events.push({ type: 'leak', leak: l }); }
      for (const l of sim.leaks) { const r = m.leaks.find((q) => q.id === l.id); if (r && r.fixed && !l.fixed) { l.fixed = true; sim.events.push({ type: 'leakFixed', leak: l }); } }
      for (const f of m.fires || []) if (!sim.fires.some((q) => q.id === f.id)) { sim.fires.push(f); if (!f.out) sim.events.push({ type: 'fire', fire: f }); }
      for (const f of sim.fires) { const r = (m.fires || []).find((q) => q.id === f.id); if (r) { if (r.out && !f.out) sim.events.push({ type: 'fireOut', fire: f }); Object.assign(f, r); } }
      if (m.power !== sim.power) { sim.power = m.power; sim.events.push({ type: 'power', on: m.power, remote: true }); }
      for (const ev of m.events || []) if (ev.type !== 'leak' && ev.type !== 'leakFixed') sim.events.push(ev);
    }
    if (m.t === 'ctl' && this.isHost) {
      Object.assign(sim.sub, m.sub); Object.assign(sim.weapons, m.weapons);
      m.tubes.forEach((t, i) => Object.assign(sim.tubes[i], t));
    }
    if (m.t === 'act' && this.isHost) {
      const ev = m.ev;
      if (ev.type === 'leakFixed') sim.fixLeak(ev.leak.id);
      if (ev.type === 'door') sim.toggleDoor(ev.index);
      if (ev.type === 'ping') sim.sonarPing();
      if (ev.type === 'shock') sim.hullShock();
      if (ev.type === 'noisemaker') sim.countermeasure();
      if (ev.type === 'launch') sim.fire();
      if (ev.type === 'extinguish') sim.extinguish(ev.id, ev.dt);
      // shared machinery: only these simulation calls may be made remotely
      const ALLOWED = ['toggleEngine', 'startEngine', 'stopEngine', 'setCoolant', 'addOil', 'fixEngine', 'fuelStroke', 'pourFuel', 'bilgeStroke',
        'setVent', 'setBreaker', 'mainBreaker', 'toggleDoor', 'fixLeak'];
      if (ev.type === 'call' && ALLOWED.includes(ev.fn) && Array.isArray(ev.args)) sim[ev.fn](...ev.args);
    }
  }
  update(dt, player) {
    this.sendT -= dt;
    if (this.sendT > 0) return;
    this.sendT = 0.1;
    this.send({ t: 'pos', x: player.pos.x, y: player.pos.y, z: player.pos.z, yaw: player.yaw, station: player.station, carry: player.carry, swim: player.swim });
    if (this.isHost) {
      const sim = this.sim;
      const strip = (e) => { const { view, ...rest } = e; return rest; };
      this.send({ t: 'state', sub: sim.sub, entities: sim.entities, torpedoes: sim.torpedoes, charges: sim.charges.map(strip), tubes: sim.tubes,
        water: sim.water, doors: sim.doors, score: sim.score, torpedoStock: sim.torpedoStock, weapons: sim.weapons,
        smoke: sim.smoke, vents: sim.vents, breakers: sim.breakers, fuel: sim.fuel, engines: sim.engines,
        contacts: [...sim.contacts], leaks: sim.leaks, fires: sim.fires, power: sim.power, events: this.outEvents || [] });
      this.outEvents = [];
    }
  }
  // every frame: glide the crewmates towards their last reported spot and animate their bodies
  animate(dt) {
    const t = performance.now() / 1000;
    for (const p of this.peers.values()) {
      const a = this.avatars[p.id];
      if (!a) { this.avatar(p); continue; }
      if (a === 'loading') continue;
      const target = new THREE.Vector3(p.x ?? 0, (p.y ?? 0) + (p.swim ? 1.15 + Math.sin(t * 2.4 + p.id) * 0.05 : 0), p.z ?? 0);
      if (!a.userData.placed) { a.userData.placed = true; a.position.copy(target); }
      const moved = a.position.distanceTo(target);
      a.position.lerp(target, Math.min(1, dt * 10));
      a.userData.speed = THREE.MathUtils.lerp(a.userData.speed || 0, moved / Math.max(dt, 1e-3), Math.min(1, dt * 4));
      a.rotation.set(p.swim ? -1.25 : 0, (p.yaw ?? 0) + Math.PI, p.swim ? Math.sin(t * 2.4) * 0.12 : 0, 'YXZ');
      poseAvatar(a, { swim: !!p.swim, moving: a.userData.speed > 0.3, t });
    }
  }
}
