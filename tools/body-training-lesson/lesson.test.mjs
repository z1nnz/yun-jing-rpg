import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { Lesson, StanceStage, BlockStage, DodgeStage } from './lesson.mjs';

const rel = p => new URL(p, import.meta.url);
const content = JSON.parse(readFileSync(rel('../../packages/content/body-training-lesson-1.json'), 'utf8'));
const cfg = id => content.stages.find(s => s.id === id);

/** Keeps the bar in the middle the way a player does: hold while it is low, let go while it is high. */
function stand(stage, seconds, step = 1 / 60) {
  for (let t = step; t <= seconds && !stage.done; t += step) {
    stage.setHeld(stage.value < 0);
    stage.update(t);
  }
}

test('content matches the work package: 15 s stance, 3 of 5 blocks, 2 of 3 dodges, no cost', () => {
  assert.equal(cfg('stance').holdSeconds, 15);
  assert.deepEqual([cfg('block').required, cfg('block').count], [3, 5]);
  assert.deepEqual([cfg('dodge').required, cfg('dodge').count], [2, 3]);
  assert.deepEqual(content.stages.map(s => s.id), ['stance', 'block', 'dodge']);
  assert.equal(content.failure.cost, 'none');
  assert.equal(content.failure.retry, 'same-stage');
});

test('the Unity copy of the content is identical to packages/content', () => {
  const copy = JSON.parse(readFileSync(rel('../../apps/game/Assets/YunJing/Resources/QingxiBodyLesson/body-training-lesson-1.json'), 'utf8'));
  assert.deepEqual(copy, content);
});

test('interface text stays within 16 characters a line', () => {
  const walk = v => (typeof v === 'string' ? [v] : Object.values(v).flatMap(walk));
  for (const line of walk(content.texts)) assert.ok([...line].length <= 16, line);
});

test('stance: staying in the middle for 15 s passes', () => {
  const s = new StanceStage(cfg('stance'));
  stand(s, 30);
  assert.equal(s.passed, true);
  assert.equal(s.resets, 0);
});

test('stance: the time out of the zone does not count', () => {
  const c = { ...cfg('stance'), swayA: 0, swayB: 0, leadIn: 0, limit: 5 };
  const s = new StanceStage(c);
  s.setHeld(true);
  s.update(c.zone / c.rise + 2);               // rises through the zone, then sits above it for 2 s
  assert.ok(Math.abs(s.count - c.zone / c.rise) < 0.02, `count ${s.count}`);
  assert.equal(s.inZone, false);
});

test('stance: drifting past the limit starts the count over', () => {
  const s = new StanceStage(cfg('stance'));
  stand(s, 6);
  assert.ok(s.count > 3);
  s.setHeld(true);
  for (let t = 6; s.resets === 0 && t < 12; t += 1 / 60) s.update(t);
  assert.equal(s.resets, 1);
  assert.ok(s.count < 0.1);
  assert.equal(s.passed, false);
});

test('stance: no input never passes, and the result does not depend on the frame rate', () => {
  const idle = new StanceStage(cfg('stance'));
  for (let t = 1 / 60; t < 60; t += 1 / 60) idle.update(t);
  assert.equal(idle.passed, false);
  assert.ok(idle.resets > 3);
  const run = step => { const s = new StanceStage(cfg('stance'), 3); s.setHeld(true); for (let t = step; t < 2; t += step) s.update(t); s.update(2); return s.value; };
  assert.ok(Math.abs(run(1 / 30) - run(1 / 144)) < 1e-6);
});

test('stance: time must not run backwards', () => {
  const s = new StanceStage(cfg('stance'));
  s.update(1);
  assert.throws(() => s.update(0.5), RangeError);
  assert.throws(() => s.update(NaN), RangeError);
});

test('block: 3 of 5 passes, 2 of 5 fails', () => {
  const play = hits => {
    const s = new BlockStage(cfg('block'));
    s.strikes.forEach((at, i) => { if (i < hits) s.press(at + 0.02); });
    s.update(100);
    return s;
  };
  assert.equal(play(3).passed, true);
  assert.equal(play(3).blocked, 3);
  assert.equal(play(2).done, true);
  assert.equal(play(2).passed, false);
  assert.equal(play(0).blocked, 0);
});

test('block: judged by the timing window', () => {
  const c = cfg('block');
  const s = new BlockStage(c);
  assert.equal(s.press(s.strikes[0] + c.perfectWindow - 0.01), 'perfect');
  assert.equal(s.press(s.strikes[1] + c.goodWindow - 0.01), 'good');
  s.update(s.strikes[2] + c.goodWindow + 0.01);
  assert.equal(s.results[2], 'hit');
  assert.equal(new BlockStage(c).press(0.1), 'early');
});

test('block: mashing can never land a block', () => {
  for (const every of [0.05, 0.1, 0.2, 0.4]) {
    const s = new BlockStage(cfg('block'));
    for (let t = every; !s.done && t < 30; t += every) s.press(t);
    assert.equal(s.blocked, 0, `every ${every}`);
    assert.equal(s.passed, false);
  }
});

