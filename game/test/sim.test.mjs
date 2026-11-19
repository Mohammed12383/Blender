// Headless checks of the game simulation: node game/test/sim.test.mjs
import assert from 'node:assert/strict';
import { Sim, R, ROOMS, SNORKEL_DEPTH } from '../src/sim.js';

const step = (sim, seconds) => { for (let t = 0; t < seconds; t += 0.05) sim.update(0.05); };
const quiet = () => { const sim = new Sim(); sim.entities.forEach((e) => { e.alive = false; }); sim.spawnWave = () => {}; return sim; };
let pass = 0;
const test = (name, fn) => { fn(); pass++; console.log('ok -', name); };

test('dives with flooded tanks and surfaces when blown', () => {
  const sim = new Sim();
  sim.setValve('flood'); step(sim, 40);
  assert.ok(sim.sub.depth > 10, `depth ${sim.sub.depth}`);
  sim.setValve('blow'); step(sim, 60);
  assert.ok(sim.sub.depth < 3, `depth ${sim.sub.depth}`);
});

test('engines and rudder move and turn the boat', () => {
  const sim = new Sim();
  sim.setTelegraph(3); sim.setRudder(1); step(sim, 30);
  assert.ok(sim.sub.speed > 5);
  assert.ok(Math.hypot(sim.sub.x, sim.sub.z) > 50);
  assert.ok(Math.abs(sim.sub.heading) > 0.5);
});

test('full firing sequence sinks a stationary freighter', () => {
  const sim = new Sim();
  const f = sim.entities.find((e) => e.kind === 'freighter');
  sim.entities.filter((e) => e !== f).forEach((e) => { e.alive = false; });
  Object.assign(f, { x: 250, z: 0, speed: 0, heading: Math.PI / 2 });
  sim.weapons.lock = f.id;
  for (const n of [1, 2]) {
    sim.weapons.selected = n; sim.floodTube(n); sim.openOuter(n);
    sim.weapons.armed = true; sim.weapons.guardOpen = true; sim.fire(); step(sim, 20);
  }
  assert.ok(f.sinking > 0, `hp ${f.hp}`);
  assert.equal(sim.score.sunk, 1);
});

test('loader reloads an empty tube from the racks', () => {
  const sim = new Sim();
  const stock = sim.torpedoStock;
  assert.ok(sim.takeTorpedo());
  assert.ok(sim.toggleBreech(3));
  assert.ok(sim.loadTube(3));
  assert.ok(sim.tubes[2].loaded);
  assert.equal(sim.torpedoStock, stock - 1);
});

test('damage tears leaks, water rises, a wrench fixes them', () => {
  const sim = new Sim();
  sim.entities.forEach((e) => { e.alive = false; });   // no sharks ramming during this check
  sim.spawnWave = () => {};
  sim.sub.depth = 40; sim.sub.ballast = 0.5;
  sim.damage(25, 'test', 0.1);
  assert.ok(sim.leaks.length >= 3);
  step(sim, 30);
  assert.ok(sim.water.some((w) => w > 0.1), sim.water.join());
  for (const l of sim.leaks) sim.fixLeak(l.id);
  sim.resetPower();                                  // the hit may have tripped the breakers
  sim.fires.forEach((f) => { f.out = true; });
  const vol = () => ROOMS.reduce((a, r, i) => a + sim.water[i] * r.area, 0);
  const before = vol();
  step(sim, 60);
  assert.ok(vol() < before - 1, `the electric bilge pumps drain the water (${before.toFixed(1)} -> ${vol().toFixed(1)} m3)`);
});

test('closed doors stop flood water spreading', () => {
  const sim = quiet();
  sim.sub.depth = 30; sim.sub.ballast = 0.5;
  sim.toggleDoor(1); sim.toggleDoor(2);          // seal the crew mess off from the control room and the galley
  sim.addLeak(R.CrewMess, 1.5); sim.addLeak(R.CrewMess, 1.5);
  step(sim, 40);
  assert.ok(sim.water[R.CrewMess] > 0.2 && sim.water[R.ControlRoom] < 0.01 && sim.water[R.Galley] < 0.01, sim.water.join());
});

test('water in the forward quarters pours down the stairwell into the torpedo room', () => {
  const sim = quiet();
  sim.power = false; sim.toggleDoor(5);           // no electric pumps, lower door shut
  sim.water[R.FwdQuarters] = 0.5;
  step(sim, 10);
  assert.ok(sim.water[R.FwdQuarters] < 0.01, `quarters ${sim.water[R.FwdQuarters]}`);
  assert.ok(sim.water[R.TorpedoRoom] > 0.4, `torpedo room ${sim.water[R.TorpedoRoom]}`);
});

