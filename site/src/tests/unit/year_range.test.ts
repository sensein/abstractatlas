/**
 * Spec 025 — NeuroScape atlas year range slider.
 *
 * Unit tests for the pure year-window math
 * (`$lib/filter/year_range`). See
 * specs/025-neuroscape-year-range-slider/contracts/year-range-helper.md
 * for the 9 required cases. These cover the SHARED helpers (Phase 2),
 * the US1 endpoint setters (setStart/setEnd incl. crossed handles), and
 * the US2 window mover (moveWindow, width-preserving + bound-clamped).
 *
 * All functions are total (never throw) and idempotent at the bounds;
 * full span maps back to {min_year:null, max_year:null} so the existing
 * `+page.svelte` filter treats it as inactive (FR-007).
 */
import { describe, expect, it } from 'vitest';
import {
	clampYear,
	resolveSpan,
	setStart,
	setEnd,
	moveWindow,
	isFullSpan,
	toFilter,
	fromFilter
} from '$lib/filter/year_range';

const BOUNDS = { lo: 1999, hi: 2023 };
const DEGEN = { lo: 2010, hi: 2010 };

describe('clampYear() — case 1', () => {
	it('clamps below lo, above hi, identity inside', () => {
		expect(clampYear(1990, BOUNDS)).toBe(1999);
		expect(clampYear(2050, BOUNDS)).toBe(2023);
		expect(clampYear(2010, BOUNDS)).toBe(2010);
	});
	it('degenerate lo === hi always returns lo', () => {
		expect(clampYear(1990, DEGEN)).toBe(2010);
		expect(clampYear(2050, DEGEN)).toBe(2010);
	});
});

describe('resolveSpan() — case 2', () => {
	it('orders swapped inputs so start <= end', () => {
		expect(resolveSpan(2020, 2005)).toEqual({ start: 2005, end: 2020 });
		expect(resolveSpan(2005, 2020)).toEqual({ start: 2005, end: 2020 });
		expect(resolveSpan(2010, 2010)).toEqual({ start: 2010, end: 2010 });
	});
});

describe('setStart() — case 3 (crossed handle)', () => {
	it('clamps the proposed start to bounds', () => {
		expect(setStart({ start: 2005, end: 2020 }, 1990, BOUNDS)).toEqual({ start: 1999, end: 2020 });
	});
	it('dragging start past end resolves to an ordered span', () => {
		expect(setStart({ start: 2005, end: 2010 }, 2018, BOUNDS)).toEqual({ start: 2010, end: 2018 });
	});
});

describe('setEnd() — case 4 (crossed handle)', () => {
	it('clamps the proposed end to bounds', () => {
		expect(setEnd({ start: 2005, end: 2020 }, 2050, BOUNDS)).toEqual({ start: 2005, end: 2023 });
	});
	it('dragging end below start resolves to an ordered span', () => {
		expect(setEnd({ start: 2010, end: 2015 }, 2003, BOUNDS)).toEqual({ start: 2003, end: 2010 });
	});
});

describe('moveWindow() — case 5 (within bounds, width preserved)', () => {
	it('shifts both ends by delta and preserves width', () => {
		const w = { start: 2010, end: 2015 };
		const moved = moveWindow(w, 3, BOUNDS);
		expect(moved).toEqual({ start: 2013, end: 2018 });
		expect(moved.end - moved.start).toBe(w.end - w.start);
	});
	it('shifts negatively within bounds', () => {
		expect(moveWindow({ start: 2010, end: 2015 }, -4, BOUNDS)).toEqual({ start: 2006, end: 2011 });
	});
});

describe('moveWindow() — case 6 (stops at bound, width preserved)', () => {
	it('stops at hi without shrinking when shifted past the top', () => {
		const w = { start: 2018, end: 2021 }; // width 3
		const moved = moveWindow(w, 10, BOUNDS);
		expect(moved).toEqual({ start: 2020, end: 2023 });
		expect(moved.end - moved.start).toBe(3);
	});
	it('stops at lo without shrinking when shifted past the bottom', () => {
		const w = { start: 2001, end: 2006 }; // width 5
		const moved = moveWindow(w, -20, BOUNDS);
		expect(moved).toEqual({ start: 1999, end: 2004 });
		expect(moved.end - moved.start).toBe(5);
	});
});

describe('isFullSpan() — case 7', () => {
	it('true when handles are at (or beyond) the bounds', () => {
		expect(isFullSpan({ start: 1999, end: 2023 }, BOUNDS)).toBe(true);
		expect(isFullSpan({ start: 1990, end: 2050 }, BOUNDS)).toBe(true);
	});
	it('false when narrowed on either side', () => {
		expect(isFullSpan({ start: 2005, end: 2023 }, BOUNDS)).toBe(false);
		expect(isFullSpan({ start: 1999, end: 2020 }, BOUNDS)).toBe(false);
	});
});

describe('toFilter() — case 8', () => {
	it('full span ⇒ null/null (inactive filter)', () => {
		expect(toFilter({ start: 1999, end: 2023 }, BOUNDS)).toEqual({
			min_year: null,
			max_year: null
		});
	});
	it('narrowed ⇒ concrete years', () => {
		expect(toFilter({ start: 2005, end: 2020 }, BOUNDS)).toEqual({
			min_year: 2005,
			max_year: 2020
		});
	});
	it('one-sided narrowing keeps the open side null', () => {
		expect(toFilter({ start: 2005, end: 2023 }, BOUNDS)).toEqual({
			min_year: 2005,
			max_year: null
		});
		expect(toFilter({ start: 1999, end: 2020 }, BOUNDS)).toEqual({
			min_year: null,
			max_year: 2020
		});
	});
	it('single-year window ⇒ equal non-null years', () => {
		expect(toFilter({ start: 2012, end: 2012 }, BOUNDS)).toEqual({
			min_year: 2012,
			max_year: 2012
		});
	});
});

describe('degenerate bounds (lo === hi) — case 9', () => {
	const w = { start: 2010, end: 2010 };
	it('every operation returns {lo, lo}', () => {
		expect(setStart(w, 2005, DEGEN)).toEqual({ start: 2010, end: 2010 });
		expect(setEnd(w, 2020, DEGEN)).toEqual({ start: 2010, end: 2010 });
		expect(moveWindow(w, 5, DEGEN)).toEqual({ start: 2010, end: 2010 });
	});
	it('toFilter ⇒ null/null', () => {
		expect(toFilter(w, DEGEN)).toEqual({ min_year: null, max_year: null });
	});
});

describe('fromFilter() — inverse seed', () => {
	it('null/null ⇒ full span at the bounds', () => {
		expect(fromFilter({ min_year: null, max_year: null }, BOUNDS)).toEqual({
			start: 1999,
			end: 2023
		});
	});
	it('concrete filter ⇒ the same window, clamped', () => {
		expect(fromFilter({ min_year: 2005, max_year: 2020 }, BOUNDS)).toEqual({
			start: 2005,
			end: 2020
		});
		expect(fromFilter({ min_year: 1990, max_year: 2050 }, BOUNDS)).toEqual({
			start: 1999,
			end: 2023
		});
	});
	it('round-trips with toFilter', () => {
		const w = { start: 2005, end: 2020 };
		expect(fromFilter(toFilter(w, BOUNDS), BOUNDS)).toEqual(w);
	});
});
