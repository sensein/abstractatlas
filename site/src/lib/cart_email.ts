/**
 * Cart → email helpers (US5 / FR-015).
 *
 * `buildMailtoLink(items, options)` returns a `mailto:` URL whose subject /
 * body are pre-populated with the user's saved abstract list. Bodies are
 * truncated to MAX_MAILTO_LENGTH so the URL stays below the 2000-character
 * limit that some mail clients (Outlook, system handlers on Windows) impose
 * on `mailto:` strings.
 *
 * Every body — truncated or not — leads with a "Restore the full cart"
 * URL of the form `<siteUrl>/?cart=0001,0042,...`. The home route reads
 * the `?cart=` query parameter on load and merges those poster_ids into
 * the cart store via `cartStore.addMany()`. That means even when a long
 * cart is truncated in the visible list, the recipient (or sender on a
 * different machine) can click the restore URL and get every saved
 * abstract back.
 */

import type { AbstractRecord } from '$lib/shards';

/** Item-based cap for the email body. Beyond this many items the
 * body switches to "first N items + truncation marker"; the
 * restore-URL at the top still lets the recipient open all of them
 * via the Atlas. Item-count cap (instead of byte cap) gives every
 * cart of typical size a complete, self-contained email body —
 * the whole point of "email my list" is to transfer the data OUT
 * of the site.
 */
export const MAX_EMAIL_ITEMS = 100;

/** Legacy byte cap, kept as a backstop. Most modern mail clients
 *  accept much larger mailto URLs (Mac Mail, Gmail web, Outlook
 *  365 all handle >5 KB); we don't enforce this for typical-sized
 *  carts but the constant remains for tests + future tuning.
 */
export const MAX_MAILTO_LENGTH = 1900;

export interface CartEmailOptions {
	/** Public site origin + path, used to embed permalinks per item. Trailing slash optional. */
	siteUrl: string;
	/** Optional subject override. Defaults to "My OHBM 2026 abstract list". */
	subject?: string;
}

function trimSlash(s: string): string {
	return s.endsWith('/') ? s.slice(0, -1) : s;
}

function permalinkFor(siteUrl: string, posterId: string): string {
	return `${trimSlash(siteUrl)}/abstract/${encodeURIComponent(posterId)}/`;
}

/**
 * Build a deep-link URL that hydrates the home page's cart with the
 * supplied poster_ids. Format: `<siteUrl>/?cart=0001,0042,0123`.
 * Poster ids are zero-padded for human readability; the home route's
 * cart-hydrate handler accepts both padded and bare numeric forms.
 *
 * The URL fits the comma-separated list inline; for 3,333 posters the
 * worst case is ~5 chars × 3333 ≈ 16,650 chars which exceeds typical
 * mailto budgets, but for human-sized carts (tens to low hundreds) it
 * fits comfortably. Callers SHOULD include this URL above the
 * per-item list so the user can recover even when the visible list
 * gets truncated.
 */
export function buildCartRestoreUrl(siteUrl: string, posterIds: number[]): string {
	const padded = posterIds
		.filter((id) => Number.isFinite(id) && id > 0)
		.map((id) => String(id).padStart(4, '0'))
		.join(',');
	const base = trimSlash(siteUrl);
	return padded ? `${base}/?cart=${padded}` : `${base}/`;
}

/**
 * Render one cart item as a four-line block:
 *
 *   1. [M-AM-101] Title goes here, wrapped if it's long
 *      — Lead Author
 *      → Open: https://abstractatlas.brainkb.org/abstract/M-AM-101/
 *
 * The `→ Open: <url>` line uses an arrow prefix + label so the URL reads
 * unambiguously as "click here to view the abstract" inside any email
 * client. Most clients auto-linkify a bare URL on its own line, which is
 * why the URL ends the block.
 */
