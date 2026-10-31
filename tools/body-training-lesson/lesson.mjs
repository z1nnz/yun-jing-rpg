// 沈岳的第一堂練體課: stance, then block, then dodge. Pure and time-driven (seconds), no rendering, no network.
// The numbers live in packages/content/body-training-lesson-1.json; the C# port is QingxiBodyLessonRules, and
// QingxiBodyLessonSmoke replays the runs recorded by parity.mjs against it. Nothing here grants anything: a failed
// stage only restarts that stage, and a finished lesson only reports `passed` for the server (core team) to act on.

const STEP = 1 / 120;

function clock(now, last) {
  if (!Number.isFinite(now) || now < last) throw new RangeError('time must be finite and monotonic');
}

/** Same generator as the training drills, fixed per seed so a run can be replayed. */
function random(seed) {
  let s = seed >>> 0;
  return () => {
    s = (Math.imul(1664525, s) + 1013904223) >>> 0;
    return s / 4294967296;
  };
}

/** One press-to-rise bar that has to stay in the middle. Leaving the limit starts the count over. */
export class StanceStage {
  constructor(cfg, seed = 7) {
    this.cfg = cfg;
    const rnd = random(seed);
    this.phaseA = rnd() * Math.PI * 2;
    this.phaseB = rnd() * Math.PI * 2;
    this.t = -cfg.leadIn;
    this.value = 0;
    this.held = false;
    this.count = 0;
    this.resets = 0;
    this.done = false;
    this.passed = false;
    this.last = 0;
    this.pending = 0;
  }

  setHeld(held) { if (!this.done) this.held = !!held; }

  get inZone() { return Math.abs(this.value) <= this.cfg.zone; }

  update(now) {
    clock(now, this.last);
    this.pending += now - this.last;
    this.last = now;
    const dt = STEP;                     // fixed steps: a phone at 30 fps and a desktop at 144 fps get the same bar
    while (!this.done && this.pending >= dt - 1e-9) {
      this.pending -= dt;
      this.t += dt;
      if (this.t < 0) continue;
      const c = this.cfg;
      const sway = c.swayA * Math.sin(c.swayRateA * this.t + this.phaseA) + c.swayB * Math.sin(c.swayRateB * this.t + this.phaseB);
      this.value += (sway + (this.held ? c.rise : -c.fall)) * dt;
      if (Math.abs(this.value) > c.limit) {
        this.value = 0;
        this.count = 0;
        this.resets += 1;
      } else if (this.inZone) {
        this.count += dt;
        if (this.count >= c.holdSeconds) {
          this.count = c.holdSeconds;
          this.done = true;
          this.passed = true;
        }
      }
    }
  }
}

function schedule(cfg, seed) {
  const rnd = random(seed);
  const out = [];
  let at = cfg.firstAt;
  for (let i = 0; i < cfg.count; i++) {
    const jitter = (rnd() * 2 - 1) * cfg.jitter;
    out.push(Math.round((at + jitter) * 1e6) / 1e6);
    at += cfg.gaps[i] ?? cfg.gaps[cfg.gaps.length - 1];
  }
  return out;
}

/** Punches on a timing window. A press with nothing arriving stiffens the stance, and pressing again extends it, so mashing never lands. */
export class BlockStage {
  constructor(cfg, seed = 7) {
    this.cfg = cfg;
    this.strikes = schedule(cfg, seed);
    this.index = 0;
    this.results = [];
    this.stiffUntil = -Infinity;
    this.done = false;
    this.last = 0;
    this.lastEvent = null;
  }

  get next() { return this.done ? null : this.strikes[this.index]; }
  get blocked() { return this.results.filter(r => r === 'perfect' || r === 'good').length; }
  get passed() { return this.done && this.blocked >= this.cfg.required; }

  record(result) {
    this.results.push(result);
    this.lastEvent = result;
    this.index += 1;
    if (this.index >= this.strikes.length) this.done = true;
  }

  update(now) {
    clock(now, this.last);
    this.last = now;
    while (!this.done && now > this.strikes[this.index] + this.cfg.goodWindow) this.record('hit');
  }

  /** Returns 'perfect', 'good', 'early' (stiffened) or null when the stage is over. */
  press(now) {
    this.update(now);
    if (this.done) return null;
    const offset = now - this.strikes[this.index];
    if (now < this.stiffUntil || Math.abs(offset) > this.cfg.goodWindow) {
      this.stiffUntil = now + this.cfg.stiffSeconds;
      this.lastEvent = 'early';
      return 'early';
    }
    const result = Math.abs(offset) <= this.cfg.perfectWindow ? 'perfect' : 'good';
    this.record(result);
    return result;
  }
}

