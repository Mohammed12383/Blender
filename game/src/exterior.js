// The world outside the hull: sky, ocean, ships, submarines, creatures, weapons and effects,
// plus the outside cameras (periscope, captain's bridge, external chase camera).
import * as THREE from 'three';
import { Water } from 'three/addons/objects/Water.js';
import { Sky } from 'three/addons/objects/Sky.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';
import { seabed, SNORKEL_DEPTH } from './sim.js';
import { Particles } from './particles.js';

const MODELS = '../submarine/models/';

// soft round sprite for all particle effects
export const DROP = (() => {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d'), grd = g.createRadialGradient(32, 32, 0, 32, 32, 32);
  grd.addColorStop(0, 'rgba(255,255,255,1)'); grd.addColorStop(0.4, 'rgba(255,255,255,0.6)'); grd.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = grd; g.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c); return t;
})();

export class Exterior {
  constructor(renderer, loader) {
    this.renderer = renderer;
    this.loader = loader;
    this.scene = new THREE.Scene();
    this.camera = new THREE.PerspectiveCamera(55, 1, 0.3, 6000);
    this.views = new Map();          // entity id -> Object3D
    this.fx = [];                    // short-lived effects {obj, t, life, update}
    this.templates = {};
    this.time = 0;
    this.orbit = { yaw: 2.4, pitch: 0.25, dist: 55 };
    this.look = { yaw: 0, pitch: 0 };
  }

