// node --test tools/qingxi-waterworks-b/tests/*.test.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { FIXTURES } from '../src/fixtures.mjs';
import { newGame, place, rotate, remove, toggleGate, setDirection, undo, redo, simulate, check, finish, retry, quote, requestIdFor, STOCK }
  from '../src/waterworks-core.mjs';

const ALL = FIXTURES.all.observationIds;
const build = (s, cells) => { for (const [x, y, t, r] of cells) assert.ok(place(s, x, y, t, r).ok, `place ${t} ${x},${y}`); return s; };
// three reference plans (see README: 直通村田 / 繞過育幼區 / 先清淤再暫時導流)
const DIRECT = [[3, 1, 'worn', 0], [3, 2, 'worn', 0], [3, 3, 'worn', 0], [3, 4, 'worn', 0], [3, 5, 'apron', 0]];
const DETOUR = [[3, 1, 'bendL', 0], [2, 1, 'straight', 1], [1, 1, 'bendR', 3], [1, 2, 'straight', 0], [1, 3, 'straight', 0], [1, 4, 'straight', 0], [1, 5, 'apron', 0]];
const DIVERT = [[3, 1, 'tee', 1], [2, 1, 'straight', 1], [1, 1, 'straight', 1], [0, 1, 'apron', 3],
  [3, 2, 'worn', 0], [3, 3, 'worn', 0], [3, 4, 'worn', 0], [3, 5, 'apron', 0]];
const plan = (cells, dir, ids = ALL) => { const s = build(newGame(ids, 't'), cells); assert.ok(setDirection(s, dir).ok); return s; };

test('three plans complete with different water, field supply and nursery impact', () => {
  const r = {};
  for (const [name, cells, dir] of [['direct', DIRECT, 'restore_channel'], ['detour', DETOUR, 'protect_nursery'], ['divert', DIVERT, 'clear_silt']]) {
    const s = plan(cells, dir); const c = check(s); assert.deepEqual(c.issues, [], name);
    const f = finish(s); assert.ok(f.ok, name); r[name] = f.receipt;
  }
  assert.deepEqual(Object.values(r).map(x => x.outcomeId), ['channel_restored_direct', 'nursery_protected_detour', 'silt_cleared_temporary_diversion']);
  const sup = Object.fromEntries(Object.entries(r).map(([k, v]) => [k, v.result.fieldsSupplyPct]));
  assert.ok(sup.direct > sup.detour && sup.detour > sup.divert, JSON.stringify(sup));
  assert.equal(r.direct.result.nursery, '受驚擾'); assert.equal(r.detour.result.nursery, '安全'); assert.equal(r.divert.result.nursery, '輕擾');
  assert.ok(r.divert.result.creekFlow > 0 && r.direct.result.creekFlow === 0);
  assert.ok(r.detour.result.leaks.some(l => l.why === 'seep'), 'detour loses water on the sandy slope');
});

test('a mis-connection names the port that is broken and how to fix it', () => {
  const s = build(newGame(ALL, 't'), [[3, 1, 'worn', 0], [3, 2, 'worn', 1]]);
  const m = simulate(s).issues.find(i => i.code === 'PORT_MISMATCH');
  assert.match(m.message, /S01 磨損直槽 的北接口（End_Back）對著 S02 磨損直槽 的側牆/);
  assert.match(m.message, /把 S02 轉向讓接口朝南/);
  assert.ok(rotate(s, 3, 2).ok);
  assert.equal(simulate(s).issues.find(i => i.code === 'PORT_MISMATCH'), undefined, 'rotating fixes it');
  const open = simulate(s).issues.find(i => i.code === 'OPEN_END');
  assert.match(open.message, /S02 磨損直槽 的北接口（End_Front）開著沒接東西/);
});

