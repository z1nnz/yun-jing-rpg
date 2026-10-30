// Draws the village slot plan and the novice-world block grid as SVG maps from the layout data, so the plan
// can be read (and reviewed) without opening Unity. Usage: node tools/qingxi-terrain/render-plan.mjs
// Output: docs/execution/maps/a1-village-plan.svg, docs/execution/maps/novice-world-blocks.svg
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadLayout } from './village-checks.mjs';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const outDir = path.join(root, 'docs', 'execution', 'maps');
fs.mkdirSync(outDir, { recursive: true });
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const ownerColour = { core: '#7A8C9E', codex: '#5FA89A', joshsu54: '#B89468', Johnnnny0823: '#9A7FB0', a0902285608: '#C27A6A' };
const surfaceColour = { plaza: '#D9CFBD', dirt: '#C8B48E', forest: '#9DB08A' };

// ------------------------------------------------------------------ A1 village plan (1 m = S px)
function villagePlan(layout, title = 'A1 青溪村核心') {
  const S = 9, { minX, minZ, sizeX, sizeZ } = layout.bounds, pad = 60;
  const W = sizeX * S + pad * 2, H = sizeZ * S + pad * 2 + 150;
  const X = x => pad + (x - minX) * S, Y = z => pad + (minZ + sizeZ - z) * S;   // +Z (north) is up
  const nodes = Object.fromEntries(layout.nodes.map(n => [n.id, n]));
  const out = [];
  out.push(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="Noto Sans TC, Microsoft JhengHei, sans-serif">`);
  out.push(`<rect width="${W}" height="${H}" fill="#EEF0E8"/>`);
  // 10 m grid
  for (let x = minX; x <= minX + sizeX; x += 10) out.push(`<line x1="${X(x)}" y1="${Y(minZ)}" x2="${X(x)}" y2="${Y(minZ + sizeZ)}" stroke="#C9CEC2" stroke-width="${x === 0 ? 1.6 : .8}"/><text x="${X(x)}" y="${Y(minZ) + 16}" font-size="11" text-anchor="middle" fill="#6E7570">${x}</text>`);
  for (let z = minZ; z <= minZ + sizeZ; z += 10) out.push(`<line x1="${X(minX)}" y1="${Y(z)}" x2="${X(minX + sizeX)}" y2="${Y(z)}" stroke="#C9CEC2" stroke-width="${z === 0 ? 1.6 : .8}"/><text x="${X(minX) - 6}" y="${Y(z) + 4}" font-size="11" text-anchor="end" fill="#6E7570">${z}</text>`);
  // pads
  for (const p of layout.pads) {
    out.push(`<rect x="${X(p.x - p.halfX)}" y="${Y(p.z + p.halfZ)}" width="${p.halfX * 2 * S}" height="${p.halfZ * 2 * S}" fill="${surfaceColour[p.surface] || '#ccc'}" fill-opacity=".75" stroke="#8C7A5E" stroke-width="1"/>`);
    out.push(`<text x="${X(p.x - p.halfX) + 4}" y="${Y(p.z + p.halfZ) + 13}" font-size="12" fill="#4A4036" font-weight="bold">${esc(p.id)}（高 ${p.height} m）</text>`);
  }
  // creek
  if (layout.creek) {
    const c = layout.creek, pts = [];
    for (let i = 0; i + 1 < c.points.length; i += 2) pts.push(`${X(c.points[i])},${Y(c.points[i + 1])}`);
    out.push(`<polyline points="${pts.join(' ')}" fill="none" stroke="#9FC3C0" stroke-width="${(c.width + c.bank * 2) * S}" stroke-linejoin="round" stroke-opacity=".45"/>`);
    out.push(`<polyline points="${pts.join(' ')}" fill="none" stroke="#2E7A78" stroke-width="${c.width * S}" stroke-linejoin="round" stroke-opacity=".8"/>`);
  }
  // roads
  for (const e of layout.edges) {
    const a = nodes[e.from], b = nodes[e.to];
    out.push(`<line x1="${X(a.x)}" y1="${Y(a.z)}" x2="${X(b.x)}" y2="${Y(b.z)}" stroke="#A88560" stroke-width="${e.width * S}" stroke-linecap="round" stroke-opacity=".85"/>`);
  }
  // herbs
  for (const h of layout.herbs) out.push(`<circle cx="${X(h.x)}" cy="${Y(h.z)}" r="5" fill="#4E6B3A"/><text x="${X(h.x) + 7}" y="${Y(h.z) + 4}" font-size="10" fill="#2F4A2A">${esc(h.id)}</text>`);
  // slots
  const slots = layout.placements.concat(layout.crossingSlots || []);
  let n = 0;
  const legend = [];
  for (const s of slots) {
    n++;
    const [w, d] = s.footprint || [1.5, 1.5];
    const colour = ownerColour[s.owner] || '#888';
    const style = s.status === 'placed' ? `fill="${colour}" fill-opacity=".85" stroke="#2B2B2B" stroke-width="1"`
      : s.status === 'ready' ? `fill="${colour}" fill-opacity=".45" stroke="#2B2B2B" stroke-width="1.6"`
        : `fill="#FFFFFF" fill-opacity=".6" stroke="${colour}" stroke-width="2.4" stroke-dasharray="6 4"`;
    // Unity yaw turns +Z (north, up here) toward +X (east): clockwise on a north-up map, like SVG rotate.
    // The short line marks the model's front (+Z before yaw).
    out.push(`<g transform="translate(${X(s.x)} ${Y(s.z)}) rotate(${s.yaw || 0})"><rect x="${-w / 2 * S}" y="${-d / 2 * S}" width="${w * S}" height="${d * S}" ${style}/><line x1="0" y1="0" x2="0" y2="${-d / 2 * S}" stroke="#2B2B2B" stroke-width="1.4"/></g>`);
    out.push(`<circle cx="${X(s.x)}" cy="${Y(s.z)}" r="8" fill="#1C1F1E"/><text x="${X(s.x)}" y="${Y(s.z) + 4}" font-size="10" fill="#fff" text-anchor="middle">${n}</text>`);
    legend.push(`${n} ${s.role}（${s.owner}${s.footprint ? `，${s.footprint.join('×')} m` : ''}）`);
  }
  // title, scale and legend
  out.push(`<text x="${pad}" y="30" font-size="20" font-weight="bold" fill="#1C1F1E">${title}｜區塊配置圖（${sizeX} × ${sizeZ} m，上方為北）</text>`);
  out.push(`<line x1="${W - pad - 10 * S}" y1="30" x2="${W - pad}" y2="30" stroke="#1C1F1E" stroke-width="3"/><text x="${W - pad - 5 * S}" y="22" font-size="12" text-anchor="middle">10 m</text>`);
  const ly = Y(minZ) + 40, cols = 3, colW = (W - pad * 2) / cols;
  out.push(`<text x="${pad}" y="${ly}" font-size="12" fill="#1C1F1E">實心＝已放置　半透明＝模型已有、自動放置　虛線＝待製作（遊戲裡顯示為灰盒）。顏色＝負責人：核心組 灰藍、Codex 玉綠、joshsu54 木褐。短線＝正面方向。</text>`);
  legend.forEach((t, i) => out.push(`<text x="${pad + (i % cols) * colW}" y="${ly + 22 + Math.floor(i / cols) * 16}" font-size="11" fill="#2B2B2B">${esc(t)}</text>`));
  out.push('</svg>');
  return out.join('\n');
}

// ------------------------------------------------------------------ novice-world block grid
function worldMap(world) {
  const S = 1.7, cell = world.blockSize * S, pad = 70;
  const xs = world.blocks.map(b => b.cell[0]), zs = world.blocks.map(b => b.cell[1]);
  const minBX = Math.min(...xs), maxBX = Math.max(...xs), minBZ = Math.min(...zs), maxBZ = Math.max(...zs);
  const W = (maxBX - minBX + 1) * cell + pad * 2, H = (maxBZ - minBZ + 1) * cell + pad * 2 + 40;
  const X = bx => pad + (bx - minBX) * cell, Y = bz => pad + 30 + (maxBZ - bz) * cell;
  const regionColour = Object.fromEntries(world.regions.map(r => [r.id, r.colour]));
  const out = [`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="Noto Sans TC, Microsoft JhengHei, sans-serif">`, `<rect width="${W}" height="${H}" fill="#EEF0E8"/>`];
  out.push(`<text x="${pad}" y="34" font-size="20" font-weight="bold" fill="#1C1F1E">雲境新手大世界｜區塊總圖（每格 ${world.blockSize} × ${world.blockSize} m，上方為北）</text>`);
  for (const b of world.blocks) {
    const x = X(b.cell[0]), y = Y(b.cell[1]);
    out.push(`<rect x="${x + 2}" y="${y + 2}" width="${cell - 4}" height="${cell - 4}" fill="${regionColour[b.region]}" fill-opacity="${b.walkable ? .8 : .35}" stroke="#4A4036" stroke-width="${b.id === 'A1' ? 3 : 1}" ${b.walkable ? '' : 'stroke-dasharray="5 4"'}/>`);
    out.push(`<text x="${x + 8}" y="${y + 20}" font-size="14" font-weight="bold" fill="#1C1F1E">${esc(b.id)} ${esc(b.name)}</text>`);
    out.push(`<text x="${x + 8}" y="${y + 38}" font-size="11" fill="#2B2B2B">${esc(b.phase)}・高 ${esc(b.elevation)}</text>`);
    const words = esc(b.landmark || '');
    out.push(`<text x="${x + 8}" y="${y + 56}" font-size="11" fill="#2B2B2B">${words}</text>`);
  }
  out.push(`<text x="${pad}" y="${H - 14}" font-size="12" fill="#1C1F1E">實線格＝可走區塊；虛線格＝只做遠景（走不到）。粗框 A1＝目前的青溪村。</text>`);
  out.push('</svg>');
  return out.join('\n');
}

const layout = loadLayout();
fs.writeFileSync(path.join(outDir, 'a1-village-plan.svg'), villagePlan(layout));
for (const [id, title] of [['A2', 'A2 村外官道與茶亭'], ['A3', 'A3 西溪與水磨坊'], ['D3', 'D3 上游溪谷'], ['D1', 'D1 林緣獵場']]) {
  const block = JSON.parse(fs.readFileSync(path.join(root, 'tools', 'qingxi-terrain', 'blocks', id + '.json'), 'utf8'));
  fs.writeFileSync(path.join(outDir, id.toLowerCase() + '-block-plan.svg'), villagePlan(block, title));
}
const territory = JSON.parse(fs.readFileSync(path.join(root, 'tools', 'qingxi-terrain', 'territory.json'), 'utf8'));
fs.writeFileSync(path.join(outDir, 'territory-plan.svg'), villagePlan(territory, '新手領地・一方小世界（場景座標）'));
const world = JSON.parse(fs.readFileSync(path.join(root, 'tools', 'qingxi-terrain', 'novice-world-blocks.json'), 'utf8'));
fs.writeFileSync(path.join(outDir, 'novice-world-blocks.svg'), worldMap(world));
console.log('maps written to', path.relative(root, outDir));
