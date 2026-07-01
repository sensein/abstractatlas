/**
 * Stage 24 (specs/024-fix-ios-safari-load) — T019 sibling-site scope check.
 *
 * atlas-root (`/`) and `/neuroscape/` share the same bootstrap (+layout /
 * +page / +error) and the same UmapPanel + capability gate as `/ohbm2026/`,
 * so the R1 (visible failure) and R2 (mobile 2D-only / no auto-rotate) fixes
 * already apply to them. This spec verifies empirically that neither sibling
 * exhibits the blank-screen / endless-spinner failure on iPhone-Safari WebKit:
 * the page must reach a NON-blank, settled state (chrome + either an
 * interactive map/list/backdrop, or a visible error) — never a permanent
 * bare spinner.
 *
 * Sibling URLs are derived from PLAYWRIGHT_BASE_URL (…/<prefix>/ohbm2026/), so
 * this runs against whatever deploy that points at. Run on the deployed
 * preview origin where the data host's CORS resolves:
 *   PLAYWRIGHT_BASE_URL=https://abstractatlas.brainkb.org/pr-N/ohbm2026/ \
 *     pnpm exec playwright test --project=iphone-webkit ios-siblings
 *
 * Skipped when no data package / base URL is wired (UI_DATA_AVAILABLE=0).
 */

import { test, expect, type Page } from '@playwright/test';

const DATA_AVAILABLE = process.env.UI_DATA_AVAILABLE !== '0';
const BASE = process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:4173/ohbm2026/';

// …/<prefix>/ohbm2026/ → atlas-root drops the trailing `ohbm2026/`; neuroscape
// swaps it for `neuroscape/`.
const ATLAS_ROOT_URL = BASE.replace(/ohbm2026\/?$/, '');
const NEUROSCAPE_URL = BASE.replace(/ohbm2026\/?$/, 'neuroscape/');

async function bodyText(page: Page): Promise<string> {
	return (await page.locator('body').innerText().catch(() => '')) ?? '';
}

test.describe('T019: sibling sites load on iPhone Safari (WebKit)', () => {
	test.skip(!DATA_AVAILABLE, 'No data package wired in this run');
	test.setTimeout(120_000); // siblings pull larger corpora (atlas / neuroscape)

	for (const [name, url] of [
		['atlas-root', ATLAS_ROOT_URL],
		['neuroscape', NEUROSCAPE_URL]
	] as const) {
		test(`${name}: reaches a non-blank, settled state (no blank/endless spinner)`, async ({
			page
		}) => {
			await page.goto(url);
			// Chrome renders → JS ran, not a blank white page. (The bootstrap
			// only reaches this — vs staying on `{#if !loaded}Loading…` — once
			// the critical load settled or errored; a blank/endless-spinner
			// regression fails HERE.)
			await expect(page.getByTestId('search-input')).toBeVisible({ timeout: 15_000 });
			// It must SETTLE off the bare spinner into a real interactive state.
			// That state is mode/viewport dependent, so accept ANY of:
			//   - the 2D scatter mounted (desktop, or after opting into the map)
			//   - the WebGL-unavailable note (no-WebGL device that opened the map)
			//   - a visible load/route error banner
			//   - the mobile map-defer landing: on phones `atlasShowMap` defaults
			//     OFF (+page.svelte:1410) so the heavy scatter + its 25–96 MB
			//     parquet are deferred behind the "Show map" toggle; the settled
			//     page shows chrome + that toggle + the mobile tip, NOT a chart.
			//     `toggle-map` only renders past the `{#if !loaded}Loading…`
			//     gate, so its presence proves we left the bare spinner.
			// (Headless WebKit has no WebGL and a mobile viewport, so on the
			// iphone-webkit project the siblings legitimately land here — see
			// ios-ohbm-load.spec.ts, which likewise gates on non-chart signals.)
			await expect
				.poll(
					async () => {
						const mapUp = (await page.getByTestId('umap-chart-2d').count()) > 0;
						const mapNote = (await page.getByTestId('umap-unavailable').count()) > 0;
						const errored = (await page.getByTestId('load-error').count()) > 0;
						const routeErr = (await page.getByTestId('route-error').count()) > 0;
						const mapDeferred = await page
							.getByTestId('toggle-map')
							.isVisible()
							.catch(() => false);
						if (mapUp || mapNote || errored || routeErr || mapDeferred) return 'settled';
						const txt = await bodyText(page);
						// A visible error banner (atlas-root/neuroscape use their own).
						if (/couldn.t load|failed to load|unavailable|error/i.test(txt)) return 'settled';
						return 'pending';
					},
					{ timeout: 90_000, intervals: [500, 1000, 2000] }
				)
				.toBe('settled');
			// Reaching 'settled' proves it left the bare spinner: the poll only
			// returns 'settled' on a mounted map / note / error / the interactive
			// mobile map-defer landing — never a permanent "Loading…".
		});
	}
});
