/**
 * Record one real-time playthrough (real keys, real Chromium) as WebM for the PR video: out of the back door, plant,
 * fast-forward, harvest both fields, then dusk and the lantern. Under a minute.
 *   node record.mjs --modules <dir with playwright-core> --chrome <chrome.exe> [--url http://127.0.0.1:4183] [--out <dir>]
 * Then encode to H.264 MP4 with Blender: art/source/territory-backyard-a/encode_video.py.
 */
import { createRequire } from 'node:module';
import path from 'node:path';
import { mkdirSync, renameSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const require = createRequire(path.join(arg('--modules', process.cwd()), 'x.js'));
const { chromium } = require('playwright-core');
const here = path.dirname(fileURLToPath(import.meta.url));
const URL_ = arg('--url', 'http://127.0.0.1:4183');
const OUT = path.resolve(arg('--out', path.join(here, '../../art/previews/territory-backyard-a/demo')));
mkdirSync(OUT, { recursive: true });
const wait = ms => new Promise(r => setTimeout(r, ms));
const browser = await chromium.launch({ executablePath: arg('--chrome'), args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });
const ctx = await browser.newContext({ viewport: { width: 1280, height: 720 }, recordVideo: { dir: OUT, size: { width: 1280, height: 720 } } });
const p = await ctx.newPage();
await p.goto(URL_);
await p.waitForFunction(() => globalThis.__yard && document.getElementById('loading').hidden, null, { timeout: 120000 });
await wait(1500);
const st = () => p.evaluate(() => __yard.state());

/** Walk there with W held, turning the view a little each frame (as a player dragging the mouse would). */
async function walkTo(x, z) {
  await p.keyboard.down('KeyW');
  for (let k = 0; k < 700; k++) {
    const pl = (await st()).player, dx = x - pl.x, dz = z - pl.z;
    if (Math.hypot(dx, dz) < 0.25) break;
    await p.evaluate(([dx, dz]) => { const want = Math.atan2(-dx, -dz) * 180 / Math.PI; __yard.look(want); }, [dx, dz]);
    await wait(25);
  }
  await p.keyboard.up('KeyW');
}
async function face(x, z, pitch) {
  await p.evaluate(([x, z, pitch]) => { const pl = __yard.state().player; __yard.look(Math.atan2(-(x - pl.x), -(z - pl.z)) * 180 / Math.PI, pitch); }, [x, z, pitch]);
}
async function grow(i) {
  await p.keyboard.down('KeyF');
  for (let k = 0; k < 400; k++) { if ((await st()).fields[i].stage >= 3) break; await wait(40); }
  await p.keyboard.up('KeyF');
}

await walkTo(-1.25, -6.7); await face(-2.8, -6.7, 0.7); await wait(500);
await p.keyboard.press('Digit1'); await wait(800);
await grow(0); await wait(900);
await p.keyboard.press('KeyE'); await wait(1200);
await walkTo(1.25, -6.7); await face(2.8, -6.7, 0.7); await wait(500);
await p.keyboard.press('Digit2'); await wait(800);
await grow(1); await wait(900);
await p.keyboard.press('KeyE'); await wait(1200);
await walkTo(4.2, -4.0); await face(5.4, -4.0, 0.35); await wait(1500);
await walkTo(-3.4, -9.2); await face(-5.2, -12.0, 0.25); await wait(1200);
await p.keyboard.press('KeyN'); await wait(3000);
const s = await st();
console.log('LEVEL', s.level, 'HARVESTS', s.harvests);
const video = p.video();
await ctx.close();
const src = await video.path();
renameSync(src, path.join(OUT, 'walkthrough.webm'));
console.log('VIDEO', path.join(OUT, 'walkthrough.webm'));
await browser.close();