test('block: a stiff stance recovers if you stop pressing', () => {
  const c = cfg('block');
  const s = new BlockStage(c);
  s.press(s.strikes[0] - c.stiffSeconds - c.goodWindow - 0.05);
  assert.equal(s.press(s.strikes[0]), 'perfect');
});

test('dodge: 2 of 3 passes, 1 of 3 fails, either side counts', () => {
  const play = list => {
    const s = new DodgeStage(cfg('dodge'));
    list.forEach((side, i) => { if (side) s.step(side, s.sweeps[i] - 0.2); });
    s.update(100);
    return s;
  };
  assert.equal(play(['left', 'right', null]).passed, true);
  assert.equal(play(['left', 'right', null]).dodged, 2);
  assert.equal(play(['left', null, null]).passed, false);
  assert.equal(play([null, null, null]).dodged, 0);
});

test('dodge: too early stumbles and misses; too late is swept', () => {
  const c = cfg('dodge');
  const early = new DodgeStage(c);
  assert.equal(early.step('left', early.sweeps[0] - c.dodgeBefore - 0.2), 'early');
  assert.equal(early.step('left', early.sweeps[0] - 0.1), null);       // still stumbling
  early.update(early.sweeps[0] + 1);
  assert.equal(early.results[0], 'swept');
  const late = new DodgeStage(c);
  late.update(late.sweeps[0] + c.dodgeAfter + 0.01);
  assert.equal(late.results[0], 'swept');
  assert.equal(new DodgeStage(c).step('up', 2), null);
});

test('dodge: mashing does not reliably pass', () => {
  let passes = 0;
  for (let seed = 1; seed <= 40; seed++) {
    const s = new DodgeStage(cfg('dodge'), seed);
    for (let t = 0.1; !s.done && t < 30; t += 0.1) s.step('left', t);
    if (s.passed) passes += 1;
  }
  assert.ok(passes < 20, `${passes}/40`);
});

/** Plays a whole stage well at 60 fps, returning the time reached. */
function playStage(lesson, from, good = true) {
  const kind = lesson.stageConfig.kind;
  const index = lesson.stageIndex;
  const attempt = lesson.attempts[index];
  let t = from;
  while (lesson.stageIndex === index && lesson.attempts[index] === attempt && lesson.phase !== 'stage-failed' && lesson.phase !== 'done' && t < from + 200) {
    t += 1 / 60;
    lesson.update(t);
    if (lesson.phase !== 'play' || lesson.stageIndex !== index) continue;
    const local = t - lesson.phaseStart;
    if (kind === 'stance') lesson.setHeld(lesson.stage.value < 0);
    if (good && kind === 'block' && Math.abs(lesson.stage.next - local) < 0.01) lesson.press(t);
    if (good && kind === 'dodge' && lesson.stage.next - local < 0.2 && t >= lesson.phaseStart + lesson.stage.readyAt) lesson.step('left', t);
  }
  return t;
}

test('lesson: demo first (input ignored), then the three stages in order, ending in passed', () => {
  const lesson = new Lesson(content);
  assert.equal(lesson.phase, 'demo');
  assert.equal(lesson.press(0.5), null);
  lesson.setHeld(true);
  let t = playStage(lesson, 0.5);
  assert.equal(lesson.stageConfig.id, 'block');
  assert.equal(lesson.phase, 'demo');
  t = playStage(lesson, t);
  assert.equal(lesson.stageConfig.id, 'dodge');
  t = playStage(lesson, t);
  assert.equal(lesson.phase, 'done');
  assert.equal(lesson.passed, true);
  assert.deepEqual(lesson.attempts, [1, 1, 1]);
});

test('lesson: a failed stage retries itself straight away; earlier stages stay passed', () => {
  const lesson = new Lesson(content);
  let t = playStage(lesson, 0);               // stance
  t = playStage(lesson, t, false);            // block with no input
  assert.equal(lesson.phase, 'stage-failed');
  assert.equal(lesson.stageConfig.id, 'block');
  assert.equal(lesson.passed, false);
  assert.equal(lesson.retry(t), true);
  assert.equal(lesson.phase, 'demo');
  assert.equal(lesson.stageConfig.id, 'block');
  assert.equal(lesson.attempts[0], 1);
  assert.equal(lesson.attempts[1], 2);
  t = playStage(lesson, t);
  assert.equal(lesson.stageConfig.id, 'dodge');
});

test('lesson: retrying changes the layout, and retry is refused unless a stage failed', () => {
  const lesson = new Lesson(content);
  assert.equal(lesson.retry(0), false);
  let t = playStage(lesson, 0);
  t = playStage(lesson, t, false);
  const first = [...lesson.stage.strikes];
  lesson.retry(t);
  t += content.demoSeconds + 0.1;
  lesson.update(t);
  assert.notDeepEqual(lesson.stage.strikes, first);
});

test('lesson: the same seed replays identically', () => {
  const a = new Lesson(content, 11), b = new Lesson(content, 11);
  for (const l of [a, b]) l.update(content.demoSeconds + 0.1);
  assert.equal(a.stage.phaseA, b.stage.phaseA);
});
