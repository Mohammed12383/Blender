// Records the director's tour frame by frame as JPEGs (encode afterwards with ffmpeg).
// node record.cjs <outdir> [maxFrames] [fps]
// Resumable: if <outdir>/frames already holds frames, the tour is fast-forwarded (simulated, not drawn) to that point.
const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const out = process.argv[2], maxFrames = +(process.argv[3] || 1e9), fps = +(process.argv[4] || 24);
  const dir = path.join(out, 'frames');
  fs.mkdirSync(dir, { recursive: true });
  const have = fs.readdirSync(dir).filter((f) => /^f\d+\.jpg$/.test(f) && fs.statSync(path.join(dir, f)).size > 1000).length;
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 960, height: 540 } });
  const errors = [];
  page.on('console', (m) => { if (m.type() === 'error') errors.push(m.text()); });
  page.on('pageerror', (e) => errors.push('pageerror ' + e.message));
  await page.goto('http://127.0.0.1:8765/game/index.html?role=weapons_officer&capture=1');
  await page.waitForFunction(() => window.__game && document.getElementById('menu').classList.contains('hidden'), null, { timeout: 300000 });
  await page.evaluate((f) => { window.__FPS = f; }, fps);
  await page.addScriptTag({ content: fs.readFileSync(path.join(__dirname, 'director.js'), 'utf8') });
  const total = await page.evaluate(() => window.__director.total);
  console.log('tour length', total.toFixed(1), 's =', Math.ceil(total * fps), 'frames; already have', have);
  let f = 0;
  if (have > 0) {
    // fast-forward: run the script without drawing, a frame per evaluate so the page's own events still fire between frames
    await page.evaluate(() => { window.__noRender = true; });
    for (; f < have; f++) await page.evaluate(() => window.__director.frame());
    await page.evaluate(() => { window.__noRender = false; });
    console.log('fast-forwarded to frame', f);
  }
  const t0 = Date.now(); let n = 0;
  for (; f < maxFrames; f++, n++) {
    const r = await page.evaluate(() => window.__director.frame());
    if (r.done) { console.log('DONE'); break; }
    await page.screenshot({ path: path.join(dir, `f${String(f).padStart(5, '0')}.jpg`), type: 'jpeg', quality: 90 });
    if (f % 100 === 0) console.log(`frame ${f} shot ${r.shot} ${((Date.now() - t0) / (n + 1)).toFixed(0)} ms/frame`);
  }
  console.log('frames', f, 'errors:', errors.length ? [...new Set(errors)].slice(0, 10).join('\n') : 'none');
  await browser.close();
})();
