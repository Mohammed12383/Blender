// GPU point sprites with per-particle size, colour and alpha: flames, embers, smoke, bubbles, splashes.
import * as THREE from 'three';

function softTexture(kind) {
  const c = document.createElement('canvas'); c.width = c.height = 64;
  const g = c.getContext('2d');
  if (kind === 'smoke') {
    // lumpy puff
    for (let i = 0; i < 9; i++) {
      const x = 22 + Math.random() * 20, y = 22 + Math.random() * 20, r = 14 + Math.random() * 12;
      const gr = g.createRadialGradient(x, y, 0, x, y, r);
      gr.addColorStop(0, 'rgba(255,255,255,0.45)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
      g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
    }
  } else {
    const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    if (kind === 'flame') { gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.35, 'rgba(255,255,255,0.55)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); }
    else { gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.5, 'rgba(255,255,255,0.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); }
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}
const TEX = {};
const tex = (k) => (TEX[k] ||= softTexture(k));

const VERT = `
attribute float size; attribute float alpha; attribute vec3 tint;
varying float vAlpha; varying vec3 vTint; varying float vNear;
uniform float scale;
#include <fog_pars_vertex>
void main() {
  vAlpha = alpha; vTint = tint;
  vec4 mvPosition = modelViewMatrix * vec4(position, 1.0);
  gl_PointSize = size * scale / max(0.05, -mvPosition.z);
  vNear = clamp((-mvPosition.z - 0.1) / 0.5, 0.0, 1.0);   // fade out sprites right in front of the lens
  gl_Position = projectionMatrix * mvPosition;
  #include <fog_vertex>
}`;
const FRAG = `
uniform sampler2D map; uniform float premul; uniform float cover; varying float vAlpha; varying vec3 vTint; varying float vNear;
#include <fog_pars_fragment>
void main() {
  vec4 t = texture2D(map, gl_PointCoord);
  float a = t.a * vAlpha * vNear;
  if (a < 0.003) discard;
  gl_FragColor = vec4(vTint, a);
  #include <fog_fragment>
  // premultiplied: add the glow, and hide part of what is behind (keeps flames orange on bright walls)
  if (premul > 0.5) gl_FragColor = vec4(gl_FragColor.rgb * a, a * cover);
}`;

export class Particles {
  constructor(n, { kind = 'flame', additive = true, fog = true, premul = false, cover = 0.55 } = {}) {
    this.n = n;
    this.pos = new Float32Array(n * 3); this.vel = new Float32Array(n * 3);
    this.age = new Float32Array(n).fill(1); this.life = new Float32Array(n).fill(1);
    this.s0 = new Float32Array(n); this.s1 = new Float32Array(n);
    this.kind = new Uint8Array(n);       // free per-particle tag for the colour function
    this.size = new Float32Array(n); this.alpha = new Float32Array(n); this.tint = new Float32Array(n * 3);
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(this.pos, 3));
    g.setAttribute('size', new THREE.BufferAttribute(this.size, 1));
    g.setAttribute('alpha', new THREE.BufferAttribute(this.alpha, 1));
    g.setAttribute('tint', new THREE.BufferAttribute(this.tint, 3));
    this.mat = new THREE.ShaderMaterial({
      uniforms: { map: { value: tex(kind) }, scale: { value: 420 }, premul: { value: premul ? 1 : 0 }, cover: { value: cover },
        ...THREE.UniformsUtils.clone(THREE.UniformsLib.fog) },
      vertexShader: VERT, fragmentShader: FRAG, transparent: true, depthWrite: false, fog,
      blending: premul ? THREE.CustomBlending : additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    });
    if (premul) {
      this.mat.blendEquation = THREE.AddEquation;
      this.mat.blendSrc = THREE.OneFactor; this.mat.blendDst = THREE.OneMinusSrcAlphaFactor;
      this.mat.blendSrcAlpha = THREE.OneFactor; this.mat.blendDstAlpha = THREE.OneMinusSrcAlphaFactor;
    }
    this.points = new THREE.Points(g, this.mat);
    this.points.frustumCulled = false;
    this.points.renderOrder = additive ? 4 : 3;
    this.next = 0;
  }
  emit(p, v, life, s0, s1) {
    const i = this.next; this.next = (this.next + 1) % this.n;
    this.pos.set(p, i * 3); this.vel.set(v, i * 3);
    this.age[i] = 0; this.life[i] = life; this.s0[i] = s0; this.s1[i] = s1;
    return i;
  }
  // colour(i, t) -> [r, g, b, a] for normalised age t; force(i, dt) may change this.vel / this.pos
  update(dt, colour, force) {
    const { pos, vel, age, life, size, alpha, tint } = this;
    for (let i = 0; i < this.n; i++) {
      if (age[i] >= 1) { alpha[i] = 0; size[i] = 0; continue; }
      age[i] += dt / life[i];
      if (force) force(i, dt);
      pos[i * 3] += vel[i * 3] * dt; pos[i * 3 + 1] += vel[i * 3 + 1] * dt; pos[i * 3 + 2] += vel[i * 3 + 2] * dt;
      const t = Math.min(1, age[i]);
      size[i] = this.s0[i] + (this.s1[i] - this.s0[i]) * t;
      const c = colour(i, t);
      tint[i * 3] = c[0]; tint[i * 3 + 1] = c[1]; tint[i * 3 + 2] = c[2]; alpha[i] = c[3];
    }
    const a = this.points.geometry.attributes;
    a.position.needsUpdate = a.size.needsUpdate = a.alpha.needsUpdate = a.tint.needsUpdate = true;
  }
  setScale(h) { this.mat.uniforms.scale.value = h * 0.55; }
}
