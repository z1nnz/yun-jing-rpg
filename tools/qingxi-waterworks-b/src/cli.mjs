// Rules bridge for the Blender play scene: one JSON request on stdin, one JSON reply on stdout.
//   { "state": <game state or null>, "action": { "op": "place", "x": 3, "y": 1, "type": "worn", "rot": 0 } }
//   -> { "state": ..., "res": <the rule call's result>, "view": { sim, check, quote } }
// The Blender side keeps no rules of its own; every edit goes through waterworks-core.mjs, same as the tests.
import { newGame, place, rotate, remove, toggleGate, setDirection, undo, redo, simulate, check, quote, finish, retry,
  requestIdFor } from './waterworks-core.mjs';
import { FIXTURES } from './fixtures.mjs';
import { siteTables } from './tables.mjs';

const OPS = {
  new: (_, a) => { const f = FIXTURES[a.fixture] ?? FIXTURES.all; return [newGame(f.observationIds, a.sessionId ?? 'blender'), { ok: true, fixture: f.id }]; },
  place: (s, a) => [s, place(s, a.x, a.y, a.type, a.rot ?? 0)],
  rotate: (s, a) => [s, rotate(s, a.x, a.y)],
  remove: (s, a) => [s, remove(s, a.x, a.y)],
  gate: (s, a) => [s, toggleGate(s, a.x, a.y)],
  direction: (s, a) => [s, setDirection(s, a.dir)],
  undo: s => [s, undo(s)],
  redo: s => [s, redo(s)],
  finish: (s, a) => [s, finish(s, a.requestId ?? requestIdFor(s))],
  retry: s => [s, retry(s)],
  view: s => [s, { ok: true }],
  // static tables the scene needs to draw the board and labels
  site: s => [s, { ok: true, site: siteTables() }],
};

let raw = ''; for await (const c of process.stdin) raw += c;
const { state, action } = JSON.parse(raw || '{}');
const op = OPS[action?.op];
if (!op) { process.stdout.write(JSON.stringify({ error: `unknown op ${action?.op}` })); process.exit(2); }
const [s, res] = op(state ?? newGame(FIXTURES.all.observationIds, 'blender'), action);
const view = { sim: simulate(s), check: check(s), quote: quote(s), requestId: requestIdFor(s) };
process.stdout.write(JSON.stringify({ state: s, res, view }));
