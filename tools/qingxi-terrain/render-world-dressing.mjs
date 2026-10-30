// Draws the novice-world dressing plan: every 100 m block coloured by its ground-cover biome, with its theme,
// landmark and build status, so "where is it empty and what goes there" can be read at a glance.
// Usage: node tools/qingxi-terrain/render-world-dressing.mjs → docs/execution/maps/novice-world-dressing.svg
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..');
const world = JSON.parse(fs.readFileSync(path.join(root, 'tools/qingxi-terrain/novice-world-blocks.json'), 'utf8'));
const plan = JSON.parse(fs.readFileSync(path.join(root, 'tools/qingxi-terrain/world-dressing.json'), 'utf8'));
const biomes = Object.fromEntries(plan.biomes.map(b => [b.id, b])), blockPlan = Object.fromEntries(plan.blocks.map(b => [b.id, b]));
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

const S = 1.9, cell = 100 * S, pad = 40;
const cells = world.blocks.map(b => b.cell);
const minX = Math.min(...cells.map(c => c[0])), maxX = Math.max(...cells.map(c => c[0]));
const minZ = Math.min(...cells.map(c => c[1])), maxZ = Math.max(...cells.map(c => c[1]));
const W = (maxX - minX + 1) * cell + pad * 2, H = (maxZ - minZ + 1) * cell + pad * 2 + 230;
const X = cx => pad + (cx - minX) * cell, Y = cz => pad + (maxZ - cz) * cell;   // north up
const out = [`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" width="${W}" height="${H}" font-family="Noto Sans TC, Microsoft JhengHei, sans-serif">`,
  `<rect width="${W}" height="${H}" fill="#EEF0E8"/>`];
for (const b of world.blocks) {
  const d = blockPlan[b.id] || {}, biome = biomes[d.biome] || { colour: '#DDD', name: '未定' };
  const x = X(b.cell[0]), y = Y(b.cell[1]);
  const built = d.status === 'built', dashed = !b.walkable;
  out.push(`<rect x="${x + 2}" y="${y + 2}" width="${cell - 4}" height="${cell - 4}" rx="6" fill="${biome.colour}" fill-opacity="${built ? .95 : .45}" stroke="${built ? '#3D4A3A' : '#8A9488'}" stroke-width="${built ? 3 : 1.4}" ${dashed ? 'stroke-dasharray="6 5"' : ''}/>`);
  out.push(`<text x="${x + 10}" y="${y + 24}" font-size="17" font-weight="bold" fill="#2A3029">${esc(b.id)} ${esc(b.name)}</text>`);
  out.push(`<text x="${x + 10}" y="${y + 44}" font-size="12" fill="#3E463C">${esc(biome.name)}</text>`);
  out.push(`<text x="${x + 10}" y="${y + 62}" font-size="12" fill="#3E463C">地標：${esc(b.landmark).slice(0, 14)}</text>`);
  (d.fill || []).slice(0, 4).forEach((f, i) => out.push(`<text x="${x + 10}" y="${y + 82 + i * 16}" font-size="11" fill="#4B5248">・${esc(f).slice(0, 16)}</text>`));
  out.push(`<text x="${x + cell - 10}" y="${y + cell - 12}" font-size="12" text-anchor="end" fill="${built ? '#2E5E2A' : '#7A6A4A'}" font-weight="bold">${built ? '已建' : b.walkable ? '待建' : '遠景'}</text>`);
}
// legend
let ly = (maxZ - minZ + 1) * cell + pad + 30;
out.push(`<text x="${pad}" y="${ly}" font-size="18" font-weight="bold" fill="#2A3029">新手大世界・擺放與填充總圖（每格 100 × 100 m，北在上）</text>`);
ly += 28;
plan.biomes.forEach((b, i) => {
  const lx = pad + (i % 3) * 330, yy = ly + Math.floor(i / 3) * 26;
  out.push(`<rect x="${lx}" y="${yy - 13}" width="18" height="18" rx="3" fill="${b.colour}"/><text x="${lx + 26}" y="${yy + 1}" font-size="13" fill="#2A3029">${esc(b.name)}：${esc(b.cover).slice(0, 16)}</text>`);
});
ly += 26 * Math.ceil(plan.biomes.length / 3) + 12;
out.push(`<text x="${pad}" y="${ly}" font-size="13" fill="#4B5248">深色實框＝已建（A1、A2、A3、D3）；淡色＝待建；虛線＝遠景。每塊的完整填充清單見 docs/execution/novice-world-dressing-plan.md。</text>`);
out.push('</svg>');
const file = path.join(root, 'docs/execution/maps/novice-world-dressing.svg');
fs.writeFileSync(file, out.join('\n'));
console.log('wrote', path.relative(root, file));
