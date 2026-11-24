/* Motion-graphics engine: deterministic timeline (seek(t) -> frame), reading-paced text, sprites from Blender renders. */
(function () {
  const W = 1280, H = 720, FPS = 24, TR = 0.6;
  const WPS = 2.3; // words per second a student can comfortably read
  const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
  const E = {
    lin: (t) => t,
    out: (t) => 1 - Math.pow(1 - t, 3),
    inout: (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2),
    back: (t) => { const c = 1.70158; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2); },
    spring: (t) => (t >= 1 ? 1 : 1 - Math.exp(-7 * t) * Math.cos(11 * t)),
    bounce: (t) => { const n = 7.5625, d = 2.75; if (t < 1 / d) return n * t * t; if (t < 2 / d) return n * (t -= 1.5 / d) * t + 0.75; if (t < 2.5 / d) return n * (t -= 2.25 / d) * t + 0.9375; return n * (t -= 2.625 / d) * t + 0.984375; },
  };
  const h = (tag, cls, html, st) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; if (st) Object.assign(e.style, st); return e; };
  let seedv = 7;
  const rnd = () => { seedv |= 0; seedv = (seedv + 0x6d2b79f5) | 0; let t = Math.imul(seedv ^ (seedv >>> 15), 1 | seedv); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };

  const THEMES = {
    space: { g1: '#150d52', g2: '#4b2394', g3: '#c2397a', acc: '#ffd23f', k1: '#c2185b', k2: '#d62828', deco: 'stars' },
    lava: { g1: '#2a0a1e', g2: '#8c1c13', g3: '#ff7a18', acc: '#ffd23f', k1: '#c2410c', k2: '#b91c1c', deco: 'embers' },
    rock: { g1: '#2d1a10', g2: '#7a4a21', g3: '#d89b4a', acc: '#ffe08a', k1: '#9a3412', k2: '#b91c1c', deco: 'embers' },
    desert: { g1: '#6b2d0c', g2: '#d9822b', g3: '#ffd27a', acc: '#fff3b0', k1: '#b45309', k2: '#b91c1c', deco: 'dust' },
    river: { g1: '#06465c', g2: '#0f8fa8', g3: '#7fe0c6', acc: '#ffe27a', k1: '#0b6e99', k2: '#d62828', deco: 'bubbles' },
    sea: { g1: '#07204f', g2: '#0b5db0', g3: '#3fc1d6', acc: '#ffe27a', k1: '#0a5ea8', k2: '#d62828', deco: 'bubbles' },
    sky: { g1: '#0c3d7a', g2: '#3d8fd6', g3: '#bfe6ff', acc: '#ffe27a', k1: '#0b5ea8', k2: '#d62828', deco: 'bubbles' },
    islam: { g1: '#042f2e', g2: '#0c6b5b', g3: '#1fa387', acc: '#f4c542', k1: '#0b7a62', k2: '#b3261e', deco: 'stars8' },
    night: { g1: '#0b1030', g2: '#1d2a6b', g3: '#4b3fa0', acc: '#f4c542', k1: '#4338ca', k2: '#b3261e', deco: 'stars8' },
    review: { g1: '#1a0b45', g2: '#5a1fa0', g3: '#e0529c', acc: '#ffd23f', k1: '#7c1fa8', k2: '#d62828', deco: 'stars' },
  };

  // ───────────── assets (3D renders from Blender) ─────────────
  const ASSET = { man: {}, bm: {}, base: '../assets/' };
  async function loadManifest() { try { ASSET.man = await (await fetch(ASSET.base + 'manifest.json')).json(); } catch (e) { ASSET.man = {}; } }
  const frameUrl = (m, i) => ASSET.base + m.d + '/' + String(i).padStart(3, '0') + '.' + (m.ext || 'png');
  async function loadLoop(name) {
    const m = ASSET.man[name];
    if (!m || m.t !== 'l' || ASSET.bm[name]) return;
    const out = new Array(m.n);
    await Promise.all(Array.from({ length: m.n }, async (_, i) => { const r = await fetch(frameUrl(m, i)); out[i] = await createImageBitmap(await r.blob()); }));
    ASSET.bm[name] = out;
  }
  function unloadLoop(name) { const a = ASSET.bm[name]; if (a) { a.forEach((b) => b.close && b.close()); delete ASSET.bm[name]; } }
  async function loadStill(name) {
    const m = ASSET.man[name];
    if (!m || m.t !== 's' || m._img) return;
    const im = new Image(); im.src = ASSET.base + m.f; try { await im.decode(); } catch (e) {} m._img = im;
  }
  function sprite(name, o = {}) {
    const m = ASSET.man[name];
    const el = h('div', 'sp' + (o.flat ? ' flat' : ''));
    let w = o.w, hh = o.h;
    const ar = m && m.w ? m.w / m.h : 1;
    if (w && !hh) hh = w / ar; else if (hh && !w) w = hh * ar; else if (!w && !hh) { hh = 300; w = hh * ar; }
    el.style.width = w + 'px'; el.style.height = hh + 'px';
    el.style.left = (o.x || 0) + 'px'; el.style.top = (o.y || 0) + 'px';
    el._w = w; el._h = hh;
    if (!m) { el.innerHTML = '<div style="width:100%;height:100%;border-radius:24px;background:rgba(255,255,255,.25);border:4px dashed #fff;color:#fff;display:flex;align-items:center;justify-content:center;font:700 22px Cairo;text-align:center;direction:ltr">' + name + '</div>'; }
    else if (m.t === 's') { const im = new Image(); im.src = ASSET.base + m.f; el.appendChild(im); }
    else { const c = document.createElement('canvas'); c.width = m.w; c.height = m.h; el.appendChild(c); el._loop = { name, m, ctx: c.getContext('2d'), last: -1, off: o.off || 0 }; }
    if (o.flip) el.dataset.flip = '1';
    return el;
  }
  function tickSprite(el, lt) {
    const L = el._loop; if (!L) return;
    const a = ASSET.bm[L.name]; if (!a) return;
    const f = Math.floor((lt + L.off) * L.m.fps) % L.m.n; const fi = f < 0 ? f + L.m.n : f;
    if (fi !== L.last) { L.ctx.clearRect(0, 0, L.m.w, L.m.h); L.ctx.drawImage(a[fi], 0, 0); L.last = fi; }
  }

  // ───────────── rich text (karaoke reading guide) ─────────────
  function rich(src) {
    let out = '', key = 0, red = 0;
    const toks = String(src).split(/(\*|\^|\n)/);
    let firstInSeg = true;
    for (const t of toks) {
      if (t === '*') { out += key ? '</b>' : '<b class="k">'; key ^= 1; continue; }
      if (t === '^') { out += red ? '</b>' : '<b class="r">'; red ^= 1; continue; }
      if (t === '\n') { out += '<br>'; continue; }
      const words = t.split(/\s+/).filter(Boolean);
      const lead = /^\s/.test(t), trail = /\s$/.test(t);
      words.forEach((w, i) => { const m = /^\[\[(#[0-9a-fA-F]{3,6})\]\]$/.exec(w); out += (i > 0 || lead ? ' ' : '') + (m ? '<i class="dot" style="background:' + m[1] + '"></i>' : '<span class="w">' + w + '</span>'); });
      if (trail && words.length) out += ' ';
    }
    return out;
  }
  class Txt {
    constructor(src, o = {}) {
      this.el = h('div', 'txt' + (o.cls ? ' ' + o.cls : ''), rich(src));
      this.spans = Array.from(this.el.querySelectorAll('.w'));
      this.n = this.spans.length; this.cur = 0; this.at = 0; this.wps = o.wps || WPS;
      this.dur = this.n / this.wps + (o.pad == null ? 0.45 : o.pad);
      if (o.noKaraoke) { this.spans.forEach((s) => s.classList.add('rd')); this.cur = this.n; this.fixed = true; }
    }
    update(lt) {
      if (this.fixed) return;
      const c = lt < 0 ? 0 : Math.min(this.n, Math.floor(lt * this.wps) + 1);
      if (c === this.cur) return;
      const a = Math.min(c, this.cur), b = Math.max(c, this.cur);
      for (let i = a; i < b; i++) this.spans[i].classList[i < c ? 'add' : 'remove']('rd');
      this.cur = c;
    }
  }

  // ───────────── items (animated elements) ─────────────
  class Item {
    constructor(el, o = {}) {
      this.el = el; this.at = o.at || 0; this.kind = o.kind || 'pop'; this.dur = o.dur || 0.5;
      this.idle = o.idle ? [].concat(o.idle) : []; this.s0 = o.s || 1; this.rot0 = o.rot || 0; this.x0 = o.dx || 0; this.y0 = o.dy || 0;
      this.out = o.out || null; this.last = ''; this.ph = o.ph == null ? rnd() * 6.28 : o.ph; this.flip = el.dataset.flip === '1' ? -1 : 1;
      this.extra = o.extra || null;
    }
    update(lt) {
      const p = clamp((lt - this.at) / this.dur);
      let dx = this.x0, dy = this.y0, s = this.s0, r = this.rot0, op = 1;
      switch (this.kind) {
        case 'pop': s *= 0.35 + 0.65 * E.back(p); op = clamp(p * 5); break;
        case 'slide': dx += (1 - E.out(p)) * 160; op = clamp(p * 3); break;
        case 'slideL': dx -= (1 - E.out(p)) * 160; op = clamp(p * 3); break;
        case 'up': dy += (1 - E.out(p)) * 70; op = clamp(p * 3); break;
        case 'down': dy -= (1 - E.out(p)) * 70; op = clamp(p * 3); break;
        case 'drop': dy -= (1 - E.bounce(p)) * 260; op = clamp(p * 6); break;
        case 'zoom': s *= 1 + 0.7 * (1 - E.out(p)); op = clamp(p * 2.5); break;
        case 'spring': s *= 0.2 + 0.8 * E.spring(p); op = clamp(p * 6); break;
        case 'fade': op = p; break;
        case 'none': op = lt >= this.at ? 1 : 0; break;
      }
      if (this.out) { const q = clamp((lt - this.out.at) / (this.out.dur || 0.4)); if (q > 0) { op *= 1 - q; if (this.out.kind === 'down') dy += q * 60; else s *= 1 - 0.2 * q; } }
      for (const i of this.idle) {
        const a = i.a == null ? 6 : i.a, sp = i.s == null ? 1.6 : i.s, t = lt * sp + this.ph;
        if (i.t === 'float') dy += Math.sin(t) * a; else if (i.t === 'sway') r += Math.sin(t) * a;
        else if (i.t === 'breathe') { s *= 1 + Math.sin(t) * a; } else if (i.t === 'spin') r += lt * a;
        else if (i.t === 'bob') { dy += Math.abs(Math.sin(t)) * -a; } else if (i.t === 'shake') { dx += Math.sin(lt * 40) * a * (i.on ? i.on(lt) : 1); dy += Math.cos(lt * 33) * a * 0.6 * (i.on ? i.on(lt) : 1); }
        else if (i.t === 'drift') { dx += Math.sin(t) * a; dy += Math.cos(t * 0.7) * a * 0.5; }
        else if (i.t === 'squash') { const k = Math.sin(t) * a; s *= 1 + k; }
      }
      if (this.extra) { const ex = this.extra(lt); if (ex) { dx += ex.dx || 0; dy += ex.dy || 0; s *= ex.s == null ? 1 : ex.s; r += ex.r || 0; op *= ex.op == null ? 1 : ex.op; } }
      const key = (lt < this.at && this.kind !== 'none' ? 'h' : dx.toFixed(1) + dy.toFixed(1) + s.toFixed(3) + r.toFixed(2) + op.toFixed(2));
      if (key === this.last) return; this.last = key;
      const st = this.el.style;
      if (lt < this.at && this.kind !== 'none') { st.opacity = 0; st.visibility = 'hidden'; return; }
      st.visibility = 'visible'; st.opacity = op;
      st.transform = 'translate3d(' + dx.toFixed(1) + 'px,' + dy.toFixed(1) + 'px,0) rotate(' + r.toFixed(2) + 'deg) scale(' + (s * this.flip).toFixed(3) + ',' + s.toFixed(3) + ')';
    }
  }

  // ───────────── scene container ─────────────
  class Scene {
    constructor(spec, L) {
      this.spec = spec; this.L = L; this.th = THEMES[spec.theme || L.theme] || THEMES.space;
      this.root = h('div', 'scene'); this.items = []; this.txts = []; this.cues = []; this.ups = []; this.sprites = []; this.loops = new Set();
      this.cur = 0.2; this.dur = 4; this.fits = [];
    }
    add(el, o = {}) { if (!el.parentNode) this.root.appendChild(el); const it = new Item(el, o); this.items.push(it); if (el._loop) { this.sprites.push(el); this.loops.add(el._loop.name); } return it; }
    sp(name, o = {}, io = {}) { const el = sprite(name, o); const it = this.add(el, Object.assign({ kind: 'pop' }, io)); return it; }
    txt(src, o = {}) { const t = new Txt(src, o); if (o.at != null) t.at = o.at; this.txts.push(t); return t; }
    cue(t, name, g = 1, r = null) { this.cues.push({ t, n: name, g, r: r == null ? 0.94 + rnd() * 0.12 : r }); }
    hdr(kicker, title, at = 0.1) {
      if (!kicker && !title) return;
      const d = h('div', 'hdr');
      if (kicker) d.appendChild(h('div', 'kick', kicker));
      if (title) d.appendChild(h('div', 'ttl', title));
      this.add(d, { at, kind: 'slide', dur: 0.5 });
      this.cue(at, 'swish', 0.7);
      return d;
    }
    update(lt) {
      for (const it of this.items) it.update(lt);
      for (const t of this.txts) t.update(lt - t.at);
      for (const s of this.sprites) tickSprite(s, lt);
      for (const u of this.ups) u(lt);
    }
    // font-size search so that `el` content fits `maxH` at width already set on it
    fit(el, maxH, max = 40, min = 20) {
      let lo = min, hi = max;
      while (hi - lo > 0.5) { const mid = (lo + hi) / 2; el.style.fontSize = mid + 'px'; if (Math.max(el.offsetHeight, el.scrollHeight) <= maxH + 1) lo = mid; else hi = mid; }
      el.style.fontSize = lo + 'px';
      return lo;
    }
  }

  // ───────────── background ─────────────
  const BG = { decos: [] };
  function buildBg(th) {
    const bg = document.getElementById('bg'); bg.innerHTML = '';
    const stage = document.getElementById('stage');
    const set = (k, v) => stage.style.setProperty(k, v);
    set('--g1', th.g1); set('--g2', th.g2); set('--g3', th.g3); set('--acc', th.acc); set('--chip', th.acc); set('--k1', th.k1); set('--k2', th.k2);
    BG.decos = []; seedv = 11;
    const blobs = [[0.85, 0.2, 560, th.g3], [0.1, 0.85, 640, th.g2], [0.5, 0.5, 420, th.acc]];
    blobs.forEach(([x, y, s, c], i) => {
      const d = h('div', 'deco', '', { width: s + 'px', height: s + 'px', borderRadius: '50%', left: (x * W - s / 2) + 'px', top: (y * H - s / 2) + 'px', background: 'radial-gradient(circle,' + c + '55 0%,transparent 68%)' });
      bg.appendChild(d); BG.decos.push({ d, x: 0, y: 0, ax: 60, ay: 40, sp: 0.15 + i * 0.05, ph: i * 2, rot: 0, base: '' });
    });
    const n = 26;
    for (let i = 0; i < n; i++) {
      const s = 6 + rnd() * 26, x = rnd() * W, y = rnd() * H;
      let st = { width: s + 'px', height: s + 'px', left: x + 'px', top: y + 'px', opacity: 0.1 + rnd() * 0.22, background: '#fff' };
      if (th.deco === 'stars8') { st.clipPath = 'polygon(50% 0,61% 22%,85% 15%,78% 39%,100% 50%,78% 61%,85% 85%,61% 78%,50% 100%,39% 78%,15% 85%,22% 61%,0 50%,22% 39%,15% 15%,39% 22%)'; st.width = st.height = (14 + rnd() * 34) + 'px'; st.background = '#f4c542'; st.opacity = 0.08 + rnd() * 0.16; }
      else if (th.deco === 'stars') { st.borderRadius = '50%'; }
      else if (th.deco === 'bubbles') { st.borderRadius = '50%'; st.background = 'transparent'; st.border = '3px solid rgba(255,255,255,.5)'; }
      else if (th.deco === 'embers') { st.borderRadius = '50%'; st.background = '#ffd27a'; }
      else if (th.deco === 'dust') { st.borderRadius = '50%'; st.background = '#fff2c9'; }
      const d = h('div', 'deco', '', st); bg.appendChild(d);
      BG.decos.push({ d, ax: 20 + rnd() * 50, ay: 25 + rnd() * 60, sp: 0.12 + rnd() * 0.5, ph: rnd() * 6.28, rot: (rnd() - 0.5) * 30, up: th.deco === 'embers' || th.deco === 'bubbles' });
    }
  }
  function updateBg(t) {
    for (const o of BG.decos) {
      const a = t * o.sp + o.ph;
      const y = o.up ? -((t * 18 * (o.sp + 0.3) + o.ph * 80) % (H + 80)) + 40 : Math.cos(a * 0.8) * o.ay;
      o.d.style.transform = 'translate3d(' + (Math.sin(a) * o.ax).toFixed(1) + 'px,' + y.toFixed(1) + 'px,0) rotate(' + (t * o.rot).toFixed(1) + 'deg)';
    }
  }

  // ───────────── engine ─────────────
  const SCENES = {};
  const ENGINE = { ready: false, info: null, SCENES, THEMES, h, E, W, H, FPS, TR, WPS, rnd, clamp, Scene, Item, Txt, sprite, rich };
  window.ENGINE = ENGINE;
  let scenes = [], starts = [], total = 0, LESSON = null, swipe, hudBar, assetNames = new Set();

  function expand(list) {
    const out = [];
    for (const s of list) {
      if (s.t === 'table' && s.per && s.rows.length > s.per) {
        const pages = Math.ceil(s.rows.length / s.per);
        for (let p = 0; p < pages; p++) out.push(Object.assign({}, s, { rows: s.rows.slice(p * s.per, (p + 1) * s.per), page: p + 1, pages, per: 0, note: p === pages - 1 ? s.note : null, intro: p === 0 ? s.intro : null, actor: p === 0 ? s.actor : s.actor2 }));
      } else out.push(s);
    }
    return out;
  }
  function collect(o, set) {
    if (typeof o === 'string') { if (ASSET.man[o]) set.add(o); } else if (Array.isArray(o)) o.forEach((x) => collect(x, set)); else if (o && typeof o === 'object') Object.values(o).forEach((x) => collect(x, set));
  }

  ENGINE.aspect = (n) => { const m = ASSET.man[n]; return m && m.w ? m.w / m.h : 1; };
  ENGINE.boot = async function (L) {
    LESSON = L;
    await loadManifest();
    await document.fonts.ready;
    const loads = [];
    for (const w of [400, 600, 700, 800, 900]) loads.push(document.fonts.load(w + ' 30px Cairo', 'أبجد 123 abc').catch(() => {}));
    for (const f of ['Lalezar', 'AmiriQuran']) loads.push(document.fonts.load('400 30px ' + f, 'أبجد 123').catch(() => {}));
    for (const f of ['Amiri', 'ReemKufi', 'ArefRuqaa', 'Changa']) for (const w of [400, 700]) loads.push(document.fonts.load(w + ' 30px ' + f, 'أبجد 123').catch(() => {}));
    await Promise.all(loads);
    const th = THEMES[L.theme] || THEMES.space;
    buildBg(th);
    const host = document.getElementById('scenes');
    const specs = expand(L.scenes);
    collect(specs, assetNames);
    await Promise.all([...assetNames].map(loadStill));
    let t0 = 0;
    for (let i = 0; i < specs.length; i++) {
      const sp = specs[i];
      const S = new Scene(sp, L);
      host.appendChild(S.root);
      const b = SCENES[sp.t];
      if (!b) throw new Error('unknown scene type ' + sp.t);
      b(sp, S);
      if (sp.mascot) ENGINE.mascot(S, sp.mascot);
      if (sp.actors) sp.actors.forEach((a) => ENGINE.actor(S, a));
      S.root.style.display = 'none';
      S.start = t0; S.idx = i;
      scenes.push(S);
      starts.push(t0);
      t0 += S.dur - (i < specs.length - 1 ? TR : 0);
    }
    total = scenes.length ? scenes[scenes.length - 1].start + scenes[scenes.length - 1].dur : 0;
    // lesson-level overlays
    swipe = h('div', 'swipe'); swipe.style.display = 'none'; document.getElementById('fx').appendChild(swipe);
    hudBar = document.querySelector('#hud .bar');
    document.querySelector('#hud .lbl').textContent = L.label || '';
    const cues = [];
    scenes.forEach((S, i) => {
      if (i > 0) cues.push({ t: S.start, n: 'whoosh', g: 0.9, r: 1 });
      S.cues.forEach((c) => cues.push({ t: +(S.start + c.t).toFixed(3), n: c.n, g: c.g, r: +c.r.toFixed(3) }));
    });
    cues.sort((a, b) => a.t - b.t);
    ENGINE.info = { total, fps: FPS, cues, theme: L.theme, music: L.music || null, scenes: scenes.map((s) => ({ start: s.start, dur: s.dur, type: s.spec.t })) };
    ENGINE.ready = true;
  };

  const loaded = new Set();
  ENGINE.seek = async function (t) {
    // load loop-sprites for scenes that are active now or within the next 2.5 s; free ones that are far in the past
    const need = new Set();
    scenes.forEach((S) => { if (t >= S.start - 2.5 && t < S.start + S.dur) S.loops.forEach((n) => need.add(n)); });
    for (const n of [...loaded]) if (!need.has(n)) { unloadLoop(n); loaded.delete(n); }
    await Promise.all([...need].filter((n) => !loaded.has(n)).map(async (n) => { await loadLoop(n); loaded.add(n); }));
    updateBg(t);
    let any = false;
    scenes.forEach((S) => {
      const lt = t - S.start;
      const on = lt >= -0.001 && lt < S.dur;
      const st = S.root.style;
      if (!on) { if (S.shown) { st.display = 'none'; S.shown = false; } return; }
      if (!S.shown) { st.display = 'block'; S.shown = true; }
      S.update(Math.max(0, lt));
      const q = clamp((lt - (S.dur - TR)) / TR);
      const last = S.idx === scenes.length - 1;
      if (q > 0 && !last) { st.opacity = 1 - E.inout(q); st.transform = 'translate3d(' + (-70 * E.inout(q)).toFixed(1) + 'px,0,0) scale(' + (1 - 0.03 * q).toFixed(3) + ')'; }
      else { st.opacity = clamp(lt / 0.25 + 0.0); if (S.idx === 0) st.opacity = 1; st.transform = 'none'; }
      any = true;
    });
    // transition swipe
    let sw = false;
    for (let i = 1; i < scenes.length; i++) {
      const p = (t - starts[i]) / (TR * 0.95);
      if (p > 0 && p < 1) { swipe.style.display = 'block'; swipe.style.transform = 'translate3d(' + ((1 - E.inout(p)) * 1700 - 420).toFixed(0) + 'px,0,0) skewX(-14deg)'; swipe.style.opacity = 0.85 * (1 - Math.abs(p - 0.5) * 1.2); sw = true; break; }
    }
    if (!sw) swipe.style.display = 'none';
    hudBar.style.width = (t / total * 100).toFixed(2) + '%';
    return any;
  };
})();
