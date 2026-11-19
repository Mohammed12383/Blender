// Drawing for the control-room console screens: SHIP STATUS pages, the DIVE PROFILE, the FIRE CONTROL target
// scope and the chart table's route overlay. Each function paints one 2D canvas from the simulation state.
import { ROOMS, DOORS, TEST_DEPTH, PERISCOPE_DEPTH, SNORKEL_DEPTH, ENGINE_FAULTS, seabed } from './sim.js';

export const STATUS_PAGES = ['noise', 'air', 'engines', 'power', 'leaks', 'flood', 'fire', 'crew'];
export const STATUS_TITLES = { noise: 'NOISE & STEALTH', air: 'AIR & SMOKE', engines: 'ENGINES & FUEL', power: 'ELECTRICAL',
  leaks: 'HULL LEAKS', flood: 'FLOODING', fire: 'FIRE', crew: 'CREW' };
export const BREAKER_NAMES = ['LIGHTING', 'NAVIGATION', 'SONAR', 'WEAPONS', 'PUMPS', 'VENTILATION', 'GALLEY', 'AUX'];

const deg = (a) => ((Math.round(a * 180 / Math.PI) % 360) + 360) % 360;
const pad3 = (n) => String(n).padStart(3, '0');
const bearingTo = (s, e) => Math.atan2(-(e.z - s.z), e.x - s.x);

function bar(ctx, x, y, w, h, frac, col, back = '#14202a') {
  ctx.fillStyle = back; ctx.fillRect(x, y, w, h);
  ctx.fillStyle = col; ctx.fillRect(x, y, w * Math.max(0, Math.min(1, frac)), h);
  ctx.strokeStyle = '#3d5566'; ctx.lineWidth = 1; ctx.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1);
}
function text(ctx, s, x, y, col = '#bfe8ff', font = '18px monospace', align = 'left') {
  ctx.fillStyle = col; ctx.font = font; ctx.textAlign = align; ctx.fillText(s, x, y); ctx.textAlign = 'left';
}

// Two-deck plan of the boat (bow on the left). fill(room) -> colour or null, then marks are drawn on top.
function deckPlan(ctx, x0, y0, w, h, fill, marks = []) {
  const sx = w / 44.3, deckH = h * 0.46;
  const ry = (r) => (r.deck === 'upper' ? y0 : y0 + h - deckH);
  // hull outline
  ctx.strokeStyle = '#4f7d90'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.ellipse(x0 + w / 2, y0 + h / 2, w / 2 + 10, h / 2 + 8, 0, 0, Math.PI * 2); ctx.stroke();
  ROOMS.forEach((r, i) => {
    const x = x0 + r.x0 * sx, y = ry(r), rw = (r.x1 - r.x0) * sx;
    const c = fill(i, r);
    ctx.fillStyle = c || '#0f1c24'; ctx.fillRect(x, y, rw, deckH);
    ctx.strokeStyle = '#3d6474'; ctx.lineWidth = 1.5; ctx.strokeRect(x + 0.5, y + 0.5, rw - 1, deckH - 1);
    ctx.fillStyle = '#9fc4d2'; ctx.font = '11px monospace';
    const lbl = r.label.replace('FORWARD ', 'FWD ').replace('ENGINE PASSAGE', 'PASSAGE');
    ctx.fillText(lbl.length * 6.6 > rw - 6 ? lbl.split(' ')[0] : lbl, x + 4, y + 13);
  });
  // watertight doors: green open, red shut
  for (const m of marks) {
    if (m.door !== undefined) {
      const d = DOORS[m.door], r = ROOMS[d.a];
      ctx.fillStyle = m.open ? '#4cff8a' : '#ff5a4f';
      ctx.fillRect(x0 + (d.x + 0.15) * sx - 2, ry(r) + deckH * 0.3, 4, deckH * 0.4);
    } else {
      const r = ROOMS[m.room];
      const px = x0 + m.x * sx, py = ry(r) + deckH * (m.v ?? 0.6);
      ctx.fillStyle = m.col; ctx.beginPath(); ctx.arc(px, py, m.r || 6, 0, Math.PI * 2); ctx.fill();
      if (m.ring) { ctx.strokeStyle = m.col; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(px, py, (m.r || 6) + m.ring, 0, Math.PI * 2); ctx.stroke(); }
    }
  }
}

