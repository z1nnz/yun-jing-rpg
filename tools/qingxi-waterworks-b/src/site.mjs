// Waterworks site and piece catalogue for the local demo.
//
// The site is a 7 x 6 grid of logical cells (x east, y north; one cell is roughly one metre of trough). Gameplay is
// decided on this grid; the 3D view snaps the real GLBs port to port along the same connections, so a cell is a
// slot, not a scale. Every piece id below is a kit model in art/exports/qingxi-waterworks-b/.

export const W = 7, H = 6;
export const SIDES = ['N', 'E', 'S', 'W'];
export const STEP = { N: [0, 1], E: [1, 0], S: [0, -1], W: [-1, 0] };
export const OPP = { N: 'S', E: 'W', S: 'N', W: 'E' };
export const SIDE_ZH = { N: '北', E: '東', S: '南', W: '西' };

// Ports at rotation 0 (side names). Rotation r turns the piece r quarter turns clockwise (N -> E -> S -> W).
// `model` / `ports` name the GLB and its model_info ports in the same order as `sides`.
export const PIECES = Object.freeze({
  straight: { label: '直槽', model: 'B02_StraightTrough', sides: ['S', 'N'], ports: ['End_Front', 'End_Back'], cost: { stone: 2 }, loss: 0.01 },
  worn: { label: '磨損直槽', model: 'B02-V02_WornStraight', sides: ['S', 'N'], ports: ['End_Front', 'End_Back'], cost: { stone: 1 }, loss: 0.03,
    note: '舊渠石重砌，省石料但漏一點' },
  bendR: { label: '右彎槽', model: 'B03_CornerTrough', sides: ['S', 'E'], ports: ['In_Front', 'Out_Right'], cost: { stone: 3 }, loss: 0.03 },
  bendL: { label: '左彎槽', model: 'B03-V03_ChamferBendLeft', sides: ['S', 'W'], ports: ['In_Front', 'Out_Left'], cost: { stone: 3 }, loss: 0.03 },
  tee: { label: '三通', model: 'B04_TeeTrough', sides: ['S', 'W', 'E'], ports: ['In_Front', 'Out_Left', 'Out_Right'], cost: { stone: 3, bronze: 1 }, loss: 0.02 },
  gate: { label: '閘板', model: 'B05_SluiceGate', sides: ['S', 'N'], ports: ['Out_Front', 'In_Back'], cost: { cedar: 2, bronze: 1 }, loss: 0.01, gate: true },
  apron: { label: '收尾溢流台', model: 'B02-V05_SpillApron', sides: ['S'], ports: ['In_Back'], cost: { stone: 3 }, loss: 0, outlet: 'N' },
});

export const DIRECTIONS = Object.freeze({
  restore_channel: { label: '修復舊渠', cost: { patch: 2, bronze: 1 },
    text: '用補石封住舊渠破槽，可以沿舊渠直通村田；施工緊貼育幼區。' },
  clear_silt: { label: '先清淤', cost: { sieve: 1, cedar: 2 },
    text: '用清淤篩清掉舊渠泥沙；清淤期間要用三通把一部分水暫時導回溪道。' },
  protect_nursery: { label: '保護育幼區', cost: { cedar: 2 },
    text: '育幼區四周不施工也不走水，水路只能繞西側沙土坡，滲漏較多。' },
});

export const SOURCE = { x: 3, y: 0, out: 'N', model: 'B01_SourcePlinth', port: 'Out_Front', flow: 100 };
export const FIELD_DEMAND = 80;                      // L/s the village fields want
export const TARGETS = [                             // where an open end may legally discharge
  { id: 'fields', label: '村田進水口', cells: [[1, 5], [2, 5], [3, 5]], side: 'N' },
  { id: 'creek', label: '溪道回流口', cells: [[0, 1], [0, 2]], side: 'W' },
];

export const TERRAIN = Object.freeze({
  oldChannel: [[3, 1], [3, 2], [3, 3], [3, 4]],     // ruined bed: a worn straight here is cheap
  crack: [[3, 2]],                                   // cracked_sluice: leaks 35 % until patched
  silt: [[3, 3], [3, 4]],                            // silt_buildup: 12 % per cell until cleared
  nursery: [[4, 3], [5, 3], [4, 4], [5, 4]],         // nursery_tracks: young beasts' den
  seep: [[1, 2], [1, 3], [1, 4]],                    // sandy slope: 15 % seepage per cell
  rock: [[5, 1], [0, 4], [6, 5]],                    // boulders: no slot
});

export const LOSS = { crack: 0.35, silt: 0.12, seep: 0.15 };

export const key = (x, y) => `${x},${y}`;
export const has = (list, x, y) => list.some(([a, b]) => a === x && b === y);
export const inside = (x, y) => x >= 0 && y >= 0 && x < W && y < H;

export function rotSide(side, r) {
  return SIDES[(SIDES.indexOf(side) + r) % 4];
}

export function sidesOf(piece) {
  return PIECES[piece.type].sides.map(s => rotSide(s, piece.rot));
}

export function nearNursery(x, y) {
  return TERRAIN.nursery.some(([a, b]) => Math.abs(a - x) + Math.abs(b - y) === 1);
}

export function slotOpen(x, y) {
  return inside(x, y) && !has(TERRAIN.rock, x, y) && !(x === SOURCE.x && y === SOURCE.y);
}
