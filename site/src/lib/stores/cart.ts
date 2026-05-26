import { writable, get, derived, type Readable } from 'svelte/store';

/**
 * Stage 15 unifying cart — saves abstracts across all three sibling
 * subsites under one shared localStorage key. Items carry a `kind`
 * tag so the drawer + email export can render the right permalink
 * format per source:
 *
 *   - { kind: 'ohbm2026', id: <poster_id> }     → /ohbm2026/abstract/<n>/
 *   - { kind: 'neuroscape', id: <pubmed_id> }   → /neuroscape/abstract/<n>/
 *
 * Internally the store wraps a `Set<string>` of `"kind:id"` keys
 * (Sets need a primitive identity check; nested object keys would
 * deduplicate by reference, not value). Subscribers receive that
 * Set plus a typed `items: CartItem[]` view for convenience.
 *
 * Storage migration: v1 (`ohbm2026.ui.cart.v1`) stored a flat array
 * of integer poster_ids. On first load v2 reads + retags each
 * legacy entry as `{ kind: 'ohbm2026', id }`, writes the new key,
 * and clears v1 so subsequent loads skip the migration.
 *
 * Legacy `has(posterId: number)` / `add(posterId: number)` /
 * `remove(posterId: number)` helpers keep the existing OHBM
 * DetailPanel + ResultList code working unchanged — they're
 * defaulted to `kind: 'ohbm2026'`.
 */

export type CartKind = 'ohbm2026' | 'neuroscape';

export interface CartItem {
	kind: CartKind;
	id: number;
}

const STORAGE_KEY_V1 = 'ohbm2026.ui.cart.v1';
const STORAGE_KEY_V2 = 'ohbm2026.ui.cart.v2';

function _isBrowser(): boolean {
	return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function _itemKey(kind: CartKind, id: number): string {
	return `${kind}:${id}`;
}

function _parseKey(key: string): CartItem | null {
	const idx = key.indexOf(':');
	if (idx < 1) return null;
	const kind = key.slice(0, idx);
	const idStr = key.slice(idx + 1);
	if (kind !== 'ohbm2026' && kind !== 'neuroscape') return null;
	const id = Number(idStr);
	if (!Number.isFinite(id)) return null;
	return { kind, id };
}

function _toLegacyPosterId(v: unknown): number | null {
	if (typeof v === 'number') return Number.isFinite(v) ? v : null;
	if (typeof v === 'string') {
		const n = Number(v);
		return Number.isFinite(n) && /^[0-9]+$/.test(v) ? n : null;
	}
	return null;
}

function loadInitial(): Set<string> {
	if (!_isBrowser()) return new Set();
	// v2 first — fast path on subsequent loads.
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY_V2);
		if (raw) {
			const parsed = JSON.parse(raw);
			if (Array.isArray(parsed)) {
				const out = new Set<string>();
				for (const v of parsed) {
					if (
						v &&
						typeof v === 'object' &&
						(v.kind === 'ohbm2026' || v.kind === 'neuroscape') &&
						typeof v.id === 'number' &&
						Number.isFinite(v.id)
					) {
						out.add(_itemKey(v.kind, v.id));
					}
				}
				return out;
			}
		}
	} catch {
		/* fall through to migration */
	}
	// v1 migration — first load after upgrade. Read v1, retag as
	// ohbm2026, write v2, leave v1 in place for one cycle so a
	// rollback doesn't lose the cart.
	try {
		const rawV1 = window.localStorage.getItem(STORAGE_KEY_V1);
		if (!rawV1) return new Set();
		const parsed = JSON.parse(rawV1);
		if (!Array.isArray(parsed)) return new Set();
		const out = new Set<string>();
		for (const v of parsed) {
			const id = _toLegacyPosterId(v);
			if (id !== null) out.add(_itemKey('ohbm2026', id));
		}
		persist(out);
		return out;
	} catch {
		return new Set();
	}
}

function persist(items: Set<string>): void {
	if (!_isBrowser()) return;
	try {
		const payload: CartItem[] = [];
		for (const key of items) {
			const parsed = _parseKey(key);
			if (parsed) payload.push(parsed);
		}
		window.localStorage.setItem(STORAGE_KEY_V2, JSON.stringify(payload));
	} catch {
		// localStorage may be unavailable (e.g. private-browsing quota) — silent
		// degrade. The store still works in-memory for the session.
	}
}

const _store = writable<Set<string>>(loadInitial());

