# Contract: `year_density.ts` pure sampler

Module: `site/src/lib/atlas/year_density.ts`. Pure, no DOM, no side effects.
Unit-tested by `site/src/tests/unit/year_density.test.ts` (`vitest run`).
Authored failing-first before the `+page.svelte` wiring.

## Types

```ts
export interface DensityPoint {
	pubmed_id: number;
	year: number;
	lod_level?: number;
}
export interface DensityCalibration {
	targetBudget: number; // ≈ full-span base-sample size
	k: number;            // dots per √article = targetBudget / Σ_all √count_y
}
```

## Functions

### `calibrate(fullCorpus, targetBudget): DensityCalibration`
- `k = targetBudget / Σ_{y} √(count_y)` where `count_y` counts `fullCorpus`
  points per `year`. Computed once per corpus load (caller memoizes).
- `Σ√count_y == 0` (empty corpus) ⇒ `k = 0`.

### `yearQuota(countY, k): number`
- Returns `round(k · √countY)`, `≥ 0`. (Caller clamps to `countY`.)

### `yearAwareSample(points, calib): DensityPoint[]`
- `points` = the already-filtered in-window set.
- Bucket by `year`; for each year `y`: take the `min(count_y, round(k·√count_y))`
  points with smallest `lod_level`, tiebreak ascending `pubmed_id`.
- Points with `lod_level === undefined` (legacy build): order by a
  deterministic stride/`pubmed_id` so selection is still reproducible.
- Return the union (order unspecified; caller renders as a set).

## Required unit tests (must fail before implementation)

1. **√ compression**: a year with 100× the count of another gets ~10× the
   quota (not 100×).
2. **Monotonic**: `year A count ≥ year B count ⇒ quota_A ≥ quota_B` (SC-002).
3. **Budget bound**: over the full corpus, `Σ quota_y ≈ targetBudget`
   (within rounding); never exceeds `Σ count_y`.
4. **Within-year blue-noise**: selected points of a year are exactly its
   lowest-`lod_level` points (tiebreak `pubmed_id`), not a raw prefix.
5. **Sparse year**: `count_y ≤ quota_y` ⇒ all points of that year returned
   (no fabrication/duplication).
6. **Single-year window**: one year present ⇒ a bounded spatial cover of it.
7. **Empty input** ⇒ `[]` (no throw).
8. **Legacy (no `lod_level`)**: deterministic, reproducible selection.
9. **Determinism**: same input ⇒ same output (stable ordering).