// ------------------------------------------------------------------ SHIP STATUS
export function drawStatus(ctx, W0, H0, sim, page, info) {
  ctx.fillStyle = '#071118'; ctx.fillRect(0, 0, W0, H0);
  ctx.save(); ctx.translate(W0 * 0.045, H0 * 0.05); ctx.scale(0.91, 0.9);
  try { statusPage(ctx, W0, H0, sim, page, info); } finally { ctx.restore(); }
}
function statusPage(ctx, W, H, sim, page, info) {
  const s = sim.sub, t = sim.time;
  ctx.fillStyle = '#071118'; ctx.fillRect(0, 0, W, H);
  // header + page tabs
  ctx.fillStyle = '#0f2a38'; ctx.fillRect(0, 0, W, 46);
  text(ctx, 'SHIP STATUS', 14, 31, '#7dd8ff', 'bold 22px monospace');
  text(ctx, STATUS_TITLES[page], W - 14, 31, '#ffffff', 'bold 22px monospace', 'right');
  const tw = W / STATUS_PAGES.length;
  STATUS_PAGES.forEach((p, i) => {
    const alert = info.alerts[p];
    ctx.fillStyle = p === page ? '#2c7fa8' : alert && Math.sin(t * 6) > 0 ? '#7a1d17' : '#0c1f29';
    ctx.fillRect(i * tw + 2, H - 30, tw - 4, 28);
    text(ctx, p.toUpperCase(), i * tw + tw / 2, H - 10, p === page ? '#ffffff' : alert ? '#ffb4ae' : '#7fa3b3', 'bold 13px monospace', 'center');
  });
  const top = 62, bottom = H - 40;
  if (sim.alarm) {
    ctx.fillStyle = Math.sin(t * 8) > 0 ? '#c0281f' : '#5a0d09'; ctx.fillRect(W / 2 - 120, 8, 240, 30);
    text(ctx, 'GENERAL ALARM', W / 2, 30, '#ffffff', 'bold 18px monospace', 'center');
  }
  if (page === 'noise') {
    const n = sim.noiseLevel || 0, k = Math.min(1, n / 16);
    const col = k < 0.35 ? '#4cff8a' : k < 0.7 ? '#ffcf4a' : '#ff5a4f';
    text(ctx, 'NOISE', 20, top + 22, '#9fc4d2', 'bold 18px monospace');
    bar(ctx, 100, top + 4, W - 220, 26, k, col);
    text(ctx, k < 0.35 ? 'QUIET' : k < 0.7 ? 'AUDIBLE' : 'LOUD', W - 20, top + 24, col, 'bold 20px monospace', 'right');
    const parts = [['SPEED', Math.abs(s.speed) * 0.6], ['DIESELS', sim.engines.filter((e) => e.running).length * 2.5],
      ['PERISCOPE', s.periscopeUp ? 2 : 0], ['BLOWING TANKS', s.valve === 'blow' ? 2 : 0], ['SURFACED', s.depth < 3 ? 4 : 0],
      ['PING / LAUNCH', s.noise]];
    parts.forEach(([nm, v], i) => {
      const y = top + 60 + i * 30;
      text(ctx, nm, 20, y + 15, v > 0.05 ? '#d8eef7' : '#5d7a87', '16px monospace');
      bar(ctx, 200, y, 220, 18, v / 6, v > 2.5 ? '#ff8a5a' : '#58c2f0');
    });
    const hostile = sim.entities.filter((e) => e.alive && (e.kind === 'frigate' || e.kind === 'enemySub'));
    const hunting = hostile.filter((e) => e.state === 'hunt').length;
    const near = hostile.length ? Math.min(...hostile.map((e) => Math.hypot(e.x - s.x, e.z - s.z))) : null;
    const known = [...sim.contacts.keys()].filter((id) => sim.entities.some((e) => e.id === id && e.alive)).length;
    [[`HUNTING US`, hunting ? `${hunting}` : 'NONE', hunting ? '#ff5a4f' : '#4cff8a'],
      ['CONTACTS', `${known}`, '#d8eef7'], ['NEAREST HOSTILE', near ? `${near.toFixed(0)} m` : '-', near && near < 600 ? '#ffcf4a' : '#d8eef7'],
      ['DEPTH', `${s.depth.toFixed(0)} m`, '#d8eef7']].forEach(([a, b, c], i) => {
      text(ctx, a, 450, top + 75 + i * 40, '#9fc4d2', '15px monospace');
      text(ctx, b, W - 20, top + 75 + i * 40, c, 'bold 18px monospace', 'right');
    });
  } else if (page === 'air') {
    text(ctx, 'OXYGEN', 20, top + 24, '#9fc4d2', 'bold 18px monospace');
    bar(ctx, 120, top + 6, 300, 26, s.oxygen / 100, s.oxygen < 25 ? '#ff5a4f' : s.oxygen < 50 ? '#ffcf4a' : '#4cff8a');
    text(ctx, `${s.oxygen.toFixed(0)} %`, 440, top + 27, '#ffffff', 'bold 20px monospace');
    const refresh = s.depth < 1 ? 'SURFACED: FRESH AIR' : s.depth <= SNORKEL_DEPTH && sim.engines.some((e) => e.running) ? 'SNORKEL DRAWING AIR' : 'SEALED: SURFACE OR SNORKEL';
    text(ctx, refresh, 120, top + 54, '#9fc4d2', '14px monospace');
    deckPlan(ctx, 40, top + 76, W - 80, bottom - top - 86, (i) => {
      const sm = sim.smoke[i]; if (sm < 0.02) return '#12303a';
      return `rgba(${120 + sm * 80 | 0},${110 - sm * 40 | 0},${100 - sm * 50 | 0},1)`;
    }, ROOMS.map((r, i) => (sim.vents[i] ? { room: i, x: r.x1 - 0.8, v: 0.75, col: '#58c2f0', r: 5, ring: Math.sin(t * 10) > 0 ? 3 : 0 } : null)).filter(Boolean));
    text(ctx, 'grey = smoke   blue = SMOKE EXTRACT fans on', W / 2, bottom - 2, '#7fa3b3', '12px monospace', 'center');
  } else if (page === 'engines') {
    sim.engines.forEach((e, i) => {
      const x = 20 + i * 305, y = top;
      ctx.strokeStyle = '#3d6474'; ctx.strokeRect(x, y, 290, 190);
      const st = e.fault ? 'FAULT' : e.running ? 'RUNNING' : e.crank ? 'CRANKING' : 'STOPPED';
      text(ctx, `DIESEL ${e.id}`, x + 12, y + 28, '#ffffff', 'bold 20px monospace');
      text(ctx, st, x + 278, y + 28, e.fault ? '#ff5a4f' : e.running ? '#4cff8a' : '#9fc4d2', 'bold 18px monospace', 'right');
      [['RPM', e.rpm / 900, `${e.rpm.toFixed(0)}`, '#58c2f0'], ['TEMP', (e.temp - 20) / 90, `${e.temp.toFixed(0)}°C`, e.temp > 95 ? '#ff5a4f' : '#ffcf4a'],
        ['OIL', e.oil / 100, `${e.oil.toFixed(0)} %`, e.oil < 25 ? '#ff5a4f' : '#c9a24a']].forEach(([a, f, v, c], k) => {
        text(ctx, a, x + 12, y + 66 + k * 34, '#9fc4d2', '15px monospace');
        bar(ctx, x + 70, y + 52 + k * 34, 140, 18, f, c);
        text(ctx, v, x + 278, y + 66 + k * 34, '#d8eef7', '15px monospace', 'right');
      });
      text(ctx, `COOLANT ${e.coolant ? 'OPEN' : 'SHUT!'}`, x + 12, y + 172, e.coolant ? '#4cff8a' : '#ff5a4f', 'bold 15px monospace');
      if (e.fault) text(ctx, ENGINE_FAULTS[e.fault].toUpperCase(), x + 278, y + 172, '#ff5a4f', 'bold 13px monospace', 'right');
    });
    text(ctx, 'DAY TANK', 20, top + 228, '#9fc4d2', '15px monospace'); bar(ctx, 120, top + 214, 200, 18, sim.fuel.day / 100, '#c9a24a');
    text(ctx, `${sim.fuel.day.toFixed(0)} L`, 330, top + 228, '#d8eef7', '15px monospace');
    text(ctx, 'BATTERY', 20, top + 260, '#9fc4d2', '15px monospace'); bar(ctx, 120, top + 246, 200, 18, s.battery / 100, s.battery < 20 ? '#ff5a4f' : '#4cff8a');
    text(ctx, `${s.battery.toFixed(0)} %  ${s.charging ? 'CHARGING' : 'DISCHARGING'}`, 330, top + 260, '#d8eef7', '15px monospace');
    text(ctx, `MAIN BUNKERS ${sim.fuel.main.toFixed(0)} L`, W - 20, top + 228, '#d8eef7', '15px monospace', 'right');
  } else if (page === 'power') {
    text(ctx, 'MAIN BUS', 20, top + 26, '#9fc4d2', 'bold 18px monospace');
    text(ctx, sim.power ? 'POWER ON' : 'NO POWER', 160, top + 26, sim.power ? '#4cff8a' : Math.sin(t * 6) > 0 ? '#ff5a4f' : '#7a1d17', 'bold 22px monospace');
    BREAKER_NAMES.forEach((nm, i) => {
      const x = 20 + (i % 4) * 152, y = top + 52 + Math.floor(i / 4) * 92, on = sim.breakers[i];
      ctx.fillStyle = on ? '#123826' : '#3a1210'; ctx.fillRect(x, y, 140, 80);
      ctx.strokeStyle = on ? '#4cff8a' : '#ff5a4f'; ctx.lineWidth = 2; ctx.strokeRect(x + 1, y + 1, 138, 78);
      text(ctx, `${i + 1}`, x + 10, y + 26, '#ffffff', 'bold 20px monospace');
      text(ctx, on ? 'CLOSED' : 'TRIPPED', x + 130, y + 26, on ? '#4cff8a' : '#ff5a4f', 'bold 14px monospace', 'right');
      text(ctx, nm, x + 10, y + 62, '#d8eef7', '14px monospace');
    });
    text(ctx, sim.power ? 'Switchboard: battery room, lower deck' : 'Close every tripped breaker, then the MAIN BREAKER', 20, bottom - 6, '#9fc4d2', '14px monospace');
  } else if (page === 'leaks' || page === 'flood' || page === 'fire') {
    const open = sim.leaks.filter((l) => !l.fixed), fires = sim.fires.filter((f) => !f.out);
    const marks = DOORS.map((d, i) => ({ door: i, open: sim.doors[i] }));
    let fill = () => null;
    if (page === 'leaks') {
      open.forEach((l) => marks.push({ room: l.room, x: l.x, v: 0.3 + (l.side > 0 ? 0.4 : 0), col: '#4fb3ff', r: 5 + l.severity * 3, ring: Math.sin(t * 8) > 0 ? 3 : 0 }));
      fill = (i) => (open.some((l) => l.room === i) ? '#123048' : null);
    } else if (page === 'flood') {
      fill = (i, r) => { const k = sim.water[i] / r.height; return k > 0.005 ? `rgb(${20}, ${60 + k * 120 | 0}, ${110 + k * 140 | 0})` : null; };
    } else {
      fires.forEach((f) => marks.push({ room: f.room, x: f.x, v: 0.62, col: Math.sin(t * 12 + f.id) > 0 ? '#ff7a2a' : '#ffcf4a', r: 5 + f.intensity * 5 }));
      fill = (i) => (fires.some((f) => f.room === i) ? '#4a1e10' : sim.smoke[i] > 0.1 ? '#3a3a36' : null);
    }
    deckPlan(ctx, 40, top + 8, W - 80, 170, fill, marks);
    const lines = page === 'leaks'
      ? (open.length ? open.slice(0, 5).map((l) => `LEAK  ${ROOMS[l.room].label.padEnd(18)} ${(l.severity * 100).toFixed(0)}%  ${l.side > 0 ? 'STBD' : 'PORT'}`) : ['NO LEAKS'])
      : page === 'flood'
        ? ROOMS.map((r, i) => [r, sim.water[i]]).filter(([, w]) => w > 0.01).slice(0, 5).map(([r, w]) => `${r.label.padEnd(18)} ${w.toFixed(2)} m`).concat(sim.floodFraction() < 0.001 ? ['BOAT IS DRY'] : [`TOTAL FLOODED ${(sim.floodFraction() * 100).toFixed(0)} %`])
        : (fires.length ? fires.slice(0, 5).map((f) => `FIRE  ${ROOMS[f.room].label.padEnd(18)} ${(f.intensity * 100).toFixed(0)}%`) : ['NO FIRES']);
    lines.forEach((l, i) => text(ctx, l, 40, top + 210 + i * 24, /NO |DRY/.test(l) ? '#4cff8a' : '#ffcf4a', '16px monospace'));
    if (page !== 'flood') text(ctx, 'green/red ticks: watertight doors open/shut', W - 20, bottom - 4, '#7fa3b3', '12px monospace', 'right');
  } else if (page === 'crew') {
    info.crew.forEach((c, i) => {
      const y = top + 8 + i * 72;
      ctx.fillStyle = '#0c1f29'; ctx.fillRect(20, y, W - 40, 62);
      ctx.fillStyle = ['#ffcf4a', '#58c2f0', '#4cff8a', '#ff8a5a'][i % 4]; ctx.beginPath(); ctx.arc(48, y + 31, 18, 0, 7); ctx.fill();
      text(ctx, `${i + 1}`, 48, y + 38, '#071118', 'bold 18px monospace', 'center');
      text(ctx, c.name, 80, y + 26, '#ffffff', 'bold 18px monospace');
      text(ctx, `${c.role}  ·  ${c.where}`, 80, y + 50, '#9fc4d2', '14px monospace');
      if (c.health !== undefined) {
        text(ctx, 'HP', 420, y + 26, '#9fc4d2', '13px monospace'); bar(ctx, 450, y + 13, 150, 14, c.health / 100, c.health < 30 ? '#ff5a4f' : '#4cff8a');
        text(ctx, 'FOOD', 404, y + 50, '#9fc4d2', '13px monospace'); bar(ctx, 450, y + 37, 150, 14, c.hunger / 100, '#ffcf4a');
      }
    });
  }
}

