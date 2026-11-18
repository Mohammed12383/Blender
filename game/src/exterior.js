// The world outside the hull: sky, ocean, ships, submarines, creatures, weapons and effects,
// plus the outside cameras (periscope, captain's bridge, external chase camera).
import * as THREE from 'three';
import { Water } from 'three/addons/objects/Water.js';
import { Sky } from 'three/addons/objects/Sky.js';
import * as SkeletonUtils from 'three/addons/utils/SkeletonUtils.js';

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
    // models
    const names = ['SubmarineExterior', 'EnemyFrigate', 'CargoFreighter', 'EnemySubmarine', 'GiantSquid', 'Shark'];
    const gl = await Promise.all(names.map((n) => this.loader.loadAsync(`${MODELS}exterior/${n}.glb`)));
    names.forEach((n, i) => { this.templates[n] = gl[i].scene; });
    const torp = await this.loader.loadAsync(`${MODELS}props/Torpedo.glb`);
    this.templates.Torpedo = torp.scene;
    this.player = this.templates.SubmarineExterior.clone();
    s.add(this.player);
    this.playerProp = this.player.getObjectByName('SubmarineExterior_Propeller');
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
    const s = sim.sub;
    // our sub
    this.player.position.set(s.x, -s.depth, s.z);
    this.player.rotation.set(0, s.heading, 0);
    this.player.rotateZ(s.pitch);
    this.player.rotateX(s.roll);
    if (this.playerProp) this.playerProp.rotation.x += s.speed * dt * 1.2;
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
      this.sunLight.intensity = 1.6 * (1 - d * 0.9);
    } else {
      s.fog = new THREE.FogExp2(0xb8d3e0, 0.00045);
      s.background = null;
      this.sky.visible = true;
      this.sunLight.intensity = 2.6;
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
    cam.position.set(s.x + fwd.x * 18 * sign, -s.depth + 1.5, s.z + fwd.z * 18 * sign);
    cam.lookAt(s.x + fwd.x * 200 * sign, -s.depth + 1.5, s.z + fwd.z * 200 * sign);
  }

  render(target = null, cam = this.camera) {
    this.renderer.setRenderTarget(target);
    this.renderer.render(this.scene, cam);
    this.renderer.setRenderTarget(null);
  }
}
