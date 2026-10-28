// Waterworks rules core: place pieces by their ports, pick a treatment direction, simulate the water, finish once.
//
// Pure and deterministic (no clock, no Math.random): the same plan always gives the same water, so a result can be
// explained and replayed. Rendering lives in ../blender/play.py (via src/cli.mjs); the server is expected to run the same rules (../CONTRACT.md).
// Materials are local display stock only and never touch the real inventory.

import { PIECES, DIRECTIONS, SOURCE, TARGETS, TERRAIN, LOSS, FIELD_DEMAND, OPP, STEP, SIDE_ZH,
  key, has, inside, sidesOf, rotSide, nearNursery, slotOpen } from './site.mjs';
import { knownHazards, UNKNOWN } from './fixtures.mjs';

export const STOCK = Object.freeze({ stone: 22, cedar: 6, bronze: 4, patch: 2, sieve: 1 });
export const STOCK_ZH = Object.freeze({ stone: '石料', cedar: '杉木', bronze: '銅箍', patch: '補石', sieve: '清淤篩' });
export const OUTCOMES = Object.freeze({
  restore_channel: 'channel_restored_direct',
  protect_nursery: 'nursery_protected_detour',
  clear_silt: 'silt_cleared_temporary_diversion',
});
const NURSERY_ZH = ['安全', '輕擾', '受驚擾'];
const FAST = 40;                                     // L/s: water louder than this next to the den counts as disturbance

const clone = o => JSON.parse(JSON.stringify(o));
const r1 = v => Math.round(v * 10) / 10;

export function newGame(observationIds, sessionId = 'local') {
  return { observationIds: [...observationIds], known: knownHazards(observationIds), pieces: {}, direction: null, nextSeg: 1,
    history: [], future: [], sessionId, attempt: 1, stock: { ...STOCK }, receipts: {}, finished: null, log: [] };
}

function snap(s) { return clone({ pieces: s.pieces, direction: s.direction, nextSeg: s.nextSeg }); }
function commit(s, label) { s.history.push(snap(s)); s.future = []; s.log.push(label); }
const locked = s => (s.finished ? { ok: false, code: 'FINISHED', message: '這個方案已完成。按「重試」開一個新方案。' } : null);

export function pieceName(s, p) { return `${p.seg} ${PIECES[p.type].label}`; }
function portName(p, side) {
  const i = sidesOf(p).indexOf(side); return `${SIDE_ZH[side]}接口（${PIECES[p.type].ports[i]}）`;
}

// --------------------------------------------------------------------------- edits (all undoable)
export function place(s, x, y, type, rot = 0) {
  const l = locked(s); if (l) return l;
  if (!PIECES[type]) return { ok: false, code: 'NO_PIECE', message: `沒有「${type}」這種件` };
  if (!slotOpen(x, y)) return { ok: false, code: 'NO_SLOT', message: has(TERRAIN.rock, x, y) ? '這格有大石，放不下槽件' : '這裡不能放' };
  if (s.direction === 'protect_nursery' && (has(TERRAIN.nursery, x, y) || nearNursery(x, y)))
    return { ok: false, code: 'NURSERY_FORBIDDEN', message: '已選「保護育幼區」：育幼區和它旁邊一圈不施工' };
  commit(s, `place ${type} ${x},${y} r${rot}`);
  const old = s.pieces[key(x, y)];
  s.pieces[key(x, y)] = { type, rot: ((rot % 4) + 4) % 4, seg: old?.seg ?? `S${String(s.nextSeg++).padStart(2, '0')}`, ...(PIECES[type].gate ? { open: true } : {}) };
  return { ok: true };
}

export function rotate(s, x, y) {
  const l = locked(s); if (l) return l;
  const p = s.pieces[key(x, y)]; if (!p) return { ok: false, code: 'EMPTY', message: '這格沒有槽件' };
  commit(s, `rotate ${x},${y}`); p.rot = (p.rot + 1) % 4; return { ok: true };
}

export function remove(s, x, y) {
  const l = locked(s); if (l) return l;
  if (!s.pieces[key(x, y)]) return { ok: false, code: 'EMPTY', message: '這格沒有槽件' };
  commit(s, `remove ${x},${y}`); delete s.pieces[key(x, y)]; return { ok: true };
}

export function toggleGate(s, x, y) {
  const l = locked(s); if (l) return l;
  const p = s.pieces[key(x, y)]; if (!p || !PIECES[p.type].gate) return { ok: false, code: 'NO_GATE', message: '這格不是閘板' };
  commit(s, `gate ${x},${y}`); p.open = !p.open; return { ok: true, open: p.open };
}