// ------------------------------------------------------------------ DIVE PROFILE (ballast panel)
export function drawDiveProfile(ctx, W0, H0, sim) {
  ctx.fillStyle = '#04100a'; ctx.fillRect(0, 0, W0, H0);
  ctx.save(); ctx.translate(W0 * 0.05, H0 * 0.06); ctx.scale(0.9, 0.88);
  try { diveProfile(ctx, W0, H0, sim); } finally { ctx.restore(); }
}
function diveProfile(ctx, W, H, sim) {
  const s = sim.sub;
  ctx.fillStyle = '#04100a'; ctx.fillRect(0, 0, W, H);
  const px0 = 54, px1 = W - 120, py0 = 40, py1 = H - 26;
  const behind = 500, ahead = 1500;
  const maxD = Math.max(260, Math.ceil((seabed(s.x, s.z) + 40) / 50) * 50);
  const X = (d) => px0 + (d + behind) / (behind + ahead) * (px1 - px0);
  const Y = (z) => py0 + z / maxD * (py1 - py0);
  text(ctx, 'DIVE PROFILE', 12, 28, '#7dffb0', 'bold 22px monospace');
  text(ctx, `HDG ${pad3(deg(s.heading))}`, px1, 28, '#7dffb0', '16px monospace', 'right');
  // depth grid
  ctx.strokeStyle = '#123a24'; ctx.lineWidth = 1;
  for (let z = 50; z < maxD; z += 50) { ctx.beginPath(); ctx.moveTo(px0, Y(z)); ctx.lineTo(px1, Y(z)); ctx.stroke(); text(ctx, `${z}`, px0 - 6, Y(z) + 5, '#3f8f5f', '12px monospace', 'right'); }
  // surface, periscope depth, test depth
  ctx.strokeStyle = '#58c2f0'; ctx.lineWidth = 2; ctx.beginPath();
  for (let x = px0; x <= px1; x += 6) ctx.lineTo(x, Y(0) + Math.sin(x * 0.12 + sim.time * 2) * 2);
  ctx.stroke();
  ctx.setLineDash([6, 6]);
  ctx.strokeStyle = '#7dffb0'; ctx.beginPath(); ctx.moveTo(px0, Y(PERISCOPE_DEPTH)); ctx.lineTo(px1, Y(PERISCOPE_DEPTH)); ctx.stroke();
  ctx.strokeStyle = '#ff5a4f'; ctx.beginPath(); ctx.moveTo(px0, Y(TEST_DEPTH)); ctx.lineTo(px1, Y(TEST_DEPTH)); ctx.stroke();
  ctx.setLineDash([]);
  text(ctx, 'PERISCOPE', px0 + 4, Y(PERISCOPE_DEPTH) - 4, '#7dffb0', '11px monospace');
  text(ctx, 'HULL LIMIT', px0 + 4, Y(TEST_DEPTH) - 4, '#ff5a4f', '11px monospace');
  // sea floor along our heading
  const cx = Math.cos(s.heading), cz = -Math.sin(s.heading);
  ctx.fillStyle = '#1d5a3a'; ctx.strokeStyle = '#7dffb0'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(px0, py1);
  for (let d = -behind; d <= ahead; d += 25) ctx.lineTo(X(d), Math.min(py1, Y(seabed(s.x + cx * d, s.z + cz * d))));
  ctx.lineTo(px1, py1); ctx.closePath(); ctx.fill(); ctx.stroke();
  // contacts near our track: ships on the surface, submarines and creatures at depth
  for (const [id, c] of sim.contacts) {
    const e = sim.entities.find((q) => q.id === id);
    if (!e || !e.alive || sim.time - c.lastSeen > 30) continue;
    const dx = e.x - s.x, dz = e.z - s.z, along = dx * cx + dz * cz, across = Math.abs(-dx * cz + dz * cx);
    if (along < -behind || along > ahead || across > 1500) continue;
    const z = e.kind === 'frigate' || e.kind === 'freighter' ? 0 : e.depth || 20;
    ctx.fillStyle = e.kind === 'freighter' ? '#4cff8a' : e.kind === 'shark' || e.kind === 'squid' ? '#c77dff' : '#ff5a4f';
    ctx.beginPath();
    if (z === 0) { ctx.moveTo(X(along) - 12, Y(0) - 2); ctx.lineTo(X(along) + 12, Y(0) - 2); ctx.lineTo(X(along) + 8, Y(0) + 5); ctx.lineTo(X(along) - 8, Y(0) + 5); ctx.rect(X(along) - 2, Y(0) - 10, 5, 8); }
    else { ctx.ellipse(X(along), Y(z), 11, 4, 0, 0, 7); }
    ctx.fill();
  }
  // our boat (pitched)
  ctx.save(); ctx.translate(X(0), Y(s.depth)); ctx.rotate(-(s.pitch || 0) * 3);
  ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.ellipse(0, 0, 16, 5, 0, 0, 7); ctx.fill(); ctx.fillRect(-3, -10, 7, 6);
  ctx.restore();
  ctx.strokeStyle = '#ffffff55'; ctx.beginPath(); ctx.arc(X(0), Y(s.depth), 34, 0, 7); ctx.stroke();
  // readouts
  const keel = seabed(s.x, s.z) - s.depth;
  const rx = W - 110;
  [['DEPTH', `${s.depth.toFixed(0)} m`, '#ffffff'], ['RATE', `${(s.vy * 60).toFixed(0)}`, s.vy > 0.3 ? '#ffcf4a' : '#d8ffe8'],
    ['KEEL', `${keel.toFixed(0)} m`, keel < 30 ? '#ff5a4f' : '#d8ffe8'], ['BALLAST', `${(s.ballast * 100).toFixed(0)} %`, '#d8ffe8'],
    ['PLANES', s.planes > 0.05 ? 'RISE' : s.planes < -0.05 ? 'DIVE' : 'LEVEL', '#d8ffe8'], ['VALVE', s.valve.toUpperCase(), s.valve === 'hold' ? '#d8ffe8' : '#ffcf4a']]
    .forEach(([a, b, c], i) => { text(ctx, a, rx, 62 + i * 52, '#3f8f5f', '13px monospace'); text(ctx, b, rx, 84 + i * 52, c, 'bold 19px monospace'); });
}

