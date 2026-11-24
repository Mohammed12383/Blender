/* Scene types: cover, idea, def, list, steps, table, why, numbers, verse, recap, callouts, timeline, versus, quote, story */
(function () {
  const { SCENES, h, E, W, H, TR, WPS, rnd, clamp, Txt } = ENGINE;
  const PAL = ['#ffd23f', '#ff6b6b', '#3ddc97', '#4cc9f0', '#f72585', '#b5179e', '#fff'];
  const topY = (sp) => (sp.kicker || sp.title ? 122 : 56);
  const wordsOf = (s) => String(s).replace(/[*^]/g, ' ').split(/\s+/).filter(Boolean).length;

  // append the scene's items into a container instead of the scene root
  const addIn = (S, parent, el, o) => { const it = S.add(el, o); parent.appendChild(el); return it; };
  const finish = (S, hold = 1.3) => { S.dur = S.cur + hold + TR; };
  const actor = (S, a, dflt = {}) => {
    if (!a) return null;
    const o = Object.assign({}, dflt, a);
    const idle = o.idle === undefined ? [{ t: 'float', a: 8, s: 1.6 }, { t: 'sway', a: 1.2, s: 1.1 }] : o.idle;
    const it = S.sp(o.img, { x: o.x, y: o.y, w: o.w, h: o.h, flip: o.flip }, { kind: o.kind || 'pop', at: o.at == null ? 0.3 : o.at, dur: o.dur || 0.7, idle, s: o.s || 1, rot: o.rot || 0, out: o.out });
    S.cue(o.at == null ? 0.3 : o.at, o.sfx || 'boing', 0.8);
    return it;
  };
  ENGINE.actor = (S, a) => actor(S, a);
  const burst = (S, x, y, at, n = 26) => {
    const fx = document.createElement('div'); fx.className = 'abs'; fx.style.cssText = 'left:0;top:0;width:0;height:0'; S.root.appendChild(fx);
    const parts = [];
    for (let i = 0; i < n; i++) {
      const e = h('div', 'spark'); e.style.background = PAL[i % PAL.length]; e.style.borderRadius = i % 3 ? '3px' : '50%'; fx.appendChild(e);
      const a = rnd() * 6.283, v = 260 + rnd() * 420; parts.push({ e, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 260, r: (rnd() - 0.5) * 900, s: 0.7 + rnd() });
    }
    S.ups.push((lt) => {
      const t = lt - at; if (t < 0 || t > 1.6) { fx.style.display = 'none'; return; } fx.style.display = 'block';
      for (const p of parts) { p.e.style.transform = 'translate3d(' + (x + p.vx * t).toFixed(0) + 'px,' + (y + p.vy * t + 900 * t * t).toFixed(0) + 'px,0) rotate(' + (p.r * t).toFixed(0) + 'deg) scale(' + p.s + ')'; p.e.style.opacity = clamp(1.6 - t); }
    });
    S.cue(at, 'tada', 0.8);
  };
  ENGINE.mascot = (S, m) => {
    const side = m.side || 'l', hh = m.h || 250, x = side === 'l' ? 14 : W - 14 - hh * 0.85;
    const at = m.at == null ? 0.6 : m.at, y = H - hh - 8;
    const a = S.sp(m.img, { x, y, h: hh }, { kind: 'spring', at, dur: 0.7, idle: [{ t: 'bob', a: 6, s: 3.2 }] });
    const talkDur = m.say ? wordsOf(m.say) / WPS + 0.5 : 0;
    if (m.img2 && m.say) {
      S.sp(m.img2, { x, y, h: hh }, { kind: 'none', at, idle: [], extra: (lt) => ({ op: lt > at + 0.4 && lt < at + 0.4 + talkDur ? (Math.floor(lt * 7) % 2) : 0, dy: -Math.abs(Math.sin((lt) * 3.2 + a.ph)) * 6 }), ph: a.ph });
    }
    S.cue(at, 'boing', 0.8);
    if (m.say) {
      const b = h('div', 'bubble' + (side === 'l' ? '' : ' r'), '', { fontSize: (m.fs || 26) + 'px', width: (m.bw || 340) + 'px', left: side === 'l' ? (x + hh * 0.7) + 'px' : 'auto', right: side === 'r' ? (W - x + 10 - hh * 0.2) + 'px' : 'auto', top: (y - 64 - (m.up || 0)) + 'px' });
      const t = S.txt(m.say, { noKaraoke: true }); b.appendChild(t.el);
      S.add(b, { kind: 'pop', at: at + 0.4, dur: 0.45 }); S.cue(at + 0.4, 'blip', 0.6);
      b.style.top = (y - 20 - b.offsetHeight - (m.up || 0)) + 'px';
      if (S.dur < at + 0.4 + talkDur + 1 + TR) { S.dur = at + 0.4 + talkDur + 1 + TR; }
    }
  };

  // ───────────── cover ─────────────
  SCENES.cover = (sp, S) => {
    const words = String(sp.title).split(/\s+/);
    const len = sp.title.length, fs = len <= 10 ? 150 : len <= 18 ? 124 : len <= 28 ? 100 : 84;
    const box = h('div', 'abs', '', { right: '70px', top: '215px', width: '700px', textAlign: 'right', lineHeight: 1.12 });
    S.root.appendChild(box);
    words.forEach((w, i) => {
      const s = h('span', 'big', w, { display: 'inline-block', fontSize: fs + 'px', color: '#fff', textShadow: '0 8px 0 rgba(0,0,0,.28)', marginLeft: '22px', willChange: 'transform' });
      box.appendChild(s); S.add(s, { kind: 'drop', at: 0.7 + i * 0.22, dur: 0.7 }); S.cue(0.7 + i * 0.22, 'thud', 0.9);
    });
    if (sp.unit) { const k = h('div', 'kick', sp.unit, { position: 'absolute', right: '70px', top: '120px', fontSize: '36px' }); S.add(k, { kind: 'slide', at: 0.3, dur: 0.5 }); S.cue(0.3, 'swish', 0.7); }
    if (sp.sub) { const k = h('div', 'chip', sp.sub, { position: 'absolute', right: '70px', top: (215 + Math.ceil(words.length * 0.5) * fs * 1.1 + 30) + 'px', fontSize: '34px' }); S.add(k, { kind: 'pop', at: 0.7 + words.length * 0.22 + 0.2, dur: 0.5 }); S.cue(0.7 + words.length * 0.22 + 0.2, 'pop', 0.9); }
    actor(S, sp.hero ? Object.assign({ x: 60, y: 80, h: 560, at: 0.25, kind: 'spring' }, sp.hero) : null);
    burst(S, 330, 340, 0.9 + words.length * 0.12);
    S.cur = 0.7 + words.length * 0.22 + 2.6; finish(S, 0.6);
  };

  // ───────────── idea / generic text card ─────────────
  SCENES.idea = (sp, S) => {
    S.hdr(sp.kicker === undefined ? 'الفكرة الرئيسية' : sp.kicker, sp.title);
    const a = sp.actor; const w = a ? (sp.w || 760) : (sp.w || 1060);
    const card = h('div', 'card', '', { right: '56px', top: topY(sp) + 'px', width: w + 'px', padding: '26px 36px' });
    const t = S.txt(sp.text, { at: 0.8 }); card.appendChild(t.el);
    if (sp.sub) { const t2 = S.txt(sp.sub, { at: 0.8 + t.dur + 0.3 }); t2.el.style.marginTop = '14px'; t2.el.style.fontSize = '0.82em'; card.appendChild(t2.el); }
    S.add(card, { kind: 'pop', at: 0.35, dur: 0.6 }); S.cue(0.35, 'pop', 1);
    S.fit(card, 540 - (topY(sp) - 56), sp.fs || 42, 22); card.querySelectorAll('.txt').forEach((e) => { e.style.fontSize = ''; });
    // fit sets card font size; inner .txt inherits
    if (!sp.keepTop) { const ch = card.offsetHeight; card.style.top = Math.max(topY(sp), (H - ch) / 2 + (sp.kicker === null ? 0 : 38)) + 'px'; }
    actor(S, a);
    S.cur = 0.8 + t.dur + (sp.sub ? S.txts[S.txts.length - 1].dur + 0.3 : 0); finish(S);
  };

  // ───────────── definition ─────────────
  SCENES.def = (sp, S) => {
    S.hdr(sp.kicker || 'التعريف', null);
    const a = sp.actor; const w = a ? 800 : 1060;
    const term = h('div', 'big', sp.term, { position: 'absolute', right: '56px', top: '112px', fontSize: (sp.termFs || 78) + 'px', color: 'var(--acc)', textShadow: '0 6px 0 rgba(0,0,0,.3)', lineHeight: 1.1 });
    S.add(term, { kind: 'spring', at: 0.3, dur: 0.7 }); S.cue(0.3, 'thud', 0.9);
    if (sp.en) { const en = h('div', '', sp.en, { position: 'absolute', right: '60px', top: '200px', fontSize: '30px', color: 'rgba(255,255,255,.85)', direction: 'ltr', fontFamily: 'Cairo' }); S.add(en, { kind: 'fade', at: 0.8 }); }
    const card = h('div', 'card', '', { right: '56px', top: (sp.en ? 250 : 215) + 'px', width: w + 'px', padding: '24px 34px' });
    const t = S.txt(sp.text, { at: 1.1 }); card.appendChild(t.el);
    let end = 1.1 + t.dur;
    if (sp.notes) { sp.notes.forEach((n) => { const tn = S.txt(n, { at: end + 0.2 }); tn.el.style.cssText = 'margin-top:12px;font-size:.82em;border-top:2px dashed rgba(0,0,0,.12);padding-top:10px'; card.appendChild(tn.el); end += tn.dur + 0.2; }); }
    S.add(card, { kind: 'pop', at: 0.9, dur: 0.6 }); S.cue(0.9, 'pop', 1);
    S.fit(card, 700 - parseInt(card.style.top) - 20, sp.fs || 36, 20);
    actor(S, a);
    S.cur = end; finish(S);
  };

  // ───────────── list (bullets) ─────────────
  SCENES.list = (sp, S) => {
    S.hdr(sp.kicker, sp.title);
    const a = sp.actor; const w = a ? (sp.w || 780) : (sp.w || 1168);
    const box = h('div', 'abs', '', { right: '56px', top: topY(sp) + 'px', width: w + 'px', display: 'flex', flexDirection: 'column', gap: (sp.gap || 13) + 'px' });
    S.root.appendChild(box);
    let t = 0.55;
    if (sp.intro) {
      const c = h('div', 'card flow', '', { position: 'relative', padding: '16px 28px', background: 'rgba(14,10,40,.72)', color: '#fff' }); c.className = 'card dark'; c.style.position = 'relative';
      const ti = S.txt(sp.intro, { at: t + 0.25 }); c.appendChild(ti.el); addIn(S, box, c, { kind: 'slide', at: t, dur: 0.5 }); S.cue(t, 'swish', 0.6); t += ti.dur + 0.2;
    }
    const num = sp.num === undefined ? true : sp.num;
    sp.items.forEach((it, i) => {
      const txt = typeof it === 'string' ? it : it.t;
      const c = h('div', 'card row', '', { position: 'relative', padding: '14px 26px', gap: '18px', alignItems: 'center' });
      if (num) c.appendChild(h('span', 'num', String(sp.start ? sp.start + i : i + 1)));
      else c.appendChild(h('span', '', '', { width: '16px', height: '16px', borderRadius: '50%', background: 'var(--k1)', flex: 'none', boxShadow: '0 3px 0 rgba(0,0,0,.2)' }));
      const tx = S.txt(txt, { at: t + 0.25 }); tx.el.style.flex = '1'; c.appendChild(tx.el);
      addIn(S, box, c, { kind: sp.kind || 'slide', at: t, dur: 0.5 }); S.cue(t, 'pop', 0.9);
      t += tx.dur + 0.2;
    });
    S.fit(box, 720 - topY(sp) - 36, sp.fs || 34, 19);
    if (sp.center !== false) { const bh = box.offsetHeight; if (bh < 560 - (topY(sp) - 56)) box.style.top = (topY(sp) + (560 - (topY(sp) - 56) - bh) / 2 - 10) + 'px'; }
    actor(S, a);
    S.cur = t; finish(S);
  };

  // ───────────── steps (ordered process) ─────────────
  SCENES.steps = (sp, S) => {
    S.hdr(sp.kicker, sp.title);
    const a = sp.actor; const w = a ? (sp.w || 800) : (sp.w || 1168);
    const n = sp.steps.length;
    const box = h('div', 'abs', '', { right: '56px', top: topY(sp) + 'px', width: w + 'px', display: 'flex', flexDirection: 'column', gap: '12px' });
    S.root.appendChild(box);
    const line = h('div', 'abs', '', { right: (56 + 27 + 26) + 'px', top: (topY(sp) + 30) + 'px', width: '8px', background: 'var(--acc)', borderRadius: '4px', height: '10px', transformOrigin: '50% 0%', opacity: 0.9 });
    S.root.insertBefore(line, box);
    let t = 0.55; const marks = [];
    sp.steps.forEach((st, i) => {
      const c = h('div', 'card row', '', { position: 'relative', padding: '12px 26px', gap: '18px', alignItems: 'center' });
      c.appendChild(h('span', 'num', String((sp.start || 1) + i)));
      const tx = S.txt(typeof st === 'string' ? st : st.t, { at: t + 0.25 }); tx.el.style.flex = '1'; c.appendChild(tx.el);
      addIn(S, box, c, { kind: 'slide', at: t, dur: 0.5 }); S.cue(t, 'tick', 1, 0.85 + i * 0.07);
      marks.push(t); t += tx.dur + 0.2;
    });
    S.fit(box, 720 - topY(sp) - 36, sp.fs || 33, 19);
    const bh = box.offsetHeight; if (bh < 540) box.style.top = (topY(sp) + (540 - bh) / 2) + 'px';
    const top0 = parseInt(box.style.top);
    line.style.top = (top0 + 30) + 'px'; line.style.right = (56 + 26 + 24) + 'px';
    S.ups.push((lt) => { const rows = box.children; let hgt = 0; for (let i = 0; i < n; i++) { if (lt >= marks[i]) hgt = rows[i].offsetTop + rows[i].offsetHeight / 2 - 30; } line.style.height = Math.max(0, hgt) + 'px'; });
    actor(S, a);
    S.cur = t; finish(S);
  };

  // ───────────── table ─────────────
  SCENES.table = (sp, S) => {
    const ttl = sp.title ? sp.title + (sp.pages > 1 ? ' (' + sp.page + '/' + sp.pages + ')' : '') : null;
    S.hdr(sp.kicker, ttl);
    const a = sp.actor; const w = a ? (sp.w || 930) : (sp.w || 1168);
    let y = topY(sp), t = 0.5;
    let introEl = null;
    if (sp.intro) {
      introEl = h('div', 'card dark', '', { right: '56px', top: y + 'px', width: w + 'px', padding: '12px 26px', fontSize: '28px' });
      const ti = S.txt(sp.intro, { at: t + 0.2 }); introEl.appendChild(ti.el); S.add(introEl, { kind: 'slide', at: t, dur: 0.5 }); S.cue(t, 'swish', 0.6); t += ti.dur + 0.2; y += introEl.offsetHeight + 14;
    }
    const card = h('div', 'card', '', { right: '56px', top: y + 'px', width: w + 'px', padding: '14px 18px' });
    const tb = h('table'); const thd = h('thead'); const tr0 = h('tr'); sp.cols.forEach((c) => tr0.appendChild(h('th', '', c))); thd.appendChild(tr0); tb.appendChild(thd);
    const tbody = h('tbody'); tb.appendChild(tbody); card.appendChild(tb);
    S.add(card, { kind: 'pop', at: t, dur: 0.5 }); S.cue(t, 'pop', 1); t += 0.55;
    const rowTimes = [];
    sp.rows.forEach((r, i) => {
      const tr = h('tr'); let nw = 0;
      r.forEach((cell) => { const td = h('td'); const tx = new Txt(cell, { noKaraoke: true }); td.appendChild(tx.el); tr.appendChild(td); nw += tx.n; });
      tbody.appendChild(tr);
      S.add(tr, { kind: 'none', at: t, dur: 0.01, extra: (lt) => { const p = clamp((lt - rowTimes[i]) / 0.4); return { op: p, dx: (1 - E.out(p)) * 90 }; } });
      rowTimes.push(t); S.cue(t, 'tick', 0.9, 0.9 + (i % 4) * 0.08);
      t += nw / 2.1 + 0.7;
    });
    // fix: items created with 'none' kind use at; recreate their start from rowTimes
    S.items.filter((it) => it.el.tagName === 'TR').forEach((it, i) => { it.at = rowTimes[i]; });
    let nt = null, tn = null;
    if (sp.note) { nt = h('div', '', '', { marginTop: '12px', background: 'var(--acc)', color: '#2a1f00', borderRadius: '20px', padding: '10px 24px', fontSize: '0.88em', boxShadow: '0 4px 0 rgba(0,0,0,.2)' }); tn = S.txt(sp.note, { at: t + 0.3 }); nt.appendChild(tn.el); card.appendChild(nt); }
    S.fit(card, 700 - y - 30, sp.fs || 32, 17);
    if (nt) { S.add(nt, { kind: 'pop', at: t, dur: 0.5 }); S.cue(t, 'ding', 0.9); t += tn.dur + 0.3; }
    const ait = actor(S, a);
    if (ait && a && a.rowShake) ait.extra = (lt) => { let k = 0; for (let i = 0; i < rowTimes.length; i++) if (lt >= rowTimes[i] + 0.2) k = i + 1; const amp = Math.max(0, k - 1) * (a.rowShake === true ? 1.8 : a.rowShake); return { dx: Math.sin(lt * 47) * amp, dy: Math.cos(lt * 39) * amp * 0.5, r: Math.sin(lt * 31) * amp * 0.12 }; };
    S.cur = t; finish(S, 1.4);
  };

  // ───────────── why (علّل) ─────────────
  SCENES.why = (sp, S) => {
    S.hdr(sp.kicker || 'علّل', null);
    const q = h('div', 'card dark', '', { right: '56px', top: '110px', width: (sp.actor ? 800 : 1168) + 'px', padding: '18px 30px', background: 'rgba(14,10,40,.82)', fontSize: '36px' });
    q.appendChild(h('span', 'big', '؟', { color: 'var(--acc)', fontSize: '1.7em', marginLeft: '16px', verticalAlign: 'middle' }));
    const tq = S.txt(sp.q, { at: 0.6, cls: '' }); tq.el.style.display = 'inline'; q.appendChild(tq.el);
    S.add(q, { kind: 'pop', at: 0.3, dur: 0.6, idle: [{ t: 'sway', a: 0.5, s: 1.3 }] }); S.cue(0.3, 'boing', 0.9);
    let t = 0.6 + tq.dur + 0.5;
    const box = h('div', 'abs', '', { right: '56px', top: '300px', width: (sp.actor ? 800 : 1168) + 'px', display: 'flex', flexDirection: 'column', gap: '12px' }); S.root.appendChild(box);
    const ans = [].concat(sp.a);
    let first = true;
    ans.forEach((x) => {
      const c = h('div', 'card row', '', { position: 'relative', padding: '12px 26px', gap: '16px', alignItems: 'center', borderRight: '12px solid var(--acc2)' });
      c.appendChild(h('span', 'num', '✓', { background: 'var(--acc2)', color: '#05301c', fontFamily: 'Cairo' }));
      const tx = S.txt(x, { at: t + 0.25 }); tx.el.style.flex = '1'; c.appendChild(tx.el);
      addIn(S, box, c, { kind: 'slide', at: t, dur: 0.5 }); S.cue(t, first ? 'ding' : 'pop', 0.9); first = false;
      t += tx.dur + 0.2;
    });
    S.fit(box, 720 - 300 - 30, sp.fs || 33, 19);
    const qh = q.offsetHeight; box.style.top = (110 + qh + 22) + 'px';
    actor(S, sp.actor);
    S.cur = t; finish(S);
  };

  // ───────────── numbers (big counters) ─────────────
  SCENES.numbers = (sp, S) => {
    S.hdr(sp.kicker, sp.title);
    const n = sp.items.length, cols = Math.min(n, sp.cols || (n > 4 ? 3 : n)), rowsN = Math.ceil(n / cols);
    const gap = 22, cw = (1168 - gap * (cols - 1)) / cols, ch = Math.min(sp.chMax || 260, (560 - topY(sp) + 56 - gap * (rowsN - 1)) / rowsN);
    let t = 0.5;
    const y0 = sp.top || (topY(sp) + Math.max(0, (560 - (topY(sp) - 56) - (ch * rowsN + gap * (rowsN - 1))) / 2));
    sp.items.forEach((it, i) => {
      const r = Math.floor(i / cols), c = i % cols;
      const card = h('div', 'card', '', { right: (56 + c * (cw + gap)) + 'px', top: (y0 + r * (ch + gap)) + 'px', width: cw + 'px', height: ch + 'px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '4px', textAlign: 'center', padding: '10px 16px' });
      const nstr = String(it.n), pre = it.pre || '', suf = it.suf || '';
      const isNum = /^[\d.]+$/.test(nstr.trim());
      const num = parseFloat(nstr);
      const fs0 = it.fs || Math.min(104, ch * 0.4, (cw - 40) / (Math.max(nstr.length, 2) * 0.62 + (suf ? 1.1 : 0) + (pre ? 0.8 : 0)));
      const big = h('div', 'big', '', { fontSize: fs0 + 'px', color: 'var(--k1)', lineHeight: 1.05, whiteSpace: 'nowrap' });
      const nspan = h('span', '', isNum ? '0' : nstr, { direction: 'ltr', display: 'inline-block', unicodeBidi: 'isolate' });
      big.appendChild(nspan);
      if (suf) big.appendChild(h('span', '', suf, { fontSize: '0.55em', marginRight: '6px', color: 'var(--ink)' }));
      if (pre) big.insertBefore(h('span', '', pre, { fontSize: '0.5em', marginLeft: '6px', color: 'var(--ink)' }), big.firstChild);
      const lab = S.txt(it.l, { noKaraoke: true }); lab.el.style.cssText = 'font-size:' + (it.lfs || 26) + 'px;line-height:1.4';
      card.appendChild(big); card.appendChild(lab.el);
      if (it.note) { const nt = h('div', '', it.note, { fontSize: '21px', color: 'rgba(29,26,58,.7)', lineHeight: 1.35 }); card.appendChild(nt); }
      const at = t; S.add(card, { kind: 'spring', at, dur: 0.7 }); S.cue(at, 'pop', 1, 0.85 + i * 0.06);
      if (isNum) S.ups.push((lt) => { const p = clamp((lt - at - 0.2) / 1.0); const v = num * E.out(p); nspan.textContent = Number.isInteger(num) ? String(Math.round(v)) : v.toFixed(1); });
      t += (it.hold || 1.1) + wordsOf(it.l + ' ' + (it.note || '')) / 2.6;
    });
    S.cur = t; finish(S);
  };

  // ───────────── verse (Quran / hadith) ─────────────
  SCENES.verse = (sp, S) => {
    S.hdr(sp.kicker || 'الدليل', null);
    const card = h('div', 'card', '', { right: '110px', left: '110px', top: '125px', padding: '26px 40px', background: 'linear-gradient(180deg,#fffdf4,#fff3cf)', border: '6px solid var(--acc)' });
    const t = S.txt(sp.text, { at: 0.9, wps: 1.9 }); t.el.className = 'txt verse'; t.el.style.fontSize = '46px'; card.appendChild(t.el);
    if (sp.src) card.appendChild(h('div', '', sp.src, { textAlign: 'center', fontSize: '24px', color: 'var(--k1)', marginTop: '6px' }));
    S.add(card, { kind: 'zoom', at: 0.4, dur: 0.8 }); S.cue(0.4, 'sparkle', 1);
    S.fit(card, sp.notes ? 330 : 470, 50, 26);
    let tt = 0.9 + t.dur + 0.4;
    if (sp.notes) {
      const box = h('div', 'abs', '', { right: '110px', left: '110px', top: (125 + card.offsetHeight + 18) + 'px', display: 'flex', flexDirection: 'column', gap: '10px' }); S.root.appendChild(box);
      sp.notes.forEach((x) => {
        const c = h('div', 'card row', '', { position: 'relative', padding: '10px 24px', gap: '14px', alignItems: 'center', background: 'rgba(14,10,40,.78)', color: '#fff' }); c.className = 'card dark row'; c.style.position = 'relative';
        const tx = S.txt(x, { at: tt + 0.25 }); tx.el.style.cssText = 'flex:1;font-size:30px'; c.appendChild(tx.el); addIn(S, box, c, { kind: 'slide', at: tt, dur: 0.5 }); S.cue(tt, 'pop', 0.8); tt += tx.dur + 0.2;
      });
    }
    S.cur = tt; finish(S);
  };

  // ───────────── recap (concepts to memorise) ─────────────
  SCENES.recap = (sp, S) => {
    S.hdr(sp.kicker || 'مفاهيم الدرس للحفظ', sp.title || null);
    const box = h('div', 'abs', '', { right: '60px', left: '300px', top: '140px', display: 'flex', flexWrap: 'wrap', gap: '14px', justifyContent: 'center', alignContent: 'flex-start' }); S.root.appendChild(box);
    const n = sp.chips.length; const fs = n > 18 ? 28 : n > 12 ? 32 : n > 8 ? 38 : 46;
    let t = 0.6; const cols = ['#fff', '#ffe58a', '#b9f3d4', '#bfe3ff', '#ffc9de'];
    sp.chips.forEach((c, i) => {
      const e = h('div', 'chip', c, { fontSize: fs + 'px', background: cols[i % cols.length] });
      addIn(S, box, e, { kind: 'spring', at: t, dur: 0.55 }); S.cue(t, 'ding', 0.8, 0.8 + (i % 8) * 0.09);
      t += 0.5 + (wordsOf(c) > 2 ? 0.2 : 0);
    });
    actor(S, sp.actor || { img: 'terra_cheer_grin', x: 30, y: 250, h: 430, at: 0.5, kind: 'spring' });
    burst(S, 150, 340, t + 0.1, 34);
    S.cur = t + 2.2; finish(S, 1.0);
  };

  // ───────────── callouts (3D image with labels) ─────────────
  SCENES.callouts = (sp, S) => {
    S.hdr(sp.kicker, sp.title);
    const b = sp.box || { x: 380, y: 112, w: 520, h: 540 };
    const it = S.sp(sp.img, { x: b.x, y: b.y, w: b.w, h: b.h }, { kind: 'zoom', at: 0.3, dur: 0.8, idle: sp.idle === undefined ? [{ t: 'float', a: 5, s: 1.3 }] : sp.idle });
    S.cue(0.3, 'whoosh', 0.7);
    let t = 0.9;
    sp.labels.forEach((l, i) => {
      const cw = l.w || 330;
      const card = h('div', 'card', '', { width: cw + 'px', padding: '10px 18px', fontSize: (l.fs || 26) + 'px', textAlign: 'center' });
      card.style.left = l.x + 'px'; card.style.top = l.y + 'px';
      const tx = S.txt(l.t, { at: t + 0.25 }); card.appendChild(tx.el); S.add(card, { kind: 'pop', at: t, dur: 0.5 }); S.cue(t, 'pop', 0.9);
      if (l.to) {
        const cx = l.x + cw / 2, cy = l.y + 30, dx = l.to[0] - cx, dy = l.to[1] - cy, len = Math.hypot(dx, dy), ang = Math.atan2(dy, dx) * 180 / Math.PI;
        const ln = h('div', 'abs', '', { left: cx + 'px', top: cy - 3 + 'px', width: len + 'px', height: '6px', background: 'var(--acc)', borderRadius: '3px', transformOrigin: '0 50%' });
        ln.style.transform = 'rotate(' + ang + 'deg)';
        const dot = h('div', 'abs', '', { left: (l.to[0] - 10) + 'px', top: (l.to[1] - 10) + 'px', width: '20px', height: '20px', borderRadius: '50%', background: 'var(--acc)', boxShadow: '0 0 0 5px rgba(255,255,255,.7)' });
        S.root.insertBefore(ln, card); S.add(dot, { kind: 'pop', at: t + 0.2, dur: 0.4 });
        const q = { at: t + 0.1 };
        S.ups.push((lt) => { const p = clamp((lt - q.at) / 0.35); ln.style.opacity = p > 0 ? 1 : 0; ln.style.transform = 'rotate(' + ang + 'deg) scaleX(' + E.out(p) + ')'; });
      }
      t += tx.dur + 0.35;
    });
    S.cur = t; finish(S);
  };

  // ───────────── timeline ─────────────
  SCENES.timeline = (sp, S) => {
    S.hdr(sp.kicker, sp.title);
    const n = sp.nodes.length, gap = 20, cw = (1168 - gap * (n - 1)) / n;
    const y0 = 120;
    const bar = h('div', 'abs', '', { right: '56px', top: (y0 + 52) + 'px', height: '10px', background: 'var(--acc)', borderRadius: '5px', width: '0px', opacity: 0.9 }); S.root.appendChild(bar);
    let t = 0.5; const ts = [];
    sp.nodes.forEach((nd, i) => {
      const card = h('div', 'card', '', { right: (56 + i * (cw + gap)) + 'px', top: y0 + 'px', width: cw + 'px', height: (560 - 56) + 'px', padding: '14px 18px', display: 'flex', flexDirection: 'column', alignItems: 'center', textAlign: 'center', gap: '8px' });
      card.appendChild(h('div', 'tag y', nd.when, { fontSize: (nd.wfs || 28) + 'px' }));
      if (nd.img) { const el = ENGINE.sprite(nd.img, { w: cw - 36, h: nd.ih || 210 }); el.style.position = 'relative'; el.style.left = '0'; el.style.top = '0'; el.classList.add('flat'); card.appendChild(el); if (el._loop) { S.sprites.push(el); S.loops.add(el._loop.name); } }
      card.appendChild(h('div', 'big', nd.title, { fontSize: '40px', color: 'var(--k1)', lineHeight: 1.1 }));
      const tx = S.txt(nd.text, { at: t + 0.4 }); tx.el.style.fontSize = (nd.fs || 26) + 'px'; card.appendChild(tx.el);
      S.add(card, { kind: 'pop', at: t, dur: 0.6 }); S.cue(t, 'pop', 1, 0.85 + i * 0.1);
      ts.push(t); t += tx.dur + 0.6;
    });
    S.ups.push((lt) => { let k = 0; for (let i = 0; i < n; i++) if (lt >= ts[i]) k = i + 1; const p = k ? clamp((lt - ts[k - 1]) / 0.5) : 0; bar.style.width = Math.max(0, ((k - 1 + E.out(p)) * (cw + gap) + cw)) + 'px'; });
    S.cur = t; finish(S);
  };

  // ───────────── versus (two lists side by side) ─────────────
  SCENES.versus = (sp, S) => {
    S.hdr(sp.kicker, sp.title);
    const gap = 26, cw = (1168 - gap) / 2; let t = 0.5;
    [sp.a, sp.b].forEach((side, si) => {
      const card = h('div', 'card', '', { right: (56 + si * (cw + gap)) + 'px', top: topY(sp) + 'px', width: cw + 'px', padding: '16px 24px', display: 'flex', flexDirection: 'column', gap: '10px' });
      card.appendChild(h('div', 'big', side.title, { fontSize: '44px', color: si ? 'var(--k2)' : 'var(--k1)', textAlign: 'center', borderBottom: '4px dashed rgba(0,0,0,.12)', paddingBottom: '6px' }));
      const startT = t; S.add(card, { kind: 'pop', at: t, dur: 0.55 }); S.cue(t, 'pop', 1);
      let tt = t + 0.6;
      side.items.forEach((x) => { const tx = S.txt(x, { at: tt }); const row = h('div', 'row', '', { gap: '10px', alignItems: 'flex-start' }); row.appendChild(h('span', '', '', { width: '14px', height: '14px', marginTop: '14px', borderRadius: '50%', background: si ? 'var(--k2)' : 'var(--k1)', flex: 'none' })); row.appendChild(tx.el); card.appendChild(row); S.cue(tt, 'tick', 0.8); tt += tx.dur + 0.15; });
      S.fit(card, 720 - topY(sp) - 36, sp.fs || 32, 19);
      t = tt + 0.3;
    });
    S.cur = t; finish(S);
  };

  // ───────────── quote (sayings of scholars) ─────────────
  SCENES.quote = (sp, S) => {
    S.hdr(sp.kicker || 'قال', null);
    const card = h('div', 'card', '', { right: '120px', left: '120px', top: '150px', padding: '30px 50px', textAlign: 'center', background: 'linear-gradient(180deg,#fffdf4,#fff1c9)' });
    card.appendChild(h('div', 'big', '”', { position: 'absolute', top: '-8px', right: '26px', fontSize: '140px', color: 'var(--acc)', lineHeight: 1 }));
    const t = S.txt(sp.text, { at: 0.9, wps: 2.0 }); t.el.style.fontFamily = 'Amiri, Cairo'; t.el.style.fontSize = '44px'; card.appendChild(t.el);
    if (sp.who) card.appendChild(h('div', 'tag', sp.who, { marginTop: '14px', fontSize: '30px' }));
    S.add(card, { kind: 'zoom', at: 0.4, dur: 0.7 }); S.cue(0.4, 'sparkle', 0.9);
    S.fit(card, 470, 50, 26);
    card.style.top = Math.max(120, (H - card.offsetHeight) / 2 + 20) + 'px';
    if (sp.actor) actor(S, sp.actor);
    S.cur = 0.9 + t.dur; finish(S);
  };


  // ───────────── tree (concept map) ─────────────
  SCENES.tree = (sp, S) => {
    S.hdr(sp.kicker, sp.title);
    const gap = 14, leaves = []; sp.branches.forEach((b, bi) => b.leaves.forEach((l) => leaves.push({ l, bi })));
    const nl = leaves.length, lw = (1168 - gap * (nl - 1)) / nl;
    const cxOf = (i) => W - (56 + i * (lw + gap) + lw / 2);
    const rootW = sp.rootW || 560, ry = 118, rh = 70;
    const lineC = 'rgba(255,255,255,.85)';
    const lines = [];
    const ln = (x, y, w, hh, at) => { const e = h('div', 'abs', '', { left: x + 'px', top: y + 'px', width: w + 'px', height: hh + 'px', background: lineC, borderRadius: '3px' }); S.root.insertBefore(e, S.root.firstChild); lines.push({ e, at }); };
    const root = h('div', 'card', '', { left: (W / 2 - rootW / 2) + 'px', top: ry + 'px', width: rootW + 'px', height: rh + 'px', display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'var(--acc)', color: '#2a1f00', textAlign: 'center', fontSize: (sp.rfs || 30) + 'px', padding: '6px 16px' });
    const rt = S.txt(sp.root, { at: 0.8 }); root.appendChild(rt.el); S.add(root, { kind: 'spring', at: 0.4, dur: 0.6 }); S.cue(0.4, 'pop', 1);
    let t = 0.8 + rt.dur + 0.2;
    const by = 250, bh = 84, ly = 385, busY = ry + rh + 22, busY2 = by + bh + 18;
    const bcx = sp.branches.map((b, bi) => { const idx = leaves.map((x, i) => x.bi === bi ? i : -1).filter((i) => i >= 0); return { idx, cx: idx.reduce((a, i) => a + cxOf(i), 0) / idx.length }; });
    ln(W / 2 - 1.5, ry + rh, 3, 22, 0.8 + rt.dur);
    const bxs = bcx.map((b) => b.cx); ln(Math.min(...bxs), busY, Math.max(...bxs) - Math.min(...bxs) + 3, 3, 0.8 + rt.dur);
    sp.branches.forEach((b, bi) => {
      const info = bcx[bi]; const bw = info.idx.length * lw + (info.idx.length - 1) * gap - 10;
      ln(info.cx - 1.5, busY, 3, by - busY, t);
      const card = h('div', 'card', '', { left: (info.cx - bw / 2) + 'px', top: by + 'px', width: bw + 'px', height: bh + 'px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', padding: '4px 10px', background: bi ? '#ffd7d7' : '#d7f5e6' });
      card.appendChild(h('div', 'big', b.title, { fontSize: '36px', color: bi ? 'var(--k2)' : 'var(--k1)', lineHeight: 1.05 }));
      if (b.sub) { const ts = S.txt(b.sub, { noKaraoke: true }); ts.el.style.cssText = 'font-size:21px;line-height:1.2'; card.appendChild(ts.el); }
      S.add(card, { kind: 'pop', at: t, dur: 0.55 }); S.cue(t, 'pop', 1, 0.9); t += 0.6;
      const lxs = info.idx.map((i) => cxOf(i));
      ln(Math.min(...lxs), busY2, Math.max(...lxs) - Math.min(...lxs) + 3, 3, t); ln(info.cx - 1.5, by + bh, 3, busY2 - by - bh, t);
      info.idx.forEach((i) => {
        const L = leaves[i].l; ln(cxOf(i) - 1.5, busY2, 3, ly - busY2, t);
        const c = h('div', 'card', '', { left: (cxOf(i) - lw / 2) + 'px', top: ly + 'px', width: lw + 'px', padding: '12px 14px', textAlign: 'center' });
        c.appendChild(h('div', 'big', L.title, { fontSize: '31px', color: bi ? 'var(--k2)' : 'var(--k1)', lineHeight: 1.1, marginBottom: '4px' }));
        let tt = t + 0.4;
        (L.lines || []).forEach((x) => { const tx = S.txt(x, { at: tt }); tx.el.style.cssText = 'font-size:' + (sp.fs || 21) + 'px;line-height:1.38;border-top:2px dashed rgba(0,0,0,.1);padding-top:4px;margin-top:4px'; c.appendChild(tx.el); tt += tx.dur; });
        S.add(c, { kind: 'pop', at: t, dur: 0.55 }); S.cue(t, 'pop', 0.9, 1.05);
        t = tt + 0.25;
      });
    });
    S.ups.push((lt) => { lines.forEach((l) => { const p = clamp((lt - l.at) / 0.3); l.e.style.opacity = p > 0 ? 1 : 0; l.e.style.transform = 'scale(' + (p) + ')'; }); });
    S.cur = t; finish(S);
  };


  // ───────────── cycle (nodes + curved arrows, e.g. the rock cycle) ─────────────
  SCENES.cycle = (sp, S) => {
    S.hdr(sp.kicker, sp.title);
    const NS = 'http://www.w3.org/2000/svg';
    const svg = document.createElementNS(NS, 'svg'); svg.setAttribute('width', W); svg.setAttribute('height', H); svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H); svg.style.cssText = 'position:absolute;left:0;top:0;pointer-events:none';
    const defs = document.createElementNS(NS, 'defs'); defs.innerHTML = '<marker id="ah" markerWidth="8" markerHeight="8" refX="5" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#ffd23f"/></marker><marker id="ah2" markerWidth="8" markerHeight="8" refX="5" refY="4" orient="auto"><path d="M0,0 L8,4 L0,8 z" fill="#ffffff"/></marker>';
    svg.appendChild(defs); S.root.appendChild(svg);
    let t = 0.5; const nt = {}, ar = [];
    sp.nodes.forEach((n, i) => {
      const size = n.size || 150;
      const box = h('div', 'abs', '', { left: (n.x - size / 2) + 'px', top: (n.y - size / 2 - 14) + 'px', width: size + 'px', height: size + 'px' });
      S.root.appendChild(box);
      const el = ENGINE.sprite(n.img, { w: size, h: size }); el.style.left = '0'; el.style.top = '0'; box.appendChild(el); if (el._loop) { S.sprites.push(el); S.loops.add(el._loop.name); }
      const lab = h('div', 'chip', n.title, { position: 'absolute', left: (n.x - 130) + 'px', top: (n.y + size / 2 - 22) + 'px', width: '260px', textAlign: 'center', fontSize: (n.fs || 27) + 'px', padding: '6px 10px 10px' });
      S.add(box, { kind: 'spring', at: t, dur: 0.6, idle: [{ t: 'float', a: 4, s: 1.4 }] }); S.add(lab, { kind: 'pop', at: t + 0.1, dur: 0.5 }); S.cue(t, 'pop', 1, 0.9 + i * 0.05);
      nt[n.id] = n; t += 0.55;
    });
    t += 0.2;
    sp.arrows.forEach((a, i) => {
      const A = nt[a.from], B = nt[a.to]; const bend = a.bend == null ? 60 : a.bend;
      const dx = B.x - A.x, dy = B.y - A.y, L = Math.hypot(dx, dy) || 1; const ux = dx / L, uy = dy / L;
      const sx = A.x + ux * 95, sy = A.y + uy * 85 - 6, ex = B.x - ux * 95, ey = B.y - uy * 85 - 6;
      const mx = (sx + ex) / 2 - uy * bend, my = (sy + ey) / 2 + ux * bend;
      const p = document.createElementNS(NS, 'path'); p.setAttribute('d', 'M' + sx + ',' + sy + ' Q' + mx + ',' + my + ' ' + ex + ',' + ey);
      p.setAttribute('fill', 'none'); p.setAttribute('stroke', a.dashed ? '#ffffff' : '#ffd23f'); p.setAttribute('stroke-width', '7'); p.setAttribute('stroke-linecap', 'round'); p.setAttribute('marker-end', a.dashed ? 'url(#ah2)' : 'url(#ah)');
      if (a.dashed) p.setAttribute('stroke-dasharray', '14 12');
      svg.appendChild(p);
      const len = p.getTotalLength();
      const lx = 0.25 * sx + 0.5 * mx + 0.25 * ex, ly = 0.25 * sy + 0.5 * my + 0.25 * ey;
      const lo = a.lo || [0, 0]; const lb = h('div', 'bubble', '', { left: (lx - 120 + lo[0]) + 'px', top: (ly - 20 + lo[1]) + 'px', width: '240px', textAlign: 'center', fontSize: (a.fs || 23) + 'px', padding: '6px 12px', background: a.dashed ? '#eef' : '#fff6cf' }); lb.style.setProperty('--x', '0');
      lb.style.cssText += ';';
      const tx = S.txt(a.t, { at: t + 0.45 }); lb.appendChild(tx.el); S.add(lb, { kind: 'pop', at: t + 0.4, dur: 0.45 }); S.cue(t, 'swish', 0.8);
      const t0 = t; ar.push({ p, len, t0 });
      p.style.strokeDasharray = a.dashed ? '14 12' : len; if (!a.dashed) p.style.strokeDashoffset = len;
      ar[ar.length - 1].dashed = !!a.dashed;
      t += tx.dur + 0.55;
    });
    S.ups.push((lt) => { ar.forEach((a) => { const q = clamp((lt - a.t0) / 0.5); if (a.dashed) a.p.style.opacity = q; else a.p.style.strokeDashoffset = a.len * (1 - E.out(q)); }); });
    S.cur = t; finish(S);
  };


  // ───────────── quiz (question → countdown → answer) ─────────────
  SCENES.quiz = (sp, S) => {
    S.hdr(sp.kicker || 'اختبر نفسك', sp.title || null);
    const think = sp.think || 3;
    let t = 0.6; const counters = [];
    sp.items.forEach((it, i) => {
      const card = h('div', 'card', '', { right: '160px', left: '160px', top: '165px', padding: '26px 40px', textAlign: 'center', minHeight: '360px' });
      const qn = h('div', 'tag', 'سؤال ' + (i + 1) + ' / ' + sp.items.length, { fontSize: '24px', marginBottom: '14px' });
      card.appendChild(qn);
      const tq = S.txt(it.q, { at: t + 0.4 }); tq.el.style.cssText = 'font-size:46px;line-height:1.5;margin-bottom:20px'; card.appendChild(tq.el);
      const ring = h('div', 'big', '', { position: 'absolute', left: '34px', top: '30px', width: '84px', height: '84px', borderRadius: '50%', border: '8px solid var(--acc)', background: 'rgba(255,255,255,.9)', color: 'var(--k1)', fontSize: '44px', display: 'flex', alignItems: 'center', justifyContent: 'center', lineHeight: 1 });
      card.appendChild(ring);
      const ans = h('div', '', '', { background: 'var(--acc2)', color: '#05301c', borderRadius: '24px', padding: '12px 28px', fontSize: '48px', fontFamily: 'Lalezar', boxShadow: '0 6px 0 rgba(0,0,0,.2)' });
      const ta = new ENGINE.Txt(it.a, { noKaraoke: true }); ans.appendChild(ta.el); card.appendChild(ans);
      const tRead = t + 0.4 + tq.dur, tReveal = tRead + think, tEnd = tReveal + (it.hold || 2.0);
      S.add(card, { kind: 'pop', at: t, dur: 0.5, out: { at: tEnd, dur: 0.35 } }); S.cue(t, 'whoosh', 0.5);
      S.add(ans, { kind: 'spring', at: tReveal, dur: 0.6 }); S.cue(tReveal, 'tada', 0.8); S.cue(tReveal - 0.05, 'ding', 0.8);
      for (let k = 0; k < think; k++) S.cue(tRead + k, 'tick', 0.9, 1.1 - k * 0.1);
      counters.push({ ring, tRead, tReveal });
      t = tEnd + 0.3;
    });
    S.ups.push((lt) => { counters.forEach((c) => { if (lt < c.tRead || lt >= c.tReveal) { c.ring.style.visibility = 'hidden'; return; } c.ring.style.visibility = 'visible'; c.ring.textContent = Math.ceil(c.tReveal - lt); }); });
    if (sp.actor) actor(S, sp.actor);
    S.cur = t; finish(S, 0.6);
  };

  // ───────────── story (cinematic beats) ─────────────
  // beats: [{bg:'asset', actors:[{img,x,y,h,flip,kind,idle,at}], cap:'narration', say:{who:0,t:'dialogue'}, cam:{z0,z1,x0,x1}, sfx:[['name',dt,g]] , dur}]
  SCENES.story = (sp, S) => {
    let t = 0.25; const beats = [];
    sp.beats.forEach((b, bi) => {
      const g = h('div', 'abs', '', { left: 0, top: 0, width: W + 'px', height: H + 'px', overflow: 'hidden' }); S.root.appendChild(g);
      const items = [];
      if (b.bg) {
        const bgIt = S.sp(b.bg, { x: -(b.bgOver || 40), y: -(b.bgOver || 40), w: W + 2 * (b.bgOver || 40), h: H + 2 * (b.bgOver || 40) }, { kind: 'none', at: 0 }); S.items.pop();
        const el = bgIt.el; el.classList.add('flat'); g.appendChild(el); el.style.transformOrigin = '50% 50%'; items.push({ el, bg: true });
        if (el._loop) { S.sprites.push(el); S.loops.add(el._loop.name); }
      } else if (b.color) { g.style.background = b.color; }
      (b.actors || []).forEach((a) => {
        const el = ENGINE.sprite(a.img, { x: a.x, y: a.y, w: a.w, h: a.h, flip: a.flip, flat: a.flat });
        g.appendChild(el); if (el._loop) { S.sprites.push(el); S.loops.add(el._loop.name); }
        const it = new ENGINE.Item(el, { kind: a.kind || 'pop', at: t + (a.at == null ? 0.25 : a.at), dur: a.dur || 0.6, idle: a.idle === undefined ? [{ t: 'float', a: 6, s: 1.5 }] : a.idle, s: a.s || 1, rot: a.rot || 0, out: a.out ? { at: t + a.out, dur: 0.4 } : null });
        S.items.push(it); S.cue(t + (a.at == null ? 0.25 : a.at), a.sfx || 'pop', 0.8);
      });
      let capDur = 0, sayEnd = 0;
      const nodes = [];
      if (b.cap) {
        const cap = h('div', 'cap', '', { fontSize: (b.fs || 32) + 'px' }); const tx = S.txt(b.cap, { at: t + 0.7 }); tx.el.style.textAlign = 'center'; cap.appendChild(tx.el); g.appendChild(cap);
        const ci = new ENGINE.Item(cap, { kind: 'up', at: t + 0.4, dur: 0.5 }); S.items.push(ci); S.cue(t + 0.4, 'swish', 0.5); capDur = 0.7 + tx.dur;
      }
      if (b.say) {
        [].concat(b.say).forEach((s, si) => {
          const bub = h('div', 'bubble' + (s.r ? ' r' : ''), '', { fontSize: (s.fs || 28) + 'px', width: (s.w || 380) + 'px', left: s.x + 'px', top: s.y + 'px' });
          const tx = S.txt(s.t, { at: t + (s.at == null ? capDur : s.at) + 0.2 }); bub.appendChild(tx.el); g.appendChild(bub);
          const bi2 = new ENGINE.Item(bub, { kind: 'pop', at: t + (s.at == null ? capDur : s.at), dur: 0.4 }); S.items.push(bi2); S.cue(t + (s.at == null ? capDur : s.at), 'blip', 0.7);
          bub.style.top = (s.y - bub.offsetHeight) + 'px';
          sayEnd = Math.max(sayEnd, (s.at == null ? capDur : s.at) + tx.dur + 0.2); if (s.at == null) capDur += tx.dur + 0.2;
        });
      }
      (b.sfx || []).forEach((s) => S.cue(t + s[1], s[0], s[2] == null ? 1 : s[2]));
      const dur = Math.max(b.dur || 0, capDur + 0.9, sayEnd + 0.8, 2.2);
      beats.push({ t0: t, t1: t + dur, g, items, cam: b.cam || { z0: 1.0, z1: 1.07 }, shake: b.shake });
      t += dur;
    });
    S.ups.push((lt) => {
      for (let i = 0; i < beats.length; i++) {
        const b = beats[i], on = lt >= b.t0 - 0.001 && lt < b.t1 + (i < beats.length - 1 ? 0 : 99);
        if (!on) { if (b.g.style.display !== 'none') b.g.style.display = 'none'; continue; }
        b.g.style.display = 'block';
        const p = clamp((lt - b.t0) / (b.t1 - b.t0)), f = clamp((lt - b.t0) / 0.3), o = i < beats.length - 1 ? clamp((b.t1 - lt) / 0.2) : 1;
        b.g.style.opacity = Math.min(f, o).toFixed(2);
        const z = b.cam.z0 + (b.cam.z1 - b.cam.z0) * E.inout(p), cx = (b.cam.x0 || 0) + ((b.cam.x1 || 0) - (b.cam.x0 || 0)) * p;
        let sx = 0, sy = 0; if (b.shake && lt > b.t0 + b.shake.at && lt < b.t0 + b.shake.at + b.shake.d) { sx = Math.sin(lt * 70) * b.shake.a; sy = Math.cos(lt * 53) * b.shake.a; }
        b.items.forEach((x) => { if (x.bg) x.el.style.transform = 'translate3d(' + (cx + sx).toFixed(1) + 'px,' + sy.toFixed(1) + 'px,0) scale(' + z.toFixed(4) + ')'; });
      }
    });
    S.cur = t; finish(S, 0.5);
  };
})();
