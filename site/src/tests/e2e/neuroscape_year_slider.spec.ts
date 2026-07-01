/**
 * Spec 025 — NeuroScape atlas year range slider e2e.
 *
 * Verifies the user-facing acceptance scenarios from
 * specs/025-neuroscape-year-range-slider/contracts/slider-ui.md
 * (U1–U6) against the `/neuroscape/` sibling deploy:
 *
 *   U1 two handles render at the corpus bounds; readout shows lo–hi;
 *      no active year filter on first open
 *   U2 dragging the start handle right raises the start year + activates
 *      the filter (US1, FR-003)
 *   U3 dragging the end handle left lowers the end year (US1, FR-003)
 *   U4 dragging the band shifts both ends, width preserved (US2, FR-004)
 *   U5 "Clear" resets both handles to the bounds + drops the filter
 *      (FR-008)
 *   U6 the readout always matches the handle positions (SC-004)
 *
 * Plus a keyboard check (FR-010 / SC-005). Like semantic.spec.ts this
 * runs against the deployed preview; the 461k-article parquet streams
 * over several seconds, so we poll for the result list before
 * interacting. The slider's year bounds are only populated once the
 * backdrop has loaded.
 */
import { test, expect, type Page } from '@playwright/test';

function neuroscapeUrl(): string {
	const raw = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:4173/ohbm2026/';
	const base = raw.endsWith('/') ? raw : `${raw}/`;
	return base.replace(/\/ohbm2026\/$/, '/neuroscape/');
}

/** Parse the "<start>–<end>" readout into numbers. */
async function readout(page: Page): Promise<{ start: number; end: number }> {
	const text = await page.getByTestId('neuroscape-year-readout').innerText();
	const m = text.match(/(\d{4})\D+(\d{4})/s);
	if (!m) throw new Error(`Unexpected year readout: ${JSON.stringify(text)}`);
	return { start: Number(m[1]), end: Number(m[2]) };
}

/** Drag a handle (or the band) to an absolute x at the track's vertical centre. */
async function dragToFraction(page: Page, testid: string, frac: number): Promise<void> {
	const track = page.getByTestId('neuroscape-year-slider').locator('.track');
	const tbox = await track.boundingBox();
	const handle = page.getByTestId(testid);
	const hbox = await handle.boundingBox();
	if (!tbox || !hbox) throw new Error('slider track/handle not laid out');
	const targetX = tbox.x + tbox.width * frac;
	const y = tbox.y + tbox.height / 2;
	await page.mouse.move(hbox.x + hbox.width / 2, hbox.y + hbox.height / 2);
	await page.mouse.down();
	await page.mouse.move(targetX, y, { steps: 12 });
	await page.mouse.up();
}

