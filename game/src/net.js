// Co-op networking: one browser (the first to join) hosts the simulation; others send their
// station inputs and receive the boat/world state. The relay server just forwards messages.
import * as THREE from 'three';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

const ROLE_FILE = { navigator: 'Navigator', weapons_officer: 'Gunner', torpedo_loader: 'Loader', cook: 'Cook' };

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
    if (['launch', 'leakFixed', 'door', 'ping', 'shock', 'noisemaker'].includes(ev.type)) this.send({ t: 'act', ev: { ...ev, leak: ev.leak ? { id: ev.leak.id } : undefined } });
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
      Object.assign(sim.weapons, m.weapons);
      sim.contacts = new Map(m.contacts);
      for (const l of m.leaks) if (!sim.leaks.some((q) => q.id === l.id)) { sim.leaks.push(l); sim.events.push({ type: 'leak', leak: l }); }
      for (const l of sim.leaks) { const r = m.leaks.find((q) => q.id === l.id); if (r && r.fixed && !l.fixed) { l.fixed = true; sim.events.push({ type: 'leakFixed', leak: l }); } }
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
    }
  }
  update(dt, player) {
    this.sendT -= dt;
    if (this.sendT > 0) return;
    this.sendT = 0.1;
    this.send({ t: 'pos', x: player.pos.x, z: player.pos.z, yaw: player.yaw, station: player.station, carry: player.carry });
    if (this.isHost) {
      const sim = this.sim;
      const strip = (e) => { const { view, ...rest } = e; return rest; };
      this.send({ t: 'state', sub: sim.sub, entities: sim.entities, torpedoes: sim.torpedoes, charges: sim.charges.map(strip), tubes: sim.tubes,
        water: sim.water, doors: sim.doors, score: sim.score, torpedoStock: sim.torpedoStock, weapons: sim.weapons,
        contacts: [...sim.contacts], leaks: sim.leaks, events: this.outEvents || [] });
      this.outEvents = [];
    }
    for (const p of this.peers.values()) {
      this.avatar(p).then((a) => { if (a && a !== 'loading') { a.position.set(p.x ?? 0, 0, p.z ?? 0); a.rotation.y = (p.yaw ?? 0) + Math.PI; } });
    }
  }
}
