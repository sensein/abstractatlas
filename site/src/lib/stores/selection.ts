import { writable } from 'svelte/store';

export interface CellSelection {
	model: string;
	input: string;
}

export const selectedCell = writable<CellSelection>({ model: 'neuroscape', input: 'abstract' });

export const searchQuery = writable<string>('');

export const activeFilters = writable<Map<string, Set<string>>>(new Map());

export const lassoSelection = writable<Set<number> | null>(null);

export const focusedAbstract = writable<string | null>(null);

/** "Show only saved" — restricts the result list to items currently in the
 *  cart. Pairs with the bulk-add affordance: save a set, flip this on,
 *  refine. Default off. Not persisted; resets per session. */
export const cartOnly = writable<boolean>(false);

/** Active author-name chips. Clicking an author name in any detail view
 *  adds the name to this set; the result list intersects with abstracts
 *  whose `author_ids` include any of these names. Render as removable
 *  chips next to the search bar; clearing them all returns to the
 *  unfiltered (by author) state. Non-destructive — coexists with the
 *  search query / facets / lasso. */
export const authorChips = writable<Set<string>>(new Set());