function _mutate(fn: (next: Set<string>) => void): void {
	const next = new Set(get(_store));
	fn(next);
	_store.set(next);
	persist(next);
}

function addItem(kind: CartKind, id: number): void {
	_mutate((next) => next.add(_itemKey(kind, id)));
}

function removeItem(kind: CartKind, id: number): void {
	_mutate((next) => next.delete(_itemKey(kind, id)));
}

function toggleItem(kind: CartKind, id: number): void {
	const key = _itemKey(kind, id);
	_mutate((next) => {
		if (next.has(key)) next.delete(key);
		else next.add(key);
	});
}

function hasItem(state: Set<string>, kind: CartKind, id: number): boolean {
	return state.has(_itemKey(kind, id));
}

function addManyItems(items: Iterable<CartItem>): void {
	_mutate((next) => {
		for (const it of items) next.add(_itemKey(it.kind, it.id));
	});
}

function removeManyItems(items: Iterable<CartItem>): void {
	_mutate((next) => {
		for (const it of items) next.delete(_itemKey(it.kind, it.id));
	});
}

function clearAll(): void {
	_store.set(new Set());
	persist(new Set());
}

function resetAll(items: Iterable<CartItem> = []): void {
	const next = new Set<string>();
	for (const it of items) next.add(_itemKey(it.kind, it.id));
	_store.set(next);
	persist(next);
}

// === Legacy single-kind API ============================================
// The existing OHBM 2026 code uses `cartStore.add(posterId)` etc. with
// raw numbers (poster_ids); these wrappers default the kind so call
// sites don't need changes.

function add(posterId: number): void {
	addItem('ohbm2026', posterId);
}
function remove(posterId: number): void {
	removeItem('ohbm2026', posterId);
}
function addMany(posterIds: Iterable<number>): void {
	const items: CartItem[] = [];
	for (const id of posterIds) if (id) items.push({ kind: 'ohbm2026', id });
	addManyItems(items);
}
function removeMany(posterIds: Iterable<number>): void {
	const items: CartItem[] = [];
	for (const id of posterIds) items.push({ kind: 'ohbm2026', id });
	removeManyItems(items);
}
function reset(items: Iterable<number> = []): void {
	const cartItems: CartItem[] = [];
	for (const id of items) cartItems.push({ kind: 'ohbm2026', id });
	resetAll(cartItems);
}

// === Derived views =====================================================

/** Typed item list. */
export const cartItems: Readable<CartItem[]> = derived(_store, ($state) => {
	const out: CartItem[] = [];
	for (const key of $state) {
		const parsed = _parseKey(key);
		if (parsed) out.push(parsed);
	}
	return out;
});

/** OHBM-only poster_id set — what `cartStore.has(posterId)` returned
 *  before Stage 15. Existing call sites that need a `Set<number>` for
 *  intersection with abstractsByPosterId keep using this. */
export const cartOhbmPosterIds: Readable<Set<number>> = derived(_store, ($state) => {
	const out = new Set<number>();
	for (const key of $state) {
		if (key.startsWith('ohbm2026:')) {
			const id = Number(key.slice('ohbm2026:'.length));
			if (Number.isFinite(id)) out.add(id);
		}
	}
	return out;
});

/** NeuroScape-only pubmed_id set — used by the /neuroscape/ subsite's
 *  result row + detail panel to render the in-cart pip. */
export const cartNeuroPubmedIds: Readable<Set<number>> = derived(_store, ($state) => {
	const out = new Set<number>();
	for (const key of $state) {
		if (key.startsWith('neuroscape:')) {
			const id = Number(key.slice('neuroscape:'.length));
			if (Number.isFinite(id)) out.add(id);
		}
	}
	return out;
});

// === Store contract ====================================================
// `subscribe` returns the OHBM poster_id Set so the dozens of
// `$cartStore.has(posterId)` / `$cartStore.size` call sites across
// DetailPanel + ResultList + +page.svelte keep working without
// touching every line. The new neuroscape + atlas-root call sites
// import `cartItems` / `hasItem` / `addItem` directly when they need
// the typed surface.

export const cartStore = {
	subscribe: cartOhbmPosterIds.subscribe,
	// Legacy single-kind API (poster_id only — defaults to ohbm2026)
	add,
	remove,
	addMany,
	removeMany,
	clear: clearAll,
	reset,
	// Typed API
	addItem,
	removeItem,
	toggleItem,
	hasItem,
	addManyItems,
	removeManyItems,
	clearAll,
	resetAll
};

export const CART_STORAGE_KEY = STORAGE_KEY_V2;