// ------------------------------------------------------------------ FIRE CONTROL target scope
export function drawFireScope(ctx, W0, H0, sim) {
  ctx.fillStyle = '#080a08'; ctx.fillRect(0, 0, W0, H0);
  ctx.save(); ctx.translate(W0 * 0.04, H0 * 0.05); ctx.scale(0.92, 0.9);
  try { fireScope(ctx, W0, H0, sim); } finally { ctx.restore(); }
}
function fireScope(ctx, W, H, sim) {
  const s = sim.sub, w = sim.weapons, t = sim.time;
  ctx.fillStyle = '#080a08'; ctx.fillRect(0, 0, W, H);
  const cx = 210, cy = 250, R = 190, range = 2000;   // torpedo reach ~2 km
  text(ctx, 'FIRE CONTROL', 16, 34, '#ffb52e', 'bold 24px monospace');
  // scope rings and bearing ticks (heading up)
  ctx.strokeStyle = '#3a5a28'; ctx.lineWidth = 1;
  for (const k of [1 / 4, 1 / 2, 3 / 4, 1]) { ctx.beginPath(); ctx.arc(cx, cy, R * k, 0, 7); ctx.stroke(); }
  for (let a = 0; a < 360; a += 10) {
    const r0 = a % 30 ? R - 6 : R - 13, ang = a * Math.PI / 180;
    ctx.strokeStyle = '#6fbf4a'; ctx.beginPath(); ctx.moveTo(cx + Math.sin(ang) * r0, cy - Math.cos(ang) * r0); ctx.lineTo(cx + Math.sin(ang) * R, cy - Math.cos(ang) * R); ctx.stroke();
  }
  ctx.strokeStyle = '#2a4a1c'; ctx.beginPath(); ctx.moveTo(cx - R, cy); ctx.lineTo(cx + R, cy); ctx.moveTo(cx, cy - R); ctx.lineTo(cx, cy + R); ctx.stroke();
  const toScope = (e) => {
    const rel = bearingTo(s, e) - s.heading, d = Math.hypot(e.x - s.x, e.z - s.z) / range * R;
    return [cx - Math.sin(rel) * d, cy - Math.cos(rel) * d, d];
  };
  // aim line along the AIM stick course
  const lock = sim.entities.find((e) => e.id === w.lock && e.alive);
  const aimA = lock ? bearingTo(s, lock) - s.heading : w.aim || 0;
  ctx.setLineDash([10, 8]); ctx.strokeStyle = lock ? '#ff5a4f' : '#ffb52e'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(cx, cy); ctx.lineTo(cx - Math.sin(aimA) * R, cy - Math.cos(aimA) * R); ctx.stroke(); ctx.setLineDash([]);
  // contacts
  for (const [id, c] of sim.contacts) {
    const e = sim.entities.find((q) => q.id === id);
    if (!e || !e.alive || sim.time - c.lastSeen > 30) continue;
    const [x, y, d] = toScope(e); if (d > R) continue;
    ctx.fillStyle = e.kind === 'freighter' ? '#4cff8a' : e.kind === 'shark' || e.kind === 'squid' ? '#c77dff' : '#ff5a4f';
    ctx.beginPath(); ctx.arc(x, y, 6, 0, 7); ctx.fill();
    if (e.id === w.lock) { ctx.strokeStyle = '#ff5a4f'; ctx.lineWidth = 2; ctx.strokeRect(x - 13, y - 13, 26, 26); ctx.beginPath(); ctx.moveTo(x - 20, y); ctx.lineTo(x + 20, y); ctx.moveTo(x, y - 20); ctx.lineTo(x, y + 20); ctx.stroke(); }
  }
  for (const tp of sim.torpedoes) { const [x, y, d] = toScope(tp); if (d < R) { ctx.fillStyle = tp.owner === 'player' ? '#58c2f0' : Math.sin(t * 10) > 0 ? '#ff1744' : '#ffffff'; ctx.fillRect(x - 3, y - 3, 6, 6); } }
  ctx.fillStyle = '#ffb52e'; ctx.beginPath(); ctx.moveTo(cx, cy - 10); ctx.lineTo(cx - 7, cy + 8); ctx.lineTo(cx + 7, cy + 8); ctx.fill();
  text(ctx, `RANGE ${range / 1000} km`, cx, cy + R + 22, '#6fbf4a', '13px monospace', 'center');
  // right column: solution + tubes
  const x0 = 430;
  text(ctx, lock ? `LOCK ${lock.kind.toUpperCase()}` : 'NO LOCK', x0, 70, lock ? '#ff5a4f' : '#9a9', 'bold 18px monospace');
  text(ctx, lock ? `RNG ${Math.hypot(lock.x - s.x, lock.z - s.z).toFixed(0)} m` : 'AIM STICK SETS', x0, 94, '#ffb52e', '15px monospace');
  text(ctx, `CRS ${pad3(deg(s.heading + aimA))}°`, x0, 116, '#ffb52e', '15px monospace');
  sim.tubes.forEach((tb, i) => {
    const y = 140 + i * 62, sel = w.selected === tb.n;
    ctx.fillStyle = sel ? '#3a2a08' : '#141410'; ctx.fillRect(x0, y, 196, 54);
    ctx.strokeStyle = sel ? '#ffb52e' : '#4a4a30'; ctx.lineWidth = sel ? 3 : 1; ctx.strokeRect(x0 + 1, y + 1, 194, 52);
    text(ctx, `${tb.n}`, x0 + 10, y + 34, '#ffb52e', 'bold 22px monospace');
    // torpedo silhouette, filled when loaded
    ctx.fillStyle = tb.loaded ? '#7dff7d' : '#2a3a2a';
    ctx.beginPath(); ctx.ellipse(x0 + 90, y + 18, 50, 8, 0, 0, 7); ctx.fill(); ctx.fillRect(x0 + 136, y + 11, 8, 14);
    ctx.font = 'bold 12px monospace';
    ctx.fillStyle = tb.flooded ? '#58c2f0' : '#556'; ctx.fillText(tb.flooded ? 'FLOOD' : 'DRY', x0 + 40, y + 46);
    ctx.fillStyle = tb.outerOpen ? '#7dff7d' : '#556'; ctx.fillText(tb.outerOpen ? 'DOOR' : 'SHUT', x0 + 100, y + 46);
    if (tb.breechOpen) { ctx.fillStyle = '#ff5a4f'; ctx.fillText('BREECH', x0 + 146, y + 46); }
  });
  text(ctx, w.armed ? 'ARMED' : 'SAFE', x0, 405, w.armed ? (Math.sin(t * 6) > 0 ? '#ff5a4f' : '#a33') : '#777', 'bold 20px monospace');
  text(ctx, w.guardOpen ? 'GUARD UP' : '', x0 + 100, 405, '#ffb52e', 'bold 14px monospace');
  text(ctx, `SPARES ${sim.torpedoStock}   DECOYS ${s.countermeasures}`, x0, 436, '#ffb52e', '14px monospace');
}

