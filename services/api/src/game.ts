import { createHash, randomInt, randomUUID } from 'node:crypto';
import content from '../../../packages/content/world.json';
import { Action, Birth, Player, Snapshot, Stack, Talent, TechniqueStudy, World } from '../../../packages/contracts/types';
import { Database, Sql } from './database';
import { buildJournal, chapter } from './journal';
import estateContent from '../../../packages/content/estate.json';
import huntingContent from '../../../packages/content/hunting.json';
import techniqueContent from '../../../packages/content/techniques.json';
import fortuneContent from '../../../packages/content/fortunes.json';
import villageContent from '../../../packages/content/village.json';
import waterlineContent from '../../../packages/content/waterline.json';
import { AlchemyEvent, alchemyContent, judge, levelOf, modsFor, profileFor, simulate, validateLog, xpGain } from './alchemy';
import { judge as judgeTea, simulate as simulateTea, TeaEvent, teaById, teaContent, validateLog as validateTeaLog } from './tea';
import { AlchemyRecord, AlchemyState, AlchemyView, HuntDeath, HuntReceipt, HuntReward, TeaState, TeaView } from '../../../packages/contracts/types';

export { content, estateContent, huntingContent, techniqueContent };
export const SELECTION_DELAY_MS = 10 * 24 * 60 * 60 * 1000;
const DAY_MS = 24 * 60 * 60 * 1000;
function studyOf(player: Player): TechniqueStudy {
  return player.study ?? { focus: null, since: null, progressMs: {}, mastered: [] };
}
function settleStudy(player: Player, birth: Birth, now: number) {
  const study = studyOf(player);
  if (study.focus && study.since !== null && now > study.since && !study.mastered.includes(study.focus)) {
    const technique = techniqueContent.techniques.find(item => item.id === study.focus);
    if (technique) {
      const rate = birth.roots.includes(technique.affinity) ? birth.efficiency : 0.8;
      const limit = technique.days * DAY_MS;
      study.progressMs[study.focus] = Math.min(limit, (study.progressMs[study.focus] ?? 0) + (now - study.since) * rate);
    }
  }
  if (study.focus) study.since = Math.max(study.since ?? now, now);
  player.study = study;
}
export function teaOf(player: Player): TeaState {
  player.tea ??= { brews: 0, best: {}, session: null, restBonus: null, history: [] };
  return player.tea;
}
export function teaView(player: Player, now: number): TeaView {
  const t = player.tea ?? { brews: 0, best: {}, session: null, restBonus: null, history: [] };
  return {
    taught: player.milestones.includes(teaContent.lessonMilestone), brews: t.brews, session: t.session,
    restBonus: t.restBonus && t.restBonus.until > now ? t.restBonus : null, last: t.history[0] ?? null,
    teas: teaContent.teas.map(x => ({ id: x.id, label: x.label, owned: owned(player, x.id), idealScoops: x.idealScoops, hint: x.hint, best: t.best[x.id] ?? null })),
  };
}
export function alchemyOf(player: Player): AlchemyState {
  player.alchemy ??= { xp: 0, identified: [], recipes: {}, perfect: [], session: null, history: [] };
  return player.alchemy;
}
const owned = (player: Player, item: string) => player.inventory.filter(x => x.item === item).reduce((sum, x) => sum + x.quantity, 0);
const sectPath = (player: Player) => content.sects.find(x => x.id === player.sect)?.path ?? null;
const gradeRank = (grade: string) => alchemyContent.grades.findIndex(x => x.id === grade);
const PREP_LABEL: Record<string, string> = { raw: '生用', ground: '研末', dried: '陰乾', 'ground+dried': '研末又陰乾', scorched: '焦乾' };
const herbName = (id: string) => alchemyContent.herbs.find(x => x.id === id)?.label ?? (id === 'water' ? '注水' : id);
// Plain text lines for clients that cannot read keyed records (Unity JsonUtility).
function recordSummary(rec: AlchemyRecord) {
  return [
    '配比　' + Object.entries(rec.ratio).map(([k, v]) => herbName(k) + v).join('：'),
    '處理　' + Object.entries(rec.prep).map(([k, v]) => herbName(k) + (PREP_LABEL[v] ?? v)).join('、'),
    '順序　' + rec.order.map(herbName).join(' → '),
    '注水　' + rec.water + ' 瓢',
    '火候　' + rec.fire.join('，'),
    '收丹　丹香起後 ' + rec.condense.join('–') + ' 息',
    '最佳　' + (alchemyContent.grades.find(g => g.id === rec.bestGrade)?.label ?? rec.bestGrade) + '（' + rec.bestScore + ' 分），共煉 ' + rec.brews + ' 爐',
  ];
}
export function alchemyView(player: Player): AlchemyView {
  const a = player.alchemy ?? { xp: 0, identified: [], recipes: {}, perfect: [], session: null, history: [] };
  const lv = levelOf(a.xp);
  const unlocked = (m: { tier: number; level?: number; technique?: string }) => m.tier === 1 || lv.level >= (m.level ?? Infinity) || (!!m.technique && !!player.study?.mastered.includes(m.technique));
  const manuals = alchemyContent.manuals.map(m => ({ tier: m.tier, label: m.label, requirement: m.requirement, unlocked: unlocked(m), hints: unlocked(m) ? m.hints : {},
    lines: unlocked(m) ? alchemyContent.recipes.map(r => ({ recipe: r.id, lines: (m.hints as Record<string, string[]>)[r.id] ?? [] })) : [] }));
  const profile = a.session ? profileFor(a.session.herbs) : null;
  return {
    level: lv.level, xp: a.xp, into: lv.into, need: lv.need, manualTier: Math.max(...manuals.filter(m => m.unlocked).map(m => m.tier)), manuals,
    herbs: alchemyContent.herbs.map(h => { const known = a.identified.includes(h.id); return { id: h.id, label: h.label, identified: known, owned: owned(player, h.id), nature: known ? h.nature : null, use: known ? h.use : null, identifyHint: h.identifyHint }; }),
    recipes: alchemyContent.recipes.map(r => { const rec = a.recipes[r.id] ?? null; return { id: r.id, label: rec ? r.label : '？', known: !!rec, effect: rec ? r.effect : null, record: rec, summary: rec ? recordSummary(rec) : [], quick: !!rec && gradeRank(rec.bestGrade) >= gradeRank(alchemyContent.mastery.minGrade) }; }),
    fire: alchemyContent.fire, drying: { minSeconds: alchemyContent.drying.minSeconds, maxSeconds: alchemyContent.drying.maxSeconds }, grindStrokes: alchemyContent.grindStrokes,
    maxHerbEach: alchemyContent.maxHerbEach, maxFuel: alchemyContent.maxFuel, fuel: owned(player, alchemyContent.fuelItem),
    profile: profile && { recipe: profile.recipe, label: profile.label, phases: profile.phases },
  };
}
export const TERRITORY_PLOTS = 2;
export function estateOf(player: Player) { return player.estate ?? { cistern: false, bound: false, modes: ['rain','rain','rain','rain'] }; }
export class GameError extends Error {
  constructor(public code: string, message: string, public status = 400) { super(message); }
}
export function ensure(condition: unknown, code: string, message: string, status = 400): asserts condition {
  if (!condition) throw new GameError(code, message, status);
}
export const hash = (text: string) => createHash('sha256').update(text).digest('hex');
const elements = ['金', '木', '水', '火', '土'];
export function drawBirth(now: number, roll = randomInt(1_000_000), offset = randomInt(5)): Birth {
  if (!Number.isInteger(roll) || roll < 0 || roll >= 1_000_000) throw new Error('Invalid birth roll');
  let remaining = roll;
  const tier = content.birthWeights.find(row => { remaining -= row.weight; return remaining < 0; })!;
  return {
    tier: tier.id as Talent, label: tier.label,
    roots: Array.from({ length: tier.rootCount }, (_, index) => elements[(offset + index) % 5]),
    apertures: tier.apertures, constitution: tier.id === 'chosen' ? '先天道體' : tier.id === 'prodigy' ? '清靈體' : '凡體',
    efficiency: tier.efficiency, version: content.version, createdAt: now,
  };
}
function initialPlayer(id: string, name: string): Player {
  return { id, name, realm: 0, path: 'body', sect: '', body: 0, qi: 0, roots: [], apertures: 0,
    inventory: [
      { item: 'qingling-seed', quantity: 3, bound: false, potency: 100 },
      { item: 'lotus-seed', quantity: 2, bound: false, potency: 100 },
      { item: 'spirit-stone', quantity: 10, bound: false, potency: 100 },
    ], plots: [], jobs: [], clues: [], milestones: [], cooldowns: {}, contribution: 0 };
}
export function grant(player: Player, item: string, quantity: number, bound = false, potency = 100) {
  const stack = player.inventory.find(x => x.item === item && x.bound === bound && x.potency === potency);
  if (stack) stack.quantity += quantity;
  else player.inventory.push({ item, quantity, bound, potency });
}
export function spend(player: Player, item: string, quantity: number): { bound: boolean; potency: number } {
  const stacks = player.inventory.filter(x => x.item === item).sort((a, b) => Number(a.bound) - Number(b.bound));
  ensure(stacks.reduce((sum, x) => sum + x.quantity, 0) >= quantity, 'MATERIALS', `材料不足：${content.items.find(x => x.id === item)?.label ?? item}`);
  let left = quantity, bound = false, potency = 100;
  for (const stack of stacks) {
    const used = Math.min(left, stack.quantity);
    if (used > 0) { stack.quantity -= used; left -= used; bound ||= stack.bound; potency = Math.max(potency, stack.potency); }
  }
  player.inventory = player.inventory.filter(x => x.quantity > 0);
  return { bound, potency };
}
function integer(value: unknown, min: number, max: number): number {
  ensure(typeof value === 'number' && Number.isInteger(value) && value >= min && value <= max, 'INVALID_NUMBER', '數量或位置不正確');
  return value;
}
function text(value: unknown, max = 100): string {
  ensure(typeof value === 'string' && value.length > 0 && value.length <= max, 'INVALID_TEXT', '缺少必要欄位');
  return value;
}
const mark = (player: Player, milestone: string) => { if (!player.milestones.includes(milestone)) player.milestones.push(milestone); };
const fingerprint = (action: Action) => hash(JSON.stringify(Object.fromEntries(Object.entries(action).sort(([a], [b]) => a.localeCompare(b)))));
const uuid = (value: unknown): value is string => typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value);
// 機緣 (hidden finds): every reward item must exist and ids must be unique.
function validateFortuneContent() {
  const ids = new Set<string>();
  for (const fortune of fortuneContent.fortunes as { id: string; item?: string; quantity?: number }[]) {
    ensure(!ids.has(fortune.id), 'FORTUNE_CONTENT', '機緣編號重複'); ids.add(fortune.id);
    if (fortune.item) ensure(content.items.some(x => x.id === fortune.item) && Number.isInteger(fortune.quantity ?? 1) && (fortune.quantity ?? 1) > 0, 'FORTUNE_CONTENT', '機緣獎勵定義無效');
  }
}
validateFortuneContent();
// Village gathering nodes: every product must exist, ids unique, a positive regrow time.
function validateVillageContent() {
  ensure(Number.isInteger(villageContent.regrowSeconds) && villageContent.regrowSeconds > 0, 'VILLAGE_CONTENT', '採集再生時間無效');
  const ids = new Set<string>();
  for (const node of villageContent.nodes) {
    ensure(!ids.has(node.id), 'VILLAGE_CONTENT', '採集點編號重複'); ids.add(node.id);
    ensure(content.items.some(x => x.id === node.item), 'VILLAGE_CONTENT', '採集產物不存在');
  }
}
validateVillageContent();
function validateWaterlineContent() {
  const ids = (list: { id: string }[]) => new Set(list.map(x => x.id)).size === list.length;
  ensure(ids(waterlineContent.observations) && ids(waterlineContent.choices) && ids(waterlineContent.reports), 'WATERLINE_CONTENT', '斷流內容編號重複');
  ensure(waterlineContent.minObservations >= 1 && waterlineContent.minObservations <= waterlineContent.observations.length, 'WATERLINE_CONTENT', '線索門檻無效');
  for (const c of waterlineContent.choices) ensure(c.stone > 0 && c.channel > 0, 'WATERLINE_CONTENT', '導水方向的花費或成效無效');
}
validateWaterlineContent();
function validateHuntingContent() {
  ensure(huntingContent.roomId === 'qingxi' && huntingContent.version.length > 0, 'HUNT_CONTENT', '狩獵內容版本或區域無效');
  ensure(huntingContent.maxParticipants >= 1 && huntingContent.maxParticipants <= 4 && huntingContent.eventMaxAgeSeconds > 0, 'HUNT_CONTENT', '狩獵人數或時間限制無效');
  for (const enemy of huntingContent.enemies) {
    ensure(enemy.maxHealth > 0 && enemy.noticeRadiusM > enemy.fleeRadiusM && enemy.fleeRadiusM > 0 && enemy.leashRadiusM > enemy.noticeRadiusM && enemy.respawnSeconds > 0, 'HUNT_CONTENT', '山兔狀態數值無效');
    for (const drop of enemy.drops) ensure(content.items.some(x => x.id === drop.item) && Number.isInteger(drop.quantity) && drop.quantity > 0 && Number.isInteger(drop.chancePerMillion) && drop.chancePerMillion >= 0 && drop.chancePerMillion <= 1_000_000, 'HUNT_CONTENT', '山兔掉落定義無效');
  }
  for (const [item, price] of Object.entries(huntingContent.sellPrices)) ensure(content.items.some(x => x.id === item) && Number.isSafeInteger(price) && price > 0, 'HUNT_CONTENT', '狩獵售價無效');
}
function huntFingerprint(input: HuntDeath) {
  return hash(JSON.stringify({ deathId: input.deathId, roomId: input.roomId, spawnId: input.spawnId, enemyId: input.enemyId, occurredAt: input.occurredAt, participants: [...input.participants].sort() }));
}
function dropsFor(deathId: string, playerId: string, enemy: (typeof huntingContent.enemies)[number]) {
  return enemy.drops.filter(drop => {
    const roll = parseInt(hash(`${deathId}:${playerId}:${drop.item}`).slice(0, 8), 16) % 1_000_000;
    return roll < drop.chancePerMillion;
  }).map(drop => ({ item: drop.item, quantity: drop.quantity }));
}