/** Sweeps resolved at the moment they arrive: dodged if a sideways step started inside the window before it. */
export class DodgeStage {
  constructor(cfg, seed = 7) {
    this.cfg = cfg;
    this.sweeps = schedule(cfg, seed);
    this.index = 0;
    this.results = [];
    this.stepAt = -Infinity;
    this.stepSide = null;
    this.readyAt = -Infinity;
    this.done = false;
    this.last = 0;
    this.lastEvent = null;
  }

  get next() { return this.done ? null : this.sweeps[this.index]; }
  get dodged() { return this.results.filter(r => r === 'dodged').length; }
  get passed() { return this.done && this.dodged >= this.cfg.required; }

  covers(at) { return this.stepAt >= at - this.cfg.dodgeBefore && this.stepAt <= at + this.cfg.dodgeAfter; }

  record(result) {
    this.results.push(result);
    this.lastEvent = result;
    this.index += 1;
    if (this.index >= this.sweeps.length) this.done = true;
  }

  update(now) {
    clock(now, this.last);
    this.last = now;
    while (!this.done && now > this.sweeps[this.index] + this.cfg.dodgeAfter) {
      this.record(this.covers(this.sweeps[this.index]) ? 'dodged' : 'swept');
    }
  }

  /** side: 'left' or 'right'. Returns 'step', 'early' (stumbled, long recovery) or null when ignored. */
  step(side, now) {
    this.update(now);
    if (this.done || now < this.readyAt || (side !== 'left' && side !== 'right')) return null;
    this.stepAt = now;
    this.stepSide = side;
    const inWindow = Math.abs(now - this.sweeps[this.index] + (this.cfg.dodgeBefore - this.cfg.dodgeAfter) / 2) <= (this.cfg.dodgeBefore + this.cfg.dodgeAfter) / 2;
    if (inWindow) {
      this.readyAt = now + this.cfg.recoverSeconds;
      this.lastEvent = 'step';
      return 'step';
    }
    this.readyAt = now + this.cfg.stumbleSeconds;
    this.lastEvent = 'early';
    return 'early';
  }
}

function makeStage(cfg, seed) {
  if (cfg.kind === 'stance') return new StanceStage(cfg, seed);
  if (cfg.kind === 'block') return new BlockStage(cfg, seed);
  if (cfg.kind === 'dodge') return new DodgeStage(cfg, seed);
  throw new RangeError(`unknown stage kind ${cfg.kind}`);
}

/**
 * The whole lesson. phase: 'demo' (the teacher shows it, input ignored), 'play', 'stage-failed' (retry() restarts this
 * stage straight away, nothing is taken), 'done' (all three stages passed). Times passed in are absolute and monotonic.
 */
export class Lesson {
  constructor(content, seed = 7) {
    this.content = content;
    this.seed = seed >>> 0;
    this.stageIndex = 0;
    this.attempts = content.stages.map(() => 0);
    this.now = 0;
    this.begin(0);
  }

  begin(now) {
    this.now = now;
    this.phase = 'demo';
    this.phaseStart = now;
    this.stage = null;
    this.attempts[this.stageIndex] += 1;
  }

  get stageConfig() { return this.content.stages[this.stageIndex]; }
  get passed() { return this.phase === 'done'; }
  /** Seconds since the running stage began. */
  get elapsed() { return this.now - this.phaseStart; }

  update(now) {
    clock(now, this.now);
    this.now = now;
    if (this.phase === 'demo') {
      if (now - this.phaseStart < this.content.demoSeconds) return;
      this.phase = 'play';
      this.phaseStart += this.content.demoSeconds;
      // A new layout each attempt, so a retry is not a memory test; still fixed per seed.
      const seed = (this.seed + this.stageIndex * 101 + this.attempts[this.stageIndex] * 7) >>> 0;
      this.stage = makeStage(this.stageConfig, seed);
    }
    if (this.phase !== 'play') return;
    this.stage.update(now - this.phaseStart);
    if (this.stage.done) this.finishStage();
  }

  finishStage() {
    if (!this.stage.passed) { this.phase = 'stage-failed'; return; }
    if (this.stageIndex === this.content.stages.length - 1) { this.phase = 'done'; return; }
    this.stageIndex += 1;
    this.begin(this.now);
  }

  setHeld(held) { if (this.phase === 'play' && this.stageConfig.kind === 'stance') this.stage.setHeld(held); }

  press(now) {
    this.update(now);
    if (this.phase !== 'play' || this.stageConfig.kind !== 'block') return null;
    const result = this.stage.press(now - this.phaseStart);
    if (this.stage.done) this.finishStage();
    return result;
  }

  step(side, now) {
    this.update(now);
    if (this.phase !== 'play' || this.stageConfig.kind !== 'dodge') return null;
    return this.stage.step(side, now - this.phaseStart);
  }

  /** After a failed stage: start that same stage again. Earlier stages stay passed; nothing is taken. */
  retry(now) {
    if (this.phase !== 'stage-failed') return false;
    this.begin(now);
    return true;
  }
}
