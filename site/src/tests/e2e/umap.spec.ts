import { test, expect } from '@playwright/test';

const DATA_AVAILABLE = process.env.UI_DATA_AVAILABLE !== '0';

test.describe('US2: UMAP panel + lasso + model selector', () => {
	test.skip(!DATA_AVAILABLE, 'Data package not deployed in this run');

	test('opens map; lazy-loads Plotly; default cell renders', async ({ page }) => {
		await page.goto('/');
		await expect(page.getByTestId('result-count')).toBeVisible({ timeout: 5000 });
		// Map is hidden by default.
		await expect(page.getByTestId('umap-panel')).toHaveCount(0);

		await page.getByTestId('toggle-map').click();
		const panel = page.getByTestId('umap-panel');
		await expect(panel).toBeVisible();

		// Plotly is lazy-loaded; the chart container appears after ~1s.
		await expect(page.getByTestId('umap-chart')).toBeVisible();
		// Wait until Plotly has injected an SVG (or WebGL canvas).
		await expect
			.poll(
				async () =>
					page.locator('[data-testid="umap-chart"] svg, [data-testid="umap-chart"] canvas').count(),
				{ timeout: 10000 }
			)
			.toBeGreaterThan(0);
	});

	test('model selector switches the cell shard; lasso selection persists by abstract_id', async ({
		page
	}) => {
		await page.goto('/');
		await page.getByTestId('toggle-map').click();
		await expect(page.getByTestId('umap-chart')).toBeVisible();
		await expect
			.poll(
				async () =>
					page.locator('[data-testid="umap-chart"] svg, [data-testid="umap-chart"] canvas').count(),
				{ timeout: 10000 }
			)
			.toBeGreaterThan(0);

		// Simulate a synthetic lasso event via Plotly's emit hook on the chart div.
		// Selecting two arbitrary points (indices 0 and 1) is enough to verify the
		// store → ResultList wiring.
		const fakeSelection = await page.evaluate(() => {
			const el = document.querySelector('[data-testid="umap-chart"]') as unknown as {
				emit?: (event: string, payload: unknown) => void;
			} | null;
			if (!el?.emit) return false;
			el.emit('plotly_selected', {
				points: [
					{ pointIndex: 0 },
					{ pointIndex: 1 }
				]
			});
			return true;
		});
		expect(fakeSelection).toBe(true);

		const clear = page.getByTestId('umap-clear-lasso');
		await expect(clear).toBeVisible({ timeout: 3000 });
		// "Clear selection (2)" is what the button label should say.
		await expect(clear).toHaveText(/Clear selection \(2\)/);

		// Switch the model — coordinates should re-render but the abstract_id set
		// stays selected (the store doesn't reset).
		await page.getByTestId('model-selector-model').selectOption('voyage');
		await expect(clear).toBeVisible();
		await expect(clear).toHaveText(/Clear selection \(2\)/);

		// Clear the selection.
		await clear.click();
		await expect(clear).toHaveCount(0);
	});
});
