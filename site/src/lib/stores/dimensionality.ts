/**
 * Stage 15 (spec 015-neuroscape-context, FR-012 + T056-prep): the
 * 2D ↔ 3D control on the bare-root atlas landing page (and on the
 * /neuroscape/ subsite home).
 *
 * Mirrors the `atlas_overlay` + `showMap` patterns —
 * localStorage-backed writable string ('2d' | '3d'), default '3d',
 * malformed inputs fall back to '3d' (Principle VI).
 */

import { writable } from 'svelte/store';

export type Dimensionality = '2d' | '3d';

const STORAGE_KEY = 'atlas.dimensionality';

function loadDimensionality(): Dimensionality {
	if (typeof window === 'undefined' || typeof window.localStorage === 'undefined') return '3d';
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY);
		if (raw === '2d' || raw === '3d') return raw;
		return '3d';
	} catch {
		return '3d';
	}
}

const _dimensionality = writable<Dimensionality>(loadDimensionality());
_dimensionality.subscribe((v) => {
	if (typeof window === 'undefined' || typeof window.localStorage === 'undefined') return;
	try {
		window.localStorage.setItem(STORAGE_KEY, v);
	} catch {
		/* private mode / quota — best effort */
	}
});

export const dimensionality = _dimensionality;

export function toggleDimensionality(): void {
	_dimensionality.update((v) => (v === '3d' ? '2d' : '3d'));
}
