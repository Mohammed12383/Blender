// Synthesised sound: engine hum, sonar ping, explosions, launches, alarm, leak hiss, hull creaks.
export class Sound {
  constructor() { this.on = true; this.ctx = null; }
  start() {
    try { this.ctx = new (window.AudioContext || window.webkitAudioContext)(); } catch { return; }
    const c = this.ctx;
    this.master = c.createGain(); this.master.gain.value = 0.5; this.master.connect(c.destination);
    this.engine = c.createOscillator(); this.engine.type = 'sawtooth'; this.engine.frequency.value = 40;
    const lp = c.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 180;
    this.engineGain = c.createGain(); this.engineGain.gain.value = 0;
    this.engine.connect(lp).connect(this.engineGain).connect(this.master); this.engine.start();
    this.noiseBuf = c.createBuffer(1, c.sampleRate * 2, c.sampleRate);
    const d = this.noiseBuf.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    const hiss = c.createBufferSource(); hiss.buffer = this.noiseBuf; hiss.loop = true;
    const hp = c.createBiquadFilter(); hp.type = 'highpass'; hp.frequency.value = 2500;
    this.hissGain = c.createGain(); this.hissGain.gain.value = 0;
    hiss.connect(hp).connect(this.hissGain).connect(this.master); hiss.start();
    this.alarmT = 0;
  }
  toggle() { this.on = !this.on; if (this.master) this.master.gain.value = this.on ? 0.5 : 0; }
  env(node, t, a, peak, decay) { const g = this.ctx.createGain(); g.gain.setValueAtTime(0, t); g.gain.linearRampToValueAtTime(peak, t + a); g.gain.exponentialRampToValueAtTime(0.001, t + a + decay); node.connect(g).connect(this.master); return g; }
  tone(freq, dur, type = 'sine', vol = 0.3) { if (!this.ctx) return; const t = this.ctx.currentTime, o = this.ctx.createOscillator(); o.type = type; o.frequency.value = freq; this.env(o, t, 0.01, vol, dur); o.start(t); o.stop(t + dur + 0.1); return o; }
  noise(dur, freq, vol, type = 'lowpass') { if (!this.ctx) return; const t = this.ctx.currentTime, s = this.ctx.createBufferSource(); s.buffer = this.noiseBuf; const f = this.ctx.createBiquadFilter(); f.type = type; f.frequency.value = freq; s.connect(f); this.env(f, t, 0.01, vol, dur); s.start(t); s.stop(t + dur + 0.2); }
  ping() { const o = this.tone(1480, 1.6, 'sine', 0.35); if (o) setTimeout(() => this.tone(1480, 1.2, 'sine', 0.08), 900); }
  boom(k = 1) { this.noise(1.8 * k + 0.4, 160, 0.9 * k); this.tone(45, 1.2 * k, 'sine', 0.5 * k); }
  launch() { this.noise(1.2, 900, 0.5, 'bandpass'); this.tone(90, 0.8, 'triangle', 0.3); }
  click() { this.tone(2200, 0.03, 'square', 0.05); }
  clunk() { this.tone(120, 0.25, 'square', 0.15); this.noise(0.2, 600, 0.2); }
  zap() { this.noise(0.6, 4000, 0.4, 'highpass'); this.tone(60, 0.6, 'sawtooth', 0.3); }
  klaxon() {
    if (!this.ctx) return;
    for (let i = 0; i < 2; i++) setTimeout(() => {
      const t = this.ctx.currentTime, o = this.ctx.createOscillator(); o.type = 'sawtooth';
      o.frequency.setValueAtTime(180, t); o.frequency.exponentialRampToValueAtTime(420, t + 0.9);
      const f = this.ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 600; f.Q.value = 2;
      o.connect(f); this.env(f, t, 0.05, 0.4, 0.9); o.start(t); o.stop(t + 1.1);
    }, i * 1200);
  }
  bell() { this.tone(1760, 0.6, 'sine', 0.15); setTimeout(() => this.tone(1760, 0.6, 'sine', 0.12), 180); }
  alarm() { for (let i = 0; i < 4; i++) setTimeout(() => this.tone(i % 2 ? 640 : 880, 0.25, 'square', 0.12), i * 280); }
  update(sim, player, dt) {
    if (!this.ctx) return;
    const s = sim.sub;
    this.engine.frequency.value = 35 + Math.abs(s.speed) * 6;
    this.engineGain.gain.value = 0.05 + Math.abs(s.speed) * 0.02;
    const near = sim.leaks.filter((l) => !l.fixed && Math.abs(l.x - player.pos.x) < 8).length;
    this.hissGain.gain.value = Math.min(0.35, near * 0.08);
    this.alarmT -= dt;
    const danger = sim.torpedoes.some((t) => t.owner !== 'player') || s.hull < 35 || sim.entities.some((e) => e.attached);
    if (danger && this.alarmT <= 0) { this.alarmT = 2.2; this.alarm(); }
    if (s.depth > 170 && Math.random() < dt * 0.4) this.tone(70 + Math.random() * 40, 1.4, 'sawtooth', 0.12);
  }
}