export function setDirection(s, dir) {
  const l = locked(s); if (l) return l;
  if (!DIRECTIONS[dir]) return { ok: false, code: 'NO_DIRECTION', message: '沒有這個處理方向' };
  if (dir === 'protect_nursery') {
    const bad = Object.entries(s.pieces).filter(([k]) => { const [x, y] = k.split(',').map(Number); return has(TERRAIN.nursery, x, y) || nearNursery(x, y); });
    if (bad.length) return { ok: false, code: 'NURSERY_FORBIDDEN', message: `先移走育幼區旁的 ${bad.map(([, p]) => p.seg).join('、')}，才能選「保護育幼區」` };
  }
  commit(s, `direction ${dir}`); s.direction = dir; return { ok: true };
}

export function undo(s) {
  if (s.finished) return { ok: false, code: 'FINISHED', message: '已完成的方案不能撤回；按「重試」開新方案' };
  if (!s.history.length) return { ok: false, code: 'NOTHING', message: '沒有可撤回的步驟' };
  s.future.push(snap(s)); Object.assign(s, s.history.pop()); s.log.push('undo'); return { ok: true };
}

export function redo(s) {
  if (s.finished) return { ok: false, code: 'FINISHED', message: '已完成的方案不能重做' };
  if (!s.future.length) return { ok: false, code: 'NOTHING', message: '沒有可重做的步驟' };
  s.history.push(snap(s)); Object.assign(s, s.future.pop()); s.log.push('redo'); return { ok: true };
}

// --------------------------------------------------------------------------- water
// hz: which hazards are in effect. preview uses only what the player has observed; finish uses the real site.
function hazards(s, real) {
  const k = real ? { crack: true, silt: true, nursery: true } : s.known;
  return { crack: k.crack && s.direction !== 'restore_channel', silt: k.silt && s.direction !== 'clear_silt', nursery: k.nursery };
}

function targetAt(x, y, side) {
  return TARGETS.find(t => t.side === side && has(t.cells, x, y)) ?? null;
}

