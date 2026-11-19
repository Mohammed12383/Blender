// Headless checks of the two-deck walkable areas: node game/test/nav.test.mjs
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Nav } from '../src/nav.js';

const data = JSON.parse(readFileSync(new URL('../../submarine/models/nav.json', import.meta.url)));
let pass = 0;
const test = (name, fn) => { fn(); pass++; console.log('ok -', name); };
const open = [true, true, true, true, true, true];

// walk towards a point in small steps (like the game loop), returning the final position
function walk(nav, p, tx, tz, doors = open, steps = 4000) {
  for (let i = 0; i < steps; i++) {
    const dx = tx - p.x, dz = tz - p.z, d = Math.hypot(dx, dz);
    if (d < 0.05) break;
    const s = Math.min(d, 0.04);
    const f = nav.move(p, dx / d * s, dz / d * s, doors);
    if (f !== null) p.y = f;
  }
  return p;
}

test('each deck has its own floor: control room above, battery room below', () => {
  const nav = new Nav(data);
  assert.equal(nav.floorAt(12, 0.5, 0, open), 0);
  assert.equal(nav.floorAt(12, 0.5, -2.9, open), -2.9);
  assert.equal(nav.floorAt(20, 0.5, -2.9, open), null, 'nothing below the crew mess');
  assert.equal(nav.floorAt(20, 0.5, -1.4, open), null, 'no floor between the decks');
});

test('closed watertight doors block the way, open ones let you through', () => {
  const nav = new Nav(data);
  const shut = [false, true, true, true, true, true];
  const p = walk(nav, { x: 9, y: 0, z: 0 }, 4, 0, shut);
  assert.ok(p.x > 7.2, `stopped at the shut door, x=${p.x.toFixed(2)}`);
  const q = walk(nav, { x: 9, y: 0, z: 0 }, 4, 0, open);
  assert.ok(q.x < 4.2, `went through the open door, x=${q.x.toFixed(2)}`);
});

test('the stairwell opening cannot be walked into from the side', () => {
  const nav = new Nav(data);
  const p = walk(nav, { x: 5.0, y: 0, z: 0 }, 5.0, -2.1);
  assert.ok(p.z > -1.2, `stopped at the railing, z=${p.z.toFixed(2)}`);
  assert.equal(p.y, 0);
});

test('down the stairs from the quarters to the torpedo room and back up', () => {
  const nav = new Nav(data);
  const p = { x: 2.6, y: 0, z: -1.72 };
  walk(nav, p, 7.0, -1.72);          // down the stairs (they run aft)
  assert.ok(Math.abs(p.y + 2.9) < 0.05, `at the bottom y=${p.y.toFixed(2)} x=${p.x.toFixed(2)}`);
  walk(nav, p, 5.0, 0.5);            // into the torpedo room
  assert.ok(Math.abs(p.y + 2.9) < 0.05 && p.x < 5.2, `in the torpedo room ${JSON.stringify(p)}`);
  walk(nav, p, 6.6, -1.72); walk(nav, p, 2.6, -1.72);   // back to the foot of the stairs and up
  assert.ok(Math.abs(p.y) < 0.05 && p.x < 3.0, `back upstairs ${JSON.stringify(p)}`);
});

test('lower deck: torpedo room to the battery room through the lower door', () => {
  const nav = new Nav(data);
  const p = walk(nav, { x: 4.0, y: -2.9, z: 0.5 }, 12, 0);
  assert.ok(p.x > 11.5 && Math.abs(p.y + 2.9) < 0.01, JSON.stringify(p));
});

test('engine room: catwalk between the diesels, not into the pit', () => {
  const nav = new Nav(data);
  const p = walk(nav, { x: 30, y: 0, z: 0 }, 43, 0);
  assert.ok(p.x > 42.5, `reached the aft platform x=${p.x.toFixed(2)}`);
  const q = walk(nav, { x: 36, y: 0, z: 0 }, 36, -1.6);
  assert.ok(q.z > -0.5, `kept on the catwalk z=${q.z.toFixed(2)}`);
  const r = walk(nav, { x: 43, y: 0, z: 0 }, 43, -2.0);
  assert.ok(r.z < -1.8, `the aft platform is wide z=${r.z.toFixed(2)}`);
});

test('passage walkway is fenced in by its railings', () => {
  const nav = new Nav(data);
  const p = walk(nav, { x: 29.5, y: 0, z: 0 }, 29.5, 2.0);
  assert.ok(p.z < 0.5, `z=${p.z.toFixed(2)}`);
});

test('swimmers float over the stairwell and sink into the torpedo room', () => {
  const nav = new Nav(data);
  assert.ok(nav.floorAt(5.0, -1.75, 0.4, open, true) !== null, 'water over the stairwell is swimmable');
  assert.equal(nav.floorAt(5.0, 0.5, -1.0, open, true), -2.9);
  assert.equal(nav.ceilingAt(10, 0, -2.0), data.ceil.lower - 0.05);
  assert.equal(nav.ceilingAt(5.0, -1.8, -2.0), data.ceil.upper - 0.1);
});

console.log(`${pass} nav tests passed`);
