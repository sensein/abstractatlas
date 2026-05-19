import { describe, expect, it } from 'vitest';
import {
	buildMailtoLink,
	buildPlainTextList,
	MAX_MAILTO_LENGTH
} from '$lib/cart_email';
import type { AbstractRecord } from '$lib/shards';

function rec(posterId: number, title: string): AbstractRecord {
	return {
		poster_id: posterId,
		title,
		accepted_for: 'Poster',
		sections: { introduction: '', methods: '', results: '', conclusion: '', references: '' },
		topics: { primary: '', primary_subcategory: '', secondary: '', secondary_subcategory: '' },
		methods_checklist: [],
		facets: {},
		author_ids: [],
		reference_dois: [],
		reference_urls: [],
		reference_titles: []
	};
}

function pad(id: number): string {
	return String(id).padStart(4, '0');
}

describe('buildMailtoLink', () => {
	it('produces a mailto: URL with the standard subject', () => {
		const url = buildMailtoLink([rec(101, 'Memory in aging')], new Map(), {
			siteUrl: 'https://example.org/atlas'
		});
		expect(url.startsWith('mailto:?subject=')).toBe(true);
		expect(decodeURIComponent(url)).toContain('My OHBM 2026 abstract list');
	});

	it('embeds each abstract as poster_id + title + permalink', () => {
		const items = [rec(101, 'A'), rec(102, 'B')];
		const url = buildMailtoLink(items, new Map(), { siteUrl: 'https://example.org/atlas' });
		const body = decodeURIComponent(url.split('&body=')[1]);
		expect(body).toContain(pad(101));
		expect(body).toContain(pad(102));
		expect(body).toContain(`https://example.org/atlas/abstract/${pad(101)}/`);
		expect(body).toContain(`https://example.org/atlas/abstract/${pad(102)}/`);
	});

	it('includes lead author when provided', () => {
		const items = [rec(101, 'Memory in aging')];
		const leads = new Map<number, string>([[101, 'José García']]);
		const url = buildMailtoLink(items, leads, { siteUrl: 'https://example.org' });
		const body = decodeURIComponent(url.split('&body=')[1]);
		expect(body).toContain('— José García');
	});

	it('truncates by item count (not byte budget) and inserts a marker', () => {
		// Manufacture 500 fake abstracts; truncation now kicks in at the
		// item-count cap (MAX_EMAIL_ITEMS = 100). The body may exceed
		// MAX_MAILTO_LENGTH — modern mail clients tolerate that, and the
		// whole point is to transfer the saved-list data OUT of the site.
		const many = Array.from({ length: 500 }, (_, i) =>
			rec(i + 1, `Abstract title number ${i} — a longish placeholder so each line eats bytes`)
		);
		const url = buildMailtoLink(many, new Map(), { siteUrl: 'https://example.org/atlas' });
		const body = decodeURIComponent(url.split('&body=')[1]);
		expect(body).toContain('more items not shown');
		// Body MUST also carry the cart-restore URL so the recipient
		// can rebuild the full saved-list state with one click.
		expect(body).toMatch(/\?cart=\d{4}(,\d{4})+/);
		// All 500 ids should be in the restore URL despite the visible
		// list being truncated.
		const restoreMatch = body.match(/\?cart=([\d,]+)/);
		expect(restoreMatch).not.toBeNull();
		expect(restoreMatch![1].split(',').length).toBe(500);
	});

	it('includes ALL items in the body when the cart is at-or-below the item cap', () => {
		// 100-item cart should land in the body in full, no truncation.
		const at_cap = Array.from({ length: 100 }, (_, i) => rec(i + 1, `Title ${i}`));
		const url = buildMailtoLink(at_cap, new Map(), { siteUrl: 'https://example.org' });
		const body = decodeURIComponent(url.split('&body=')[1]);
		expect(body).not.toContain('more items not shown');
		// First and last item numbers both present.
		expect(body).toMatch(/^1\. \[/m);
		expect(body).toMatch(/^100\. \[/m);
	});

	it('handles an empty cart gracefully', () => {
		const url = buildMailtoLink([], new Map(), { siteUrl: 'https://example.org' });
		expect(url.startsWith('mailto:?')).toBe(true);
		const body = decodeURIComponent(url.split('&body=')[1]);
		expect(body).toContain('(0 items)');
	});

	it('puts each item on its own numbered block with a labelled Open link', () => {
		const items = [rec(101, 'Memory in aging'), rec(102, 'Vision')];
		const url = buildMailtoLink(items, new Map(), { siteUrl: 'https://example.org/atlas' });
		const body = decodeURIComponent(url.split('&body=')[1]);
		expect(body).toContain(`1. [${pad(101)}] Memory in aging`);
		expect(body).toContain(`2. [${pad(102)}] Vision`);
		expect(body).toContain(`→ Open: https://example.org/atlas/abstract/${pad(101)}/`);
		expect(body).toContain(`→ Open: https://example.org/atlas/abstract/${pad(102)}/`);
		expect(body).toContain('Browse the rest at https://example.org/atlas/');
	});

	it('respects custom subject', () => {
		const url = buildMailtoLink([], new Map(), {
			siteUrl: 'https://example.org',
			subject: 'Hand-picked for you'
		});
		expect(url).toContain('subject=Hand-picked%20for%20you');
	});
});

describe('buildPlainTextList', () => {
	it('produces a clipboard-friendly plain-text rendering', () => {
		const items = [rec(101, 'Memory in aging')];
		const txt = buildPlainTextList(items, new Map(), 'https://example.org');
		expect(txt).toContain(pad(101));
		expect(txt).toContain('Memory in aging');
		expect(txt).toContain(`https://example.org/abstract/${pad(101)}/`);
	});
});
