// Backyard rules for the local demo: planting, growth stages, harvest, the corner lantern's brightness and the gate.
// Pure state (no rendering, no network). The demo never grants real items: harvests are counted here only, and the
// server (core team) decides real items and the hidden "pulse" that drives the lantern in the game.

/** Growth stage thresholds from the work package (01-A section 6): t < 0.25 sprout, < 0.6 young, < 1 grown, >= 1 mature. */
export const STAGE_T = [0.25, 0.6, 1.0];
export const CROPS = {
  qingling: { name: '青靈草', stages: ['嫩芽', '幼株', '成株', '成熟'], flooded: false },
  lotus: { name: '淨水蓮', stages: ['浮葉', '立葉', '花苞', '開花'], flooded: true },
};
export const GROW_SECONDS = 90;      // demo pace at 1x; fast-forward multiplies it
export const MAX_LEVEL = 4;

/** Stage index 0..3 for growth progress t. */
export function stageOf(t) {
  if (!(t >= 0)) return 0;
  if (t < STAGE_T[0]) return 0;
  if (t < STAGE_T[1]) return 1;
  if (t < STAGE_T[2]) return 2;
  return 3;
}

/** Lantern brightness 0..4 from the number of harvests (the game maps the server-side pulse instead). */
export function lanternLevel(harvests) {
  return Math.max(0, Math.min(MAX_LEVEL, Math.floor(harvests)));
}

export class Yard {
  constructor(fieldCount = 2) {
    this.fields = Array.from({ length: fieldCount }, () => ({ crop: null, t: 0, plantedAt: 0, planting: null }));
    this.harvests = 0;
    this.harvested = new Set();      // planting ids already harvested: a repeat or late event never counts twice
    this.gateOpen = false;
    this.rackFull = false;
    this.clock = 0;
    this.speed = 1;
    this.nextPlanting = 1;
  }

  /** Plant a crop in an empty field. Returns the planting id, or null if the field is busy or the crop unknown. */
  plant(i, crop) {
    const f = this.fields[i];
    if (!f || f.crop || !CROPS[crop]) return null;
    Object.assign(f, { crop, t: 0, plantedAt: this.clock, planting: this.nextPlanting++ });
    return f.planting;
  }

  /** Advance the demo clock by dt seconds (times the fast-forward speed). */
  tick(dt) {
    const step = Math.max(0, dt) * this.speed;
    this.clock += step;
    for (const f of this.fields) if (f.crop) f.t = Math.min(1, f.t + step / GROW_SECONDS);
  }

  setSpeed(x) { this.speed = Math.max(1, Math.min(60, x)); }

  stage(i) { const f = this.fields[i]; return f && f.crop ? stageOf(f.t) : -1; }

  canHarvest(i) { return this.stage(i) === 3; }

  /**
   * Harvest a mature field. `planting` (optional) is the id the caller saw; a stale or repeated request for a planting
   * that was already harvested is ignored, so a double click or a replayed event cannot brighten the lantern twice.
   */
  harvest(i, planting = this.fields[i]?.planting) {
    const f = this.fields[i];
    if (!f || !f.crop || planting == null || this.harvested.has(planting) || planting !== f.planting || !this.canHarvest(i)) return false;
    this.harvested.add(planting);
    this.harvests += 1;
    this.rackFull = true;
    Object.assign(f, { crop: null, t: 0, planting: null });
    return true;
  }

  get level() { return lanternLevel(this.harvests); }

  /**
   * Toggle the gate. Closing is refused while the player stands in the leaf's swing area, so the gate never shuts on
   * (or traps) the player. Returns the new state.
   */
  toggleGate(playerInSwing = false) {
    if (this.gateOpen && playerInSwing) return this.gateOpen;
    this.gateOpen = !this.gateOpen;
    return this.gateOpen;
  }

  snapshot() {
    return {
      fields: this.fields.map((f, i) => ({ crop: f.crop, t: +f.t.toFixed(3), stage: this.stage(i) })),
      harvests: this.harvests, level: this.level, gateOpen: this.gateOpen, rackFull: this.rackFull, speed: this.speed,
    };
  }
}
