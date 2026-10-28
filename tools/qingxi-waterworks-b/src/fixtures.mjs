// Local fixtures standing in for A's observation export (docs/execution/2026-10-29/10-waterline-revised-brief.md):
// A outputs `observationIds` from { cracked_sluice, silt_buildup, nursery_tracks }; the player may miss any of them.
// Copied ids only; nothing is imported from A's branch.

export const OBSERVATIONS = Object.freeze({
  cracked_sluice: { label: '破槽', reveals: 'crack', text: '舊渠中段石槽裂開，水從裂口漏掉。' },
  silt_buildup: { label: '泥沙堆積', reveals: 'silt', text: '舊渠上段積了泥沙，水過不去多少。' },
  nursery_tracks: { label: '育幼足跡', reveals: 'nursery', text: '舊渠東側有幼獸足跡，那裡是牠們的育幼區。' },
});

// Unknown-risk text shown while a clue is missing (the player can still try).
export const UNKNOWN = Object.freeze({
  crack: '舊渠中段狀況未確認：走這段可能會漏水。',
  silt: '舊渠上段狀況未確認：實際水量可能比預估少。',
  nursery: '東側那片草叢未確認：施工可能驚擾到什麼。',
});

export const FIXTURES = Object.freeze({
  all: { id: 'all', label: '三條線索都看到', observationIds: ['cracked_sluice', 'silt_buildup', 'nursery_tracks'] },
  two: { id: 'two', label: '漏看育幼足跡', observationIds: ['cracked_sluice', 'silt_buildup'] },
  one: { id: 'one', label: '只看到破槽', observationIds: ['cracked_sluice'] },
  none: { id: 'none', label: '沒有線索', observationIds: [] },
});

export function knownHazards(observationIds) {
  const ids = new Set(observationIds.filter(id => OBSERVATIONS[id]));
  return Object.fromEntries(Object.values(OBSERVATIONS).map(o => [o.reveals, [...ids].some(id => OBSERVATIONS[id].reveals === o.reveals)]));
}
