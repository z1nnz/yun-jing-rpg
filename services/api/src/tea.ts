import teaContent from '../../../packages/content/tea-brewing-v1.json';

// Deterministic home tea brewing shared by the server and (as a C# port, TeaSim.cs) the Unity client.
// The client replays this only to draw the steam and the cup; the result is always recomputed here.
export { teaContent };
export type Tea = typeof teaContent.teas[number];
export type TeaResultId = 'weak' | 'good' | 'bitter';
export interface TeaEvent { t: number; k: string; v?: number }
export interface TeaSimResult { endTick: number; temperature: number; peak: number; brewTemp: number | null; steepSeconds: number; strength: number; scorch: number }
export interface TeaJudgement {
  result: TeaResultId; label: string; score: number; strength: number; brewTemp: number; steepSeconds: number;
  describe: string; reasons: string[]; restMultiplier: number;
}
const KINDS = new Set(['fire', 'leaves', 'pour']);
const round = (value: number, digits = 4) => Math.round(value * 10 ** digits) / 10 ** digits;

export const teaById = (id: unknown) => teaContent.teas.find(x => x.id === id);

/** Steam stage the player reads at the spout for a water temperature. */
export function steamAt(temperature: number) {
  let stage = teaContent.steam[0];
  for (const s of teaContent.steam) if (temperature >= s.from) stage = s;
  return stage;
}

/** Event log shape: fire changes, then exactly one leaves, ending with one pour. Returns an error code or null. */
export function validateLog(log: unknown): string | null {
  if (!Array.isArray(log) || log.length < 2 || log.length > 400) return 'LOG_SIZE';
  let last = 0, leaves = 0;
  for (let i = 0; i < log.length; i++) {
    const e = log[i] as TeaEvent;
    if (!e || typeof e !== 'object') return 'LOG_EVENT';
    if (!Number.isInteger(e.t) || e.t < last || e.t > teaContent.maxLogSeconds * 10) return 'LOG_TIME';
    if (!KINDS.has(e.k)) return 'LOG_KIND';
    if (e.k === 'fire' && !teaContent.fires.some(f => f.id === e.v)) return 'LOG_FIRE';
    if (e.k === 'leaves' && ++leaves > 1) return 'LOG_DOUBLE_LEAVES';
    if (e.k === 'pour' && (i !== log.length - 1 || leaves === 0)) return 'LOG_POUR';
    last = e.t;
  }
  return (log[log.length - 1] as TeaEvent).k === 'pour' ? null : 'LOG_NO_POUR';
}

/** Fixed-step kettle and pot replay. Integer ticks of `step` seconds; identical arithmetic in TeaSim.cs. */
export function simulate(log: TeaEvent[], tea: Tea, scoops: number): TeaSimResult {
  const c = teaContent, x = c.extraction, dt = c.step;
  const mid = (tea.idealTemp[0] + tea.idealTemp[1]) / 2, dose = scoops / tea.idealScoops;
  let T = c.ambient, heat = 0, peak = T, brewTemp: number | null = null, leavesTick = 0, strength = 0, scorch = 0;
  const endTick = log.length ? log[log.length - 1].t : 0;
  let e = 0;
  for (let tick = 0; tick <= endTick; tick++) {
    while (e < log.length && log[e].t === tick) {
      const ev = log[e++];
      if (ev.k === 'fire') heat = c.fires.find(f => f.id === ev.v)!.heat;
      else if (ev.k === 'leaves' && brewTemp === null) {
        brewTemp = T; leavesTick = tick;
        scorch = Math.max(0, T - tea.idealTemp[1]) * x.scorchPerDegree; strength += scorch;
      }
    }
    if (tick === endTick) break;
    if (brewTemp === null) {
      T = Math.min(c.boil, T + (heat - c.cooling * (T - c.ambient)) * dt);
      if (T > peak) peak = T;
    } else {
      T = T - c.steepCooling * (T - c.ambient) * dt;
      let rate = dose * Math.max(x.minFactor, x.base + x.perDegree * (T - mid));
      if (brewTemp < x.coldBelow) rate *= x.coldRate;
      strength += rate * dt;
    }
  }
  return {
    endTick, temperature: round(T), peak: round(peak), brewTemp: brewTemp === null ? null : round(brewTemp),
    steepSeconds: brewTemp === null ? 0 : (endTick - leavesTick) / 10, strength: round(strength), scorch: round(scorch),
  };
}

/** Weak below the tea's window, bitter above it, good inside. The reasons say what to change next time. */
export function judge(sim: TeaSimResult, tea: Tea, scoops: number): TeaJudgement {
  const c = teaContent, w = tea.strength, brewTemp = sim.brewTemp ?? c.ambient;
  const result: TeaResultId = sim.strength < w.weakBelow ? 'weak' : sim.strength > w.bitterAbove ? 'bitter' : 'good';
  const reasons: string[] = [];
  if (result === 'weak') {
    if (brewTemp < c.extraction.coldBelow) reasons.push(c.advice.cold);
    if (scoops < tea.idealScoops) reasons.push(c.advice.light);
    if (!reasons.length) reasons.push(c.advice.early);
  } else if (result === 'bitter') {
    if (brewTemp > tea.idealTemp[1]) reasons.push(c.advice.hot);
    if (scoops > tea.idealScoops) reasons.push(c.advice.heavy);
    if (!reasons.length) reasons.push(c.advice.late);
  }
  const centre = (w.weakBelow + w.bitterAbove) / 2, half = (w.bitterAbove - w.weakBelow) / 2;
  const off = Math.abs(sim.strength - centre) / half;   // 0 at the centre, 1 at the edge of the good window
  const score = result === 'good' ? Math.round(100 - 30 * off) : Math.max(10, Math.round(60 - 25 * (off - 1)));
  const row = c.results.find(r => r.id === result)!;
  return {
    result, label: row.label, score, strength: sim.strength, brewTemp: round(brewTemp, 1), steepSeconds: sim.steepSeconds,
    describe: tea.describe[result], reasons, restMultiplier: row.restMultiplier,
  };
}
