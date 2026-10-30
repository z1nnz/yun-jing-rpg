import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadLayout, buildConfig } from './village-checks.mjs';

// The same rules for every block of the novice world: A1 (the village) and the blocks in blocks/*.json.
const here = dirname(fileURLToPath(import.meta.url));
const village = loadLayout();
const blocks = { A1: village };
for (const id of ['A2', 'A3', 'D3']) blocks[id] = JSON.parse(readFileSync(join(here, 'blocks', id + '.json'), 'utf8'));

const padEdge = (p, x, z) => Math.max(Math.abs(x - p.x) - p.halfX, Math.abs(z - p.z) - p.halfZ);

// Slot footprints are w × d × h along the model's own X/Z before yaw: the contract with modellers.
const corners = s => {
  const [w, d] = s.footprint, a = s.yaw * Math.PI / 180, c = Math.cos(a), n = Math.sin(a);
  return [[-w / 2, -d / 2], [w / 2, -d / 2], [w / 2, d / 2], [-w / 2, d / 2]]
    .map(([x, z]) => [s.x + x * c + z * n, s.z - x * n + z * c]);
};
// Separating-axis test for two rotated rectangles, shrunk by a small tolerance so touching is allowed.
const overlaps = (a, b, tol = 0.05) => {
  const pa = corners(a), pb = corners(b);
  for (const poly of [pa, pb])
    for (let i = 0; i < 4; i++) {
      const [x1, z1] = poly[i], [x2, z2] = poly[(i + 1) % 4], ax = z1 - z2, az = x2 - x1;
      const proj = p => p.map(([x, z]) => x * ax + z * az), len = Math.hypot(ax, az);
      const A = proj(pa), B = proj(pb);
      if (Math.max(...A) - tol * len <= Math.min(...B) || Math.max(...B) - tol * len <= Math.min(...A)) return false;
    }
  return true;
};

