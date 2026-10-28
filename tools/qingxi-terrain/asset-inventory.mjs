// Inventory of the exported GLB assets for the Qingxi terrain rework.
// For each asset: real size, how far its base sits from the origin, footprint centre offset,
// triangles/materials, the person who first added it, and a first-pass class:
//   place     – stands on the ground as-is; drop it onto terrain height
//   adjust    – placeable, but base or footprint centre is off the origin
//   scatter   – small clump/stone; used as a detail instance, not hand-placed
//   structure – bridge, steps, plank, terrace, channel: stays a model, terrain is shaped to meet it
//   terrain   – road/trail/tile/riverbank surface; replaced by terrain height + paint
// Classes are heuristics from names and proportions; the `review` column records manual overrides.
//
//   node tools/qingxi-terrain/asset-inventory.mjs            writes JSON + Markdown
//   node tools/qingxi-terrain/asset-inventory.mjs --check    exits 1 if outputs are stale

import { readFileSync, readdirSync, statSync, writeFileSync, existsSync } from 'node:fs';
import { join, relative, basename, dirname } from 'node:path';
import { execFileSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const exportsDir = join(root, 'art', 'exports');
const jsonOut = join(root, 'tools', 'qingxi-terrain', 'asset-inventory.json');
const mdOut = join(root, 'docs', 'execution', 'qingxi-terrain-asset-inventory.md');
const unityModels = join(root, 'tools', 'qingxi-terrain', 'unity-models.json'); // written by QingxiGroundingCheck.InventoryModels
const GROUND_TOLERANCE = 0.03;

// Manual decisions after looking at the previews; they win over the heuristic.
const REVIEW = {
  'qingxi-listening-terrace-v1': ['structure', '聽風台是有台階的建築平台，保留模型，地形做到台基邊'],
  'aptitude-plaza-v1/aptitude-plaza-v1': ['structure', '鋪石廣場是硬質地坪，保留模型，周圍地形壓平接上'],
  'irrigation-v2/spirit-bed': ['structure', '靈田有田埂，需要地形挖平一塊再放'],
  'irrigation-v1/spirit-bed': ['structure', '舊版靈田，同上'],
  'qingxi-mountain-rabbit-v003/QingxiMountainRabbit_v003': ['place', '角色模型，由遊戲邏輯放到地面'],
  'qingxi-entry-assets-v13/novice-cultivator-v13': ['place', '角色樣片，不參與地形'],
  'qingxi-encounter-a/A01_SlopeTile': ['terrain', '坡度改由地形做；表面貼圖可轉成地形材質層'],
  'qingxi-encounter-a/A02_HollowTile': ['terrain', '兔穴凹地是玩法位置，地形照它的尺寸挖出凹地；邊緣樹根可拆成單件擺放'],
  'qingxi-encounter-a/A07_RabbitTrailTile': ['terrain', '兔徑改為路線資料中的窄徑，地形上畫材質'],
  'qingxi-riverbank-v2/qingxi-riverbank-v2': ['terrain', '河岸高差由地形做；石塊與蘆葦拆成散布件或結構件'],
  'qingxi-road-props-v12/qingxi-road-v12': ['terrain', '泥土路改由路線＋地形材質；v13 已取代本件'],
  'qingxi-road-props-v13/qingxi-road-v13': ['terrain', '泥土路改由路線＋地形材質；路面與路緣貼圖可轉成地形材質層，作為配色基準'],
  'qingxi-winding-road-v1/qingxi-winding-road-v1': ['terrain', '彎路造型可當路線形狀參考；路面交給地形'],
  'qingxi-entry-assets-v13/road-dressing-v13': ['terrain', '路邊點綴整片相連，拆成單叢後當散布件'],
  'qingxi-detail-props-v2/qingxi-trail-lantern-v2': ['place', '路燈，名稱含 trail 被誤判'],
  'qingxi-village-signs-v1/Q03': ['place', 'ground_stone 是木樁底下的墊石，屬於本件，不是地面'],
  'qingxi-detail-props-v2/qingxi-moss-boulder-v2': ['place', '大石，手放後依地形高度下沉一點'],
};

function readGlb(file) {
  const buf = readFileSync(file);
  if (buf.readUInt32LE(0) !== 0x46546c67) throw new Error(`${file} is not a GLB (is Git LFS pulled?)`);
  const jsonLength = buf.readUInt32LE(12);
  return JSON.parse(buf.toString('utf8', 20, 20 + jsonLength));
}

function trs(node) {
  if (node.matrix) return node.matrix.slice();
  const [tx, ty, tz] = node.translation ?? [0, 0, 0];
  const [x, y, z, w] = node.rotation ?? [0, 0, 0, 1];
  const [sx, sy, sz] = node.scale ?? [1, 1, 1];
  return [
    (1 - 2 * (y * y + z * z)) * sx, 2 * (x * y + z * w) * sx, 2 * (x * z - y * w) * sx, 0,
    2 * (x * y - z * w) * sy, (1 - 2 * (x * x + z * z)) * sy, 2 * (y * z + x * w) * sy, 0,
    2 * (x * z + y * w) * sz, 2 * (y * z - x * w) * sz, (1 - 2 * (x * x + y * y)) * sz, 0,
    tx, ty, tz, 1,
  ];
}

function mul(a, b) {
  const out = new Array(16).fill(0);
  for (let c = 0; c < 4; c++) for (let r = 0; r < 4; r++)
    for (let k = 0; k < 4; k++) out[c * 4 + r] += a[k * 4 + r] * b[c * 4 + k];
  return out;
}

const apply = (m, [x, y, z]) => [0, 1, 2].map(r => m[r] * x + m[4 + r] * y + m[8 + r] * z + m[12 + r]);

export function measure(gltf) {
  const min = [Infinity, Infinity, Infinity], max = [-Infinity, -Infinity, -Infinity];
  let triangles = 0;
  const names = new Set();
  const scene = gltf.scenes?.[gltf.scene ?? 0];
  const visit = (index, parent) => {
    const node = gltf.nodes[index];
    if (node.name) names.add(node.name);
    const world = mul(parent, trs(node));
    if (node.mesh !== undefined) {
      const mesh = gltf.meshes[node.mesh];
      if (mesh.name) names.add(mesh.name);
      for (const p of mesh.primitives) {
        const pos = gltf.accessors[p.attributes.POSITION];
        const count = p.indices !== undefined ? gltf.accessors[p.indices].count : pos.count;
        if ((p.mode ?? 4) === 4) triangles += count / 3;
        // Skinned meshes ignore their node transform in glTF.
        const m = node.skin !== undefined ? mul(parent, [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]) : world;
        for (const cx of [pos.min[0], pos.max[0]]) for (const cy of [pos.min[1], pos.max[1]]) for (const cz of [pos.min[2], pos.max[2]]) {
          const v = apply(m, [cx, cy, cz]);
          for (let i = 0; i < 3; i++) { min[i] = Math.min(min[i], v[i]); max[i] = Math.max(max[i], v[i]); }
        }
      }
    }
    for (const child of node.children ?? []) visit(child, world);
  };
  for (const n of scene?.nodes ?? []) visit(n, [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]);
  for (const m of gltf.materials ?? []) if (m.name) names.add(m.name);
  const size = [0, 1, 2].map(i => max[i] - min[i]);
  return {
    size, bottom: min[1],
    centreOffset: Math.hypot((min[0] + max[0]) / 2, (min[2] + max[2]) / 2),
    triangles: Math.round(triangles), materials: gltf.materials?.length ?? 0,
    animations: gltf.animations?.length ?? 0, names: [...names],
  };
}

const STRUCTURE = /bridge|stair|step|plank|boardwalk|terrace|cliff|gate|channel|cistern|(?<!t)rail/i;
const TERRAIN = /road|trail|tile|terrain|ground|riverbank|dressing|slope|hollow|turf|soil/i;
const SCATTER = /grass|flower|fern|reed|cobble|pebble|clump|wildflower/i;
const GROUND_PART = /ground|soil|turf|dirt|grass_?base|base_?grass|earth|mound/i;

export function classify(key, m) {
  const name = basename(key);
  const footprint = m.size[0] * m.size[2];
  const flat = m.size[1] < 0.35 && footprint >= 4;
  const notes = [];
  let cls;
  if (STRUCTURE.test(name)) cls = 'structure';
  else if (TERRAIN.test(name) || flat) cls = 'terrain';
  else if (SCATTER.test(name) && footprint < 2.5) cls = 'scatter';
  else if (SCATTER.test(name)) { cls = 'terrain'; notes.push('草石成片，應拆成單叢交給散布'); }
  else cls = 'place';
  const offGround = Math.abs(m.bottom) > GROUND_TOLERANCE;
  const offCentre = m.centreOffset > Math.max(0.1, 0.25 * Math.max(m.size[0], m.size[2]));
  if (offGround) notes.push(`底部在原點${m.bottom > 0 ? '上方' : '下方'} ${Math.abs(m.bottom).toFixed(2)} m`);
  if (offCentre) notes.push(`腳印中心偏離原點 ${m.centreOffset.toFixed(2)} m`);
  if (cls === 'place' && (offGround || offCentre)) cls = 'adjust';
  const groundParts = m.names.filter(n => GROUND_PART.test(n));
  if (cls === 'scatter' && groundParts.length) notes.push('根部帶小土堆，散布時有助接地，不算底板');
  else if (cls !== 'terrain' && groundParts.length) notes.push(`可能含地面底板：${groundParts.slice(0, 3).join('、')}`);
  return { cls, notes };
}

function walk(dir) {
  return readdirSync(dir).flatMap(f => {
    const p = join(dir, f);
    return statSync(p).isDirectory() ? walk(p) : f.endsWith('.glb') ? [p] : [];
  });
}

function firstAuthor(file) {
  try {
    const out = execFileSync('git', ['log', '--diff-filter=A', '--format=%an', '--', relative(root, file)], { cwd: root, encoding: 'utf8' });
    return out.trim().split('\n').pop() || '未知';
  } catch { return '未知'; }
}

const LABEL = { place: '直接擺放', adjust: '調整接地', scatter: '散布件', structure: '結構件（保留模型）', terrain: '交給地形' };

export function build() {
  const rows = walk(exportsDir)
    .filter(f => !/[-_]lod\d\.glb$/i.test(f))
    .sort()
    .map(file => {
      const key = relative(exportsDir, file).replace(/\\/g, '/').replace(/\.glb$/, '');
      const m = measure(readGlb(file));
      const auto = classify(key, m);
      const reviewKey = Object.keys(REVIEW).find(k => key === k || key.endsWith('/' + k) || key === k.split('/').pop());
      const [cls, review] = reviewKey ? REVIEW[reviewKey] : [auto.cls, ''];
      return {
        key, set: key.split('/')[0], author: firstAuthor(file),
        size: m.size.map(v => +v.toFixed(3)), bottom: +m.bottom.toFixed(3), centreOffset: +m.centreOffset.toFixed(3),
        triangles: m.triangles, materials: m.materials, animations: m.animations,
        auto: auto.cls, class: cls, notes: auto.notes, review, source: 'glb',
      };
    });
  // FBX models that exist only inside the Unity project (no GLB export) come from the Unity measurement.
  if (existsSync(unityModels)) {
    const known = new Set(rows.map(r => basename(r.key).toLowerCase()));
    for (const u of JSON.parse(readFileSync(unityModels, 'utf8'))) {
      const name = basename(u.path).replace(/\.fbx$/i, '');
      if (known.has(name.toLowerCase())) continue;
      const key = u.path.replace(/^Assets\/YunJing\/Models\//, '').replace(/\.fbx$/i, '');
      const auto = classify(key, { ...u, names: [] });
      const reviewKey = Object.keys(REVIEW).find(k => key === k || key.endsWith('/' + k));
      const [cls, review] = reviewKey ? REVIEW[reviewKey] : [auto.cls, ''];
      rows.push({
        key, set: key.split('/')[0], author: firstAuthor(join(root, 'apps', 'game', u.path)),
        size: u.size, bottom: u.bottom, centreOffset: u.centreOffset, triangles: u.triangles, materials: u.materials, animations: 0,
        auto: auto.cls, class: cls, notes: auto.notes, review, source: 'unity-fbx',
      });
    }
  }
  return rows;
}

function markdown(rows) {
  const count = c => rows.filter(r => r.class === c).length;
  const lines = [
    '# 青溪地形改造｜現有模型盤點',
    '',
    `由 \`node tools/qingxi-terrain/asset-inventory.mjs\` 從 \`art/exports/**/*.glb\` 與 Unity FBX 量測產生，共 ${rows.length} 件（LOD 檔不重複計）。尺寸單位為公尺，Y 為高度。`,
    '「分類」先由名稱與比例自動判斷，再以表內「人工判斷」覆寫；**這是給地形整合的起點，不是最終決定**，擺進新地形後仍要看玩家視角。',
    '',
    '| 分類 | 件數 | 在新地形上怎麼用 |',
    '|---|---:|---|',
    `| 直接擺放 | ${count('place')} | 原點在底部中心，依地形高度放上即可 |`,
    `| 調整接地 | ${count('adjust')} | 可以用，但底部或中心偏離原點；擺放時補位移，或請原作者重設原點 |`,
    `| 散布件 | ${count('scatter')} | 小叢草、花、石；由道路遮罩外的散布規則自動放 |`,
    `| 結構件（保留模型） | ${count('structure')} | 橋、台階、平台、水渠；地形塑形去接它，接口高度要對齊路線 |`,
    `| 交給地形 | ${count('terrain')} | 道路、獸徑、地形磚、河岸面；改由地形高度＋材質處理，原件作為造型與配色參考 |`,
    '',
    '| 資產 | 作者 | 分類 | 尺寸 X×Y×Z | 底部 | 三角面 | 材質 | 說明 |',
    '|---|---|---|---|---:|---:|---:|---|',
  ];
  for (const r of rows) {
    const note = [r.review && `人工判斷：${r.review}`, ...r.notes].filter(Boolean).join('；');
    lines.push(`| \`${r.key}\`${r.source === 'unity-fbx' ? '（Unity FBX）' : ''} | ${r.author} | ${LABEL[r.class]}${r.class !== r.auto ? '＊' : ''} | ${r.size.map(v => v.toFixed(2)).join('×')} | ${r.bottom.toFixed(2)} | ${r.triangles} | ${r.materials} | ${note} |`);
  }
  lines.push('', '＊ 人工判斷與自動分類不同。', '',
    '## 限制', '',
    '- GLB 從 `art/exports` 量測；只存在 Unity `Assets/YunJing/Models` 的 FBX 讀 `tools/qingxi-terrain/unity-models.json`（由 `check-grounding.ps1 -Inventory` 在 Unity 內量測），標「（Unity FBX）」。這些 FBX 沒有節點名稱資料，無法判斷是否含地面底板。',
    '- 骨架模型以綁定姿勢量測；動畫中的範圍可能更大。',
    '- 「可能含地面底板」只看節點、網格與材質名稱，需要開預覽確認。',
    '- 「作者」是第一次把檔案加入 Git 的提交者，不一定等於建模者；以各資產 README 為準。', '');
  return lines.join('\n');
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const rows = build();
  const json = JSON.stringify({ generatedFrom: 'art/exports/**/*.glb', groundTolerance: GROUND_TOLERANCE, assets: rows }, null, 1) + '\n';
  const md = markdown(rows);
  if (process.argv.includes('--check')) {
    const stale = [[jsonOut, json], [mdOut, md]].filter(([p, s]) => !existsSync(p) || readFileSync(p, 'utf8') !== s);
    if (stale.length) { console.error('inventory is stale:', stale.map(([p]) => relative(root, p)).join(', ')); process.exit(1); }
    console.log(`inventory up to date (${rows.length} assets)`);
  } else {
    writeFileSync(jsonOut, json);
    writeFileSync(mdOut, md);
    const by = {};
    for (const r of rows) by[r.class] = (by[r.class] ?? 0) + 1;
    console.log(`${rows.length} assets`, by);
  }
}
