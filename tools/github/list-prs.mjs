// Lists PRs on z1nnz/yun-jing-rpg with author, branch, files changed (token from git credential; never printed).
import { execSync } from 'node:child_process';
const cred = execSync('git credential fill', { input: 'protocol=https\nhost=github.com\n\n' }).toString();
const token = /password=(.*)/.exec(cred)[1].trim();
const api = async (path) => (await fetch('https://api.github.com/repos/z1nnz/yun-jing-rpg' + path, { headers: { Authorization: 'Bearer ' + token, 'User-Agent': 'yj' } })).json();
const state = process.argv[2] || 'all';
const prs = await api(`/pulls?state=${state}&per_page=40&sort=updated&direction=desc`);
for (const p of prs) {
  const files = await api(`/pulls/${p.number}/files?per_page=100`);
  const reviews = await api(`/pulls/${p.number}/reviews`);
  console.log(`#${p.number} [${p.state}${p.merged_at ? ',merged' : ''}${p.draft ? ',draft' : ''}] ${p.user.login} ${p.head.ref} -> ${p.base.ref} | ${p.title}`);
  console.log(`   files ${files.length}: ${files.slice(0, 6).map(f => f.filename + `(+${f.additions}/-${f.deletions})`).join(', ')}${files.length > 6 ? ' …' : ''}`);
  if (reviews.length) console.log(`   reviews: ${reviews.map(r => r.user.login + ':' + r.state).join(', ')}`);
}