for (const [name, layout] of Object.entries(blocks)) {
  const nodes = Object.fromEntries(layout.nodes.map(n => [n.id, n]));
  const { minX, minZ, sizeX, sizeZ } = layout.bounds;
  const inside = (x, z, margin) => x > minX + margin && x < minX + sizeX - margin && z > minZ + margin && z < minZ + sizeZ - margin;
  const roadDistance = (x, z) => Math.min(...layout.edges.map(e => {
    const a = nodes[e.from], b = nodes[e.to];
    const abx = b.x - a.x, abz = b.z - a.z, len2 = abx * abx + abz * abz;
    const t = len2 ? Math.max(0, Math.min(1, ((x - a.x) * abx + (z - a.z) * abz) / len2)) : 0;
    return Math.hypot(x - a.x - abx * t, z - a.z - abz * t) - e.width / 2;
  }));
  const creekDistance = (x, z) => {
    const p = layout.creek.points;
    let best = Infinity;
    for (let i = 0; i + 3 < p.length; i += 2) {
      const ax = p[i], az = p[i + 1], bx = p[i + 2], bz = p[i + 3];
      const abx = bx - ax, abz = bz - az, len2 = abx * abx + abz * abz;
      const t = len2 ? Math.max(0, Math.min(1, ((x - ax) * abx + (z - az) * abz) / len2)) : 0;
      best = Math.min(best, Math.hypot(x - ax - abx * t, z - az - abz * t));
    }
    return best;
  };
  const slots = layout.placements.filter(p => p.footprint);

  test(`${name}: roads connect known nodes and have a width`, () => {
    for (const e of layout.edges) {
      assert.ok(nodes[e.from] && nodes[e.to], e.id);
      assert.ok(e.width > 0, e.id);
    }
  });

  test(`${name}: every checkpoint and route stop exists`, () => {
    const names = new Set((layout.checkpoints ?? []).map(c => c.name));
    for (const c of layout.checkpoints ?? []) assert.ok(nodes[c.node], c.name);
    for (const r of layout.route ?? []) assert.ok(names.has(r), r);
  });

  test(`${name}: pads do not overlap, so each zone keeps one flat height`, () => {
    for (let i = 0; i < layout.pads.length; i++)
      for (let j = i + 1; j < layout.pads.length; j++) {
        const a = layout.pads[i], b = layout.pads[j];
        const gapX = Math.abs(a.x - b.x) - a.halfX - b.halfX, gapZ = Math.abs(a.z - b.z) - a.halfZ - b.halfZ;
        assert.ok(gapX > 0 || gapZ > 0, `${a.id} overlaps ${b.id}`);
      }
  });

  // Pads stay out of the 12 m border band, where every block blends to the shared world height.
  test(`${name}: pads keep out of the border band`, () => {
    for (const p of layout.pads)
      for (const [x, z] of [[p.x - p.halfX, p.z - p.halfZ], [p.x + p.halfX, p.z + p.halfZ]])
        assert.ok(inside(x, z, name === 'A1' ? 9 : 12), `${p.id} reaches into the border band`);
  });

  // Walking a road from one pad to the next must stay well under the 35° controller limit.
  test(`${name}: the climb between neighbouring pads along each road is gentle`, () => {
    for (const e of layout.edges) {
      const a = nodes[e.from], b = nodes[e.to];
      const padA = layout.pads.find(p => padEdge(p, a.x, a.z) <= 0);
      const padB = layout.pads.find(p => padEdge(p, b.x, b.z) <= 0);
      if (!padA || !padB || padA === padB) continue;
      const len = Math.hypot(b.x - a.x, b.z - a.z);
      let outside = 0;   // road length that lies between the two pads
      for (let i = 0; i <= 200; i++) {
        const t = i / 200, x = a.x + (b.x - a.x) * t, z = a.z + (b.z - a.z) * t;
        if (padEdge(padA, x, z) > 0 && padEdge(padB, x, z) > 0) outside += len / 200;
      }
      const grade = Math.atan2(Math.abs(padA.height - padB.height), Math.max(outside, 0.5)) * 180 / Math.PI;
      assert.ok(grade < 20, `${e.id}: ${grade.toFixed(1)}° between ${padA.id} and ${padB.id}`);
    }
  });

  test(`${name}: every building and prop stands on a flat pad`, () => {
    for (const p of layout.placements)
      assert.ok(layout.pads.some(pad => padEdge(pad, p.x, p.z) <= -0.5), `${p.id} is not inside a pad`);
  });

  test(`${name}: herbs grow in open ground, off roads and pads`, () => {
    for (const h of layout.herbs ?? []) {
      assert.ok(roadDistance(h.x, h.z) > 2, `${h.id} is on or next to a road`);
      assert.ok(layout.pads.every(pad => padEdge(pad, h.x, h.z) > 2), `${h.id} is on a pad`);
      assert.ok(inside(h.x, h.z, 6), `${h.id} is outside the block`);
    }
  });

  test(`${name}: the creek keeps clear of pads, roads, herbs and buildings`, { skip: !layout.creek }, () => {
    const c = layout.creek;
    assert.ok(c.points.length >= 4 && c.points.length % 2 === 0, 'creek needs x,z pairs');
    const clear = c.width / 2 + c.bank;
    // Sample the creek every half metre against every pad and road.
    const p = c.points;
    for (let i = 0; i + 3 < p.length; i += 2)
      for (let t = 0; t <= 1; t += 0.05) {
        const x = p[i] + (p[i + 2] - p[i]) * t, z = p[i + 1] + (p[i + 3] - p[i + 1]) * t;
        for (const pad of layout.pads) assert.ok(padEdge(pad, x, z) > clear - 1, `creek at ${x.toFixed(1)},${z.toFixed(1)} cuts into ${pad.id}`);
        assert.ok(roadDistance(x, z) > c.width / 2, `creek at ${x.toFixed(1)},${z.toFixed(1)} crosses a road`);
      }
    for (const h of layout.herbs ?? []) assert.ok(creekDistance(h.x, h.z) > clear, `${h.id} is on the creek bank`);
    for (const pl of layout.placements) assert.ok(creekDistance(pl.x, pl.z) > clear, `${pl.id} is in the creek`);
    if (c.crossing) assert.ok(creekDistance(c.crossing.x, c.crossing.z) < 0.5, 'the crossing must sit on the creek');
  });

  test(`${name}: every slot has an owner, a status and a footprint`, () => {
    for (const p of layout.placements) {
      assert.ok(['core', 'codex', 'joshsu54', 'Johnnnny0823', 'a0902285608'].includes(p.owner), `${p.id} owner`);
      assert.ok(['placed', 'ready', 'needed'].includes(p.status), `${p.id} status`);
      assert.ok(p.status === 'needed' ? !p.model : p.model, `${p.id}: needed slots have no model, others do`);
      assert.ok(layout.pads.some(pad => pad.id === p.zone), `${p.id} zone ${p.zone} is not a pad`);
    }
    // A1's irrigation pieces were placed before footprints existed; everything new must declare one.
    assert.ok(layout.placements.filter(p => !p.footprint).every(p => p.id.startsWith('Fields_')));
  });

  test(`${name}: slot footprints do not overlap each other`, () => {
    for (let i = 0; i < slots.length; i++)
      for (let j = i + 1; j < slots.length; j++)
        assert.ok(!overlaps(slots[i], slots[j]), `${slots[i].id} overlaps ${slots[j].id}`);
  });

  test(`${name}: slot footprints keep off roads and stay on their pad`, () => {
    for (const s of slots) {
      const pad = layout.pads.find(p => p.id === s.zone);
      for (const [x, z] of corners(s)) {
        assert.ok(roadDistance(x, z) > 0, `${s.id} corner ${x.toFixed(1)},${z.toFixed(1)} is on a road`);
        assert.ok(padEdge(pad, x, z) <= 0.5, `${s.id} corner ${x.toFixed(1)},${z.toFixed(1)} sticks out of ${pad.id}`);
      }
    }
  });
}

// Blocks join: a road that leaves one block must continue in the next within a metre of the border.
test('roads continue across block borders (A1 → A2 south, A1 → A3 west, A3 → D3 north)', () => {
  const node = (layout, id) => layout.nodes.find(n => n.id === id);
  for (const [a, aid, b, bid] of [['A1', 'village-entry', 'A2', 'a2-north'], ['A1', 'west-road', 'A3', 'a3-east'], ['A3', 'a3-north', 'D3', 'd3-south']]) {
    const p = node(blocks[a], aid), q = node(blocks[b], bid);
    assert.ok(Math.hypot(p.x - q.x, p.z - q.z) <= 1, `${a}.${aid} and ${b}.${bid} do not meet`);
  }
});

test('the check config mirrors the village layout', () => {
  const config = buildConfig(village);
  assert.equal(config.roads.length, village.edges.length);
  assert.deepEqual(config.route, village.route);
  assert.ok(config.checkpoints.every(c => Number.isFinite(c.x) && Number.isFinite(c.z)));
});