// ------------------------------------------------------------------ chart table overlay: route, waypoints, cursor
export function drawRoute(ctx, s, sim, scale, cursor, round = false) {
  const P = (w) => [(w.x - s.x) * scale, (w.z - s.z) * scale];
  if (sim.route.length) {
    ctx.strokeStyle = round ? '#ffe0a0' : '#ff8f00'; ctx.lineWidth = 3; ctx.setLineDash([12, 6]);
    ctx.beginPath(); ctx.moveTo(0, 0); for (const w of sim.route) ctx.lineTo(...P(w)); ctx.stroke(); ctx.setLineDash([]);
    sim.route.forEach((w, i) => {
      const [x, y] = P(w);
      ctx.fillStyle = round ? '#ffe0a0' : '#ff8f00'; ctx.beginPath(); ctx.moveTo(x, y - 11); ctx.lineTo(x + 9, y); ctx.lineTo(x, y + 11); ctx.lineTo(x - 9, y); ctx.fill();
      ctx.fillStyle = round ? '#1a0e02' : '#ffffff'; ctx.font = 'bold 13px monospace'; ctx.textAlign = 'center'; ctx.fillText(`${i + 1}`, x, y + 5); ctx.textAlign = 'left';
    });
  }
  if (cursor) {
    const x = cursor.x * scale, y = cursor.z * scale;
    ctx.strokeStyle = '#d32f2f'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.arc(x, y, 14, 0, 7); ctx.moveTo(x - 24, y); ctx.lineTo(x - 6, y); ctx.moveTo(x + 6, y); ctx.lineTo(x + 24, y);
    ctx.moveTo(x, y - 24); ctx.lineTo(x, y - 6); ctx.moveTo(x, y + 6); ctx.lineTo(x, y + 24); ctx.stroke();
    const d = Math.hypot(cursor.x, cursor.z), b = Math.atan2(-cursor.z, cursor.x);
    ctx.fillStyle = '#7a1010'; ctx.font = 'bold 15px monospace'; ctx.fillText(`${pad3(deg(b))}° ${d.toFixed(0)}m`, x + 18, y - 16);
  }
}
