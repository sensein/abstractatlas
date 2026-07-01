/**
 * Spec 025 — NeuroScape atlas year range slider: pure window math.
 *
 * The NeuroScape "Years" facet filters by publication year. This module
 * holds ALL the arithmetic behind the dual-handle range slider so the
 * Svelte component (`YearRangeSlider.svelte`) only translates pointer /
 * keyboard events into calls here and renders the result. Keeping it pure
 * mirrors the existing `$lib/filter` (`normalize`) + `$lib/selection`
 * helpers and makes the behaviour unit-testable without a browser.
 *
 * Semantics (unchanged from the previous two-number-box control):
 *   - `bounds` (corpus min/max year) is the slider's fixed extent,
 *     discovered at runtime from the loaded backdrop — never hardcoded
 *     (Constitution VII / CA-007).
 *   - A window whose start sits at `lo` is "unbounded below" ⇒ min_year
 *     null; whose end sits at `hi` is "unbounded above" ⇒ max_year null.
 *     Both at the bounds ⇒ the year filter is inactive (FR-007).
 *
 * Every function is total (never throws) and idempotent at the bounds.
 * Contract: specs/025-neuroscape-year-range-slider/contracts/year-range-helper.md
 */

export interface YearBounds {
	lo: number;
	hi: number;
}

export interface YearWindow {
	start: number;
	end: number;
}

export interface YearFilter {
	min_year: number | null;
	max_year: number | null;
}

/** Clamp a year into `[lo, hi]`. Degenerate `lo === hi` ⇒ always `lo`. */
export function clampYear(year: number, bounds: YearBounds): number {
	if (year < bounds.lo) return bounds.lo;
	if (year > bounds.hi) return bounds.hi;
	return year;
}

/** Order two years into a window with `start <= end` (resolves crossed handles). */
export function resolveSpan(a: number, b: number): YearWindow {
	return a <= b ? { start: a, end: b } : { start: b, end: a };
}

/** Set the lower endpoint; clamp to bounds then re-order against the end. */
export function setStart(window: YearWindow, year: number, bounds: YearBounds): YearWindow {
	return resolveSpan(clampYear(year, bounds), window.end);
}

/** Set the upper endpoint; clamp to bounds then re-order against the start. */
export function setEnd(window: YearWindow, year: number, bounds: YearBounds): YearWindow {
	return resolveSpan(window.start, clampYear(year, bounds));
}

/**
 * Shift the whole window by `deltaYears`, preserving its width. If a
 * leading edge would pass a bound the shift is clamped so the window
 * stops at the bound rather than shrinking (FR-004 / SC-002).
 */
export function moveWindow(window: YearWindow, deltaYears: number, bounds: YearBounds): YearWindow {
	const width = window.end - window.start;
	// If the window is at least as wide as the bounds (invalid/stale state,
	// or a degenerate single-year corpus), there is nowhere to slide it —
	// collapse to the full span rather than clamp `start` below `lo`.
	if (width >= bounds.hi - bounds.lo) {
		return { start: bounds.lo, end: bounds.hi };
	}
	// Largest range the start may occupy while keeping the full width inside bounds.
	const minStart = bounds.lo;
	const maxStart = bounds.hi - width;
	let nextStart = window.start + deltaYears;
	if (nextStart < minStart) nextStart = minStart;
	if (nextStart > maxStart) nextStart = maxStart;
	return { start: nextStart, end: nextStart + width };
}

/** True when the window spans (or exceeds) the full bounds ⇒ filter inactive. */
export function isFullSpan(window: YearWindow, bounds: YearBounds): boolean {
	return window.start <= bounds.lo && window.end >= bounds.hi;
}

/** Map an internal window to the app-facing filter (full span ⇒ null/null). */
export function toFilter(window: YearWindow, bounds: YearBounds): YearFilter {
	return {
		min_year: window.start <= bounds.lo ? null : window.start,
		max_year: window.end >= bounds.hi ? null : window.end
	};
}

/** Inverse of {@link toFilter}: seed a window from the current filter state. */
export function fromFilter(filter: YearFilter, bounds: YearBounds): YearWindow {
	const start = clampYear(filter.min_year ?? bounds.lo, bounds);
	const end = clampYear(filter.max_year ?? bounds.hi, bounds);
	return resolveSpan(start, end);
}