test('water runs over the sill into the passage pit and down the decks, never uphill', () => {
  const sim = quiet();
  sim.power = false;                              // no electric pumps
  sim.water[R.Galley] = 0.3;
  step(sim, 30);
  assert.ok(sim.water[R.Passageway] > 0.05, `passage pit ${sim.water[R.Passageway]}`);
  assert.ok(sim.water[R.Galley] < 0.05, `galley ${sim.water[R.Galley]}`);
  const total = ROOMS.reduce((a, r, i) => a + sim.water[i] * r.area, 0);
  assert.ok(Math.abs(total - 0.3 * ROOMS[R.Galley].area) < 0.05, `volume is conserved (${total.toFixed(3)})`);
  assert.ok(sim.water[R.TorpedoRoom] > 0.01, 'it found its way down the stairwell too');
});

test('hand bilge pump strokes lift water out of a compartment', () => {
  const sim = quiet();
  sim.water[R.BatteryRoom] = 0.6; sim.toggleDoor(5);
  for (let i = 0; i < 40; i++) sim.bilgeStroke(R.BatteryRoom);
  assert.ok(sim.water[R.BatteryRoom] < 0.6 - 0.25, `battery room ${sim.water[R.BatteryRoom]}`);
  sim.bilgeStroke(R.ControlRoom);                 // no pump there: nothing happens
  assert.equal(sim.water[R.ControlRoom], 0);
});

test('diesels start only with air, fuel and oil, then charge the battery and burn fuel', () => {
  const sim = quiet();
  sim.sub.depth = 40; sim.sub.ballast = 0.5; sim.sub.battery = 50;
  assert.equal(sim.startEngine(0), false, 'too deep');
  sim.sub.depth = SNORKEL_DEPTH - 2; sim.sub.ballast = 0.42;
  const fuel = sim.fuel.day;
  assert.equal(sim.startEngine(0), true);
  for (let t = 0; t < 30; t += 0.05) { sim.sub.depth = 8; sim.sub.vy = 0; sim.update(0.05); }
  assert.ok(sim.engines[0].running, 'running');
  assert.ok(sim.sub.battery > 55, `battery ${sim.sub.battery}`);
  assert.ok(sim.fuel.day < fuel, 'burns fuel');
  sim.sub.depth = 30; sim.update(0.05);
  assert.ok(!sim.engines[0].running, 'stalls when the snorkel goes under');
});

test('a shut coolant valve overheats the diesel until it stops', () => {
  const sim = quiet();
  sim.sub.depth = 8; sim.sub.ballast = 0.42;
  sim.startEngine(1);
  sim.setCoolant(1, false);
  let fault = null;
  for (let t = 0; t < 120 && !fault; t += 0.05) { sim.sub.depth = 8; sim.sub.vy = 0; sim.update(0.05); fault = sim.engines[1].fault; }
  assert.equal(fault, 'overheat');
  assert.ok(!sim.engines[1].running);
  sim.setCoolant(1, true);
  for (let t = 0; t < 120; t += 0.05) { sim.sub.depth = 8; sim.update(0.05); }
  assert.equal(sim.engines[1].fault, null, 'clears once cool');
});

test('fuel transfer pump fills the day tank; jerrycans top it up; oil cans and wrenches fix the engines', () => {
  const sim = quiet();
  sim.fuel.day = 10; const main = sim.fuel.main;
  for (let i = 0; i < 20; i++) sim.fuelStroke();
  assert.ok(sim.fuel.day > 35 && sim.fuel.main < main);
  sim.pourFuel(20);
  assert.ok(sim.fuel.day > 55);
  sim.engines[0].oil = 5; sim.engines[0].fault = 'oil'; sim.addOil(0);
  assert.equal(sim.engines[0].oil, 100); assert.equal(sim.engines[0].fault, null);
  sim.engines[1].fault = 'injector';
  assert.ok(sim.fixEngine(1)); assert.equal(sim.engines[1].fault, null);
});