export class Game {
  constructor(public db: Database, public options: { now?: () => number; birth?: () => Birth; speed?: number } = {}) {}
  now() { return this.options.now?.() ?? Date.now(); }
  get speed() { return this.options.speed ?? 1; }
  async initialize() {
    validateHuntingContent();
    await this.db.initialize();
    const world: World = { channel: 0, required: content.project.requiredStone, waterQuality: 20, sanctuary: false, history: [] };
    await this.db.query('INSERT INTO worlds(id,state) VALUES($1,$2) ON CONFLICT DO NOTHING', ['qingxi', JSON.stringify(world)]);
  }
  async playerFor(subject: string, name: string): Promise<string> {
    text(subject, 200); text(name, 32);
    const id = randomUUID();
    return this.db.transaction(async tx => {
      const player=initialPlayer(id,name);
      const inserted=await tx.query('INSERT INTO players(id,subject,state) VALUES($1,$2,$3) ON CONFLICT(subject) DO NOTHING RETURNING id', [id, subject, JSON.stringify(player)]);
      if(inserted.rows.length) {
        const createdAt=this.now(); const birth=this.options.birth?.() ?? drawBirth(createdAt);
        player.roots=[...birth.roots];player.apertures=birth.apertures;player.path='uncommitted';
        player.journey={version:1,createdAt,selectionAt:createdAt+SELECTION_DELAY_MS,assessedAt:null,manual:'qi-primer',housing:'lodging'};
        mark(player,'received:qi-primer');
        await tx.query('UPDATE players SET state=$2 WHERE id=$1',[id,JSON.stringify(player)]);
        await tx.query('INSERT INTO births(player_id,payload) VALUES($1,$2)',[id,JSON.stringify(birth)]);
        await tx.query('INSERT INTO ledger(actor_id,request_id,changes) VALUES($1,$2,$3)',[id,'system:create',JSON.stringify({kind:'create-character',before:[],after:player.inventory})]);
      }
      return (await tx.query<{ id: string }>('SELECT id FROM players WHERE subject=$1', [subject])).rows[0].id;
    });
  }
  async snapshot(id: string): Promise<Snapshot> {
    return this.db.transaction(async tx => {
      const result = await this.lock(tx, id);
      return this.toSnapshot(result.player, result.world, result.birth, result.version);
    });
  }
  private toSnapshot(player: Player, world: World, birth: Birth | null, version: number): Snapshot {
    const hidden=!!player.journey && player.journey.assessedAt===null;
    const projected=structuredClone(player);
    if (birth && projected.study) settleStudy(projected, birth, this.now());
    if (hidden && projected.study) projected.study.progressMs = {};
    const publicPlayer={...projected,roots:hidden?null:[...player.roots],apertures:hidden?null:player.apertures};
    return { player:publicPlayer, world, birth:hidden?null:birth, birthAssigned:!!birth, version, serverTime: this.now(), contentVersion: content.version, speed: this.speed, journal: buildJournal(player, birth), alchemy: alchemyView(player), tea: teaView(player, this.now()) };
  }
  private async lock(tx: Sql, id: string) {
    // All gameplay mutations use this lock order. One shared prototype world, no client authority.
    const world = (await tx.query<{ state: World }>('SELECT state FROM worlds WHERE id=$1 FOR UPDATE', ['qingxi'])).rows[0].state;
    const row = (await tx.query<{ state: Player; version: number }>('SELECT state,version FROM players WHERE id=$1 FOR UPDATE', [id])).rows[0];
    ensure(row, 'PLAYER_NOT_FOUND', '找不到修行身分', 404);
    const birth = (await tx.query<{ payload: Birth }>('SELECT payload FROM births WHERE player_id=$1', [id])).rows[0]?.payload ?? null;
    return { world, player: row.state, version: row.version, birth };
  }
  async act(id: string, requestId: string, action: Action): Promise<Snapshot> {
    text(requestId, 100); text(action.kind, 40);
    const digest = fingerprint(action);
    return this.db.transaction(async tx => {
      const state = await this.lock(tx, id);
      const previous = (await tx.query<{ fingerprint: string; result: Snapshot }>('SELECT fingerprint,result FROM receipts WHERE actor_id=$1 AND request_id=$2', [id, requestId])).rows[0];
      if (previous) {
        ensure(previous.fingerprint === digest, 'IDEMPOTENCY_CONFLICT', '相同請求編號不能用於不同操作', 409);
        // Reproject historical receipts for an unassessed character; never leak a private birth payload.
        if(state.player.journey?.assessedAt===null) {
          previous.result.birth=null;previous.result.player.roots=null;previous.result.player.apertures=null;
          if(previous.result.player.study)previous.result.player.study.progressMs={};
        }
        return previous.result;
      }
      const before = structuredClone(state.player.inventory);
      if (action.kind === 'sell-hunt') {
        const proximity = (await tx.query<{ valid_until: string }>('SELECT valid_until FROM merchant_proximity WHERE player_id=$1 AND room_id=$2 AND merchant_id=$3', [id, huntingContent.roomId, 'material-merchant'])).rows[0];
        ensure(proximity && Number(proximity.valid_until) > this.now(), 'MERCHANT_DISTANCE', '請到青溪材料商販面前出售', 409);
      }
      if (action.kind === 'birth') {
        if (!state.birth) {
          state.birth = this.options.birth?.() ?? drawBirth(this.now());
          state.player.roots = [...state.birth.roots]; state.player.apertures = state.birth.apertures;
          state.player.path = state.birth.tier === 'mortal' ? 'body' : 'spell';
          await tx.query('INSERT INTO births(player_id,payload) VALUES($1,$2)', [id, JSON.stringify(state.birth)]);
        }
      } else {
        ensure(state.birth, 'BIRTH_REQUIRED', '請先完成天賦分配');
        this.apply(state.player, state.world, state.birth, action);
      }
      state.version++;
      const result = this.toSnapshot(state.player, state.world, state.birth, state.version);
      await tx.query('UPDATE players SET state=$2,version=$3 WHERE id=$1', [id, JSON.stringify(state.player), state.version]);
      await tx.query('UPDATE worlds SET state=$2,version=version+1 WHERE id=$1', ['qingxi', JSON.stringify(state.world)]);
      await tx.query('INSERT INTO ledger(actor_id,request_id,changes) VALUES($1,$2,$3)', [id, requestId, JSON.stringify({ kind: action.kind, before, after: state.player.inventory })]);
      await tx.query('INSERT INTO receipts(actor_id,request_id,fingerprint,result) VALUES($1,$2,$3,$4)', [id, requestId, digest, JSON.stringify(result)]);
      return result;
    });
  }
  private apply(player: Player, world: World, birth: Birth, action: Action) {
    const now = this.now();
    if (player.study) settleStudy(player, birth, now);
    const cooldown = (key: string, seconds: number) => {
      ensure((player.cooldowns[key] ?? 0) <= now, 'COOLDOWN', '尚在調息，請稍後再試', 409);
      player.cooldowns[key] = now + seconds * 1000;
    };
    const history = (label: string) => { world.history.push({ player: player.name, action: label, at: now }); world.history = world.history.slice(-30); };
    // Newcomers farm their own territory (the lent old house) from day one, on its two fields.
    // The cistern, irrigation and the other two fields come with the sect residence.
    if(player.journey && ['build-cistern','configure-irrigation'].includes(action.kind))
      ensure(player.journey.housing==='cave','CAVE_REQUIRED','入宗後宗門分派的住處才有蓄水池與水路；新手領地可以先種兩塊田',409);
    if(player.journey && player.journey.housing==='lodging' && action.kind==='plant')
      ensure(integer(action.plot,0,3)<TERRITORY_PLOTS,'PLOT_LOCKED','新手領地只有兩塊靈田；入宗後住處有四塊',409);
    switch (action.kind) {
      case 'appraise': {
        ensure(player.journey,'LEGACY_ASSESSED','既有測試角色已沿用原本資質紀錄',409);
        ensure(now>=player.journey.selectionAt,'SELECTION_NOT_READY','創角滿十個現實日後，才可前往廣場測資',409);
        if(player.journey.assessedAt===null)player.journey.assessedAt=now;
        mark(player,'assessed');break;
      }
      case 'practice-basic': {
        ensure(player.journey?.manual==='qi-primer','PRIMER_REQUIRED','此操作適用已領取煉氣訣的新入世角色',409);
        ensure(['body','qi'].includes(action.discipline as string),'INVALID_DISCIPLINE','請選擇基礎武技或煉氣訣引氣');
        if(action.discipline==='qi')ensure(player.roots.length>0,'NO_ROOT','目前未感應靈氣，可先練基礎武技、藥浴淬體或探索後天開靈');
        cooldown('practice',15);
        if(action.discipline==='body')player.body+=Math.ceil(3*birth.efficiency)+(player.study?.mastered.includes('body-footwork')?1:0);
        else player.qi+=Math.ceil(3*birth.efficiency);
        mark(player,'practiced');break;
      }
      case 'focus-technique': {
        const technique = techniqueContent.techniques.find(item => item.id === action.technique);
        ensure(technique, 'UNKNOWN_TECHNIQUE', '找不到這門基礎技藝');
        const study = studyOf(player);
        ensure(!study.mastered.includes(technique.id), 'ALREADY_MASTERED', '這門技藝已完成入門', 409);
        study.focus = technique.id; study.since = now; player.study = study;
        mark(player, 'began-technique-study'); break;
      }
      case 'claim-technique': {
        ensure(!player.journey || player.journey.assessedAt!==null, 'ASSESSMENT_REQUIRED', '廣場測資後可確認技藝入門成果', 409);
        const technique = techniqueContent.techniques.find(item => item.id === action.technique);
        ensure(technique, 'UNKNOWN_TECHNIQUE', '找不到這門基礎技藝');
        const study = studyOf(player);
        ensure(!study.mastered.includes(technique.id), 'ALREADY_MASTERED', '這門技藝已完成入門', 409);
        ensure((study.progressMs[technique.id] ?? 0) >= technique.days * DAY_MS, 'STUDY_INCOMPLETE', '還需要繼續專注研習', 409);
        study.mastered.push(technique.id);
        if (study.focus === technique.id) { study.focus = null; study.since = null; }
        player.study = study; mark(player, `mastered:${technique.id}`); break;
      }
      case 'build-cistern': {
        const estate = estateOf(player);
        ensure(!estate.cistern, 'ALREADY_BUILT', '蓄水池已建成', 409);
        let bound = false;
        for (const cost of estateContent.cistern.cost) { const paid = spend(player, cost.item, cost.quantity); bound ||= paid.bound; }
        player.estate = { ...estate, modes: [...estate.modes], cistern: true, bound };
        mark(player, 'built:cistern'); break;
      }
      case 'configure-irrigation': {
        const index = integer(action.plot, 0, 3);
        const mode = estateContent.modes.find(x => x.id === action.mode);
        ensure(mode, 'INVALID_IRRIGATION', '未知的灌溉方式');
        ensure(!player.plots.some(x => x.index === index), 'PLOT_OCCUPIED', '請等這一茬收成後再調整水路', 409);
        const estate = estateOf(player); const modes = [...estate.modes]; modes[index] = mode.id;
        const used = modes.reduce((sum,id) => sum + estateContent.modes.find(x => x.id === id)!.water, 0);
        ensure(used <= (estate.cistern ? estateContent.cistern.capacity : 0), 'WATER_CAPACITY', '供水不足：先建蓄水池，或釋出其他空田的水路', 409);
        player.estate = { ...estate, modes }; break;
      }
      case 'tend-plot': {
        const index = integer(action.plot, 0, 3);
        const plot = player.plots.find(x => x.index === index);
        ensure(plot && plot.plantingId && plot.plantingId === action.plantingId, 'PLANTING_CHANGED', '這一茬作物已改變，請重新確認', 409);
        ensure(!plot.tended, 'ALREADY_TENDED', '這一茬已施過草肥', 409);
        ensure(now < plot.readyAt, 'CROP_MATURE', '已成熟的作物不需再照料', 409);
        const cost = spend(player, estateContent.tending.item, estateContent.tending.quantity);
        const crop = content.crops.find(x => x.id === plot.crop)!;
        plot.harvestYield = (plot.harvestYield ?? crop.yield) + estateContent.tending.extraYield;
        plot.bound ||= cost.bound; plot.tended = true; mark(player, 'tended'); break;
      }
      case 'talk': {
        const mentor = chapter.mentors.find(x => x.id === action.mentor);
        ensure(mentor && mentor.topics.some(x => x.id === action.topic), 'UNKNOWN_DIALOGUE', '找不到這段師承對話');
        mark(player, `talked:${mentor.id}`);
        mark(player, `topic:${mentor.id}:${action.topic}`);
        break;
      }
      case 'claim-quest': {
        if(player.journey?.assessedAt===null && chapter.quests.some(q=>q.id===action.quest && q.audience))
          throw new GameError('QUEST_NOT_READY','測資後再確認個人修行支線',409);
        const quest = buildJournal(player, birth).quests.find(x => x.id === action.quest);
        ensure(quest, 'UNKNOWN_QUEST', '此修行目標不存在或不適用');
        ensure(quest.status !== 'claimed', 'QUEST_CLAIMED', '已領取此修行成果', 409);
        ensure(quest.status === 'ready', 'QUEST_NOT_READY', '請先完成目標條件與前置手札', 409);
        for (const reward of quest.rewards) grant(player, reward.item, reward.quantity, true);
        mark(player, `quest:${quest.id}`);
        break;
      }
      case 'buy': {
        const offer = chapter.merchant.offers.find(x => x.id === action.offer);
        ensure(offer, 'UNKNOWN_OFFER', '找不到這項補給');
        const packs = integer(action.packs, 1, 10);
        const payment = spend(player, 'spirit-stone', offer.price * packs);
        grant(player, offer.item, offer.quantity * packs, payment.bound);
        mark(player, 'purchased-supplies');
        break;
      }
      case 'sell-hunt': {
        const item = text(action.item);
        const price = (huntingContent.sellPrices as Record<string, number>)[item];
        ensure(Number.isSafeInteger(price) && price > 0, 'NOT_SELLABLE', '這項材料不能在此出售');
        const quantity = integer(action.quantity, 1, 10);
        // The room server grants short-lived proximity only after checking the player's position.
        // This is checked by act() inside the same transaction before apply() runs.
        const unbound = player.inventory.filter(x => x.item === item && !x.bound);
        ensure(unbound.reduce((sum, x) => sum + x.quantity, 0) >= quantity, 'MATERIALS', '可出售的未綁定材料不足');
        let remaining = quantity;
        for (const stack of unbound) { const used = Math.min(remaining, stack.quantity); stack.quantity -= used; remaining -= used; }
        player.inventory = player.inventory.filter(x => x.quantity > 0);
        grant(player, 'spirit-stone', price * quantity);
        mark(player, 'sold-hunt');
        break;
      }
      case 'village-gather': {
        // One herb per node; the node regrows for this character after regrowSeconds (server clock).
        const node = villageContent.nodes.find(x => typeof action.node === 'string' && x.id === action.node);
        ensure(node, 'INVALID_NODE', '未知採集點');
        cooldown(`village:${node.id}`, villageContent.regrowSeconds);
        grant(player, node.item, 1);
        mark(player, 'gathered');
        break;
      }
      case 'discover-fortune': {
        // Each find is granted once per character; finding it again is harmless (no second reward).
        const fortune = (fortuneContent.fortunes as { id: string; item?: string; quantity?: number }[]).find(x => typeof action.fortune === 'string' && x.id === action.fortune);
        ensure(fortune, 'INVALID_FORTUNE', '未知的機緣');
        player.fortunes ??= [];
        if (!player.fortunes.includes(fortune.id)) {
          player.fortunes.push(fortune.id);
          if (fortune.item) grant(player, fortune.item, fortune.quantity ?? 1);
          mark(player, 'fortune');
        }
        break;
      }
      // 斷流第一章: A's upstream clues, B's water routing, C's report to the village.
      case 'observe-upstream': {
        const id = text(action.observation);
        ensure(waterlineContent.observations.some(x => x.id === id), 'INVALID_OBSERVATION', '未知的上游線索');
        // Kept apart from the chapter clues: the old 'resolve' route counts those.
        player.upstream ??= [];
        if (!player.upstream.includes(id)) { player.upstream.push(id); mark(player, 'upstream-observed'); }
        break;
      }
      case 'waterworks-commit': {
        const choice = waterlineContent.choices.find(x => x.id === action.choice);
        ensure(choice, 'INVALID_CHOICE', '未知的導水方向');
        const seen = (player.upstream ?? []).length;
        ensure(seen >= waterlineContent.minObservations, 'CLUE_REQUIRED', `先到上游找到至少 ${waterlineContent.minObservations} 處跡象`, 409);
        ensure(!player.milestones.includes(`waterworks:${choice.id}`), 'ALREADY_BUILT', '這個方向你已經完成了', 409);
        spend(player, 'stone', choice.stone);
        world.channel = Math.min(world.required, world.channel + choice.channel);
        if ('sanctuary' in choice && choice.sanctuary) world.sanctuary = true;
        player.contribution++;
        mark(player, `waterworks:${choice.id}`); mark(player, `outcome:${choice.outcome}`);
        history(`導水：${choice.label}`); break;
      }
      case 'village-report': {
        const report = waterlineContent.reports.find(x => x.id === action.report);
        ensure(report, 'INVALID_REPORT', '未知的回報');
        // Changing your mind is allowed; a report never grants anything.
        if (player.waterReport !== report.id) { player.waterReport = report.id; mark(player, 'village-reported'); }
        break;
      }
      case 'investigate': {
        const clue = text(action.clue);
        ensure(chapter.clues.some(x => x.id === clue), 'INVALID_CLUE', '未知線索');
        if (!player.clues.includes(clue)) player.clues.push(clue);
        break;
      }
      case 'gather': {
        const node = text(action.node); ensure(['quarry', 'seed-bank', 'herb-bank'].includes(node), 'INVALID_NODE', '未知採集點');
        cooldown(`gather:${node}`, 15);
        if (node === 'quarry') grant(player, 'stone', 3+(player.study?.mastered.includes('stone-sense')?1:0));
        if (node === 'seed-bank') { grant(player, 'qingling-seed', 1); grant(player, 'lotus-seed', 1); }
        if (node === 'herb-bank') grant(player, 'qingling-herb', 1+(player.study?.mastered.includes('herb-lore')?1:0));
        mark(player, 'gathered'); break;
      }
      case 'plant': {
        const plot = integer(action.plot, 0, 3); const crop = content.crops.find(x => x.id === action.crop);
        ensure(crop, 'INVALID_CROP', '未知作物'); ensure(!player.plots.some(x => x.index === plot), 'PLOT_OCCUPIED', '這塊田已有作物', 409);
        const seed = spend(player, crop.seed, 1);
        const estate = estateOf(player);
        const mode = estateContent.modes.find(x => x.id === estate.modes[plot])!;
        player.plots.push({ index: plot, crop: crop.id, plantedAt: now, readyAt: now + Math.ceil(crop.growthSeconds * 1000 / this.speed * mode.durationPercent / 100), bound: seed.bound || (mode.water > 0 && estate.bound), plantingId: randomUUID(), mode: mode.id, harvestYield: crop.yield + mode.extraYield, tended: false });
        mark(player, 'planted'); break;
      }
      case 'harvest': {
        const index = integer(action.plot, 0, 3); const plot = player.plots.find(x => x.index === index);
        ensure(plot, 'EMPTY_PLOT', '這塊田沒有作物', 409); ensure(plot.readyAt <= now, 'NOT_READY', '作物尚未成熟', 409);
        const crop = content.crops.find(x => x.id === plot.crop)!;
        grant(player, crop.item, plot.harvestYield ?? crop.yield, plot.bound); player.plots = player.plots.filter(x => x.index !== index);
        player.vein = (player.vein ?? 0) + 1; // 脈息: hidden, revealed by the story later (docs/story/world-lore-v1.md §七)
        mark(player, 'harvested'); break;
      }
      case 'craft': {
        const recipe = content.recipes.find(x => x.id === action.recipe); ensure(recipe, 'INVALID_RECIPE', '未知配方');
        ensure(player.jobs.filter(x => !x.claimed).length < 3, 'JOBS_FULL', '丹房工作位已滿', 409);
        let bound = false, potency = 100;
        if (action.useCompanion === true) {
          ensure(recipe.id === 'body-bath', 'INVALID_SUBSTITUTE', '此配方不接受替代材料');
          spend(player, 'companion-herb', 1); bound = true; potency = 110;
          spend(player, 'qingling-herb', 1);
        } else for (const ingredient of recipe.ingredients) {
          const used = spend(player, ingredient.item, ingredient.quantity); bound = used.bound || bound;
        }
        player.jobs.push({ id: randomUUID(), recipe: recipe.id, readyAt: now + recipe.seconds * 1000 / this.speed, bound, potency, claimed: false });
        break;
      }
      case 'claim-craft': {
        const job = player.jobs.find(x => x.id === action.job); ensure(job && !job.claimed, 'ALREADY_CLAIMED', '成品已領取或不存在', 409);
        ensure(job.readyAt <= now, 'NOT_READY', '尚未煉製完成', 409);
        const recipe = content.recipes.find(x => x.id === job.recipe)!;
        grant(player, recipe.output, recipe.quantity, job.bound, job.potency); job.claimed = true;
        player.jobs = player.jobs.filter(x => !x.claimed || x.id === job.id);
        mark(player, `crafted:${job.recipe}`); break;
      }
      case 'enroll': {
        const sect = content.sects.find(x => x.id === action.sect);
        ensure(sect && ['taixuan', 'xuanyue'].includes(sect.id), 'SECT_NOT_OPEN', '此階段開放太玄道院與玄岳宗');
        if(player.journey) {
          ensure(player.journey.assessedAt!==null,'ASSESSMENT_REQUIRED','滿十日後先到廣場測資，再選擇宗門',409);
          ensure(!player.sect || player.sect===sect.id,'TRANSFER_NOT_OPEN','新流程的轉宗規則尚未開放',409);
          player.journey.housing='cave';mark(player,'received:cave');
        }
        player.sect = sect.id; player.path = sect.path;
        break;
      }
      case 'practice': {
        ensure(player.sect, 'MENTOR_REQUIRED', '請先選擇師承'); cooldown('practice', 15);
        if (player.path === 'body') player.body += Math.ceil(5 * birth.efficiency);
        else { ensure(player.roots.length > 0, 'NO_ROOT', '目前無法引氣，可先向玄岳宗學習體修'); player.qi += Math.ceil(5 * birth.efficiency); }
        mark(player, 'practiced'); break;
      }
      case 'bathe': {
        const used = spend(player, 'body-bath', 1); player.body += Math.round(20 * used.potency / 100); mark(player, 'bathed'); break;
      }
      case 'awaken': {
        ensure(player.roots.length === 0, 'ALREADY_AWAKENED', '已能感應靈根', 409);
        ensure(player.body >= 40 && player.milestones.includes('bathed') && player.clues.length === 3, 'AWAKEN_REQUIREMENTS', '後天開靈需要體魄 40、完成藥浴並調查三處線索');
        player.roots.push('木'); player.apertures++; mark(player, 'awakened'); break;
      }
      case 'contribute': {
        ensure(player.clues.includes('broken-array'), 'CLUE_REQUIRED', '先調查破裂陣基');
        const requested = integer(action.quantity, 1, 12);
        const quantity = world.channel >= world.required ? 1 : Math.min(requested, world.required - world.channel);
        spend(player, 'stone', quantity); player.contribution += quantity;
        world.channel = Math.min(world.required, world.channel + quantity);
        history(world.channel >= world.required ? '維護／完成青溪水渠' : '修復青溪水渠'); break;
      }
      case 'resolve': {
        ensure(player.clues.length === 3, 'CLUE_REQUIRED', '請先完成三處調查');
        const route = text(action.route);
        ensure(['ecology', 'coexist'].includes(route), 'ROUTE_NOT_OPEN', '此路線尚未開放');
        ensure(!player.milestones.includes(`resolved:${route}`), 'ALREADY_RESOLVED', '此路線已完成', 409);
        if (route === 'ecology') { spend(player, 'water-purifier', 1); world.waterQuality = Math.min(100, world.waterQuality + 40); history('種下淨水陣，改善水質'); }
        else { spend(player, 'qingling-herb', 2); world.sanctuary = true; history('為靈獸留下棲地'); }
        player.contribution++; mark(player, `resolved:${route}`); break;
      }
      case 'claim-project': {
        ensure(world.channel >= world.required, 'PROJECT_NOT_READY', '水渠尚未修復');
        ensure(player.contribution > 0, 'PARTICIPATION_REQUIRED', '參與修復、維護或生態路線即可領取');
        ensure(!player.milestones.includes('project-reward'), 'ALREADY_CLAIMED', '已領取共同成果', 409);
        grant(player, 'spirit-stone', content.project.reward, true); mark(player, 'project-reward'); break;
      }
      case 'breakthrough': {
        ensure(player.realm === 0, 'ALREADY_ASCENDED', '已完成本階段突破', 409);
        ensure(player.sect && (player.path === 'body' ? player.body : player.qi) >= 100, 'CULTIVATION_REQUIRED', '主修進度需達 100');
        ensure(player.clues.length === 3 && player.milestones.includes('project-reward') && player.milestones.some(x => x.startsWith('crafted:')), 'TRIAL_REQUIRED', '完成調查、煉製與共同工程成果後再來試煉');
        player.realm = 1; mark(player, 'first-breakthrough'); break;
      }
      case 'tea-lesson': {
        ensure(!player.milestones.includes(teaContent.lessonMilestone), 'ALREADY_TAUGHT', '茶亭老人已經教過你泡茶了', 409);
        for (const g of teaContent.lesson.grant) grant(player, g.item, g.quantity, true);
        mark(player, teaContent.lessonMilestone); break;
      }
      case 'tea-begin': {
        ensure(player.milestones.includes(teaContent.lessonMilestone), 'TEA_NOT_TAUGHT', '先到茶亭向老人學泡茶', 409);
        const t = teaOf(player); ensure(!t.session, 'TEA_BUSY', '茶爐上已經有一壺水了', 409);
        const tea = teaById(action.tea); ensure(tea, 'INVALID_TEA', '請選擇青溪野茶或梅花茶');
        const scoops = integer(action.scoops, teaContent.minScoops, teaContent.maxScoops);
        t.session = { tea: tea.id, scoops, bound: spend(player, tea.id, scoops).bound, startedAt: now }; break;
      }
      case 'tea-abandon': {
        const t = teaOf(player); const s = t.session; ensure(s, 'NO_TEA', '茶爐上沒有在燒的水', 409);
        grant(player, s.tea, s.scoops, s.bound); t.session = null; break;   // leaves never go to waste
      }
      case 'tea-finish': {
        const t = teaOf(player); const s = t.session; ensure(s, 'NO_TEA', '茶爐上沒有在燒的水', 409);
        const invalid = validateTeaLog(action.log); ensure(!invalid, 'INVALID_LOG', `泡茶紀錄不合法（${invalid}）`);
        const log = action.log as TeaEvent[];
        ensure(now - s.startedAt + 1500 >= log[log.length - 1].t * 100 / this.speed, 'LOG_TOO_FAST', '泡茶紀錄比實際經過時間更長', 409);
        const tea = teaById(s.tea)!;
        const out = judgeTea(simulateTea(log, tea, s.scoops), tea, s.scoops);
        const brew = { at: now, tea: tea.id, scoops: s.scoops, result: out.result, label: out.label, score: out.score, brewTemp: out.brewTemp, steepSeconds: out.steepSeconds, describe: out.describe, reasons: out.reasons };
        // Every cup is drunk: the rest bonus is a parameter for bed rest healing (not wired to healing yet).
        t.restBonus = { multiplier: out.restMultiplier, until: now + teaContent.restBonusMinutes * 60_000 / this.speed };
        t.brews++; if (out.result === 'good') t.best[tea.id] = Math.max(t.best[tea.id] ?? 0, out.score);
        t.history.unshift(brew); t.history = t.history.slice(0, 10);
        t.session = null; mark(player, 'tea:brewed'); if (out.result === 'good') mark(player, `tea:good:${tea.id}`); break;
      }
      case 'alchemy-identify': {
        const a = alchemyOf(player); const herb = alchemyContent.herbs.find(x => x.id === action.item);
        ensure(herb, 'INVALID_HERB', '這不是可辨識的藥材');
        ensure(owned(player, herb.id) > 0, 'HERB_MISSING', `身上沒有${herb.label}，無從辨識`, 409);
        ensure(!a.identified.includes(herb.id), 'ALREADY_IDENTIFIED', `${herb.label}已辨識`, 409);
        a.identified.push(herb.id); mark(player, `identified:${herb.id}`); break;
      }
      case 'alchemy-begin': {
        const a = alchemyOf(player);
        ensure(!a.session, 'ALCHEMY_BUSY', a.session?.result ? '上一爐丹藥尚未裝瓶領取' : '丹爐中已有一爐進行中', 409);
        ensure(Array.isArray(action.herbs) && action.herbs.length === alchemyContent.herbs.length, 'INVALID_HERBS', '請選擇青靈草與淨水蓮兩味藥材');
        const rows = action.herbs as { item?: unknown; quantity?: unknown }[];
        const herbs = alchemyContent.herbs.map(h => {
          const row = rows.find(x => x && x.item === h.id); ensure(row, 'INVALID_HERBS', `缺少${h.label}`);
          ensure(a.identified.includes(h.id), 'HERB_UNIDENTIFIED', `請先在藥櫃辨識${h.label}`, 409);
          return { item: h.id, quantity: integer(row.quantity, 1, alchemyContent.maxHerbEach) };
        });
        const fuel = integer(action.fuel, 1, alchemyContent.maxFuel);
        // Spend throws before any partial write survives: the whole transaction rolls back.
        const locks = herbs.map(h => ({ ...h, bound: spend(player, h.item, h.quantity).bound }));
        const fuelBound = spend(player, alchemyContent.fuelItem, fuel).bound;
        a.session = { id: randomUUID(), recipe: profileFor(herbs).recipe, herbs: locks, fuel, fuelBound, startedAt: now, charged: false, result: null };
        mark(player, 'alchemy:begun'); break;
      }
      case 'alchemy-charge': {
        const s = alchemyOf(player).session;
        ensure(s && !s.result, 'NO_BREW', '目前沒有進行中的一爐', 409);
        s.charged = true; break;
      }
      case 'alchemy-abandon': {
        const a = alchemyOf(player); const s = a.session;
        ensure(s && !s.result, 'NO_BREW', '目前沒有進行中的一爐', 409);
        if (!s.charged) { for (const h of s.herbs) grant(player, h.item, h.quantity, h.bound); grant(player, alchemyContent.fuelItem, s.fuel, s.fuelBound); }
        else grant(player, alchemyContent.residueItem, 1, s.herbs.some(h => h.bound));
        a.history.unshift({ at: now, recipe: s.recipe, label: s.charged ? '棄爐（材料已入爐）' : '取消（材料退回）', score: 0, quick: false, reasons: [] });
        a.history = a.history.slice(0, 20); a.session = null; break;
      }
      case 'alchemy-finish': {
        const a = alchemyOf(player); const s = a.session;
        ensure(s && !s.result, 'NO_BREW', '目前沒有進行中的一爐', 409);
        ensure(s.charged, 'NOT_CHARGED', '尚未投料入爐', 409);
        const herbIds = s.herbs.map(h => h.item);
        const invalid = validateLog(action.log, herbIds, s.fuel);
        ensure(!invalid, 'INVALID_LOG', `煉丹紀錄不合法（${invalid}）`);
        const log = action.log as AlchemyEvent[];
        ensure(now - s.startedAt + 1500 >= log[log.length - 1].t * 100 / this.speed, 'LOG_TOO_FAST', '煉丹紀錄比實際經過時間更長', 409);
        const profile = profileFor(s.herbs); const mods = modsFor(birth.tier, birth.roots, sectPath(player));
        const sim = simulate(log, herbIds, profile, mods); const out = judge(sim, s.herbs, profile, mods);
        const P = alchemyContent.proficiency; const talentXp = (alchemyContent.talents as Record<string, { xp: number }>)[birth.tier]?.xp ?? 1;
        const recipe = alchemyContent.recipes.find(x => x.id === profile.recipe);
        let gain = xpGain(out.success ? P.success : P.fail, a.xp, talentXp), first = false;
        if (out.success && recipe) {
          const rec = a.recipes[recipe.id]; first = !rec;
          if (first) { gain += xpGain(P.firstUnlock, a.xp, talentXp); mark(player, `alchemy-recipe:${recipe.id}`); }
          if (out.grade === 'ji' && !a.perfect.includes(recipe.id)) { a.perfect.push(recipe.id); gain += xpGain(P.firstPerfect, a.xp, talentXp); }
          const better = !rec || out.score > rec.bestScore;
          a.recipes[recipe.id] = better ? {
            ratio: Object.fromEntries(s.herbs.map(h => [h.item, h.quantity])), prep: sim.prep, order: sim.order, water: sim.water,
            fire: profile.phases.map(p => `${p.label} ${p.low}–${p.high}`), condense: recipe.condense.best,
            bestGrade: out.grade!, bestScore: out.score, firstAt: rec?.firstAt ?? now, brews: (rec?.brews ?? 0) + 1,
          } : { ...rec, brews: rec.brews + 1 };
        }
        a.xp += gain;
        const fuelReturned = s.fuel - sim.fuelUsed;
        if (fuelReturned > 0) grant(player, alchemyContent.fuelItem, fuelReturned, s.fuelBound);
        const bound = s.herbs.some(h => h.bound) || s.fuelBound;
        const total = s.herbs.reduce((sum, h) => sum + h.quantity, 0);
        if (!out.success) grant(player, alchemyContent.residueItem, 1, bound);
        s.result = {
          ...out, output: out.success && recipe ? recipe.output : null, quantity: out.success ? Math.max(1, Math.floor(total / 3)) : 0, bound,
          residue: out.success ? 0 : 1, firstUnlock: first, xpGain: gain, level: levelOf(a.xp).level, fuelUsed: sim.fuelUsed, fuelReturned,
        };
        a.history.unshift({ at: now, recipe: profile.recipe, label: `${profile.label}・${out.label}`, score: out.score, quick: false, reasons: out.reasons.slice(0, 4) });
        a.history = a.history.slice(0, 20); mark(player, 'alchemy:finished'); break;
      }
      case 'alchemy-claim': {
        const a = alchemyOf(player); const s = a.session;
        ensure(s && s.result, 'NOTHING_TO_CLAIM', '沒有待裝瓶的丹藥', 409);
        if (s.result.success && s.result.output) { grant(player, s.result.output, s.result.quantity, s.result.bound, s.result.potency); mark(player, `alchemy-crafted:${s.recipe}`); }
        a.session = null; break;
      }
      case 'alchemy-quick': {
        const a = alchemyOf(player);
        ensure(!a.session, 'ALCHEMY_BUSY', '丹爐正在使用中', 409);
        const recipe = alchemyContent.recipes.find(x => x.id === action.recipe); ensure(recipe, 'INVALID_RECIPE', '未知丹方');
        const rec = a.recipes[recipe.id];
        ensure(rec && gradeRank(rec.bestGrade) >= gradeRank(alchemyContent.mastery.minGrade), 'NOT_MASTERED', '需曾親手煉出良品以上才能快速煉製', 409);
        let bound = false;
        for (const [item, quantity] of Object.entries(recipe.ratio)) bound = spend(player, item, quantity).bound || bound;
        bound = spend(player, alchemyContent.fuelItem, recipe.quick.fuel).bound || bound;
        const P = alchemyContent.proficiency; const talentXp = (alchemyContent.talents as Record<string, { xp: number }>)[birth.tier]?.xp ?? 1;
        const good = levelOf(a.xp).level >= alchemyContent.mastery.quickGoodLevel;
        const grade = alchemyContent.grades.find(g => g.id === (good ? 'liang' : 'fan'))!;
        grant(player, recipe.output, 1, bound, grade.potency);
        a.xp += xpGain(P.quick, a.xp, talentXp); rec.brews++;
        a.history.unshift({ at: now, recipe: recipe.id, label: `${recipe.label}・快速煉製・${grade.label}`, score: 0, quick: true, reasons: [] });
        a.history = a.history.slice(0, 20); mark(player, `alchemy-crafted:${recipe.id}`); break;
      }
      case 'alchemy-use': {
        ensure(action.item === 'huichun-pill' || action.item === 'juqi-pill', 'INVALID_PILL', '這不是可服用的丹藥');
        // spend() reports the highest potency, so pick one stack of the requested grade explicitly.
        const potency = action.potency === undefined || action.potency === 0 ? undefined : integer(action.potency, 1, 1000);
        const stack = player.inventory.filter(x => x.item === action.item && x.quantity > 0 && (potency === undefined || x.potency === potency))
          .sort((a, b) => b.potency - a.potency)[0];
        ensure(stack, 'MATERIALS', '沒有這種丹藥');
        stack.quantity--; player.inventory = player.inventory.filter(x => x.quantity > 0);
        if (action.item === 'huichun-pill') player.body += Math.round(8 * stack.potency / 100);
        else player.qi += Math.round(15 * stack.potency / 100);
        mark(player, `took:${action.item}`); break;
      }
      default: throw new GameError('UNKNOWN_ACTION', '未知操作');
    }
  }
  async markMerchantProximity(playerId: string, roomId: string, merchantId: string) {
    ensure(uuid(playerId) && roomId === huntingContent.roomId && merchantId === 'material-merchant', 'INVALID_MERCHANT_VISIT', '商販位置資料無效');
    await this.db.transaction(async tx => {
      const row = (await tx.query('SELECT id FROM players WHERE id=$1', [playerId])).rows[0];
      ensure(row, 'PLAYER_NOT_FOUND', '找不到修行身分', 404);
      await tx.query('INSERT INTO merchant_proximity(player_id,room_id,merchant_id,valid_until) VALUES($1,$2,$3,$4) ON CONFLICT(player_id) DO UPDATE SET room_id=$2,merchant_id=$3,valid_until=$4', [playerId, roomId, merchantId, this.now() + 30_000]);
    });
    return { playerId, validForSeconds: 30 };
  }
  async settleHuntDeath(input: HuntDeath): Promise<HuntReceipt> {
    ensure(input && typeof input === 'object' && !Array.isArray(input), 'INVALID_HUNT', '擊殺資料無效');
    ensure(Object.keys(input).sort().join(',') === 'deathId,enemyId,occurredAt,participants,roomId,spawnId', 'INVALID_HUNT', '擊殺欄位無效');
    ensure(uuid(input.deathId) && uuid(input.spawnId) && input.roomId === huntingContent.roomId, 'INVALID_HUNT', '擊殺識別或區域無效');
    ensure(typeof input.occurredAt === 'number' && Number.isSafeInteger(input.occurredAt), 'INVALID_HUNT', '擊殺時間無效');
    ensure(Array.isArray(input.participants) && input.participants.length >= 1 && input.participants.length <= huntingContent.maxParticipants && input.participants.every(uuid) && new Set(input.participants).size === input.participants.length, 'INVALID_HUNT', '參與名單無效');
    const enemy = huntingContent.enemies.find(x => x.id === input.enemyId);
    ensure(enemy, 'UNKNOWN_ENEMY', '未知的狩獵目標');
    const digest = huntFingerprint(input);
    return this.db.transaction(async tx => {
      // Match act() lock order (world, then players) and serialize competing deaths for one spawn.
      await tx.query('SELECT id FROM worlds WHERE id=$1 FOR UPDATE', [huntingContent.roomId]);
      const existing = (await tx.query<{ fingerprint: string; receipt: HuntReceipt }>('SELECT fingerprint,receipt FROM hunt_deaths WHERE death_id=$1', [input.deathId])).rows[0];
      if (existing) {
        ensure(existing.fingerprint === digest, 'HUNT_CONFLICT', '擊殺識別已用於不同事件', 409);
        return existing.receipt;
      }
      const duplicateSpawn = (await tx.query('SELECT death_id FROM hunt_deaths WHERE room_id=$1 AND spawn_id=$2', [input.roomId, input.spawnId])).rows[0];
      ensure(!duplicateSpawn, 'HUNT_ALREADY_SETTLED', '這次山兔出生已結算', 409);
      const age = this.now() - input.occurredAt;
      ensure(age >= -5_000 && age <= huntingContent.eventMaxAgeSeconds * 1000, 'HUNT_EXPIRED', '擊殺事件過期或時間無效', 409);
      const rewards: HuntReward[] = [];
      for (const playerId of [...input.participants].sort()) {
        const row = (await tx.query<{ state: Player }>('SELECT state FROM players WHERE id=$1 FOR UPDATE', [playerId])).rows[0];
        ensure(row, 'PLAYER_NOT_FOUND', '參與者不存在', 404);
        const before = structuredClone(row.state.inventory);
        const items = dropsFor(input.deathId, playerId, enemy);
        for (const item of items) grant(row.state, item.item, item.quantity);
        await tx.query('UPDATE players SET state=$2,version=version+1 WHERE id=$1', [playerId, JSON.stringify(row.state)]);
        await tx.query('INSERT INTO ledger(actor_id,request_id,changes) VALUES($1,$2,$3)', [playerId, `hunt:${input.deathId}`, JSON.stringify({ kind: 'hunt', before, after: row.state.inventory, spawnId: input.spawnId })]);
        rewards.push({ playerId, items });
      }
      const receipt = { deathId: input.deathId, roomId: input.roomId, spawnId: input.spawnId, rewards };
      await tx.query('INSERT INTO hunt_deaths(death_id,room_id,spawn_id,fingerprint,receipt,occurred_at) VALUES($1,$2,$3,$4,$5,$6)', [input.deathId, input.roomId, input.spawnId, digest, JSON.stringify(receipt), input.occurredAt]);
      return receipt;
    });
  }
  async receiveTransfer(input: { id: string; playerId: string; linkId: string; quantity: number; cancel?: boolean }) {
    text(input.id); text(input.linkId); integer(input.quantity, 1, 4);
    return this.db.transaction(async tx => {
      const state = await this.lock(tx, input.playerId);
      const previous = (await tx.query<{ player_id: string; link_id: string; quantity: number; status: string }>('SELECT * FROM transfers WHERE id=$1', [input.id])).rows[0];
      if (previous) {
        ensure(previous.player_id === input.playerId && previous.link_id === input.linkId && previous.quantity === input.quantity, 'TRANSFER_CONFLICT', '輸送識別已用於不同內容', 409);
        ensure(!(input.cancel && previous.status === 'received'), 'TRANSFER_RECEIVED', '已入帳，不能退回來源', 409);
        return { id: input.id, status: previous.status };
      }
      const link = (await tx.query('SELECT id FROM companion_links WHERE id=$1 AND player_id=$2 AND active=true', [input.linkId, input.playerId])).rows[0];
      ensure(link, 'LINK_REQUIRED', '找不到有效綁定', 409);
      ensure(state.birth, 'BIRTH_REQUIRED', '請先完成天賦分配');
      const status = input.cancel ? 'cancelled' : 'received';
      if (!input.cancel) {
        const row = (await tx.query<{ used: string }>("SELECT COALESCE(sum(quantity),0)::text AS used FROM transfers WHERE player_id=$1 AND status='received' AND at_ms > $2", [input.playerId, this.now() - content.transfer.windowDays * 86400000])).rows[0];
        ensure(Number(row.used) + input.quantity <= content.transfer.maximumHerbs, 'TRANSFER_LIMIT', '連續 28 日最多接收 4 株', 409);
        const before = structuredClone(state.player.inventory);
        grant(state.player, 'companion-herb', input.quantity, true);
        await tx.query('UPDATE players SET state=$2,version=version+1 WHERE id=$1', [input.playerId, JSON.stringify(state.player)]);
        await tx.query('INSERT INTO ledger(actor_id,request_id,changes) VALUES($1,$2,$3)', [input.playerId, `transfer:${input.id}`, JSON.stringify({ before, after: state.player.inventory })]);
      }
      await tx.query('INSERT INTO transfers(id,player_id,link_id,quantity,status,at_ms) VALUES($1,$2,$3,$4,$5,$6)', [input.id, input.playerId, input.linkId, input.quantity, status, this.now()]);
      return { id: input.id, status };
    });
  }
}
