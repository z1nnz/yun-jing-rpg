import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { teaTraceCases } from '../tests/tea-cases';

// npm run build && node dist/tools/tea-fixture.js — rewrites the tea replay fixture Unity checks TeaSim.cs against.
const file = join(__dirname, '..', '..', 'tests', 'fixtures', 'tea-trace.json');
writeFileSync(file, JSON.stringify({ cases: teaTraceCases() }, null, 1) + '\n');
console.log('wrote', file);
