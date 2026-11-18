// Inside the boat: loads the interior model, finds stations / doors / hand targets / cameras from the
// glTF extras, builds walking colliders, live screens, leaks with spray, flood water and alarms.
import * as THREE from 'three';
import { ROOMS } from './sim.js';
import { DROP } from './exterior.js';

const MODELS = '../submarine/models/';
const BULKHEADS = [7.0, 16.3, 22.6];        // x of the doors between rooms (three.js X = Blender X)

export class Interior {
  constructor(renderer, loader) {
    this.renderer = renderer;
    this.loader = loader;
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0b0f12);
    this.colliders = [];          // {minX,maxX,minZ,maxZ}
    this.stations = {};           // key -> {root, cam, hands:[], anchor}
    this.interactables = [];      // {pos, radius, label, kind, data}
    this.leakViews = new Map();
    this.screens = {};
    this.time = 0;
  }

  async load() {
    const gltf = await this.loader.loadAsync(`${MODELS}Submarine_Interior.glb`);
    this.root = gltf.scene;
    this.scene.add(this.root);
    this.scene.add(new THREE.HemisphereLight(0xfff1dd, 0x34302a, 0.55));
    this.alarm = new THREE.PointLight(0xff2010, 0, 30, 1.2);
    this.alarm.position.set(12, 2.6, 0);
    this.scene.add(this.alarm);
    this.root.traverse((o) => {
      if (o.isLight) { o.intensity *= 0.0035; o.castShadow = false; o.distance = o.distance || 9; }
      if (o.isMesh) { o.frustumCulled = true; }
    });
    this.root.updateMatrixWorld(true);
    this.indexScene();
    this.setupScreens();
    this.makeWater();
    const [wrench, crack, patch, torpedo] = await Promise.all(['Wrench', 'HullCrack', 'HullPatch', 'Torpedo']
      .map((n) => this.loader.loadAsync(`${MODELS}props/${n}.glb`)));
    this.tpl = { wrench: wrench.scene, crack: crack.scene, patch: patch.scene, torpedo: torpedo.scene };
    // wrenches to pick up: torpedo room workbench, control room, galley counter
    this.wrenches = [];
    for (const p of [[6.0, 0.93, 2.15], [9.9, 0.02, -1.6], [23.95, 0.93, 2.05]]) {
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
    for (const r of tops) {
      const ud = r.userData || {};
      const name = r.name;
      if (/_Shell|^Bulkhead|CableLooms/.test(name)) continue;
      box.setFromObject(r);
      if (box.isEmpty()) continue;
      const low = box.min.y < 1.3 && box.max.y > 0.25;
      const thin = (box.max.x - box.min.x) < 0.05 || (box.max.z - box.min.z) < 0.05;
      const passable = /Door|Hatch|Lamp|Stool|Torpedo$|Torpedo\.|Poster|Sign|Clock|Extinguisher|Intercom|Monitor|Box|Speaker|Board|Mug|Plate|Steak|Drum|Patty|Tray|Checkers|Toolbox|Junction|Ladder|LoadingCradle|ChainHoist/.test(name);
      if (low && !thin && !passable) this.colliders.push({ minX: box.min.x, maxX: box.max.x, minZ: box.min.z, maxZ: box.max.z, name });
      if (ud.station) (byStation[ud.station] ||= []).push(r);
    }
    const find = (root, test) => { let f = null; root.traverse((o) => { if (!f && test(o)) f = o; }); return f; };
    const all = (root, test) => { const out = []; root.traverse((o) => { if (test(o)) out.push(o); }); return out; };
    const stationDefs = [
      ['helm', 'navigation', /^NavConsole/, 'Use HELM (throttle & rudder)'],
      ['chart', 'navigation', /^NavTable/, 'Use CHART TABLE'],
      ['weapons', 'weapons', /^FireControl/, 'Use FIRE CONTROL'],
      ['periscope', 'periscope', /^Periscope/, 'Use PERISCOPE'],
      ['sonar', 'sonar', /^SonarStation/, 'Use SONAR'],
      ['ballast', 'ballast', /^BallastPanel/, 'Use BALLAST & DIVE PLANES'],
      ['griddle', 'cooking', /^Griddle/, 'Use GRIDDLE'],
    ];
    for (const [key, st, re, label] of stationDefs) {
      const root = (byStation[st] || []).find((r) => re.test(r.name));
      if (!root) continue;
      const cam = find(root, (o) => o.isCamera && !/back/.test(o.name));
      const hands = all(root, (o) => o.userData && o.userData.interaction === 'hand_target');
      const parts = {};
      root.traverse((o) => { if (o.userData && o.userData.interact) parts[o.name.replace(root.name.split('.')[0] + '_', '')] = o; });
      this.stations[key] = { key, root, cam, hands, parts };
      const p = new THREE.Vector3(); (cam || root).getWorldPosition(p);
      const c = new THREE.Box3().setFromObject(root).getCenter(new THREE.Vector3());
      this.interactables.push({ pos: new THREE.Vector3(c.x, Math.min(1.3, c.y + 0.2), c.z), radius: 1.3, label, kind: 'station', data: key });
    }
    // torpedo tubes (breech doors) and racks
    const tubes = this.root.children.find((r) => /^TorpedoTubes/.test(r.name));
    this.tubes = [];
    if (tubes) {
      for (let n = 1; n <= 4; n++) {
        const door = tubes.getObjectByName(`TorpedoTubes_Door${n}`);
        const wheel = tubes.getObjectByName(`TorpedoTubes_Door${n}Wheel`);
        const p = new THREE.Vector3(); (wheel || door).getWorldPosition(p);
        const hands = all(tubes, (o) => o.userData && o.userData.control === `Door${n}Wheel`);
        const cam = find(tubes, (o) => o.isCamera && o.name.includes(`tube${n}`));
        this.tubes.push({ n, door, wheel, rest: door ? door.quaternion.clone() : null, open: 0 });
        this.stations[`tube${n}`] = { key: `tube${n}`, root: tubes, cam, hands, parts: { wheel } };
        this.interactables.push({ pos: p, radius: 0.9, label: `TUBE ${n}`, kind: 'tube', data: n });
      }
    }
    for (const r of this.root.children.filter((o) => /^TorpedoRack/.test(o.name))) {
      const c = new THREE.Box3().setFromObject(r).getCenter(new THREE.Vector3());
      this.interactables.push({ pos: c.setY(0.9), radius: 1.4, label: 'Take TORPEDO from rack', kind: 'rack', data: r });
    }
    this.rackTorpedoes = this.root.children.filter((o) => /^Torpedo(\.\d+)?$/.test(o.name) && o.position.x > 3);
    // watertight doors
    this.doors = this.root.children.filter((r) => /^WatertightDoor/.test(r.name)).sort((a, b) => a.position.x - b.position.x).map((r, i) => {
      const leaf = r.getObjectByName(r.name.replace(/(\.\d+)?$/, '') === 'WatertightDoor' ? 'WatertightDoor_Leaf' : '') || find(r, (o) => /Leaf/.test(o.name));
      this.interactables.push({ pos: r.position.clone().setY(1.0), radius: 1.0, label: 'Open/close WATERTIGHT DOOR', kind: 'door', data: i });
      return { root: r, leaf, rest: leaf ? leaf.quaternion.clone() : null, open: 1 };
    });
    // misc
    const add = (re, label, kind, y = 1.1, radius = 1.2) => {
      for (const r of this.root.children.filter((o) => re.test(o.name))) {
        const c = new THREE.Box3().setFromObject(r).getCenter(new THREE.Vector3());
        this.interactables.push({ pos: c.setY(y), radius, label, kind, data: r });
      }
    };
    add(/^Ladder/, 'Climb to the BRIDGE (when surfaced)', 'ladder', 1.4);
    add(/^ElectricalCabinet/, 'HULL SHOCK (repel creatures)', 'shock', 1.2, 1.0);
    add(/^Fridge|^WireShelf/, 'Take RAW FOOD', 'food', 1.1, 1.0);
    add(/^CoffeeStation/, 'Drink COFFEE (stamina)', 'coffee', 1.0, 1.0);
    add(/^WallMonitor/, 'EXTERNAL CAMERA view', 'chase', 1.8, 1.0);
    add(/^MessTable/, 'EAT cooked food', 'eat', 0.8, 1.4);
    add(/^BunkBed/, 'Rest (restore stamina)', 'rest', 0.6, 1.2);
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
    for (const n of ['screen_chart', 'screen_nav_scope', 'screen_sonar', 'screen_fire_control', 'screen_ballast', 'screen_target_id']) {
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
    // chart / nav scope: top-down tactical map centred on us
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
      for (const tp of sim.torpedoes) { ctx.fillStyle = tp.owner === 'player' ? '#1565c0' : '#ff1744'; ctx.fillRect((tp.x - s.x) * scale - 2, (tp.z - s.z) * scale - 2, 4, 4); }
      ctx.rotate(-s.heading); ctx.fillStyle = round ? '#ffe0a0' : '#0d47a1';
      ctx.beginPath(); ctx.moveTo(14, 0); ctx.lineTo(-10, -7); ctx.lineTo(-10, 7); ctx.fill();
      ctx.restore();
      ctx.fillStyle = round ? '#ffae2e' : '#102030'; ctx.font = 'bold 22px monospace';
      ctx.fillText(`HDG ${deg(s.heading)}°  SPD ${s.speed.toFixed(1)}  DEPTH ${s.depth.toFixed(0)}m`, 16, H - 18);
      sc.tex.needsUpdate = true;
    }
    // sonar PPI
    const so = this.screens.screen_sonar;
    if (so) {
      const { ctx } = so, R = 230;
      ctx.fillStyle = 'rgba(0,12,4,0.25)'; ctx.fillRect(0, 0, 512, 512);
      ctx.save(); ctx.translate(256, 256);
      ctx.strokeStyle = '#1f8f4a'; for (const r of [R / 3, 2 * R / 3, R]) { ctx.beginPath(); ctx.arc(0, 0, r, 0, 7); ctx.stroke(); }
      const sweep = (sim.time * 1.6) % (Math.PI * 2);
      ctx.strokeStyle = '#53ff8a'; ctx.beginPath(); ctx.moveTo(0, 0); ctx.lineTo(Math.cos(sweep) * R, Math.sin(sweep) * R); ctx.stroke();
      for (const [id, c] of sim.contacts) {
        const e = sim.entities.find((q) => q.id === id); if (!e || !e.alive) continue;
        const rel = Math.atan2(-(e.z - s.z), e.x - s.x) - s.heading;
        const rng = Math.min(1, Math.hypot(e.x - s.x, e.z - s.z) / 1500) * R;
        const x = Math.sin(rel) * -rng, y = -Math.cos(rel) * rng;
        ctx.fillStyle = e.id === sim.weapons.lock ? '#ffffff' : '#7dffb0'; ctx.beginPath(); ctx.arc(x, y, 5, 0, 7); ctx.fill();
      }
      ctx.restore();
      so.tex.needsUpdate = true;
    }
    // fire control
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
        `HULL   ${s.hull.toFixed(0)} %`, `WATER  ${sim.water.map((w) => w.toFixed(1)).join(' ')}`].forEach((l, i) => ctx.fillText(l, 20, 96 + i * 44));
      bl.tex.needsUpdate = true;
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
    this.waterMeshes = ROOMS.map((r) => {
      const m = new THREE.Mesh(new THREE.BoxGeometry(r.x1 - r.x0, 1, 4.96),
        new THREE.MeshStandardMaterial({ color: 0x1f6f86, transparent: true, opacity: 0.55, roughness: 0.05, metalness: 0.1 }));
      m.position.set((r.x0 + r.x1) / 2, -1, 0); m.visible = false;
      this.scene.add(m);
      return m;
    });
  }

  spawnLeak(l) {
    const g = new THREE.Group();
    const crack = this.tpl.crack.clone();
    crack.rotation.y = l.side > 0 ? 0 : Math.PI;    // the model faces +Z (into the room) for a port-side leak
    g.add(crack);
    g.position.set(l.x, l.y, -l.side * 2.03);
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

  fixLeakView(l) {
    const v = this.leakViews.get(l.id); if (!v) return;
    this.scene.remove(v.spray); v.g.clear();
    const patch = this.tpl.patch.clone(); patch.rotation.y = l.side > 0 ? 0 : Math.PI;
    v.g.add(patch);
    this.leakViews.delete(l.id);
    this.interactables = this.interactables.filter((i) => !(i.kind === 'leak' && i.data === l.id));
  }

  update(sim, dt) {
    this.time += dt;
    // leaks: high pressure spray, stronger with depth
    for (const v of this.leakViews.values()) {
      const p = v.spray.geometry.attributes.position, o = v.g.position, inward = -Math.sign(o.z);
      const speed = 3 + sim.sub.depth / 25;
      for (let i = 0; i < v.age.length; i++) {
        v.age[i] += dt * (1.2 + Math.random());
        if (v.age[i] > 1) {
          v.age[i] = 0;
          p.array.set([o.x, o.y, o.z], i * 3);
          v.vel[i].set((Math.random() - 0.5) * 1.2, (Math.random() - 0.3) * 1.5, inward * speed * (0.7 + Math.random() * 0.6));
        }
        v.vel[i].y -= 9.8 * dt;
        p.array[i * 3] += v.vel[i].x * dt; p.array[i * 3 + 1] = Math.max(sim.water[v.leak.room], p.array[i * 3 + 1] + v.vel[i].y * dt); p.array[i * 3 + 2] += v.vel[i].z * dt;
      }
      p.needsUpdate = true;
    }
    // flood water
    sim.water.forEach((w, i) => {
      const m = this.waterMeshes[i];
      m.visible = w > 0.01;
      m.scale.y = Math.max(0.01, w);
      m.position.y = w / 2 + Math.sin(this.time * 1.7 + i) * 0.01;
    });
    // doors
    sim.doors.forEach((open, i) => {
      const d = this.doors[i]; if (!d || !d.leaf) return;
      d.open += ((open ? 1 : 0) - d.open) * Math.min(1, dt * 3);
      d.leaf.quaternion.copy(d.rest).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -1.75 * d.open));
    });
    // tube breech doors
    sim.tubes.forEach((t, i) => {
      const v = this.tubes[i]; if (!v || !v.door) return;
      v.open += ((t.breechOpen ? 1 : 0) - v.open) * Math.min(1, dt * 3);
      v.door.quaternion.copy(v.rest).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), -1.8 * v.open));
    });
    // rack torpedoes reflect the spare count
    this.rackTorpedoes.forEach((t, i) => { t.visible = i < sim.torpedoStock; });
    // alarm when damaged / under attack
    const danger = sim.leaks.some((l) => !l.fixed) || sim.sub.hull < 40 || sim.torpedoes.some((t) => t.owner !== 'player') || sim.sub.lost;
    this.alarm.intensity = danger ? (Math.sin(this.time * 6) > 0 ? 40 : 4) : 0;
  }

  collide(pos, radius, sim) {
    // hull sides
    pos.z = Math.max(-2.2 + radius, Math.min(2.2 - radius, pos.z));
    pos.x = Math.max(0.2 + radius, Math.min(27.3 - radius, pos.x));
    // bulkheads: pass only through an open doorway
    BULKHEADS.forEach((bx, i) => {
      const inDoor = Math.abs(pos.z) < 0.42 && sim.doors[i];
      if (!inDoor && pos.x > bx - radius && pos.x < bx + 0.3 + radius) pos.x = pos.x < bx + 0.15 ? bx - radius : bx + 0.3 + radius;
    });
    for (const c of this.colliders) {
      const nx = Math.max(c.minX, Math.min(pos.x, c.maxX)), nz = Math.max(c.minZ, Math.min(pos.z, c.maxZ));
      const dx = pos.x - nx, dz = pos.z - nz, d = Math.hypot(dx, dz);
      if (d < radius) {
        if (d > 1e-5) { pos.x = nx + dx / d * radius; pos.z = nz + dz / d * radius; }
        else pos.x = pos.x < (c.minX + c.maxX) / 2 ? c.minX - radius : c.maxX + radius;
      }
    }
    return pos;
  }

  roomAt(x) { return ROOMS.findIndex((r) => x >= r.x0 - 0.2 && x <= r.x1 + 0.2); }
}
