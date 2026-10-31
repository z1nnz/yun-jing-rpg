import { after, before, test } from 'node:test';
import assert from 'node:assert/strict';
import { randomUUID } from 'node:crypto';
import { mkdtemp, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { Database } from '../services/api/src/database';
import { Game, drawBirth } from '../services/api/src/game';
import { simulate, steamAt, Tea, teaContent, validateLog } from '../services/api/src/tea';
import { brewLog, heatTick, outcome, PLUM, teaTraceCases, WILD } from './tea-cases';

let directory: string, game: Game, now = 1_900_000_000_000;
before(async () => {
  directory = await mkdtemp(join(tmpdir(), 'yunjing-tea-'));
  game = new Game(new Database({ directory }), { now: () => now, speed: 3600, birth: () => drawBirth(now, 500000, 1) });
  await game.initialize();
});
after(async () => { await game.db.close(); await rm(directory, { recursive: true }); });
const act = (id: string, kind: string, extras: Record<string, unknown> = {}) => game.act(id, randomUUID(), { kind, ...extras });
const count = (snap: { player: { inventory: { item: string; quantity: number }[] } }, item: string) =>
  snap.player.inventory.filter(x => x.item === item).reduce((sum, x) => sum + x.quantity, 0);
/** Pour times (whole seconds) that land weak, good and bitter for one heating plan. */
function sweep(tea: Tea, scoops: number, fire: number, leavesAt: number) {
  const rows: { s: number; result: string }[] = [];
  for (let s = 1; s <= 120; s++) rows.push({ s, result: outcome(tea, scoops, brewLog(fire, leavesAt, s)).result });
  return rows;
}

test('log validation rejects malformed brews', () => {
  assert.equal(validateLog([]), 'LOG_SIZE');
  assert.equal(validateLog('x'), 'LOG_SIZE');
  assert.equal(validateLog([{ t: 0, k: 'fire', v: 2 }, { t: 5, k: 'leaves' }]), 'LOG_NO_POUR');
  assert.equal(validateLog([{ t: 0, k: 'fire', v: 2 }, { t: 5, k: 'pour' }]), 'LOG_POUR');
  assert.equal(validateLog([{ t: 0, k: 'leaves' }, { t: 1, k: 'leaves' }, { t: 2, k: 'pour' }]), 'LOG_DOUBLE_LEAVES');
  assert.equal(validateLog([{ t: 0, k: 'fire', v: 7 }, { t: 1, k: 'leaves' }, { t: 2, k: 'pour' }]), 'LOG_FIRE');
  assert.equal(validateLog([{ t: 5, k: 'leaves' }, { t: 2, k: 'pour' }]), 'LOG_TIME');
  assert.equal(validateLog([{ t: 0, k: 'leaves' }, { t: 1, k: 'pour' }, { t: 2, k: 'fire', v: 1 }]), 'LOG_POUR');
  assert.equal(validateLog([{ t: 0, k: 'stir' }, { t: 1, k: 'pour' }]), 'LOG_KIND');
  assert.equal(validateLog([{ t: 0, k: 'leaves' }, { t: teaContent.maxLogSeconds * 10 + 1, k: 'pour' }]), 'LOG_TIME');
  assert.equal(validateLog(brewLog(3, 200, 30)), null);
});

test('three fire levels heat at different speeds and the steam tells the stage', () => {
  const big = heatTick(3, 85), mid = heatTick(2, 85), small = heatTick(1, 85);
  assert.ok(big < mid && mid < small, `big ${big} < mid ${mid} < small ${small}`);
  assert.ok(small / 10 <= 120, 'small fire still boils inside two minutes');
  assert.equal(steamAt(30).id, 'still');
  assert.equal(steamAt(74).id, 'fisheye');
  assert.equal(steamAt(90).id, 'pearls');
  assert.equal(steamAt(100).id, 'roaring');
  // Deterministic replay: same log, same numbers.
  assert.deepEqual(simulate(brewLog(2, mid, 30), WILD, 3), simulate(brewLog(2, mid, 30), WILD, 3));
});

test('pouring too early is weak, on time is good, too late is bitter', () => {
  for (const [tea, temp] of [[WILD, 90], [PLUM, 78]] as const) {
    const leavesAt = heatTick(2, temp);
    const rows = sweep(tea, tea.idealScoops, 2, leavesAt);
    const firstGood = rows.find(r => r.result === 'good'), firstBitter = rows.find(r => r.result === 'bitter');
    assert.equal(rows[0].result, 'weak', tea.label);
    assert.ok(firstGood && firstBitter && firstGood.s < firstBitter.s, `${tea.label}: weak → good → bitter`);
    const goodSpan = rows.filter(r => r.result === 'good').length;
    assert.ok(goodSpan >= 8, `${tea.label} good window ${goodSpan}s is wide enough to be relaxing`);
    // Results only ever move weak → good → bitter as the pour gets later.
    const order = rows.map(r => ['weak', 'good', 'bitter'].indexOf(r.result));
    assert.deepEqual(order, [...order].sort((a, b) => a - b));
    const early = outcome(tea, tea.idealScoops, brewLog(2, leavesAt, 1));
    assert.deepEqual(early.reasons, [teaContent.advice.early]);
    const late = outcome(tea, tea.idealScoops, brewLog(2, leavesAt, 120));
    assert.deepEqual(late.reasons, [teaContent.advice.late]);
    const good = outcome(tea, tea.idealScoops, brewLog(2, leavesAt, firstGood!.s + Math.floor(goodSpan / 2)));
    assert.equal(good.result, 'good'); assert.ok(good.score >= 85, `centre of window scores ${good.score}`);
    assert.deepEqual(good.reasons, []);
  }
});

test('water temperature and dose shift the result with the right advice', () => {
  // Plum blossom in rolling boil is scorched: a steep that is good at fish-eye turns bitter.
  const fisheye = heatTick(3, 78), roaring = heatTick(3, 99);
  const rows = sweep(PLUM, 2, 3, fisheye); const s = rows.find(r => r.result === 'good')!.s + 2;
  assert.equal(outcome(PLUM, 2, brewLog(3, fisheye, s)).result, 'good');
  const hot = outcome(PLUM, 2, brewLog(3, roaring, s));
  assert.equal(hot.result, 'bitter'); assert.ok(hot.reasons.includes(teaContent.advice.hot));
  // Cold water never opens the leaves, however long they sit.
  const cold = outcome(WILD, 3, brewLog(1, heatTick(1, 40), 200));
  assert.equal(cold.result, 'weak'); assert.ok(cold.reasons.includes(teaContent.advice.cold));
  // Same timing, wrong dose.
  const leavesAt = heatTick(2, 90); const mid = sweep(WILD, 3, 2, leavesAt).filter(r => r.result === 'good');
  const at = mid[Math.floor(mid.length / 2)].s;
  const heavy = outcome(WILD, 5, brewLog(2, leavesAt, at)), light = outcome(WILD, 1, brewLog(2, leavesAt, at));
  assert.equal(heavy.result, 'bitter'); assert.ok(heavy.reasons.includes(teaContent.advice.heavy));
  assert.equal(light.result, 'weak'); assert.ok(light.reasons.includes(teaContent.advice.light));
});

test('lesson, brewing, abandoning and the rest bonus on the server', async () => {
  const id = await game.playerFor(randomUUID(), 'tea-player');
  await assert.rejects(act(id, 'tea-begin', { tea: WILD.id, scoops: 3 }), (e: any) => e.code === 'TEA_NOT_TAUGHT');
  let snap = await act(id, 'tea-lesson');
  assert.equal(snap.tea!.taught, true);
  assert.equal(count(snap, WILD.id), 4); assert.equal(count(snap, PLUM.id), 4);
  await assert.rejects(act(id, 'tea-lesson'), (e: any) => e.code === 'ALREADY_TAUGHT');
  await assert.rejects(act(id, 'tea-begin', { tea: 'pu-erh', scoops: 2 }), (e: any) => e.code === 'INVALID_TEA');
  await assert.rejects(act(id, 'tea-begin', { tea: WILD.id, scoops: 6 }), (e: any) => e.code === 'INVALID_INPUT' || e.code === 'INVALID_NUMBER' || e.status === 400);

  // Abandon before the leaves go in: they come back.
  snap = await act(id, 'tea-begin', { tea: WILD.id, scoops: 3 });
  assert.equal(count(snap, WILD.id), 1); assert.equal(snap.tea!.session!.scoops, 3);
  await assert.rejects(act(id, 'tea-begin', { tea: PLUM.id, scoops: 2 }), (e: any) => e.code === 'TEA_BUSY');
  snap = await act(id, 'tea-abandon');
  assert.equal(count(snap, WILD.id), 4); assert.equal(snap.tea!.session, null);

  // A good pot of wild tea.
  const leavesAt = heatTick(2, 90); const good = sweep(WILD, 3, 2, leavesAt).filter(r => r.result === 'good');
  const log = brewLog(2, leavesAt, good[Math.floor(good.length / 2)].s);
  await act(id, 'tea-begin', { tea: WILD.id, scoops: 3 });
  await assert.rejects(act(id, 'tea-finish', { log: [{ t: 0, k: 'pour' }] }), (e: any) => e.code === 'INVALID_LOG');
  now += 120_000;
  snap = await act(id, 'tea-finish', { log });
  assert.equal(snap.tea!.last!.result, 'good'); assert.equal(snap.tea!.last!.label, '好');
  assert.equal(snap.tea!.restBonus!.multiplier, 1.25);
  assert.equal(snap.tea!.teas.find(t => t.id === WILD.id)!.best, snap.tea!.last!.score);
  assert.equal(count(snap, WILD.id), 1); assert.equal(snap.tea!.session, null);
  assert.ok(snap.player.milestones.includes(`tea:good:${WILD.id}`));

  // A bitter pot is still drunk: it is recorded with advice and replaces the bonus, nothing is lost.
  await act(id, 'tea-begin', { tea: PLUM.id, scoops: 2 });
  now += 120_000;
  snap = await act(id, 'tea-finish', { log: brewLog(3, heatTick(3, 99), 90) });
  assert.equal(snap.tea!.last!.result, 'bitter'); assert.ok(snap.tea!.last!.reasons.length > 0);
  assert.equal(snap.tea!.restBonus!.multiplier, 1.0); assert.equal(snap.tea!.brews, 2);
  assert.equal(snap.tea!.teas.find(t => t.id === PLUM.id)!.best, null);
  await assert.rejects(act(id, 'tea-finish', { log }), (e: any) => e.code === 'NO_TEA');
  // The rest bonus expires after restBonusMinutes of game time.
  now += teaContent.restBonusMinutes * 60_000 / 3600 + 1;
  snap = await act(id, 'tea-begin', { tea: PLUM.id, scoops: 1 });
  assert.equal(snap.tea!.restBonus, null);
});

test('the replay fixture Unity checks TeaSim.cs against is current and covers every result', async () => {
  const fixture = JSON.parse(await readFile(join(__dirname, '..', '..', 'tests', 'fixtures', 'tea-trace.json'), 'utf8'));
  assert.deepEqual(fixture.cases, teaTraceCases(), 'run: npm run build && node dist/tools/tea-fixture.js');
  const results = new Set(fixture.cases.map((c: { result: string }) => c.result));
  assert.deepEqual([...results].sort(), ['bitter', 'good', 'weak']);
});

test('the C# port carries the same constants', async () => {
  const cs = await readFile(join(__dirname, '..', '..', 'apps', 'game', 'Assets', 'YunJing', 'Runtime', 'Tea', 'TeaSim.cs'), 'utf8');
  const c = teaContent, x = c.extraction;
  const expected: Record<string, number> = {
    step: c.step, ambient: c.ambient, boil: c.boil, cooling: c.cooling, steepCooling: c.steepCooling, base_: x.base, perDegree: x.perDegree,
    minFactor: x.minFactor, coldBelow: x.coldBelow, coldRate: x.coldRate, scorchPerDegree: x.scorchPerDegree,
    maxLogSeconds: c.maxLogSeconds, minScoops: c.minScoops, maxScoops: c.maxScoops, restBonusMinutes: c.restBonusMinutes,
  };
  for (const [key, value] of Object.entries(expected)) {
    const m = cs.match(new RegExp(`\\b${key} = ([\\d.]+)`));
    assert.ok(m, `TeaSim.cs defines ${key}`); assert.equal(Number(m![1]), value, `TeaSim.cs ${key}`);
  }
  assert.deepEqual(cs.match(/fireHeat = \{([^}]*)\}/)![1].split(',').map(Number), c.fires.map(f => f.heat), 'fire heat table');
  for (const t of c.teas) {
    assert.ok(cs.includes(`"${t.id}", "${t.label}", ${t.idealTemp[0]}, ${t.idealTemp[1]}, ${t.idealScoops}, ${t.strength.weakBelow}, ${t.strength.bitterAbove}, "${t.hint}"`), `${t.label} row`);
    assert.ok(cs.includes(`"${t.describe.weak}", "${t.describe.good}", "${t.describe.bitter}"`), `${t.label} descriptions`);
  }
  for (const s of c.steam) assert.ok(cs.includes(`("${s.id}", "${s.label}", ${s.from}, "${s.hint}")`), `steam ${s.id}`);
  for (const r of c.results) assert.equal(Number(cs.match(new RegExp(`\\("${r.id}", "${r.label}", ([\\d.]+)\\)`))?.[1]), r.restMultiplier, `result ${r.id}`);
  for (const [key, text] of Object.entries(c.advice)) assert.ok(cs.includes(`"${text}"`), `advice ${key}`);
});