export function simulate(s, { real = false } = {}) {
  const hz = hazards(s, real); const issues = []; const wet = {}; const out = { fields: 0, creek: 0, leaks: [] }; const links = [];
  const first = [SOURCE.x + STEP[SOURCE.out][0], SOURCE.y + STEP[SOURCE.out][1]];
  const p0 = s.pieces[key(...first)];
  if (!p0 || !sidesOf(p0).includes(OPP[SOURCE.out])) {
    issues.push({ level: 'error', code: 'SOURCE_OPEN', at: first, message: p0
      ? `水源 B01 的出水口（北，Out_Front）對著 ${pieceName(s, p0)} 的側牆。把 ${p0.seg} 轉到南面有接口。`
      : '水源 B01 的出水口（北，Out_Front）還沒接上。在它正北那格放一段南面有接口的槽。' });
  }
  // topology: walk from the source; every side of a reached piece is linked, open, discharging or blocked
  const seen = new Set(); const tree = {};
  const reach = {};
  function walk(x, y, inSide, from) {
    const k = key(x, y); const p = s.pieces[k];
    if (seen.has(k)) { issues.push({ level: 'error', code: 'LOOP', at: [x, y], message: `${pieceName(s, p)} 讓水路繞回自己，拆掉其中一段` }); return null; }
    seen.add(k); const node = { x, y, p, inSide, kids: [] }; tree[k] = node; reach[k] = { from, inSide, order: Object.keys(reach).length };
    const outlet = PIECES[p.type].outlet ? rotSide(PIECES[p.type].outlet, p.rot) : null;
    for (const side of outlet ? [outlet] : sidesOf(p)) {
      if (side === inSide) continue;
      const nx = x + STEP[side][0], ny = y + STEP[side][1]; const q = inside(nx, ny) ? s.pieces[key(nx, ny)] : null;
      if (outlet) {   // terminal: its open discharge edge must face a target, with nothing in the way
        const t = q ? null : targetAt(x, y, side);
        if (t) { node.kids.push({ side, kind: 'target', target: t.id }); continue; }
        issues.push({ level: 'error', code: 'APRON_MISPLACED', at: [x, y], side, message: q
          ? `${pieceName(s, p)} 的出水口朝${SIDE_ZH[side]}，被 ${pieceName(s, q)} 擋住。`
          : `${pieceName(s, p)} 的出水口朝${SIDE_ZH[side]}，${inside(nx, ny) ? '對著空地' : '對著場地邊'}；收尾溢流台要放在村田進水口（北緣）或溪道回流口（西緣），出水口朝外。` });
        node.kids.push({ side, kind: 'leak' }); continue;
      }
      if (q && sidesOf(q).includes(OPP[side])) { links.push([k, key(nx, ny)]); const c = walk(nx, ny, OPP[side], k); if (c) node.kids.push({ side, kind: 'pipe', node: c }); continue; }
      if (q) {
        issues.push({ level: 'error', code: 'PORT_MISMATCH', at: [x, y], side, message:
          `${pieceName(s, p)} 的${portName(p, side)}對著 ${pieceName(s, q)} 的側牆，沒有接口。把 ${q.seg} 轉向讓接口朝${SIDE_ZH[OPP[side]]}，或換一種槽件。` });
        node.kids.push({ side, kind: 'leak' }); continue;
      }
      const t = targetAt(x, y, side);
      const where = t ? `直接沖進${t.label}會沖壞田埂／岸邊，要放收尾溢流台` : !inside(nx, ny) ? '對著場地邊' : has(TERRAIN.rock, nx, ny) ? '對著大石' : '開著沒接東西';
      issues.push({ level: 'error', code: 'OPEN_END', at: [x, y], side, message: `${pieceName(s, p)} 的${portName(p, side)}${where}，水會從這裡流掉。接上下一段或放收尾溢流台。` });
      node.kids.push({ side, kind: 'leak' });
    }
    return node;
  }
  const root = p0 && sidesOf(p0).includes(OPP[SOURCE.out]) ? walk(first[0], first[1], OPP[SOURCE.out], 'source') : null;
  // which branches can take water (a closed gate with nothing open behind it backs the water up)
  function open(n) {
    if (PIECES[n.p.type].gate && !n.p.open) return false;
    return n.kids.some(c => c.kind !== 'pipe' || open(c.node));
  }
  function flow(n, q) {
    const [x, y] = [n.x, n.y]; q *= 1 - (n.p.type === 'worn' && !has(TERRAIN.oldChannel, x, y) ? 0.05 : PIECES[n.p.type].loss);
    if (hz.crack && has(TERRAIN.crack, x, y)) { out.leaks.push({ at: [x, y], q: r1(q * LOSS.crack), why: 'crack' }); q *= 1 - LOSS.crack; }
    if (hz.silt && has(TERRAIN.silt, x, y)) q *= 1 - LOSS.silt;
    if (has(TERRAIN.seep, x, y)) { out.leaks.push({ at: [x, y], q: r1(q * LOSS.seep), why: 'seep' }); q *= 1 - LOSS.seep; }
    wet[key(x, y)] = r1(q);
    if (PIECES[n.p.type].gate && !n.p.open) return;
    const ways = n.kids.filter(c => c.kind !== 'pipe' || open(c.node));
    for (const c of ways) {
      const share = q / ways.length;
      if (c.kind === 'pipe') flow(c.node, share);
      else if (c.kind === 'target') out[c.target] += share;
      else out.leaks.push({ at: [x, y], side: c.side, q: r1(share), why: 'open' });
    }
  }
  if (root) flow(root, SOURCE.flow);
  for (const [k, p] of Object.entries(s.pieces)) {
    if (!seen.has(k)) { const [x, y] = k.split(',').map(Number); issues.push({ level: 'error', code: 'DRY', at: [x, y], message: `${pieceName(s, p)} 沒有接到水（孤立的一段）。接回水路，或把它拆掉。` }); }
  }
  for (const n of Object.values(tree)) {
    if (PIECES[n.p.type].gate && !n.p.open && out.fields === 0)
      issues.push({ level: 'error', code: 'GATE_CLOSED', at: [n.x, n.y], message: `${pieceName(s, n.p)} 關著，水到不了村田。轉動閘輪把它打開（G）。` });
  }
  // nursery: slots in / beside the den, fast water beside it, silt work beside it
  let nursery = 0;
  if (hz.nursery || real) {
    for (const [k, p] of Object.entries(s.pieces)) {
      const [x, y] = k.split(',').map(Number);
      if (has(TERRAIN.nursery, x, y)) nursery += 3; else if (nearNursery(x, y)) nursery += 1 + ((wet[k] ?? 0) > FAST ? 1 : 0);
    }
    if (s.direction === 'clear_silt') nursery += 1;
  }
  const level = nursery === 0 ? 0 : nursery < 4 ? 1 : 2;
  // unknown risks the plan touches
  const risks = [];
  if (!s.known.crack && Object.keys(wet).some(k => has(TERRAIN.crack, ...k.split(',').map(Number)))) risks.push(UNKNOWN.crack);
  if (!s.known.silt && Object.keys(wet).some(k => has(TERRAIN.silt, ...k.split(',').map(Number)))) risks.push(UNKNOWN.silt);
  if (!s.known.nursery && Object.keys(s.pieces).some(k => { const [x, y] = k.split(',').map(Number); return has(TERRAIN.nursery, x, y) || nearNursery(x, y); })) risks.push(UNKNOWN.nursery);
  return { wet, links, reach, issues, risks, fields: r1(out.fields), creek: r1(out.creek), leaks: out.leaks,
    supply: Math.min(100, Math.round(out.fields / FIELD_DEMAND * 100)), nursery: { score: nursery, level, text: NURSERY_ZH[level] } };
}

