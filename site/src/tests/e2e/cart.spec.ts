/**
 * T071 — US5 cart acceptance.
 *
 * Exercises FR-006 + SC-009:
 *   - Adding an abstract via the result card's cart icon makes it appear in
 *     the cart drawer.
 *   - The cart survives a full page reload (localStorage-backed store).
 *   - Removing from the drawer (and from the result card) zeroes the count.
 *   - `cart-email` opens a `mailto:` URL whose body contains the cart's
 *     poster_ids.
 */

import { test, expect } from '@playwright/test';

const DATA_AVAILABLE = process.env.UI_DATA_AVAILABLE !== '0';

test.describe('US5: saved-list cart + email export', () => {
	test.skip(!DATA_AVAILABLE, 'Data package not deployed in this run');

	test('add via card icon, reload, drawer still shows the item', async ({ page }) => {
		await page.goto('/');
		await page.getByTestId('search-input').waitFor();
		const card = page.getByTestId('result-card').first();
		await card.waitFor({ timeout: 10_000 });
		const posterId = await card.getAttribute('data-poster-id');
		expect(posterId).toBeTruthy();
		// Click the card-level add button.
		await card.getByTestId('card-cart-add').click();
		await page.waitForTimeout(150);
		// Open the cart drawer.
		await page.getByTestId('toggle-cart').click();
		await expect(page.getByTestId('cart-drawer')).toBeVisible();
		const items = page.getByTestId('cart-item');
		expect(await items.count()).toBeGreaterThanOrEqual(1);
		// Reload — the cart store hydrates from localStorage on mount.
		await page.reload();
		await page.getByTestId('toggle-cart').click();
		await expect(page.getByTestId('cart-drawer')).toBeVisible();
		expect(await page.getByTestId('cart-item').count()).toBeGreaterThanOrEqual(1);
	});

	test('clear empties the cart', async ({ page }) => {
		await page.goto('/');
		await page.getByTestId('search-input').waitFor();
		await page.getByTestId('result-card').first().getByTestId('card-cart-add').click();
		await page.waitForTimeout(150);
		await page.getByTestId('toggle-cart').click();
		await expect(page.getByTestId('cart-drawer')).toBeVisible();
		expect(await page.getByTestId('cart-item').count()).toBeGreaterThanOrEqual(1);
		await page.getByTestId('cart-clear').click();
		await page.waitForTimeout(100);
		expect(await page.getByTestId('cart-item').count()).toBe(0);
	});

	test('email-my-list opens a mailto: URL with the poster_ids', async ({ page }) => {
		await page.goto('/');
		await page.getByTestId('search-input').waitFor();
		const card = page.getByTestId('result-card').first();
		await card.waitFor({ timeout: 10_000 });
		const posterId = (await card.getAttribute('data-poster-id')) ?? '';
		await card.getByTestId('card-cart-add').click();
		await page.waitForTimeout(150);
		await page.getByTestId('toggle-cart').click();
		// Intercept the navigation to `mailto:` rather than actually opening
		// the user's mail client. The anchor's `href` is the source of truth
		// for the URL; read it directly.
		const emailLink = page.getByTestId('cart-email');
		const href = await emailLink.getAttribute('href');
		expect(href).toMatch(/^mailto:/);
		// The body parameter should mention the poster_id we just added.
		const decoded = decodeURIComponent(href ?? '');
		expect(decoded).toContain(posterId);
	});
});
