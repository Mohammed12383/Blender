// Renders one frame from the middle of every shot of the director's tour (fast-forwarding in between), for checking.
// node sample.cjs <outdir> [fps] [frac]
const { chromium } = require('playwright'); const fs = require('fs'); const path = require('path');
(async () => {
  const out = process.argv[2], fps = +(process.argv[3] || 20), frac = +(process.argv[4] || 0.6);
  fs.mkdirSync(out, { recursive: true });
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror ' + e.message));
  await page.goto('http://127.0.0.1:8765/game/index.html?role=weapons_officer&capture=1');
  await page.waitForFunction(() => window.__game && document.getElementById('menu').classList.contains('hidden'), null, { timeout: 300000 });
  await page.evaluate((f) => { window.__FPS = f; }, fps);
  await page.addScriptTag({ content: fs.readFileSync(path.join(__dirname, 'director.js'), 'utf8') });
  const durs = await page.evaluate(() => window.__director.durs);
  let t0 = 0; const starts = durs.map((d) => { const s = t0; t0 += d; return s; });
  let targets = durs.map((d, i) => Math.round((starts[i] + d * frac) * fps));
  if (process.argv[5]) targets = process.argv[5].split(',').map((p) => { const [i, fr] = p.split(':').map(Number); return Math.round((starts[i] + durs[i] * fr) * fps); });
  let f = 0;
  for (let k = 0; k < targets.length; k++) {
    const want = targets[k];
    await page.evaluate(() => { window.__noRender = true; });
    for (; f < want - 3; f++) await page.evaluate(() => window.__director.frame());
    await page.evaluate(() => { window.__noRender = false; });
    for (; f <= want; f++) await page.evaluate(() => window.__director.frame());
    await page.screenshot({ path: path.join(out, `s${String(k).padStart(2, '0')}.jpg`), type: 'jpeg', quality: 85 });
    console.log('shot', k, 'frame', want);
  }
  console.log('errors:', errors.length ? [...new Set(errors)].slice(0, 10).join('\n') : 'none');
  await browser.close();
})();
