// PR detail: body, commits, file summary by folder/extension, checks. Usage: node pr-detail.mjs 45
import { execSync } from 'node:child_process';
const cred = execSync('git credential fill', { input: 'protocol=https\nhost=github.com\n\n' }).toString();
const token = /password=(.*)/.exec(cred)[1].trim();
const api = async (path) => (await fetch('https://api.github.com/repos/z1nnz/yun-jing-rpg' + path, { headers: { Authorization: 'Bearer ' + token, 'User-Agent': 'yj' } })).json();
const n = process.argv[2];
const p = await api(`/pulls/${n}`);
console.log(`#${n} ${p.user.login} ${p.head.ref}@${p.head.sha.slice(0, 8)} base ${p.base.ref} | ${p.title}`);
console.log(`mergeable: ${p.mergeable} (${p.mergeable_state}) | +${p.additions}/-${p.deletions} in ${p.changed_files} files | commits ${p.commits}`);
console.log('--- body ---\n' + (p.body || '(empty)').slice(0, 3500));
let files = [], page = 1;
while (true) { const f = await api(`/pulls/${n}/files?per_page=100&page=${page}`); if (!f.length) break; files = files.concat(f); if (f.length < 100) break; page++; }
const groups = {};
for (const f of files) { const dir = f.filename.split('/').slice(0, 3).join('/'); const ext = (f.filename.match(/\.[^./]+$/) || ['(none)'])[0]; const k = dir + ' ' + ext; groups[k] = (groups[k] || 0) + 1; }
console.log('--- files by folder/ext ---'); for (const [k, v] of Object.entries(groups).sort()) console.log(`${v}\t${k}`);
const touchesCore = files.filter(f => /^(apps\/game\/(Assets\/YunJing|ProjectSettings|Packages)|services|packages|tools\/unity)/.test(f.filename)).map(f => f.filename);
console.log('--- touches shared/core paths ---\n' + (touchesCore.join('\n') || '(none)'));
const checks = await api(`/commits/${p.head.sha}/check-runs`);
console.log('--- checks ---'); for (const c of checks.check_runs || []) console.log(`${c.name}: ${c.status}/${c.conclusion}`);
const comments = await api(`/issues/${n}/comments`);
console.log('--- comments ---'); for (const c of comments) console.log(`${c.user.login}: ${c.body.slice(0, 300).replace(/\n/g, ' ')}`);