test.describe('Spec 025: /neuroscape/ year range slider', () => {
	test.beforeEach(async ({ page }) => {
		// Heavy suite: every handle/band drag recomputes the year filter
		// over the 461k-article corpus + re-renders the backdrop (~30-60s
		// each on the preview infra), and U4 chains three drags after the
		// stabilisation wait. 180s tips over on the busiest test; budget
		// 240s to match the semantic suite and stop riding the timeout.
		test.setTimeout(240_000);
		await page.goto(neuroscapeUrl(), { waitUntil: 'domcontentloaded' });
		await page.getByTestId('search-input').waitFor({ state: 'visible', timeout: 30_000 });
		// Wait for the backdrop/result list to populate AND settle. The
		// 461k-article corpus streams over several seconds and
		// `yearBounds` is derived from the loaded points, so the slider's
		// upper bound keeps ticking up (e.g. 2022→2023) until the load
		// finishes. Poll until the row count is STABLE across two reads
		// (mirrors semantic.spec.ts) so a full-span handle isn't still
		// tracking a moving bound while a test captures a baseline.
		let previous = -1;
		await expect
			.poll(
				async () => {
					const cur = await page.getByTestId('neuroscape-result-row').count();
					if (cur === 0) return 'empty';
					const settled = cur === previous;
					previous = cur;
					return settled ? 'stable' : 'changing';
				},
				{ timeout: 120_000, intervals: [1_000, 2_000, 3_000] }
			)
			.toBe('stable');
		// On the narrow mobile project the facet sidebar is behind the
		// "🔍 Filters" toggle; open it if the slider isn't already shown.
		const slider = page.getByTestId('neuroscape-year-slider');
		if (!(await slider.isVisible())) {
			await page.getByTestId('toggle-facets').click();
		}
		await slider.waitFor({ state: 'visible', timeout: 30_000 });
	});

	test('U1: two handles at the corpus bounds, no active year filter', async ({ page }) => {
		await expect(page.getByTestId('neuroscape-year-handle-start')).toBeVisible();
		await expect(page.getByTestId('neuroscape-year-handle-end')).toBeVisible();
		const { start, end } = await readout(page);
		expect(end).toBeGreaterThan(start);
		// Full span ⇒ the facet "Clear (N)" badge is absent (FR-007).
		await expect(page.getByTestId('neuroscape-facets-clear')).toHaveCount(0);
		// aria values agree with the readout (SC-004 / FR-010).
		expect(
			Number(await page.getByTestId('neuroscape-year-handle-start').getAttribute('aria-valuenow'))
		).toBe(start);
		expect(
			Number(await page.getByTestId('neuroscape-year-handle-end').getAttribute('aria-valuenow'))
		).toBe(end);
	});

	test('U2: dragging the start handle right raises the start year + activates the filter', async ({
		page
	}) => {
		const before = await readout(page);
		await dragToFraction(page, 'neuroscape-year-handle-start', 0.3);
		const after = await readout(page);
		expect(after.start).toBeGreaterThan(before.start);
		// Dragging the START handle never lowers the end. It stays equal,
		// except the initial full-span end tracks the corpus upper bound,
		// which may still tick up as the corpus finishes streaming — so
		// assert "does not decrease" rather than strict equality.
		expect(after.end).toBeGreaterThanOrEqual(before.end);
		// The year filter is now active (FR-007/FR-008 badge).
		await expect(page.getByTestId('neuroscape-facets-clear')).toBeVisible();
	});

	test('U3: dragging the end handle left lowers the end year', async ({ page }) => {
		const before = await readout(page);
		await dragToFraction(page, 'neuroscape-year-handle-end', 0.7);
		const after = await readout(page);
		expect(after.end).toBeLessThan(before.end);
		expect(after.start).toBe(before.start);
	});

	test('U4: dragging the band shifts both ends, width preserved', async ({ page }) => {
		// First narrow to a sub-window so the band has width to drag.
		await dragToFraction(page, 'neuroscape-year-handle-start', 0.3);
		await dragToFraction(page, 'neuroscape-year-handle-end', 0.6);
		const before = await readout(page);
		const widthBefore = before.end - before.start;
		expect(widthBefore).toBeGreaterThan(0);

		await dragToFraction(page, 'neuroscape-year-band', 0.75);
		const after = await readout(page);
		expect(after.end - after.start).toBe(widthBefore); // width preserved
		expect(after.start).toBeGreaterThan(before.start); // window moved later
	});

	test('U5: Clear resets both handles to the bounds and drops the filter', async ({ page }) => {
		await dragToFraction(page, 'neuroscape-year-handle-start', 0.4);
		await expect(page.getByTestId('neuroscape-facets-clear')).toBeVisible();
		await page.getByTestId('neuroscape-facets-clear').click();
		// After Clear the window is full span: each handle sits at its
		// bound. Assert against the handles' live aria-valuemin/max rather
		// than a baseline captured before the corpus finished streaming
		// (the bounds can shift mid-load).
		const startHandle = page.getByTestId('neuroscape-year-handle-start');
		const endHandle = page.getByTestId('neuroscape-year-handle-end');
		expect(await startHandle.getAttribute('aria-valuenow')).toBe(
			await startHandle.getAttribute('aria-valuemin')
		);
		expect(await endHandle.getAttribute('aria-valuenow')).toBe(
			await endHandle.getAttribute('aria-valuemax')
		);
		await expect(page.getByTestId('neuroscape-facets-clear')).toHaveCount(0);
	});

	test('FR-010: start handle is keyboard-operable', async ({ page }) => {
		const before = await readout(page);
		const startHandle = page.getByTestId('neuroscape-year-handle-start');
		await startHandle.focus();
		await startHandle.press('ArrowRight');
		const after = await readout(page);
		expect(after.start).toBe(before.start + 1);
		await startHandle.press('ArrowLeft');
		expect((await readout(page)).start).toBe(before.start);
	});
});
