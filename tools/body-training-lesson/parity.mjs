// Copies the lesson content to where Unity can load it, and records runs from lesson.mjs for the C# port
// (QingxiBodyLessonRules). QingxiBodyLessonSmoke replays the same inputs and must match.
//   node tools/body-training-lesson/parity.mjs
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { Lesson } from './lesson.mjs';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..');
const raw = readFileSync(resolve(root, 'packages/content/body-training-lesson-1.json'), 'utf8');
const content = JSON.parse(raw);
const r6 = v => Math.round(v * 1e6) / 1e6;

/** Plays a whole lesson at a fixed step. `skill(kind, attempt, index)` says which beats the player gets right. */
function run(name, seed, step, skill) {
  const lesson = new Lesson(content, seed);
  const inputs = [];
  const log = [];
  let t = 0, frame = 0, held = false, retries = 0;
  while (lesson.phase !== 'done' && t < 240) {
    t += step; frame++;
    lesson.update(t);
    if (lesson.phase === 'stage-failed') {
      lesson.retry(t); retries++;
      inputs.push({ frame, kind: 'retry', side: '' });
      continue;
    }
    if (lesson.phase !== 'play') continue;
    const kind = lesson.stageConfig.kind, attempt = lesson.attempts[lesson.stageIndex], local = t - lesson.phaseStart, s = lesson.stage;
    if (kind === 'stance') {
      const want = s.value < 0;
      if (want !== held) { held = want; inputs.push({ frame, kind: 'hold', side: held ? 'on' : 'off' }); }
      lesson.setHeld(held);
    } else if (kind === 'block') {
      if (s.next - local < step && s.next - local >= 0 && skill(kind, attempt, s.index)) {
        inputs.push({ frame, kind: 'press', side: '' });
        log.push(`${kind}:${lesson.press(t)}`);
      }
    } else if (s.next - local < 0.2 && local >= s.readyAt && skill(kind, attempt, s.index)) {
      const side = s.index % 2 ? 'right' : 'left';
      inputs.push({ frame, kind: 'step', side });
      log.push(`${kind}:${lesson.step(side, t)}`);
    }
  }
  return { name, seed, step, frames: frame, inputs, log, retries, phase: lesson.phase, attempts: lesson.attempts, end: r6(t) };
}

/** Sessions on their own: the schedules, and the stance bar under a known input. */
function schedules(seed) {
  const out = { seed, stance: [], block: [], dodge: [] };
  for (const id of ['block', 'dodge']) {
    const c = content.stages.find(s => s.id === id);
    out[id] = (id === 'block' ? new ProbeBlock(c, seed) : new ProbeDodge(c, seed)).times.map(r6);
  }
  return out;
}
class ProbeBlock { constructor(c, seed) { const l = new Lesson({ ...content, demoSeconds: 0, stages: [c] }, 0); l.seed = seed; l.attempts = [-1]; l.begin(0); l.attempts = [0]; l.update(0); this.times = l.stage.strikes; } }
class ProbeDodge { constructor(c, seed) { const l = new Lesson({ ...content, demoSeconds: 0, stages: [c] }, 0); l.seed = seed; l.attempts = [-1]; l.begin(0); l.attempts = [0]; l.update(0); this.times = l.stage.sweeps; } }

const data = {
  source: 'tools/body-training-lesson/lesson.mjs (Johnnnny0823)',
  schedules: [7, 3].map(schedules),
  runs: [
    run('clean-60fps', 7, 1 / 60, () => true),
    run('clean-30fps', 9, 1 / 30, () => true),
    run('fail-block-once', 7, 1 / 60, (kind, attempt) => !(kind === 'block' && attempt === 1)),
    run('fail-dodge-once-minimum', 5, 1 / 60, (kind, attempt, i) => (kind === 'dodge' && attempt === 1 ? false : kind === 'dodge' ? i < 2 : kind === 'block' ? i < 3 : true)),
  ],
};
const unity = resolve(root, 'apps/game/Assets/YunJing/Resources/QingxiBodyLesson');
mkdirSync(unity, { recursive: true });
writeFileSync(resolve(unity, 'body-training-lesson-1.json'), raw);
writeFileSync(resolve(root, 'apps/game/Assets/YunJing/Data/QingxiBodyLessonParity.json'), JSON.stringify(data, null, 1) + '\n');
console.log('wrote', data.runs.map(r => `${r.name}:${r.phase}/${r.attempts.join('-')}/${r.end}s`).join(' '));
