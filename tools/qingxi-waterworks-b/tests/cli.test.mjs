// The Blender scene talks to the rules only through src/cli.mjs; check that bridge end to end.
import test from 'node:test';
import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const CLI = fileURLToPath(new URL('../src/cli.mjs', import.meta.url));
const call = (state, action) => JSON.parse(execFileSync(process.execPath, [CLI], { input: JSON.stringify({ state, action }) }).toString());

test('cli: build the direct plan, finish twice, materials deducted once', () => {
  let r = call(null, { op: 'new', fixture: 'two', sessionId: 'cli' });
  assert.deepEqual(r.state.observationIds, ['cracked_sluice', 'silt_buildup']);
  assert.ok(r.view.sim.issues.some(i => i.code === 'SOURCE_OPEN'));
  for (const y of [1, 2, 3, 4]) r = call(r.state, { op: 'place', x: 3, y, type: 'worn' });
  r = call(r.state, { op: 'place', x: 3, y: 5, type: 'apron' });
  r = call(r.state, { op: 'direction', dir: 'restore_channel' });
  assert.ok(r.view.check.ok, JSON.stringify(r.view.check.issues));
  assert.ok(r.view.sim.risks.length, 'missed nursery clue shows as unknown risk');
  r = call(r.state, { op: 'finish' }); const first = r.res.receipt; const stock = r.state.stock;
  assert.equal(first.outcomeId, 'channel_restored_direct'); assert.equal(r.res.replay, false);
  r = call(r.state, { op: 'finish' });
  assert.equal(r.res.replay, true); assert.deepEqual(r.res.receipt, first); assert.deepEqual(r.state.stock, stock);
  r = call(r.state, { op: 'retry' }); assert.equal(r.view.requestId, 'ww-cli-a2');
});

test('cli: site tables and unknown op', () => {
  const r = call(null, { op: 'site' });
  assert.equal(r.res.site.W, 7); assert.equal(r.res.site.PIECES.gate.model, 'B05_SluiceGate');
  assert.throws(() => call(null, { op: 'nope' }));
});
