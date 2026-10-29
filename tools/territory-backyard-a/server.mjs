import http from 'node:http';
import { readFile } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

// Local-only static server: loopback bind, GET/HEAD, fixed allowlist. No API, no persistence, no rewards.
const here = path.dirname(fileURLToPath(import.meta.url));
const repo = path.resolve(here, '../..');
const KIT = ['TY01_SpiritField', 'TY02_QinglingGrass', 'TY03_ClearwaterLotus', 'TY04_Shoudeng', 'TY05_PracticeFloor', 'TY06_TrainingGear',
  'TY07_Fence', 'TY08_HerbRack', 'TY09_YardClutter', 'TY10_GravelPath'].map(k => `${k}_v001.glb`);
const routes = {
  '/assets/': { root: path.join(repo, 'art/exports/territory-backyard-a'), allow: KIT },
  '/tex/': { root: path.join(repo, 'art/exports/territory-backyard-a/textures'), allow: ['T_TY01_SpiritField_Wet_BaseColor.png', 'T_TY01_SpiritField_Wet_ORM.png'] },
  // the practice post is the author's delivered training-yard model (PR #38), reused read-only as the work package asks
  '/post/': { root: path.join(repo, 'art/exports/qingxi-training-yard-v1'), allow: ['agility-post.glb'] },
  '/vendor/': { root: path.join(here, 'node_modules/three'), allow: null },
};
const SHELL = ['index.html', 'app.mjs', 'yard.mjs', 'layout.mjs', 'style.css'];
const types = { '.html': 'text/html; charset=utf-8', '.mjs': 'text/javascript', '.js': 'text/javascript', '.css': 'text/css', '.glb': 'model/gltf-binary',
  '.png': 'image/png' };
const PORT = Number(process.env.PORT || 4183);

http.createServer(async (req, res) => {
  try {
    if (req.method !== 'GET' && req.method !== 'HEAD') { res.writeHead(405); return res.end(); }
    const pathname = decodeURIComponent(new URL(req.url, 'http://localhost').pathname);
    const prefix = Object.keys(routes).find(p => pathname.startsWith(p));
    const rel = prefix ? pathname.slice(prefix.length) : pathname === '/' ? 'index.html' : pathname.slice(1);
    const root = prefix ? routes[prefix].root : here;
    const file = path.resolve(root, rel);
    const ok = prefix ? (routes[prefix].allow ? routes[prefix].allow.includes(rel) : /^(build|examples\/jsm)\//.test(rel)) : SHELL.includes(rel);
    if (!file.startsWith(root + path.sep) || !ok) { res.writeHead(403); return res.end(); }
    const data = await readFile(file);
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream', 'Cache-Control': 'no-store' });
    res.end(req.method === 'HEAD' ? undefined : data);
  } catch { res.writeHead(404); res.end('Not found'); }
}).listen(PORT, '127.0.0.1', () => console.log(`Territory backyard: http://127.0.0.1:${PORT} (local demo; no rewards)`));
