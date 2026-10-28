import test from 'node:test';
import assert from 'node:assert/strict';
import { classify, measure } from './asset-inventory.mjs';

const box = (name, size, bottom = 0, centreOffset = 0, names = []) => classify(name, { size, bottom, centreOffset, names });

test('props on their base stay placeable', () => {
  assert.equal(box('qingxi-return-c/C02', [1.15, 0.66, 0.64]).cls, 'place');
});

test('a prop floating above its origin needs adjusting', () => {
  const r = box('qingxi-entry-assets-v13/herb-basket-v13', [0.54, 0.47, 0.36], 0.055);
  assert.equal(r.cls, 'adjust');
  assert.match(r.notes[0], /上方 0\.06|上方 0\.05/);
});

test('roads, trails and big flat slabs go to the terrain', () => {
  assert.equal(box('qingxi-road-props-v13/qingxi-road-v13', [8.7, 0.4, 12]).cls, 'terrain');
  assert.equal(box('qingxi-encounter-a/A07_RabbitTrailTile', [2.1, 0.45, 4.1]).cls, 'terrain');
  assert.equal(box('misc/stone-slab', [3, 0.1, 3]).cls, 'terrain');
});

test('"trail" does not count as a rail structure', () => {
  assert.notEqual(box('qingxi-encounter-a/A07_RabbitTrailTile', [2.1, 0.45, 4.1]).cls, 'structure');
  assert.equal(box('qingxi-road-props-v12/qingxi-bridge-rail-v12', [2.4, 1.1, 0.2]).cls, 'structure');
});

test('small grass clumps scatter, a large grass patch does not', () => {
  assert.equal(box('qingxi-prop-kit-v1/qingxi-grass-v1', [0.6, 0.3, 0.7]).cls, 'scatter');
  assert.equal(box('kit/grass-patch', [3, 0.5, 3]).cls, 'terrain');
});

test('a prop with a soil slab is flagged', () => {
  const r = box('kit/lantern', [0.6, 1.8, 0.6], 0, 0, ['SM_Lantern', 'M_Soil_Base', 'ground']);
  assert.ok(r.notes.some(n => n.startsWith('可能含地面底板')));
});

test('bounds follow node transforms', () => {
  const gltf = {
    scene: 0, scenes: [{ nodes: [0] }],
    nodes: [{ mesh: 0, translation: [1, 0.5, 0], scale: [2, 2, 2] }],
    meshes: [{ primitives: [{ attributes: { POSITION: 0 } }] }],
    accessors: [{ count: 3, min: [-0.5, 0, -0.5], max: [0.5, 1, 0.5] }],
  };
  const m = measure(gltf);
  assert.deepEqual(m.size, [2, 2, 2]);
  assert.equal(m.bottom, 0.5);
  assert.equal(m.centreOffset, 1);
  assert.equal(m.triangles, 1);
});
