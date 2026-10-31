export type Talent = 'mortal' | 'ordinary' | 'gifted' | 'prodigy' | 'chosen';
export interface Birth {
  tier: Talent; label: string; roots: string[]; apertures: number;
  constitution: string; efficiency: number; version: string; createdAt: number;
}
export interface Stack { item: string; quantity: number; bound: boolean; potency: number }
export interface Plot { index: number; crop: string; plantedAt: number; readyAt: number; bound: boolean; plantingId?: string; mode?: string; harvestYield?: number; tended?: boolean }
export interface Estate { cistern: boolean; bound: boolean; modes: string[] }
export interface CraftJob { id: string; recipe: string; readyAt: number; bound: boolean; potency: number; claimed: boolean }
export interface Journey {
  version: 1; createdAt: number; selectionAt: number; assessedAt: number | null;
  manual: 'qi-primer'; housing: 'lodging' | 'cave';
}
export interface TechniqueStudy {
  focus: string | null; since: number | null;
  progressMs: Record<string, number>; mastered: string[];
}
export interface Player {
  id: string; name: string; realm: number; path: string; sect: string;
  body: number; qi: number; roots: string[]; apertures: number;
  inventory: Stack[]; plots: Plot[]; jobs: CraftJob[]; clues: string[];
  milestones: string[]; cooldowns: Record<string, number>; contribution: number;
  estate?: Estate;
  journey?: Journey;
  study?: TechniqueStudy;
  alchemy?: AlchemyState;
  tea?: TeaState;        // 第 1 天・在家泡茶 (packages/content/tea-brewing-v1.json)
  upstream?: string[];  // 斷流第一章: upstream signs this character found (ids from packages/content/waterline.json)
  waterReport?: string; // 斷流第一章: what this character told the village (tell_shortage | inspect_crack | protect_nursery)
  vein?: number;        // 脈息: harvests that fed the spirit vein; hidden from players for now
  fortunes?: string[];   // 機緣 found by this character (ids from packages/content/fortunes.json)
}
export interface World {
  channel: number; required: number; waterQuality: number; sanctuary: boolean;
  history: { player: string; action: string; at: number }[];
}
export interface QuestProgress {
  id: string; title: string; description: string; optional: boolean; hint: string;
  status: 'locked' | 'active' | 'ready' | 'claimed'; blockedBy: string[];
  objectives: { label: string; current: number; target: number; complete: boolean }[];
  rewards: { item: string; quantity: number; bound: boolean }[];
}
export interface Journal {
  chapterId: string; title: string; introduction: string; completed: number; total: number;
  finished: boolean; nextQuestId: string | null; guidance: string; quests: QuestProgress[];
}
// Null means undisclosed, not "no spiritual root" / "zero apertures".
export type PublicPlayer = Omit<Player, 'roots' | 'apertures'> & { roots: string[] | null; apertures: number | null };
export interface Snapshot { player: PublicPlayer; birth: Birth | null; birthAssigned: boolean; world: World; serverTime: number; version: number; contentVersion: string; speed: number; journal: Journal; alchemy?: AlchemyView; tea?: TeaView }
export interface Action { kind: string; [key: string]: unknown }
export interface HuntDeath {
  deathId: string;
  roomId: string;
  spawnId: string;
  enemyId: string;
  occurredAt: number;
  participants: string[];
}
export interface HuntReward { playerId: string; items: { item: string; quantity: number }[] }
export interface HuntReceipt { deathId: string; roomId: string; spawnId: string; rewards: HuntReward[] }

export interface AlchemyHerbLock { item: string; quantity: number; bound: boolean }
export interface AlchemyResult {
  success: boolean; grade: string | null; label: string; score: number;
  parts: { ratio: number; prep: number; fire: number; condense: number }; reasons: string[];
  output: string | null; quantity: number; potency: number; bound: boolean; residue: number;
  firstUnlock: boolean; xpGain: number; level: number; fuelUsed: number; fuelReturned: number;
}
export interface AlchemySession {
  id: string; recipe: string | null; herbs: AlchemyHerbLock[]; fuel: number; fuelBound: boolean;
  startedAt: number; charged: boolean; result: AlchemyResult | null;
}
export interface AlchemyRecord {
  ratio: Record<string, number>; prep: Record<string, string>; order: string[]; water: number;
  fire: string[]; condense: number[]; bestGrade: string; bestScore: number; firstAt: number; brews: number;
}
export interface AlchemyHistory { at: number; recipe: string | null; label: string; score: number; quick: boolean; reasons: string[] }
export interface AlchemyState {
  xp: number; identified: string[]; recipes: Record<string, AlchemyRecord>; perfect: string[];
  session: AlchemySession | null; history: AlchemyHistory[];
}
export interface TeaSession { tea: string; scoops: number; bound: boolean; startedAt: number }
export interface TeaBrew { at: number; tea: string; scoops: number; result: 'weak' | 'good' | 'bitter'; label: string; score: number; brewTemp: number; steepSeconds: number; describe: string; reasons: string[] }
export interface TeaState { brews: number; best: Record<string, number>; session: TeaSession | null; restBonus: { multiplier: number; until: number } | null; history: TeaBrew[] }
export interface TeaView {
  taught: boolean; brews: number; session: TeaSession | null; restBonus: { multiplier: number; until: number } | null; last: TeaBrew | null;
  teas: { id: string; label: string; owned: number; idealScoops: number; hint: string; best: number | null }[];
}
export interface AlchemyView {
  level: number; xp: number; into: number; need: number; manualTier: number;
  manuals: { tier: number; label: string; requirement: string; unlocked: boolean; hints: Record<string, string[]>; lines: { recipe: string; lines: string[] }[] }[];
  herbs: { id: string; label: string; identified: boolean; owned: number; nature: string | null; use: string | null; identifyHint: string }[];
  recipes: { id: string; label: string; known: boolean; effect: string | null; record: AlchemyRecord | null; summary: string[]; quick: boolean }[];
  fire: Record<string, number>; drying: { minSeconds: number; maxSeconds: number }; grindStrokes: number;
  maxHerbEach: number; maxFuel: number; fuel: number;
  profile: { recipe: string | null; label: string; phases: { label: string; fire: string; low: number; high: number; seconds: number }[] } | null;
}
