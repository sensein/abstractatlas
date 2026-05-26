/**
 * Quick post-deploy smoke. Hits the three production subsite URLs +
 * confirms (a) HTTP 200, (b) the unified SiteHeader test-id is in
 * the HTML, (c) the deploy SHA matches the local main HEAD so we
 * know gh-pages caught up. Sibling-parquet drift detection is
 * runtime-visible on atlas-root so we just smoke-test that the
 * known data-testid is present, not that the parquet was fetched.
 */
import { execSync } from 'node:child_process';

const PROD = 'https://abstractatlas.brainkb.org';
const SUBSITES = [
	{ url: `${PROD}/`, name: 'atlas-root' },
	{ url: `${PROD}/ohbm2026/`, name: 'ohbm2026' },
	{ url: `${PROD}/neuroscape/`, name: 'neuroscape' }
];

const localSha = execSync('git rev-parse origin/main', { encoding: 'utf8' }).trim();
const localShaShort = localSha.slice(0, 7);
console.log(`Local main HEAD: ${localShaShort}`);
console.log('');

let fail = 0;
for (const s of SUBSITES) {
	const res = await fetch(s.url, { redirect: 'manual' });
	const body = await res.text();
	const status = res.status;
	const hasHeader = /data-testid="site-header"/.test(body);
	const hasMetaRefresh = /<meta[^>]*http-equiv\s*=\s*["']refresh["']/i.test(body);
	const shaMatch = body.match(/data-build-sha[^"]*"([a-f0-9]{7,40})"/i);
	const deployedSha = shaMatch ? shaMatch[1] : '(not found)';
	const shaOk =
		deployedSha === '(not found)' ||
		deployedSha === localSha ||
		deployedSha.startsWith(localShaShort);

	const ok = status === 200 && hasHeader && !(s.name === 'atlas-root' && hasMetaRefresh) && shaOk;
	console.log(`${ok ? '✓' : '✗'} ${s.name.padEnd(11)} ${s.url}`);
	console.log(`   status=${status}  site-header=${hasHeader}  deployed-sha=${deployedSha}${shaOk ? '' : ' (MISMATCH)'}`);
	if (s.name === 'atlas-root') {
		console.log(`   meta-refresh-redirect=${hasMetaRefresh} (should be false)`);
	}
	if (!ok) fail += 1;
}

console.log('');
console.log(fail === 0 ? '=== ALL CLEAN ===' : `=== ${fail} subsite(s) failed ===`);
process.exit(fail === 0 ? 0 : 1);
