/**
 * Spec 026 — NeuroScape year-aware backdrop density e2e.
 *
 * Verifies the render-integration contract (B1–B5,
 * specs/026-neuroscape-year-density/contracts/render-integration.md)
 * against the deployed `/neuroscape/` preview:
 *
 *   B1 full span: a baseline rendered backdrop dot count exists.
 *   B2 a narrow window in the EARLY era and one in the RECENT era render
 *      backdrop dot counts within a bounded ratio (compressed) — not the
 *      order-of-magnitude swing a raw spatial sample gives (SC-001).
 *   B4 the RESULT-COUNT still reflects TRUE volume (recent ≫ early), i.e.
 *      the feature changes only backdrop rendering, not filtering
 *      semantics (FR-006 / SC-004).
 *   B5 clearing the year filter restores ~the full-span backdrop count.
 *
 * Like the other neuroscape specs this runs against the deployed preview
 * (the 461k corpus streams over several seconds), so we poll for a stable
 * result list before measuring, and use generous bands to stay robust
 * while still catching the 10×+ regression.
 */
import { test, expect, type Page } from '@playwright/test';

function neuroscapeUrl(): string {
	const raw = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:4173/ohbm2026/';
	const base = raw.endsWith('/') ? raw : `${raw}/`;
	return base.replace(/\/ohbm2026\/$/, '/neuroscape/');
}

/** Total points rendered across the 2D scatter's traces (the backdrop base
 *  sample dominates at default zoom; viewport-detail is off when zoomed out). */
async function renderedBackdropCount(page: Page): Promise<number> {
	return page.evaluate(() => {
		const el = document.querySelector('[data-testid="umap-chart-2d"]') as unknown as {
			data?: Array<{ x?: unknown[] }>;
		} | null;
		if (!el?.data) return 0;
		return el.data.reduce((sum, tr) => sum + (Array.isArray(tr.x) ? tr.x.length : 0), 0);
	});
}

async function resultCount(page: Page): Promise<number> {
	const t = (await page.getByTestId('result-count').textContent())?.trim() ?? '0';
	return Number.parseInt(t.replace(/[^0-9]/g, ''), 10) || 0;
}

/** Drag a slider handle to an absolute fraction of the track width. */
async function dragToFraction(page: Page, testid: string, frac: number): Promise<void> {
	const track = page.getByTestId('neuroscape-year-slider').locator('.track');
	const tbox = await track.boundingBox();
	const handle = page.getByTestId(testid);
	const hbox = await handle.boundingBox();
	if (!tbox || !hbox) throw new Error('slider not laid out');
	await page.mouse.move(hbox.x + hbox.width / 2, hbox.y + hbox.height / 2);
	await page.mouse.down();
	await page.mouse.move(tbox.x + tbox.width * frac, tbox.y + tbox.height / 2, { steps: 12 });
	await page.mouse.up();
}

/** Poll until the rendered backdrop count settles (two equal reads). */
async function stableBackdropCount(page: Page): Promise<number> {
	let prev = -1;
	await expect
		.poll(
			async () => {
				const cur = await renderedBackdropCount(page);
				const settled = cur > 0 && cur === prev;
				prev = cur;
				return settled ? 'stable' : 'moving';
			},
			{ timeout: 60_000, intervals: [500, 1000, 2000] }
		)
		.toBe('stable');
	return renderedBackdropCount(page);
}

test.describe('Spec 026: /neuroscape/ year-aware backdrop density', () => {
	test.beforeEach(async ({ page }) => {
		test.setTimeout(240_000);
		await page.goto(neuroscapeUrl(), { waitUntil: 'domcontentloaded' });
		await page.getByTestId('search-input').waitFor({ state: 'visible', timeout: 30_000 });
		// Ensure the map is mounted (desktop shows it by default; on a narrow
		// project tap "Show map").
		const chart = page.getByTestId('umap-chart-2d');
		if (!(await chart.isVisible().catch(() => false))) {
			const showMap = page.getByTestId('toggle-map');
			if (await showMap.isVisible().catch(() => false)) await showMap.click();
		}
		await chart.waitFor({ state: 'visible', timeout: 60_000 });
		// Wait for the corpus + scatter to settle before measuring.
		await stableBackdropCount(page);
	});

	test('B1/B2/B4/B5: compressed backdrop density while true counts reflect volume', async ({
		page
	}) => {
		// B1 — full-span baseline.
		const fullSpanDots = await stableBackdropCount(page);
		expect(fullSpanDots).toBeGreaterThan(0);

		// EARLY-era narrow window (left ~15% of the track).
		await dragToFraction(page, 'neuroscape-year-handle-start', 0.02);
		await dragToFraction(page, 'neuroscape-year-handle-end', 0.17);
		const earlyDots = await stableBackdropCount(page);
		const earlyResults = await resultCount(page);

		// RECENT-era narrow window (right ~15% of the track), same width.
		await dragToFraction(page, 'neuroscape-year-handle-start', 0.83);
		await dragToFraction(page, 'neuroscape-year-handle-end', 0.98);
		const recentDots = await stableBackdropCount(page);
		const recentResults = await resultCount(page);

		// B4 / FR-006 — the RESULT list still reflects TRUE volume: recent
		// years have many more articles than early years.
		expect(recentResults).toBeGreaterThan(earlyResults);

		// B2 / SC-001 — the rendered BACKDROP density is compressed: the two
		// same-width windows are within a bounded ratio (generous band for
		// e2e; the pre-feature swing was 10×+). Guard against divide-by-zero.
		expect(earlyDots).toBeGreaterThan(0);
		expect(recentDots).toBeGreaterThan(0);
		const ratio = recentDots / earlyDots;
		expect(ratio).toBeLessThanOrEqual(4);
		// And both windows render fewer dots than the full span.
		expect(recentDots).toBeLessThanOrEqual(fullSpanDots);

		// B5 — clearing the year filter restores ~the full-span backdrop.
		await page.getByTestId('neuroscape-facets-clear').click();
		const restored = await stableBackdropCount(page);
		expect(Math.abs(restored - fullSpanDots) / fullSpanDots).toBeLessThan(0.1);
	});
});
