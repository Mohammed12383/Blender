// Headless checks of the game simulation: node game/test/sim.test.mjs
import assert from 'node:assert/strict';
import { Sim } from '../src/sim.js';

const step = (sim, seconds) => { for (let t = 0; t < seconds; t += 0.05) sim.update(0.05); };
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
  const before = sim.water.reduce((a, b) => a + b);
  step(sim, 60);
  assert.ok(sim.water.reduce((a, b) => a + b) < before, 'pumps drain the water');
});

test('closed doors stop flood water spreading', () => {
  const sim = new Sim();
  sim.entities.forEach((e) => { e.alive = false; }); sim.spawnWave = () => {};
  sim.toggleDoor(0); sim.toggleDoor(1); sim.toggleDoor(2);
  sim.addLeak(0, 1.5); sim.addLeak(0, 1.5);
  step(sim, 40);
  assert.ok(sim.water[0] > 0.2 && sim.water[2] < 0.01, sim.water.join());
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
console.log(`${pass} tests passed`);