  async load() {
    const s = this.scene;
    // sky + sun
    this.sky = new Sky();
    this.sky.scale.setScalar(10000);
    s.add(this.sky);
    const u = this.sky.material.uniforms;
    u.turbidity.value = 6; u.rayleigh.value = 1.6; u.mieCoefficient.value = 0.005; u.mieDirectionalG.value = 0.8;
    this.sun = new THREE.Vector3().setFromSphericalCoords(1, THREE.MathUtils.degToRad(90 - 24), THREE.MathUtils.degToRad(200));
    u.sunPosition.value.copy(this.sun);
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const envScene = new THREE.Scene();
    envScene.add(this.sky.clone());
    this.envMap = pmrem.fromScene(envScene).texture;
    s.environment = this.envMap;
    this.sunLight = new THREE.DirectionalLight(0xfff1dc, 2.6);
    this.sunLight.position.copy(this.sun).multiplyScalar(100);
    s.add(this.sunLight);
    this.hemi = new THREE.HemisphereLight(0xbfd9ff, 0x0b2a3a, 0.9);
    s.add(this.hemi);
    // ocean
    const normals = await new THREE.TextureLoader().loadAsync('assets/waternormals.png');
    normals.wrapS = normals.wrapT = THREE.RepeatWrapping;
    this.water = new Water(new THREE.PlaneGeometry(8000, 8000), {
      textureWidth: 512, textureHeight: 512, waterNormals: normals, sunDirection: this.sun.clone(),
      sunColor: 0xfff4e0, waterColor: 0x0d4a63, distortionScale: 3.2, fog: true,
    });
    this.water.rotation.x = -Math.PI / 2;
    s.add(this.water);
    this.underside = new THREE.Mesh(new THREE.PlaneGeometry(8000, 8000),
      new THREE.MeshBasicMaterial({ color: 0x6fb7c9, side: THREE.BackSide, transparent: true, opacity: 0.75, fog: true }));
    this.underside.rotation.x = -Math.PI / 2;
    this.underside.position.y = -0.05;
    s.add(this.underside);
    this.snow = this.makeSnow();
    s.add(this.snow);
    this.makeSeabed();
    this.makeFish();
    this.bubbles = this.trail();
    // models
    const names = ['SubmarineExterior', 'EnemyFrigate', 'CargoFreighter', 'EnemySubmarine', 'GiantSquid', 'Shark'];
    const gl = await Promise.all(names.map((n) => this.loader.loadAsync(`${MODELS}exterior/${n}.glb`)));
    names.forEach((n, i) => { this.templates[n] = gl[i].scene; });
    const torp = await this.loader.loadAsync(`${MODELS}props/Torpedo.glb`);
    this.templates.Torpedo = torp.scene;
    this.player = this.templates.SubmarineExterior.clone();
    s.add(this.player);
    this.playerProp = this.player.getObjectByName('SubmarineExterior_Propeller');
    // diesel exhaust and the snorkel mast that pokes above the waves when we run the engines submerged
    this.exhaust = new Particles(260, { kind: 'smoke', additive: false });
    this.scene.add(this.exhaust.points);
    this.snorkel = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.2, 1, 12), new THREE.MeshStandardMaterial({ color: 0x1d2a2c, roughness: 0.6, metalness: 0.4 }));
    this.snorkel.visible = false;
    this.scene.add(this.snorkel);
  }

  makeSeabed() {
    const size = 1600, seg = 128;
    const g = new THREE.PlaneGeometry(size, size, seg, seg);
    g.rotateX(-Math.PI / 2);
    const col = new Float32Array(g.attributes.position.count * 3);
    g.setAttribute('color', new THREE.BufferAttribute(col, 3));
    this.bed = new THREE.Mesh(g, new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.95 }));
    this.bed.userData.base = g.attributes.position.array.slice();
    this.scene.add(this.bed);
    // rocks and kelp scattered on the bed (repositioned around the boat)
    const rockGeo = new THREE.IcosahedronGeometry(1, 1);
    this.rocks = new THREE.InstancedMesh(rockGeo, new THREE.MeshStandardMaterial({ color: 0x4a4f4a, roughness: 1, flatShading: true }), 260);
    this.kelp = new THREE.InstancedMesh(new THREE.ConeGeometry(0.35, 9, 5, 4, true), new THREE.MeshStandardMaterial({ color: 0x3f6b2e, roughness: 0.8, side: THREE.DoubleSide }), 400);
    this.scene.add(this.rocks); this.scene.add(this.kelp);
    this.bedCenter = new THREE.Vector2(1e9, 1e9);
  }

  updateSeabed(cx, cz) {
    if (Math.hypot(cx - this.bedCenter.x, cz - this.bedCenter.y) < 200) return;
    this.bedCenter.set(Math.round(cx / 50) * 50, Math.round(cz / 50) * 50);
    const p = this.bed.geometry.attributes.position, c = this.bed.geometry.attributes.color, b = this.bed.userData.base;
    const sand = new THREE.Color(0xb8a77a), rock = new THREE.Color(0x585e5a), tmp = new THREE.Color();
    for (let i = 0; i < p.count; i++) {
      const x = b[i * 3] + this.bedCenter.x, z = b[i * 3 + 2] + this.bedCenter.y;
      const y = -seabed(x, z);
      p.array[i * 3] = x; p.array[i * 3 + 1] = y; p.array[i * 3 + 2] = z;
      const k = Math.min(1, Math.max(0, (215 + y + 60) / 120)) * 0.7 + Math.sin(x * 0.3) * Math.cos(z * 0.27) * 0.08;
      tmp.copy(sand).lerp(rock, Math.min(1, Math.max(0, k))); c.array.set([tmp.r, tmp.g, tmp.b], i * 3);
    }
    p.needsUpdate = true; c.needsUpdate = true;
    this.bed.geometry.computeVertexNormals();
    this.bed.geometry.computeBoundingSphere();
    const m = new THREE.Matrix4(), q = new THREE.Quaternion(), sc = new THREE.Vector3(), pos = new THREE.Vector3();
    let seed = Math.floor(this.bedCenter.x * 7 + this.bedCenter.y * 13);
    const rnd = () => { seed = (seed * 16807) % 2147483647; return (seed & 0xffff) / 0xffff; };
    for (let i = 0; i < this.rocks.count; i++) {
      const x = this.bedCenter.x + (rnd() - 0.5) * 1400, z = this.bedCenter.y + (rnd() - 0.5) * 1400;
      pos.set(x, -seabed(x, z), z); q.setFromEuler(new THREE.Euler(rnd() * 3, rnd() * 3, rnd() * 3)); sc.set(1 + rnd() * 6, 0.6 + rnd() * 3, 1 + rnd() * 5);
      this.rocks.setMatrixAt(i, m.compose(pos, q, sc));
    }
    for (let i = 0; i < this.kelp.count; i++) {
      const x = this.bedCenter.x + (rnd() - 0.5) * 900, z = this.bedCenter.y + (rnd() - 0.5) * 900;
      const h = 0.6 + rnd() * 1.8;
      pos.set(x, -seabed(x, z) + 4.5 * h, z); q.setFromEuler(new THREE.Euler((rnd() - 0.5) * 0.3, rnd() * 6, (rnd() - 0.5) * 0.3)); sc.set(1, h, 1);
      this.kelp.setMatrixAt(i, m.compose(pos, q, sc));
    }
    this.rocks.instanceMatrix.needsUpdate = true; this.kelp.instanceMatrix.needsUpdate = true;
  }

  makeFish() {
    const geo = new THREE.ConeGeometry(0.12, 0.6, 5); geo.rotateZ(-Math.PI / 2);
    this.fish = new THREE.InstancedMesh(geo, new THREE.MeshStandardMaterial({ color: 0xa9c4cf, metalness: 0.6, roughness: 0.3 }), 360);
    this.fish.frustumCulled = false;
    this.fishState = Array.from({ length: 360 }, (_, i) => ({ school: i % 6, phase: Math.random() * 6.28, r: 3 + Math.random() * 6, h: (Math.random() - 0.5) * 4, sp: 0.6 + Math.random() * 0.5 }));
    this.scene.add(this.fish);
  }

  updateFish(sim) {
    const s = sim.sub, m = new THREE.Matrix4(), q = new THREE.Quaternion(), one = new THREE.Vector3(1, 1, 1), p = new THREE.Vector3();
    for (let i = 0; i < this.fishState.length; i++) {
      const f = this.fishState[i];
      const cx = s.x + Math.cos(f.school * 1.7 + this.time * 0.03) * (40 + f.school * 25), cz = s.z + Math.sin(f.school * 2.3 + this.time * 0.03) * (40 + f.school * 25);
      const cy = -Math.min(seabed(cx, cz) - 10, 25 + f.school * 18);
      const a = f.phase + this.time * f.sp;
      p.set(cx + Math.cos(a) * f.r, cy + f.h + Math.sin(a * 2) * 0.6, cz - Math.sin(a) * f.r);
      q.setFromAxisAngle(new THREE.Vector3(0, 1, 0), a + Math.PI / 2 + Math.PI);
      this.fish.setMatrixAt(i, m.compose(p, q, one));
    }
    this.fish.instanceMatrix.needsUpdate = true;
  }

  makeSnow() {
    const n = 1500, g = new THREE.BufferGeometry(), p = new Float32Array(n * 3);
    for (let i = 0; i < n * 3; i++) p[i] = (Math.random() - 0.5) * 60;
    g.setAttribute('position', new THREE.BufferAttribute(p, 3));
    const pts = new THREE.Points(g, new THREE.PointsMaterial({ color: 0xcfe8f0, size: 0.12, map: DROP, transparent: true, opacity: 0.6, depthWrite: false }));
    pts.frustumCulled = false;
    return pts;
  }

  viewFor(e) {
    let v = this.views.get(e.id);
    if (v) return v;
    const map = { frigate: 'EnemyFrigate', freighter: 'CargoFreighter', enemySub: 'EnemySubmarine', squid: 'GiantSquid', shark: 'Shark' };
    const t = this.templates[map[e.kind]];
    v = (e.kind === 'squid' || e.kind === 'shark') ? SkeletonUtils.clone(t) : t.clone();
    v.userData.kind = e.kind;
    if (e.kind === 'squid') v.scale.setScalar(1.9);
    v.userData.bones = [];
    v.traverse((o) => { if (o.isBone) v.userData.bones.push(o); });
    v.userData.rest = v.userData.bones.map((b) => b.quaternion.clone());
    if (e.kind === 'frigate' || e.kind === 'freighter') {   // navigation lights (visible at night)
      const L = e.kind === 'frigate' ? 38 : 46;
      for (const [x, y, z, c] of [[L * 0.62, 7.5, -2.4, 0xff2a1a], [L * 0.62, 7.5, 2.4, 0x2aff5a], [L * 0.58, 15.5, 0, 0xffffff], [1, 5, 0, 0xffffff]]) {
        const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: DROP, color: c, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
        sp.position.set(x, y, z); sp.scale.setScalar(2.2); sp.userData.navLight = true; sp.visible = this.night || (this.elevation ?? 24) < 8; v.add(sp);
      }
    }
    if (e.kind === 'frigate') {
      v.userData.radar = v.getObjectByName('EnemyFrigate_Radar');
      v.userData.turret = v.getObjectByName('EnemyFrigate_Turret');
    }
    this.scene.add(v);
    this.views.set(e.id, v);
    return v;
  }

  // -------------------------------------------------------------- effects
  explosion(x, y, z, surface, big = 1) {
    const g = new THREE.SphereGeometry(1, 16, 12);
    const fire = new THREE.Mesh(g, new THREE.MeshBasicMaterial({ color: surface ? 0xffa040 : 0xcfeeff, transparent: true, opacity: 0.9 }));
    fire.position.set(x, y, z);
    this.scene.add(fire);
    this.fx.push({ obj: fire, t: 0, life: 1.6, update: (f, k) => { f.obj.scale.setScalar(2 + k * 18 * big); f.obj.material.opacity = 0.9 * (1 - k); } });
    // water column or bubble burst
    const n = 400, geo = new THREE.BufferGeometry(), pos = new Float32Array(n * 3), vel = [];
    for (let i = 0; i < n; i++) {
      pos.set([x, Math.max(y, surface ? 0 : y), z], i * 3);
      vel.push(new THREE.Vector3((Math.random() - 0.5) * 8, surface ? 12 + Math.random() * 22 : 2 + Math.random() * 6, (Math.random() - 0.5) * 8).multiplyScalar(big));
    }
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xffffff, size: surface ? 1.6 : 0.6, map: DROP, transparent: true, opacity: 0.9, depthWrite: false }));
    pts.frustumCulled = false;
    this.scene.add(pts);
    this.fx.push({ obj: pts, t: 0, life: 3.5, update: (f, k, dt) => {
      const a = f.obj.geometry.attributes.position;
      for (let i = 0; i < n; i++) {
        vel[i].y -= (surface ? 9.8 : -1.5) * dt;
        a.array[i * 3] += vel[i].x * dt; a.array[i * 3 + 1] += vel[i].y * dt; a.array[i * 3 + 2] += vel[i].z * dt;
      }
      a.needsUpdate = true; f.obj.material.opacity = 0.9 * (1 - k);
    } });
  }

  smoke(obj) {
    const n = 120, geo = new THREE.BufferGeometry(), pos = new Float32Array(n * 3), age = new Float32Array(n);
    for (let i = 0; i < n; i++) age[i] = Math.random() * 8;
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0x2a2a2a, size: 7, map: DROP, transparent: true, opacity: 0.5, depthWrite: false }));
    pts.frustumCulled = false;
    this.scene.add(pts);
    this.fx.push({ obj: pts, t: 0, life: 45, update: (f, k, dt) => {
      const a = f.obj.geometry.attributes.position;
      for (let i = 0; i < n; i++) {
        age[i] += dt;
        if (age[i] > 8) { age[i] = 0; a.array.set([obj.position.x + (Math.random() - 0.5) * 6, obj.position.y + 6, obj.position.z + (Math.random() - 0.5) * 6], i * 3); }
        a.array[i * 3 + 1] += dt * 4; a.array[i * 3] += dt * 1.5;
      }
      a.needsUpdate = true; f.obj.material.opacity = 0.5 * (1 - k);
    } });
  }

  // --------------------------------------------------------------- update
  sync(sim, dt) {
    this.time += dt;
    if (this._wave !== sim.score.wave) { this._wave = sim.score.wave; this.setTimeOfDay([24, 5, -6, 11][(sim.score.wave - 1) % 4], [200, 250, 200, 110][(sim.score.wave - 1) % 4]); }
    const s = sim.sub;
    // our sub
    this.player.position.set(s.x, -s.depth, s.z);
    this.player.rotation.set(0, s.heading, 0);
    this.player.rotateZ(s.pitch);
    this.player.rotateX(s.roll);
    if (this.playerProp) this.playerProp.rotation.x += s.speed * dt * 1.2;
    this.updateSeabed(s.x, s.z);
    this.updateFish(sim);
    if (s.depth > 3 && Math.abs(s.speed) > 0.5 && Math.random() < 0.8) {
      const back = new THREE.Vector3(-Math.cos(s.heading) * 18, -s.depth, Math.sin(s.heading) * 18).add(new THREE.Vector3(s.x, 0, s.z));
      this.bubbles.push(back);
    }
    // diesels: snorkel up and exhaust smoke
    const running = sim.engines ? sim.engines.filter((e) => e.running).length : 0;
    const fwd = new THREE.Vector3(Math.cos(s.heading), 0, -Math.sin(s.heading));
    const sailTop = -s.depth + 7.0;
    this.snorkel.visible = running > 0 && s.depth > 1.5 && s.depth <= SNORKEL_DEPTH + 1;
    if (this.snorkel.visible) {
      const top = 1.2, h = top - sailTop;
      this.snorkel.scale.set(1, Math.max(0.1, h), 1);
      this.snorkel.position.set(s.x + fwd.x * 2.6, sailTop + h / 2, s.z + fwd.z * 2.6);
    }
    if (running) {
      const y = s.depth > 1.5 ? 1.3 : sailTop + 0.4;
      const p = [s.x + fwd.x * 2.6, y, s.z + fwd.z * 2.6];
      if (Math.random() < dt * 14 * running) this.exhaust.emit(p, [(Math.random() - 0.5) * 0.6 - fwd.x * 0.8, 1.2 + Math.random() * 0.8, (Math.random() - 0.5) * 0.6 - fwd.z * 0.8], 5 + Math.random() * 2, 1.2, 7);
    }
    this.exhaust.setScale(this.renderer.domElement.height);
    this.exhaust.update(dt, (i, t) => [0.2, 0.2, 0.21, Math.min(1, t * 6) * (1 - t) * 0.45]);
    // entities
    const alive = new Set();
    for (const e of sim.entities) {
      if (!e.alive) continue;
      alive.add(e.id);
      const v = this.viewFor(e);
      v.position.set(e.x, -(e.depth || 0), e.z);
      v.rotation.set(0, e.heading, 0);
      if (e.sinking) {
        v.rotation.z = Math.min(0.6, e.sinking * 0.02) * (e.id % 2 ? 1 : -1);
        v.rotation.x = Math.min(0.3, e.sinking * 0.01);
        if (!v.userData.smoking && e.kind !== 'enemySub') { v.userData.smoking = true; this.smoke(v); }
      } else if (!e.depth) {
        v.position.y = Math.sin(this.time * 0.8 + e.id) * 0.25;   // bob on the swell
        v.rotation.z = Math.sin(this.time * 0.6 + e.id) * 0.02;
      }
      if (v.userData.radar) v.userData.radar.rotation.y += dt * 1.5;
      if (v.userData.turret && e.state === 'hunt') v.userData.turret.rotation.y = Math.atan2(-(s.z - e.z), s.x - e.x) - e.heading;
      this.animateCreature(e, v);
    }
    for (const [id, v] of this.views) if (!alive.has(id)) { this.scene.remove(v); this.views.delete(id); }
    // torpedoes
    this.torps = this.torps || new Map();
    const live = new Set();
    for (const tp of sim.torpedoes) {
      live.add(tp.id);
      let v = this.torps.get(tp.id);
      if (!v) { v = this.templates.Torpedo.clone(); v.scale.setScalar(1.6); this.scene.add(v); this.torps.set(tp.id, v); v.userData.trail = this.trail(); }
      v.position.set(tp.x, -tp.depth, tp.z);
      v.rotation.set(0, tp.heading, 0);
      v.userData.trail.push(v.position);
    }
    for (const [id, v] of this.torps) if (!live.has(id)) { this.scene.remove(v); this.torps.delete(id); }
    for (const c of sim.charges) {
      if (!c.view) { c.view = new THREE.Mesh(new THREE.CylinderGeometry(0.4, 0.4, 0.9, 12), new THREE.MeshStandardMaterial({ color: 0x333333 })); this.scene.add(c.view); }
      c.view.position.set(c.x, -c.depth, c.z);
      c.view.rotation.x += dt * 2;
    }
    if (this._charges) for (const c of this._charges) if (!sim.charges.includes(c) && c.view) this.scene.remove(c.view);
    this._charges = sim.charges.slice();
    // effects
    for (const f of this.fx) { f.t += dt; f.update(f, Math.min(1, f.t / f.life), dt); if (f.t >= f.life) this.scene.remove(f.obj); }
    this.fx = this.fx.filter((f) => f.t < f.life);
    this.water.material.uniforms.time.value += dt * 0.6;
  }

  trail() {
    const n = 160, geo = new THREE.BufferGeometry(), pos = new Float32Array(n * 3);
    geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    const pts = new THREE.Points(geo, new THREE.PointsMaterial({ color: 0xe8fbff, size: 0.6, map: DROP, transparent: true, opacity: 0.7, depthWrite: false }));
    pts.frustumCulled = false;
    this.scene.add(pts);
    let i = 0;
    const f = { obj: pts, t: 0, life: 120, update: () => {} };
    this.fx.push(f);
    return { push: (p) => { pos.set([p.x + (Math.random() - 0.5) * 0.6, p.y + 0.3 + Math.random() * 0.5, p.z + (Math.random() - 0.5) * 0.6], (i++ % n) * 3); geo.attributes.position.needsUpdate = true; } };
  }

  animateCreature(e, v) {
    const bones = v.userData.bones;
    if (!bones.length) return;
    const t = this.time * (e.attached ? 3 : 1.6);
    const q = new THREE.Quaternion(), ax = new THREE.Vector3();
    bones.forEach((b, i) => {
      b.quaternion.copy(v.userData.rest[i]);
      const n = b.name;
      const k = parseInt(n.match(/(\d+)$/)?.[1] || '1', 10);
      if (e.kind === 'shark') {
        q.setFromAxisAngle(ax.set(0, 0, 1), Math.sin(t * 2.2 - k * 0.7) * 0.06 * k);
      } else if (/^Arm|^Tentacle/.test(n)) {
        const arm = parseInt(n.match(/^\D+(\d)/)?.[1] || '1', 10);
        const amp = e.attached ? 0.35 : 0.18;
        q.setFromAxisAngle(ax.set(Math.sin(arm), 0, Math.cos(arm)).normalize(), Math.sin(t - k * 0.6 + arm) * amp);
      } else q.identity();
      b.quaternion.multiply(q);
    });
  }

  // ---------------------------------------------------------- time of day
  setTimeOfDay(elevation, azimuth = 200) {
    this.elevation = elevation;
    const night = elevation < 0;
    this.sun.setFromSphericalCoords(1, THREE.MathUtils.degToRad(90 - Math.max(elevation, -2)), THREE.MathUtils.degToRad(azimuth));
    const u = this.sky.material.uniforms;
    u.sunPosition.value.copy(this.sun);
    u.rayleigh.value = night ? 0.4 : elevation < 8 ? 2.6 : 1.6;
    u.turbidity.value = elevation < 8 ? 9 : 6;
    this.sunLight.position.copy(this.sun).multiplyScalar(100);
    if (night) { this.sunLight.position.set(-40, 60, -30); }
    this.sunLight.color.set(night ? 0x8fa8ff : elevation < 8 ? 0xffb070 : 0xfff1dc);
    this.dayLight = night ? 0.35 : elevation < 8 ? 1.8 : 2.6;
    this.hemi.intensity = night ? 0.18 : elevation < 8 ? 0.6 : 0.9;
    this.water.material.uniforms.sunDirection.value.copy(this.sun);
    this.water.material.uniforms.sunColor.value.set(night ? 0x334466 : elevation < 8 ? 0xffa060 : 0xfff4e0);
    this.fogColor = night ? 0x0a1220 : elevation < 8 ? 0xd9a07a : 0xb8d3e0;
    const pmrem = new THREE.PMREMGenerator(this.renderer);
    const envScene = new THREE.Scene();
    envScene.add(this.sky.clone());
    if (night) envScene.background = new THREE.Color(0x05080f);
    this.scene.environment = pmrem.fromScene(envScene).texture;
    for (const v of this.views.values()) v.traverse((o) => { if (o.userData.navLight) o.visible = night || elevation < 8; });
    this.night = night;
  }

  // -------------------------------------------------------------- cameras
  setUnderwater(depth) {
    const s = this.scene;
    const under = this.camera.position.y < 0;
    this.water.visible = !under;
    this.underside.visible = under;
    this.snow.visible = under;
    if (under) {
      const d = Math.min(1, -this.camera.position.y / 220);
      const col = new THREE.Color(0x1d6f86).lerp(new THREE.Color(0x020b12), d);
      s.fog = new THREE.FogExp2(col, 0.012 + d * 0.01);
      s.background = col;
      this.sky.visible = false;
      this.snow.position.copy(this.camera.position);
      this.sunLight.intensity = (this.dayLight ?? 2.6) * 0.6 * (1 - d * 0.9);
    } else {
      s.fog = new THREE.FogExp2(this.fogColor ?? 0xb8d3e0, this.night ? 0.0012 : 0.00045);
      s.background = null;
      this.sky.visible = true;
      this.sunLight.intensity = this.dayLight ?? 2.6;
    }
    this.water.position.x = this.camera.position.x;
    this.water.position.z = this.camera.position.z;
    this.underside.position.x = this.camera.position.x;
    this.underside.position.z = this.camera.position.z;
  }

  periscopeCamera(sim, aspect) {
    const s = sim.sub;
    const c = this.camera;
    c.fov = 48 / s.periscopeZoom;
    c.aspect = aspect;
    c.updateProjectionMatrix();
    const fwd = new THREE.Vector3(Math.cos(s.heading), 0, -Math.sin(s.heading));
    c.position.set(s.x + fwd.x * 2.8, -s.depth + 10.5 + Math.sin(this.time * 1.3) * 0.25, s.z + fwd.z * 2.8);
    c.rotation.set(0, 0, 0, 'YXZ');
    c.rotation.y = s.heading + s.periscopeBearing - Math.PI / 2;
    c.rotation.x = s.periscopePitch;
    this.setUnderwater();
  }

  bridgeCamera(sim, aspect) {
    const s = sim.sub, c = this.camera;
    c.fov = this.look.zoom ? 22 : 62; c.aspect = aspect; c.updateProjectionMatrix();
    const fwd = new THREE.Vector3(Math.cos(s.heading), 0, -Math.sin(s.heading));
    c.position.set(s.x + fwd.x * 4.4, -s.depth + 9.2 + Math.sin(this.time) * 0.15, s.z + fwd.z * 4.4);
    c.rotation.set(this.look.pitch, s.heading - Math.PI / 2 + this.look.yaw, 0, 'YXZ');
    this.setUnderwater();
  }

  chaseCamera(sim, aspect) {
    const s = sim.sub, c = this.camera, o = this.orbit;
    c.fov = 55; c.aspect = aspect; c.updateProjectionMatrix();
    const center = new THREE.Vector3(s.x, -s.depth + 2, s.z);
    const yaw = s.heading + o.yaw;
    c.position.set(center.x + Math.cos(yaw) * Math.cos(o.pitch) * o.dist, center.y + Math.sin(o.pitch) * o.dist, center.z - Math.sin(yaw) * Math.cos(o.pitch) * o.dist);
    c.lookAt(center);
    this.setUnderwater();
  }

  monitorCamera(sim, cam, aft) {
    const s = sim.sub;
    const fwd = new THREE.Vector3(Math.cos(s.heading), 0, -Math.sin(s.heading));
    const sign = aft ? -1 : 1;
    cam.position.set(s.x + fwd.x * 26 * sign, -s.depth + 1.5, s.z + fwd.z * 26 * sign);
    cam.lookAt(s.x + fwd.x * 200 * sign, -s.depth + 1.5, s.z + fwd.z * 200 * sign);
  }

  render(target = null, cam = this.camera) {
    this.renderer.setRenderTarget(target);
    this.renderer.render(this.scene, cam);
    this.renderer.setRenderTarget(null);
  }
}
