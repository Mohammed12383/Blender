// Usage: node render.cjs <lesson> [--out dir] [--workers 4] [--range a:b] [--chunk 20] [--q 88] [--shots t1,t2,...]
const { chromium } = require('playwright');
const http = require('http'), fs = require('fs'), path = require('path'), { spawn } = require('child_process');
const argv = process.argv.slice(2);
const lesson = argv[0];
const opt = (k, d) => { const i = argv.indexOf('--' + k); return i >= 0 ? argv[i + 1] : d; };
const ROOT = path.resolve(__dirname, '..');
const OUT = path.resolve(opt('out', path.join(ROOT, 'out', lesson)));
const WORKERS = +opt('workers', 4), CHUNK = +opt('chunk', 20), Q = +opt('q', 88), CRF = opt('crf', '22');
const mime = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json', '.png': 'image/png', '.jpg': 'image/jpeg', '.woff2': 'font/woff2' };
const server = http.createServer((req, res) => {
  const p = path.join(ROOT, decodeURIComponent(req.url.split('?')[0]));
  if (!p.startsWith(ROOT) || !fs.existsSync(p) || fs.statSync(p).isDirectory()) { res.writeHead(404); return res.end(); }
  res.writeHead(200, { 'Content-Type': mime[path.extname(p)] || 'application/octet-stream', 'Cache-Control': 'max-age=3600' });
  fs.createReadStream(p).pipe(res);
});
async function openPage(browser, port) {
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1 });
  const page = await ctx.newPage();
  page.on('pageerror', (e) => console.error('PAGEERROR', e.message));
  page.on('console', (m) => { if (m.type() === 'error') console.error('CONSOLE', m.text()); });
  await page.goto(`http://127.0.0.1:${port}/engine/index.html?lesson=${lesson}`);
  await page.waitForFunction(() => window.ENGINE && (window.ENGINE.ready || window.ENGINE.error), null, { timeout: 120000 });
  const err = await page.evaluate(() => window.ENGINE.error); if (err) throw new Error(err);
  return page;
}
(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  await new Promise((r) => server.listen(0, '127.0.0.1', r));
  const port = server.address().port;
  const browser = await chromium.launch({ args: ['--disable-gpu', '--force-device-scale-factor=1', '--font-render-hinting=none'] });
  const page0 = await openPage(browser, port);
  const info = await page0.evaluate(() => window.ENGINE.info);
  fs.writeFileSync(path.join(OUT, 'info.json'), JSON.stringify(info));
  console.log(`lesson ${lesson}: ${info.total.toFixed(1)} s, ${info.scenes.length} scenes, ${info.cues.length} cues`);
  const shots = opt('shots', null);
  if (shots) {
    for (const t of shots.split(',').map(Number)) { await page0.evaluate((t) => window.ENGINE.seek(t), t); await page0.screenshot({ path: path.join(OUT, `shot_${t.toFixed(1)}.png`) }); }
    await browser.close(); server.close(); return;
  }
  const fps = info.fps; let [a, b] = opt('range', `0:${info.total}`).split(':').map(Number);
  const tasks = []; for (let s = a, i = 0; s < b - 1e-6; s += CHUNK, i++) tasks.push({ i, s, e: Math.min(b, s + CHUNK) });
  const t0 = Date.now(); let done = 0, frames = 0;
  const pages = [page0]; for (let k = 1; k < WORKERS; k++) pages.push(await openPage(browser, port));
  const run = async (page) => {
    while (tasks.length) {
      const tk = tasks.shift(); const file = path.join(OUT, `chunk_${String(tk.i).padStart(4, '0')}.mp4`);
      if (fs.existsSync(file)) { done++; continue; }
      const tmp = file + '.part';
      const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', CRF, '-pix_fmt', 'yuv420p', '-threads', '1', '-f', 'mp4', tmp], { stdio: ['pipe', 'inherit', 'inherit'] });
      const n0 = Math.round(tk.s * fps), n1 = Math.round(tk.e * fps);
      for (let f = n0; f < n1; f++) {
        await page.evaluate((t) => window.ENGINE.seek(t), f / fps);
        const buf = await page.screenshot({ type: 'jpeg', quality: Q });
        if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
        frames++;
      }
      ff.stdin.end(); await new Promise((r) => ff.on('close', r)); fs.renameSync(tmp, file); done++;
      const el = (Date.now() - t0) / 1000; console.log(`chunk ${tk.i} ok  (${frames} frames, ${(frames / el).toFixed(1)} fps, ${el.toFixed(0)} s)`);
    }
  };
  await Promise.all(pages.map(run));
  await browser.close(); server.close();
  // concat
  const list = fs.readdirSync(OUT).filter((f) => /^chunk_\d+\.mp4$/.test(f)).sort().map((f) => `file '${path.join(OUT, f)}'`).join('\n');
  fs.writeFileSync(path.join(OUT, 'list.txt'), list);
  await new Promise((r) => spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'concat', '-safe', '0', '-i', path.join(OUT, 'list.txt'), '-c', 'copy', path.join(OUT, 'video_silent.mp4')], { stdio: 'inherit' }).on('close', r));
  console.log('done', path.join(OUT, 'video_silent.mp4'), ((Date.now() - t0) / 1000).toFixed(0) + 's');
})().catch((e) => { console.error(e); process.exit(1); });
