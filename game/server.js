// Static file server for the game + a tiny WebSocket relay for 4-player co-op.
// Run from the repository root:  node game/server.js   then open http://localhost:8080/game/
import { createServer } from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { extname, join, normalize, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { WebSocketServer } from 'ws';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const PORT = +(process.env.PORT || 8080);
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.png': 'image/png', '.jpg': 'image/jpeg',
  '.glb': 'model/gltf-binary', '.json': 'application/json' };

const server = createServer(async (req, res) => {
  try {
    let p = normalize(decodeURIComponent(new URL(req.url, 'http://x').pathname)).replace(/^([/\\])+/, '');
    if (p.includes('..')) throw new Error('bad path');
    let file = join(ROOT, p);
    if ((await stat(file)).isDirectory()) file = join(file, 'index.html');
    const data = await readFile(file);
    res.writeHead(200, { 'Content-Type': TYPES[extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-cache' });
    res.end(data);
  } catch {
    res.writeHead(404); res.end('not found');
  }
});

const wss = new WebSocketServer({ server });
const players = new Map();
let nextId = 1, hostId = null;
const broadcast = (o, except) => { const s = JSON.stringify(o); for (const c of wss.clients) if (c !== except && c.readyState === 1) c.send(s); };
const roster = () => broadcast({ t: 'players', players: [...players.values()].map(({ ws, ...p }) => p) });

wss.on('connection', (ws) => {
  const id = nextId++;
  ws.on('message', (raw) => {
    let m; try { m = JSON.parse(raw); } catch { return; }
    if (m.t === 'hello') {
      if (players.size >= 4) { ws.send(JSON.stringify({ t: 'full' })); ws.close(); return; }
      if (!hostId) hostId = id;
      players.set(id, { id, ws, name: String(m.name).slice(0, 20), role: m.role, station: null });
      ws.send(JSON.stringify({ t: 'welcome', id, host: hostId === id }));
      roster();
      return;
    }
    const p = players.get(id); if (!p) return;
    if (m.t === 'claim') { p.station = m.station; roster(); return; }
    if (m.t === 'pos') { Object.assign(p, { x: m.x, z: m.z, yaw: m.yaw, station: m.station, carry: m.carry }); broadcast({ ...m, id }, ws); return; }
    if (m.t === 'state' && id === hostId) { broadcast(m, ws); return; }
    if ((m.t === 'ctl' || m.t === 'act') && id !== hostId) { const h = players.get(hostId); if (h) h.ws.send(JSON.stringify(m)); }
  });
  ws.on('close', () => {
    players.delete(id);
    if (hostId === id) { hostId = players.keys().next().value ?? null; if (hostId) broadcast({ t: 'host', id: hostId }); }
    roster();
  });
});

server.listen(PORT, () => console.log(`Deepwater Crew: http://localhost:${PORT}/game/  (co-op relay on ws://localhost:${PORT})`));
