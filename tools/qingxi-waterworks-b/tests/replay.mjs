// Replays tests/scenarios.json through the JS core and records a client-neutral projection of every step.
// The same projection is computed by the Unity port (unity/Assets/Waterworks/Tests) and compared with golden.json.
import { readFileSync } from 'node:fs';
import { FIXTURES } from '../src/fixtures.mjs';
import { newGame, place, rotate, remove, toggleGate, setDirection, undo, redo, simulate, check, quote, finish, retry, requestIdFor }
  from '../src/waterworks-core.mjs';

export const SCENARIOS = JSON.parse(readFileSync(new URL('./scenarios.json', import.meta.url), 'utf8')).scenarios;

const DO = {
  place: (s, a) => place(s, a.x, a.y, a.type, a.rot ?? 0), rotate: (s, a) => rotate(s, a.x, a.y), remove: (s, a) => remove(s, a.x, a.y),
  gate: (s, a) => toggleGate(s, a.x, a.y), direction: (s, a) => setDirection(s, a.dir), undo: s => undo(s), redo: s => redo(s),
  finish: s => finish(s), retry: s => retry(s),
};

const issue = i => ({ code: i.code, at: i.at ?? null, side: i.side ?? null, message: i.message });
const receipt = r => r && ({ requestId: r.requestId, attempt: r.attempt, outcomeId: r.outcomeId, spent: r.materials.spent, result: r.result,
  surprises: r.surprises, plan: r.plan });

export function project(s, res) {
  const sim = simulate(s); const c = check(s); const q = quote(s);
  return {
    res: { ok: res.ok, code: res.code ?? null, message: res.message ?? null, open: res.open ?? null, replay: res.replay ?? null,
      receipt: receipt(res.receipt) ?? null, issues: (res.issues ?? []).map(issue) },
    sim: { fields: sim.fields, creek: sim.creek, supply: sim.supply, nursery: sim.nursery, wet: sim.wet, risks: sim.risks,
      issues: sim.issues.map(issue), leaks: sim.leaks.map(l => ({ at: l.at, q: l.q, why: l.why, side: l.side ?? null })) },
    check: c.issues.map(i => i.code), need: q.need, short: q.short, stock: { ...s.stock }, requestId: requestIdFor(s),
    finished: s.finished, direction: s.direction,
    pieces: Object.entries(s.pieces).map(([k, p]) => ({ cell: k, type: p.type, rot: p.rot, seg: p.seg, open: p.open ?? null })),
  };
}

export function replay(sc) {
  const s = newGame(FIXTURES[sc.fixture].observationIds, sc.id); const out = [project(s, { ok: true })];
  for (const a of sc.steps) out.push(project(s, DO[a.op](s, a)));
  return out;
}
