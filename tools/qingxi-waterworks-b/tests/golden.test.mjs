// The golden file and the Unity site export must match what the JS core says today, so the C# port is checked against
// current rules, not stale ones. Regenerate with: node tools/qingxi-waterworks-b/tests/make-golden.mjs
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { golden, GOLDEN_JSON, SITE_JSON } from './make-golden.mjs';
import { siteTables } from '../src/tables.mjs';

test('golden.json is current', () => {
  assert.deepEqual(JSON.parse(readFileSync(GOLDEN_JSON, 'utf8')), JSON.parse(JSON.stringify(golden())));
});

test('unity site export is current', () => {
  assert.deepEqual(JSON.parse(readFileSync(SITE_JSON, 'utf8')), JSON.parse(JSON.stringify(siteTables())));
});
