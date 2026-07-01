# Phase 1 Data Model: Year-Aware Backdrop Density

No persisted data and no new corpus fields. The "model" is the in-memory
value objects the pure sampler operates on — all already resident on
`/neuroscape/`.

## Value objects

### BackdropPoint (input, existing shape)
Each loaded NeuroScape backdrop point already carries:

| Field | Type | Notes |
|-------|------|-------|
| `pubmed_id` | `number` | identity + deterministic tiebreak |
| `cluster_id` | `number` | (used by upstream cluster filter, not by the sampler) |
| `year` | `number` | publication year — the bucketing key |
| `lod_level` | `number \| undefined` | quadtree blue-noise spatial rank (lower = coarser/more representative); `undefined` on legacy builds |
| `umap_2d` | `[number, number]` | render coords (passed through) |

The sampler receives the already year+cluster-filtered `scatterBackdrop`.

### YearWindow
| Field | Type | Notes |
|-------|------|-------|
| `lo` | `number` | inclusive start year of the active filter |
| `hi` | `number` | inclusive end year |

"Active" ⇔ `filterMinYear != null || filterMaxYear != null` (not full span).

### DensityCalibration (computed once per corpus load, memoized)
| Field | Type | Notes |
|-------|------|-------|
| `targetBudget` | `number` | ≈ size of today's full-span base sample (count of corpus points with `lod_level ≤ neuroscapeLodCap`) |
| `k` | `number` | dots-per-√article = `targetBudget / Σ_{all years} √(count_y)` over the full corpus |

## Derived quantities (per render, over the filtered set)

| Quantity | Definition |
|----------|------------|
| `count_y` | number of filtered points with `year == y` |
| `quota_y` | `min(count_y, round(k · √count_y))` |
| per-year selection | the `quota_y` points of year `y` with smallest `lod_level` (tiebreak `pubmed_id`) |
| base sample | union of per-year selections across all years in the window |

Invariants:
- `0 ≤ quota_y ≤ count_y` (never fabricates/duplicates points; sparse year ⇒ all shown).
- Total rendered `= Σ_y quota_y ≤ Σ_y count_y` (bounded; ≈ `k·Σ√count_y`).
- `quota_y` is monotonic non-decreasing in `count_y` (SC-002).
- Empty window ⇒ empty sample (no throw).
- Full span ⇒ sampler not invoked; today's `lod_level ≤ cap` path used verbatim (SC-003).

## Relationship to existing state (unchanged plumbing)

```
+page.svelte
  scatterBackdrop            (year+cluster-filtered full set — UNCHANGED)
  filterMinYear/MaxYear      (null ⇒ full span)
  neuroscapeLodCap, DensityCalibration (from corpus/manifest at load)
        │
        ▼
  scatterBackdropForMap  ── full span ─▶ scatterBackdrop.filter(lod_level ≤ cap)   [UNCHANGED]
        │
        └── year filter active ─▶ yearAwareSample(scatterBackdrop, {lo,hi}, calib)  [NEW]
        ▼
  <UmapPanel backdropPoints={scatterBackdropForMap} …>   (UNCHANGED component)
```

The result list, facet counts, `backdropFull` (viewport detail), overlay,
and all other derivations are untouched — only the base-map sample changes,
and only while a year filter is active.