test('fires fill the room with smoke, smoke spreads, vent fans clear it (with power)', () => {
  const sim = quiet();
  sim.sub.depth = 30; sim.sub.ballast = 0.5;
  sim.addFire(R.CrewMess); sim.fires[0].intensity = 1;
  step(sim, 15);
  assert.ok(sim.smoke[R.CrewMess] > 0.3, `mess ${sim.smoke[R.CrewMess]}`);
  assert.ok(sim.smoke[R.ControlRoom] > 0.01, 'drifts through the open door');
  sim.fires.forEach((f) => { f.out = true; });
  sim.doors.fill(false);                           // seal the mess: only its own fans can clear it now
  const s0 = sim.smoke[R.CrewMess];
  sim.setVent(R.CrewMess, true);
  sim.power = false; step(sim, 5);
  assert.ok(sim.smoke[R.CrewMess] > s0 * 0.9, `no fans without power (${s0.toFixed(2)} -> ${sim.smoke[R.CrewMess].toFixed(2)})`);
  sim.power = true; step(sim, 15);
  assert.ok(sim.smoke[R.CrewMess] < 0.1, `cleared ${sim.smoke[R.CrewMess]}`);
});

test('flood water puts out a fire', () => {
  const sim = quiet();
  sim.addFire(R.TorpedoRoom);
  sim.water[R.TorpedoRoom] = 0.5;
  step(sim, 3);
  assert.ok(sim.fires[0].out);
});

test('hull shock frees the boat from a squid', () => {
  const sim = new Sim();
  sim.sub.depth = 80;
  const q = sim.add({ kind: 'squid', x: 0, z: 0, depth: 82, heading: 0, speed: 0, hp: 2, length: 13, state: 'stalk', attached: true, grabTimer: 3 });
  sim.hullShock();
  assert.equal(q.attached, false);
  assert.equal(q.state, 'flee');
});

test('crushing depth damages the hull', () => {
  const sim = new Sim();
  sim.sub.depth = 230; sim.sub.ballast = 0.5;
  step(sim, 10);
  assert.ok(sim.sub.hull < 100);
});

test('flat battery limits speed when submerged', () => {
  const sim = new Sim();
  sim.sub.depth = 40; sim.sub.ballast = 0.5; sim.sub.battery = 0.01;
  sim.setTelegraph(4); step(sim, 2);
  assert.equal(sim.sub.telegraph, 1);
});

test('a long patrol runs without errors', () => {
  const sim = new Sim();
  sim.setTelegraph(2); sim.setValve('flood');
  for (let i = 0; i < 6000; i++) { sim.update(0.05); if (i % 400 === 0) sim.setRudder(Math.sin(i) * 0.8); if (sim.sub.depth > 80) sim.setValve('hold'); }
  assert.ok(sim.time > 299);
});
test('fires grow, burn oxygen and can be put out', () => {
  const sim = new Sim();
  sim.entities.forEach((e) => { e.alive = false; }); sim.spawnWave = () => {};
  sim.sub.depth = 30; sim.sub.ballast = 0.5;
  sim.addFire(1);
  const o2 = sim.sub.oxygen;
  step(sim, 10);
  assert.ok(sim.sub.oxygen < o2 - 0.5);
  const f = sim.fires[0];
  for (let i = 0; i < 100 && !f.out; i++) sim.extinguish(f.id, 0.05);
  assert.ok(f.out);
});

test('power failure limits speed until the breakers are reset', () => {
  const sim = new Sim();
  sim.power = false; sim.setTelegraph(4); step(sim, 1);
  assert.equal(sim.sub.telegraph, 1);
  sim.resetPower(); sim.setTelegraph(4); step(sim, 1);
  assert.equal(sim.sub.telegraph, 4);
});

test('the main breaker only closes once every tripped breaker is closed', () => {
  const sim = quiet();
  sim.tripPower();
  const tripped = sim.breakers.map((b, k) => (b ? -1 : k)).filter((k) => k >= 0);
  assert.ok(tripped.length >= 1 && !sim.power);
  sim.mainBreaker();
  assert.ok(!sim.power, 'still dark');
  for (const k of tripped) sim.setBreaker(k, true);
  sim.mainBreaker();
  assert.ok(sim.power);
});

test('damage tears leaks in compartments along the hull, including the lower deck', () => {
  const sim = quiet();
  const seen = new Set();
  for (let i = 0; i < 200; i++) sim.addLeak(sim.roomsAlongHull(Math.random())[0]);
  for (const l of sim.leaks) seen.add(l.room);
  assert.ok(seen.size >= 5, [...seen].join());
  for (const l of sim.leaks) {
    const r = ROOMS[l.room];
    assert.ok(l.x >= r.x0 && l.x <= r.x1, `leak inside ${r.name}`);
    assert.ok(Math.abs(l.z) < r.halfW, 'on the hull plating');
  }
});
console.log(`${pass} tests passed`);