function renderItemLine(
	record: AbstractRecord,
	leadAuthor: string,
	siteUrl: string,
	index: number
): string {
	// poster_id is the sole identifier; format as zero-padded 4-digit for display
	const id = record.poster_id ? String(record.poster_id).padStart(4, '0') : '';
	const url = record.poster_id ? permalinkFor(siteUrl, id) : '';
	const lines: string[] = [`${index}. [${id}] ${record.title}`];
	if (leadAuthor) lines.push(`   — ${leadAuthor}`);
	if (url) lines.push(`   → Open: ${url}`);
	return lines.join('\n');
}

/**
 * Build the mailto: URL for a cart of abstracts.
 *
 * @param items   Records the user has saved (already filtered to those in cart).
 * @param leadAuthorByPosterId  Maps poster_id → first-author display string.
 *                                Empty string if unknown. Caller computes this.
 * @param options Site URL + optional subject override.
 */
export function buildMailtoLink(
	items: AbstractRecord[],
	leadAuthorByPosterId: Map<number, string>,
	options: CartEmailOptions
): string {
	const subject = options.subject ?? 'My OHBM 2026 abstract list';
	const subjectPart = 'mailto:?subject=' + encodeURIComponent(subject) + '&body=';
	const siteHome = trimSlash(options.siteUrl);
	const restoreUrl = buildCartRestoreUrl(
		options.siteUrl,
		items.map((r) => r.poster_id)
	);
	// Lead the body with the cart-restore URL so a recipient (or
	// sender on a different machine) can rebuild the full saved-list
	// state with one click — useful when their cart is empty on the
	// device they're opening the email from.
	const header =
		`Saved abstracts from the OHBM 2026 Atlas (${items.length} item${items.length === 1 ? '' : 's'}).\n\n` +
		`★ Open all ${items.length} item${items.length === 1 ? '' : 's'} in the Atlas (restores the cart): ${restoreUrl}\n\n` +
		`Each entry below has an "Open:" link that lands directly on its full-detail page.\n\n`;
	const footer = `\n\n— Browse the rest at ${siteHome}/`;

	// Item-count cap, NOT byte cap. The mailto's purpose is to ship
	// the data out of the site; cutting the body short to please
	// Outlook 2083 defeats that. Modern mail clients accept much
	// larger URLs; for huge carts (> MAX_EMAIL_ITEMS) we truncate
	// and the restore URL above does the rest.
	const visibleCount = Math.min(items.length, MAX_EMAIL_ITEMS);
	const truncated = items.length > MAX_EMAIL_ITEMS;
	const lines = items
		.slice(0, visibleCount)
		.map((rec, i) =>
			renderItemLine(
				rec,
				leadAuthorByPosterId.get(rec.poster_id) ?? '',
				options.siteUrl,
				i + 1
			)
		);
	const truncationSuffix = truncated
		? `\n\n…(${items.length - visibleCount} more items not shown above; click the ★ link at the top to load the FULL list back into your cart.)`
		: '';

	const body = header + lines.join('\n\n') + truncationSuffix + footer;
	return subjectPart + encodeURIComponent(body);
}

/** Plain-text rendering (for the clipboard fallback). Includes
 * EVERY saved item — the clipboard path has no length budget so the
 * email truncation doesn't apply here.
 */
export function buildPlainTextList(
	items: AbstractRecord[],
	leadAuthorByPosterId: Map<number, string>,
	siteUrl: string
): string {
	const siteHome = trimSlash(siteUrl);
	const restoreUrl = buildCartRestoreUrl(
		siteUrl,
		items.map((r) => r.poster_id)
	);
	const header =
		`Saved abstracts from the OHBM 2026 Atlas (${items.length} item${items.length === 1 ? '' : 's'}).\n\n` +
		`★ Open all ${items.length} item${items.length === 1 ? '' : 's'} in the Atlas (restores the cart): ${restoreUrl}\n\n` +
		`Each entry below has an "Open:" link that lands directly on its full-detail page.\n\n`;
	const body = items
		.map((rec, i) =>
			renderItemLine(rec, leadAuthorByPosterId.get(rec.poster_id) ?? '', siteUrl, i + 1)
		)
		.join('\n\n');
	return header + body + `\n\n— Browse the rest at ${siteHome}/`;
}
