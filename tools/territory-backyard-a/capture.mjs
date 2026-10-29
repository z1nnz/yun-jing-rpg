/**
 * Play the backyard demo in a real Chromium with real key input and save screenshots (and optionally a short video).
 *   node capture.mjs --modules <dir with playwright-core> --chrome <chrome.exe> [--url http://127.0.0.1:4183] [--out <dir>] [--video <dir>]
 * playwright-core is not a dependency of the demo; install it outside the repo.
 */
import { createRequire } from 'node:module';
import path from 'node:path';
import { mkdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const require = createRequire(path.join(arg('--modules', process.cwd()), 'x.js'));
const { chromium } = require('playwright-core');
const here = path.dirname(fileURLToPath(import.meta.url));
const URL_ = arg('--url', 'http://127.0.0.1:4183');
const OUT = path.resolve(arg('--out', path.join(here, '../../art/previews/territory-backyard-a/demo')));
const VIDEO = arg('--video', null);
mkdirSync(OUT, { recursive: true });
const wait = ms => new Promise(r => setTimeout(r, ms));
const browser = await chromium.launch({ executablePath: arg('--chrome'), args: ['--use-angle=d3d11', '--enable-gpu', '--ignore-gpu-blocklist'] });

async function open(viewport, mobile = false) {
  const ctx = await browser.newContext({ viewport, deviceScaleFactor: 1, hasTouch: mobile, isMobile: mobile,
    ...(VIDEO && !mobile ? { recordVideo: { dir: VIDEO, size: viewport } } : {}) });
  const p = await ctx.newPage(); const errors = [];
  p.on('pageerror', e => errors.push(String(e))); p.on('console', m => m.type() === 'error' && errors.push(m.text()));
  await p.goto(URL_);
  await p.waitForFunction(() => globalThis.__yard && document.getElementById('loading').hidden, null, { timeout: 120000 });
  await wait(1000);
  return { p, ctx, errors };
}
const shot = async (p, n) => { await p.screenshot({ path: path.join(OUT, n) }); console.log('SHOT', n); };
const st = p => p.evaluate(() => __yard.state());
async function eyeShot(p, n) { await p.evaluate(() => __yard.eye(true)); await wait(400); await shot(p, n); await p.evaluate(() => __yard.eye(false)); }

/** Walk with the real W key toward (x, z), steering the camera yaw toward the goal each frame. */
async function walkTo(p, x, z, tol = 0.25) {
  await p.keyboard.down('KeyW');
  let left = Infinity;
  for (let k = 0; k < 700; k++) {
    const pl = (await st(p)).player, dx = x - pl.x, dz = z - pl.z;
    left = Math.hypot(dx, dz);
    if (left < tol) break;
    await p.evaluate(([dx, dz]) => __yard.look(Math.atan2(-dx, -dz) * 180 / Math.PI), [dx, dz]);
    await wait(25);
  }
  await p.keyboard.up('KeyW');
  console.log('WALK', x, z, 'left', left.toFixed(2));
  return left;
}
async function face(p, x, z, pitch = 0.5) {
  await p.evaluate(([x, z, pitch]) => { const pl = __yard.state().player; __yard.look(Math.atan2(-(x - pl.x), -(z - pl.z)) * 180 / Math.PI, pitch); }, [x, z, pitch]);
  await wait(300);
}
/** Hold F (fast-forward) until field i reaches `stage` (0..3). */
async function growTo(p, i, stage) {
  await p.keyboard.down('KeyF');
  for (let k = 0; k < 400; k++) { if ((await st(p)).fields[i].stage >= stage) break; await wait(40); }
  await p.keyboard.up('KeyF');
  await wait(200);
}

const result = {};
{
  const { p, ctx, errors } = await open({ width: 1280, height: 720 });
  await shot(p, '00-back-door-1280x720.png');
  await eyeShot(p, '01-eye-1p7m-from-back-door-1280x720.png');
  // left field: qingling grass through its four stages
  await walkTo(p, -1.25, -6.7);
  await face(p, -2.8, -6.7, 0.75);
  await p.keyboard.press('Digit1');
  await wait(300);
  for (const [stage, n] of [[0, '02-qingling-sprout'], [1, '03-qingling-young'], [2, '04-qingling-grown'], [3, '05-qingling-mature']]) {
    await growTo(p, 0, stage);
    await shot(p, `${n}-1280x720.png`);
  }
  const before = (await st(p)).level;
  await p.keyboard.press('KeyE');
  await wait(200);
  await p.keyboard.press('KeyE');                 // a second press must not count twice
  await wait(300);
  const s1 = await st(p);
  result.harvest1 = { before, after: s1.level, harvests: s1.harvests, rackFull: s1.rackFull, field: s1.fields[0] };
  await shot(p, '06-harvested-1280x720.png');
  // right field: clearwater lotus (flooded bed)
  await walkTo(p, 1.25, -6.7);
  await face(p, 2.8, -6.7, 0.75);
  await p.keyboard.press('Digit2');
  for (const [stage, n] of [[0, '07-lotus-floating'], [1, '08-lotus-standing'], [2, '09-lotus-bud'], [3, '10-lotus-bloom']]) {
    await growTo(p, 1, stage);
    await shot(p, `${n}-1280x720.png`);
  }
  await p.keyboard.press('KeyE');
  await wait(300);
  // two more harvests so the lantern reaches level 4, then one more (it stays at 4)
  for (const [i, key] of [[1, 'Digit2'], [1, 'Digit2'], [1, 'Digit2']]) {
    await p.keyboard.press(key); await growTo(p, i, 3); await p.keyboard.press('KeyE'); await wait(200);
  }
  const s2 = await st(p);
  result.lantern = { harvests: s2.harvests, level: s2.level };
  // the rack by the right fence shows the drying herbs
  await walkTo(p, 4.2, -4.0);
  await face(p, 5.4, -4.0, 0.35);
  await shot(p, '11-rack-full-1280x720.png');
  // the lantern in the corner, by day and at dusk
  await walkTo(p, -3.6, -9.0);
  await face(p, -5.2, -12.0, 0.25);
  await shot(p, '12-lantern-day-1280x720.png');
  await p.keyboard.press('KeyN');
  await wait(600);
  await shot(p, '13-lantern-dusk-1280x720.png');
  await p.keyboard.press('KeyN');
  // the gate: open, walk through, try closing while standing in it (refused), step back in, close
  await walkTo(p, 3.5, -11.6);
  await face(p, 3.5, -13.0, 0.35);
  const g0 = (await st(p)).gateOpen;
  await p.keyboard.press('KeyE');
  await wait(900);
  await shot(p, '14-gate-open-1280x720.png');
  await walkTo(p, 3.5, -12.5, 0.2);
  await p.keyboard.press('KeyE');
  await wait(300);
  const inSwing = (await st(p)).gateOpen;
  const outside = await walkTo(p, 3.5, -13.6);
  const back = await walkTo(p, 3.5, -11.35, 0.1);                     // clear of the leaf's swing (1 m), still within reach (1.3 m)
  await face(p, 3.5, -13.0, 0.35);
  await p.keyboard.press('KeyE');
  await wait(900);
  const closed = !(await st(p)).gateOpen;
  const blockedTry = await walkTo(p, 3.5, -13.6);
  result.gate = { startedOpen: g0, stayedOpenWhenPlayerInSwing: inSwing, reachedOutside: outside < 0.3, cameBack: back < 0.3, closed,
    closedGateBlocks: blockedTry > 0.5 };
  await shot(p, '15-gate-closed-1280x720.png');
  // a look back at the house from the end of the yard, 1.7 m eye height
  await walkTo(p, 0.9, -11.7);
  await face(p, 0, -3.0, 0.1);
  await eyeShot(p, '16-eye-1p7m-from-yard-end-1280x720.png');
  result.errors = errors;
  console.log('RESULT', JSON.stringify(result));
  await ctx.close();
}
{
  const { p, ctx, errors } = await open({ width: 844, height: 390 }, true);
  await shot(p, '30-mobile-landscape-844x390.png');
  console.log('MOBILE errors', JSON.stringify(errors));
  await ctx.close();
}
await browser.close();
