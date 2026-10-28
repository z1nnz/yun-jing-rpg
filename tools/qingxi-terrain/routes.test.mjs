import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const graph = JSON.parse(readFileSync(new URL('./routes.json', import.meta.url)));
const nodes = new Map(graph.nodes.map(node => [node.id, node]));

test('route endpoints, widths and checkpoint references are valid', () => {
  assert.equal(nodes.size, graph.nodes.length);
  for (const edge of graph.edges) {
    assert.ok(edge.width > 0, edge.id);
    assert.ok(nodes.has(edge.from) && nodes.has(edge.to), edge.id);
    assert.notEqual(edge.from, edge.to, edge.id);
  }
  for (const checkpoint of graph.checkpoints) assert.ok(nodes.has(checkpoint.node), checkpoint.name);
  const names = new Set(graph.checkpoints.map(checkpoint => checkpoint.name));
  for (const name of graph.route) assert.ok(names.has(name), name);
});

test('the village and tree forks share exactly three incident paths', () => {
  for (const id of ['bridge-fork', 'tree-fork']) {
    assert.equal(graph.edges.filter(edge => edge.from === id || edge.to === id).length, 3, id);
  }
});
