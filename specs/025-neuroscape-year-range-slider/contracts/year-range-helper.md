# Contract: `year_range.ts` pure helper

Module: `site/src/lib/filter/year_range.ts`. Pure, no DOM, no side effects.
Unit-tested by `site/src/tests/unit/year_range.test.ts` (run with
`vitest run`). These are the failing-first tests authored before the
component.

## Types

```ts
export interface YearBounds { lo: number; hi: number; }
export interface YearWindow { start: number; end: number; }
export interface YearFilter { min_year: number | null; max_year: number | null; }
```

## Functions

### `clampYear(year: number, bounds: YearBounds): number`
- Returns `year` clamped to `[lo, hi]`.
- `lo === hi` ⇒ always returns `lo`.

### `resolveSpan(a: number, b: number): YearWindow`
- Returns `{ start: Math.min(a, b), end: Math.max(a, b) }`.
- Guarantees `start <= end` regardless of input order (FR-009).

### `setStart(window, year, bounds): YearWindow`
- Clamp `year` to bounds, then `resolveSpan(clamped, window.end)`.

### `setEnd(window, year, bounds): YearWindow`
- Clamp `year` to bounds, then `resolveSpan(window.start, clamped)`.

### `moveWindow(window, deltaYears, bounds): YearWindow`
- Let `width = window.end - window.start`.
- Shift both ends by `deltaYears`, then clamp the shift so the window
  stays within `[lo, hi]` **without changing `width`** (the window stops
  at the bound, it does not shrink) — FR-004 / SC-002.
- If `width > (hi - lo)` (cannot happen given invariants) it degrades to
  full span.

### `isFullSpan(window, bounds): boolean`
- `window.start <= bounds.lo && window.end >= bounds.hi`.

### `toFilter(window, bounds): YearFilter`
- `min_year = window.start <= bounds.lo ? null : window.start`
- `max_year = window.end >= bounds.hi ? null : window.end`

### `fromFilter(filter, bounds): YearWindow`
- Inverse used to seed the slider from app state:
  `start = filter.min_year ?? bounds.lo`, `end = filter.max_year ?? bounds.hi`,
  then `resolveSpan` + clamp.

## Required unit tests (must fail before implementation)

1. `clampYear` clamps below `lo`, above `hi`, and is identity inside.
2. `resolveSpan` orders swapped inputs.
3. `setStart` past `end` swaps to keep `start <= end` (crossed handle).
4. `setEnd` below `start` swaps likewise.
5. `moveWindow` preserves width when shifted within bounds.
6. `moveWindow` preserves width and stops at `lo` / `hi` when shifted past a bound.
7. `isFullSpan` true at exact bounds and when handles exceed bounds; false when narrowed.
8. `toFilter` returns `null/null` at full span; concrete years when narrowed; single-year window (`start === end`) yields equal non-null years.
9. Degenerate `lo === hi`: all operations return `{lo, lo}` and `toFilter` ⇒ `null/null`.
