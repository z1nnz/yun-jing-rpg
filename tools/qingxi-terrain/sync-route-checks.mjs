import { readFileSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const graph = JSON.parse(readFileSync(new URL('./routes.json', import.meta.url), 'utf8'));
const nodes = new Map(graph.nodes.map(node => [node.id, node]));
const target = new URL('./checks/qingxi-world-preview.json', import.meta.url);
const checks = JSON.parse(readFileSync(target, 'utf8'));
checks.roads = graph.edges.map(edge => {
  const a = nodes.get(edge.from), b = nodes.get(edge.to);
  if (!a || !b || edge.width <= 0) throw new Error(`Invalid road: ${edge.id}`);
  return { id: edge.id, width: edge.width, points: [a.x, a.z, b.x, b.z] };
});
checks.checkpoints = graph.checkpoints.map(checkpoint => {
  const node = nodes.get(checkpoint.node);
  if (!node) throw new Error(`Invalid checkpoint: ${checkpoint.name}`);
  return { name: checkpoint.name, x: node.x, y: 0, z: node.z };
});
checks.route = graph.route;
const next = JSON.stringify(checks, null, 2) + '\n';
if (process.argv.includes('--check')) {
  if (next !== readFileSync(target, 'utf8').replace(/\r\n/g, '\n')) {
    throw new Error(`${fileURLToPath(target)} is out of date; run sync-route-checks.mjs`);
  }
} else {
  writeFileSync(target, next);
}
