import { judge, simulate, Tea, TeaEvent, teaById, teaContent } from '../services/api/src/tea';

// Shared by tests/tea.test.ts and tools/tea-fixture.ts. The fixture is replayed by TeaRoomBuilder.VerifySim in Unity,
// so the C# port of the tea rules is checked against these exact numbers.
export const WILD = teaById('qingxi-wild-tea')!, PLUM = teaById('plum-blossom-tea')!;

/** First tick at which the kettle on `fire` reaches `target` degrees (same replay the server uses). */
export function heatTick(fire: number, target: number) {
  for (let t = 1; t < teaContent.maxLogSeconds * 10 - 1; t++) {
    const sim = simulate([{ t: 0, k: 'fire', v: fire }, { t, k: 'leaves' }, { t: t + 1, k: 'pour' }], WILD, 3);
    if (sim.brewTemp! >= target) return t;
  }
  throw new Error(`fire ${fire} never reaches ${target}`);
}
export const brewLog = (fire: number, leavesAt: number, steepSeconds: number): TeaEvent[] =>
  [{ t: 0, k: 'fire', v: fire }, { t: leavesAt, k: 'fire', v: 0 }, { t: leavesAt, k: 'leaves' }, { t: leavesAt + steepSeconds * 10, k: 'pour' }];
export const outcome = (tea: Tea, scoops: number, log: TeaEvent[]) => judge(simulate(log, tea, scoops), tea, scoops);

export function teaTraceCases() {
  const plans: [string, Tea, number, TeaEvent[]][] = [
    ['wild-medium-good', WILD, 3, brewLog(2, heatTick(2, 90), 33)],
    ['wild-early-weak', WILD, 3, brewLog(2, heatTick(2, 90), 6)],
    ['wild-late-bitter', WILD, 3, brewLog(2, heatTick(2, 90), 110)],
    ['wild-cold', WILD, 3, brewLog(1, heatTick(1, 40), 200)],
    ['wild-heavy', WILD, 5, brewLog(3, heatTick(3, 92), 33)],
    ['plum-fisheye-good', PLUM, 2, brewLog(2, heatTick(2, 78), 22)],
    ['plum-roaring-scorched', PLUM, 2, brewLog(3, heatTick(3, 99), 30)],
    ['plum-light', PLUM, 1, brewLog(2, heatTick(2, 78), 22)],
    // Fire changes mid-boil, the way a player nudges the stove.
    ['wild-fire-changes', WILD, 3, [{ t: 0, k: 'fire', v: 3 }, { t: 120, k: 'fire', v: 1 }, { t: 260, k: 'fire', v: 2 }, { t: 400, k: 'leaves' }, { t: 720, k: 'pour' }]],
  ];
  return plans.map(([name, tea, scoops, log]) => {
    const j = outcome(tea, scoops, log);
    return { name, tea: tea.id, scoops, log, result: j.result, score: j.score, strength: j.strength, brewTemp: j.brewTemp };
  });
}
