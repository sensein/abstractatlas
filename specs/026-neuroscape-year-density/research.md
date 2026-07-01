# Phase 0 Research: Year-Aware Backdrop Density

All Technical Context items were resolvable from the codebase + the
brainstorming decisions; nothing remains NEEDS CLARIFICATION.

## R1 — Density model: compressed-proportional via a fixed dots-per-√article constant

**Decision**: For each year `y` in the active (filtered) window with count
`c_y`, render `quota_y = min(c_y, round(K · √c_y))` dots, where `K` is a
single **dots-per-√article** constant calibrated once from the loaded
corpus. Total rendered ≈ `K · Σ_y √c_y`.

**Rationale**:
- √ compresses the 1999→2023 volume ratio: a year with 100× more articles
  contributes only 10× more dots, so a fixed-width window's dot count is
  far more stable as it slides (SC-001, target ≤~2× swing) while remaining
  monotonic in true volume (SC-002 — not flattened).
- A **fixed `K`** (not a per-window renormalized budget) means no global
  re-normalization each frame and makes the total scale naturally with
  window width ("wider windows show proportionally more"). `K` is computed
  once: `K = TARGET_BUDGET / Σ_{all years} √(count_y)` over the full
  corpus, so the notional full-corpus total equals `TARGET_BUDGET`.
- `TARGET_BUDGET` is set to the size of today's full-span base sample (the
  count of corpus points with `lod_level ≤ neuroscapeLodCap`, ≈ the
  representative-tier size ~56k), so windowed on-screen density is
  comparable to the unchanged full-span view (FR-003, SC-003).

**Alternatives considered**:
- *Equal quota per year* (flat): rejected — flattens real volume, which the
  user explicitly did not want (they chose compressed).
- *Raw proportional (∝ c_y)*: this is effectively today's behaviour — the
  order-of-magnitude swing being fixed.
- *Per-window renormalized fixed total*: rejected — makes a 1-year and a
  20-year window identical in total dot count, less intuitive than width-
  scaling, and needs a per-frame Σ pass anyway.

## R2 — Within-year selection: reuse `lod_level` (no new data)

**Decision**: Within year `y`, take the `quota_y` points with the smallest
`lod_level` (ties broken deterministically, e.g. by `pubmed_id`).

**Rationale**: `lod_level` is the existing per-point quadtree blue-noise
rank (coarsest first = spatially uniform cover). Taking the lowest ranks of
a year's points yields a shape-preserving spatial cover *of that year*
(FR-002) for free — no new precomputed data, honouring the client-side /
byte-identical constraint (FR-009). Older builds without `lod_level` fall
back to a deterministic stride so the feature degrades gracefully.

## R3 — Seam + activation

**Decision**: Implement inside `scatterBackdropForMap` (`+page.svelte:840`).
Today it returns `scatterBackdrop.filter(lod_level ≤ cap)`. New logic:
- If **not** neuroscape, or `neuroscapeLodCap === null` (old build), or the
  year filter is inactive (`filterMinYear == null && filterMaxYear == null`,
  i.e. full span) → **unchanged** path (FR-004).
- Else → `yearAwareSample(scatterBackdrop, { lo, hi }, budget)`.

`scatterBackdrop` is already year+cluster filtered, so the sampler sees
exactly the in-window (and in-cluster) set; per-year counts reflect the
filtered set, so cluster+year compose correctly (spec edge case).

**Rationale**: single, minimal seam; `UmapPanel` and the result-list/counts
paths are untouched (FR-006). `backdropFull` (viewport rest-tier detail,
`:643`) is already year+cluster filtered, so zoomed detail already respects
the window (FR-008) — no change needed there; the year-density feature
deliberately governs only the zoomed-out **base** sample.

## R4 — Performance

**Decision**: One pass to bucket the filtered points by year; per year, a
partial selection of the `quota_y` smallest `lod_level` points. Precompute
per-point `lod_level` is already resident. `K` and `TARGET_BUDGET` are
computed once per corpus load (memoized), not per drag.

**Rationale**: bucket + per-year `quota_y`-select is O(n) over the filtered
set (≤461k) with small constants; comparable to today's `lod_level ≤ cap`
filter which is already O(n). Slider drag already recomputes `scatterBackdrop`
(an O(n) filter) each commit, so adding an O(n) sample keeps the same order
(FR-010/SC-005). If profiling shows a hotspot, a per-year pre-sorted index
by `lod_level` can be built once at load — noted, not required up-front.

## R5 — Full-span identity + scope guards

**Decision**: The feature is a no-op unless a year filter is active; the
full-span path returns byte-for-byte today's result (FR-004/SC-003).
atlas-root never enters this branch (guarded by `SITE_MODE === 'neuroscape'`)
and has no year facet; `/ohbm2026/` uses a different backdrop path entirely
(FR-007/SC-006).

**Rationale**: strictly additive and reversible; zero risk to the default
landing view and the sibling surfaces.