test('open ends, wrong terminals, closed gates and isolated pieces are explained', () => {
  const s = build(newGame(ALL, 't'), [[3, 1, 'straight', 0], [3, 2, 'gate', 0], [3, 3, 'straight', 0], [3, 4, 'straight', 0], [3, 5, 'straight', 0], [6, 0, 'straight', 0]]);
  const codes = simulate(s).issues.map(i => i.code);
  assert.ok(codes.includes('OPEN_END') && codes.includes('DRY'));
  assert.match(simulate(s).issues.find(i => i.code === 'OPEN_END').message, /直接沖進村田進水口會沖壞田埂/);
  assert.ok(remove(s, 6, 0).ok); assert.ok(place(s, 3, 5, 'apron', 0).ok);
  assert.ok(toggleGate(s, 3, 2).ok);
  assert.match(simulate(s).issues.find(i => i.code === 'GATE_CLOSED').message, /S02 閘板 關著/);
  assert.ok(toggleGate(s, 3, 2).ok); assert.ok(setDirection(s, 'restore_channel').ok);
  assert.deepEqual(check(s).issues, []);
  const a = build(newGame(ALL, 't'), [[3, 1, 'straight', 0], [3, 2, 'apron', 0]]);
  assert.match(simulate(a).issues[0].message, /S02 收尾溢流台 的出水口朝北，對著空地/);
});

test('undo and redo walk the edit history; finished plans are locked until retry', () => {
  const s = build(newGame(ALL, 't'), DIRECT);
  assert.ok(undo(s).ok); assert.equal(s.pieces['3,5'], undefined);
  assert.ok(redo(s).ok); assert.equal(s.pieces['3,5'].type, 'apron');
  assert.ok(rotate(s, 3, 4).ok); assert.ok(undo(s).ok); assert.equal(s.pieces['3,4'].rot, 0);
  assert.equal(redo(s).ok, true); assert.equal(undo(s).ok, true); assert.equal(redo(s).ok, true); assert.equal(redo(s).ok, false);
  undo(s); setDirection(s, 'restore_channel');
  assert.ok(finish(s).ok); assert.equal(place(s, 0, 0, 'straight', 0).code, 'FINISHED'); assert.equal(undo(s).code, 'FINISHED');
  retry(s); assert.equal(requestIdFor(s), 'ww-t-a2'); assert.ok(remove(s, 3, 5).ok);
});

test('pressing finish twice, or resending the same request, never spends materials twice', () => {
  const s = plan(DIRECT, 'restore_channel'); const need = quote(s).need;
  const a = finish(s); const b = finish(s); const c = finish(s, a.receipt.requestId);
  assert.equal(a.replay, false); assert.equal(b.replay, true); assert.equal(c.replay, true);
  assert.deepEqual(b.receipt, a.receipt);
  for (const [m, n] of Object.entries(need)) assert.equal(s.stock[m], STOCK[m] - n, m);
  const other = finish(s, 'ww-t-other');
  assert.equal(other.code, 'ALREADY_FINISHED'); assert.equal(s.stock.stone, STOCK.stone - need.stone);
  assert.equal(a.receipt.materials.source, 'local-display-stock');
});

test('missing clues still allow a try, but the screen states the unknown risk and the result can surprise', () => {
  const s = plan(DIRECT, 'clear_silt', FIXTURES.none.observationIds);
  const sim = simulate(s);
  assert.equal(sim.risks.length, 3); assert.match(sim.risks.join(), /可能會漏水/);
  assert.equal(sim.nursery.text, '安全', 'the den is not known yet');
  assert.ok(check(s).issues.some(i => i.code === 'NO_DIVERSION'));
  const t = plan(DIRECT, 'restore_channel', FIXTURES.one.observationIds);
  const f = finish(t); assert.ok(f.ok);
  assert.ok(f.receipt.surprises.length >= 1, 'silt and the den show up only on finishing');
  assert.equal(f.receipt.result.nursery, '受驚擾');
});

test('protecting the nursery forbids slots in and beside the den', () => {
  const s = newGame(ALL, 't'); setDirection(s, 'protect_nursery');
  assert.equal(place(s, 3, 3, 'straight', 0).code, 'NURSERY_FORBIDDEN');
  const t = build(newGame(ALL, 't'), DIRECT);
  assert.match(setDirection(t, 'protect_nursery').message, /先移走育幼區旁的 S03、S04/);
});

test('rocks and the source block slots; the source must be met by a port', () => {
  const s = newGame(ALL, 't');
  assert.equal(place(s, 5, 1, 'straight', 0).code, 'NO_SLOT');
  assert.equal(place(s, 3, 0, 'straight', 0).code, 'NO_SLOT');
  place(s, 3, 1, 'straight', 1);
  assert.match(simulate(s).issues[0].message, /水源 B01 的出水口（北，Out_Front）對著 S01 直槽 的側牆/);
});
