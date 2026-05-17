import { test, expect } from '@playwright/test';

const DATA_AVAILABLE = process.env.UI_DATA_AVAILABLE !== '0';

/**
 * T036a / FR-011 — the detail panel surfaces **only** the Topics + Methods
 * extra-question fields. Other submission-form extras (study_type,
 * population, field_strength, processing_packages, species, etc.) live in
 * `facets` for filtering but MUST NOT render in the detail panel.
 *
 * Negative test: scan the panel's DOM for any leakage of the other facet
 * keys. The fixture-style assertion here scans the live corpus instead of a
 * synthetic abstract — that catches both component bugs and accidental
 * shard-schema regressions.
 */
test.describe('FR-011 — detail panel renders only Topics + Methods extras', () => {
	test.skip(!DATA_AVAILABLE, 'Data package not deployed in this run');

	test('opening any abstract shows topics + methods + no other facet keys as headings', async ({
		page
	}) => {
		await page.goto('/');
		await expect(page.getByTestId('result-card').first()).toBeVisible({ timeout: 5000 });
		await page.getByTestId('result-card').first().click();
		await expect(page.getByTestId('detail-panel')).toBeVisible();

		// Allowed extra-question sections — at least one must be visible.
		const topicsCount = await page.getByTestId('extra-topics').count();
		const methodsCount = await page.getByTestId('extra-methods').count();
		expect(topicsCount + methodsCount).toBeGreaterThan(0);

		// Forbidden extra-question keys must NOT appear as testid'd blocks.
		const forbidden = [
			'extra-study_type',
			'extra-population',
			'extra-field_strength',
			'extra-processing_packages',
			'extra-species',
			'extra-recording_technology',
			'extra-brain_regions',
			'extra-brain_networks',
			'extra-keywords'
		];
		for (const key of forbidden) {
			await expect(page.getByTestId(key)).toHaveCount(0);
		}

		// Defensive: the rendered <h2> headings inside the detail panel are
		// limited to Authors / Introduction / Methods / Results / Conclusion /
		// Topics / Methods (the checklist) / References.
		const headings = await page.getByTestId('detail-panel').locator('h2').allTextContents();
		const allowed = new Set([
			'Authors',
			'Introduction',
			'Methods',
			'Results',
			'Conclusion',
			'Topics',
			'References'
		]);
		for (const h of headings) {
			expect(allowed.has(h.trim())).toBe(true);
		}
	});
});