// --------------------------------------------------------------------------- cost, checks, finish
export function quote(s) {
  const need = {};
  const add = c => { for (const [m, n] of Object.entries(c)) need[m] = (need[m] ?? 0) + n; };
  for (const [k, p] of Object.entries(s.pieces)) {
    const [x, y] = k.split(',').map(Number);
    add(p.type === 'worn' && !has(TERRAIN.oldChannel, x, y) ? { stone: 2 } : PIECES[p.type].cost);
  }
  if (s.direction) add(DIRECTIONS[s.direction].cost);
  const short = Object.entries(need).filter(([m, n]) => n > (s.stock[m] ?? 0)).map(([m, n]) => ({ material: m, need: n, have: s.stock[m] ?? 0 }));
  return { need, short };
}

export function check(s) {
  const sim = simulate(s); const issues = [...sim.issues];
  if (!s.direction) issues.push({ level: 'error', code: 'NO_DIRECTION', message: '還沒選處理方向：修復舊渠、先清淤，或保護育幼區。' });
  if (!sim.issues.length && sim.fields <= 0) issues.push({ level: 'error', code: 'NO_FIELDS', message: '水沒有送到村田進水口（北緣）。' });
  if (s.direction === 'clear_silt' && sim.creek <= 0)
    issues.push({ level: 'error', code: 'NO_DIVERSION', message: '清淤期間要暫時導流：用三通分一支水到溪道回流口（西緣），出口放收尾溢流台。' });
  for (const { material, need, have } of quote(s).short)
    issues.push({ level: 'error', code: 'NOT_ENOUGH', message: `${STOCK_ZH[material]}不夠：需要 ${need}，展示材料只有 ${have}。` });
  return { ok: !issues.length, issues, sim };
}

export const requestIdFor = s => `ww-${s.sessionId}-a${s.attempt}`;

// Finish once per requestId: a resend returns the stored receipt and never deducts materials twice.
export function finish(s, requestId = requestIdFor(s)) {
  if (s.receipts[requestId]) return { ok: true, replay: true, receipt: s.receipts[requestId] };
  if (s.finished) return { ok: false, code: 'ALREADY_FINISHED', message: '這個方案已用另一個請求完成。', receipt: s.receipts[s.finished] };
  const c = check(s); if (!c.ok) return { ok: false, code: 'NOT_READY', issues: c.issues };
  const real = simulate(s, { real: true }); const { need } = quote(s);
  for (const [m, n] of Object.entries(need)) s.stock[m] -= n;
  const surprises = [];
  if (real.fields < c.sim.fields) surprises.push(`實際到村田 ${real.fields} L/s，比預估 ${c.sim.fields} 少：${real.leaks.some(l => l.why === 'crack') ? '舊渠破槽在漏水' : '泥沙擋住了水'}。`);
  if (real.nursery.level > c.sim.nursery.level) surprises.push(`東側原來是育幼區，施工驚擾了牠們（${real.nursery.text}）。`);
  const receipt = {
    requestId, projectId: 'qingxi-waterworks-b:public-channel', attempt: s.attempt, outcomeId: OUTCOMES[s.direction], direction: s.direction,
    observationIds: s.observationIds, role: 'waterworks_builder', contribution: { pieces: Object.keys(s.pieces).length, note: '本機展示，不入正式貢獻' },
    materials: { spent: need, source: 'local-display-stock', note: '展示材料，不入正式背包' },
    plan: Object.entries(s.pieces).map(([k, p]) => ({ seg: p.seg, cell: k, type: p.type, model: PIECES[p.type].model, rot: p.rot, ...(p.open === undefined ? {} : { open: p.open }) }))
      .sort((a, b) => a.seg.localeCompare(b.seg)),
    result: { fieldsFlow: real.fields, fieldsSupplyPct: real.supply, creekFlow: real.creek, nursery: real.nursery.text, nurseryScore: real.nursery.score,
      leaks: real.leaks.map(l => ({ at: l.at, q: l.q, why: l.why })) },
    surprises,
  };
  s.receipts[requestId] = receipt; s.finished = requestId; s.log.push(`finish ${requestId}`);
  return { ok: true, replay: false, receipt };
}

// New attempt: same session, fresh local display stock, new requestId. Earlier receipts stay for comparison.
export function retry(s) {
  s.attempt += 1; s.finished = null; s.stock = { ...STOCK }; s.history = []; s.future = []; s.log.push(`retry a${s.attempt}`);
  return { ok: true, requestId: requestIdFor(s) };
}
