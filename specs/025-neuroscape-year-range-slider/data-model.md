# Phase 1 Data Model: NeuroScape Atlas Year Range Slider

This feature introduces no persisted data and no new corpus fields. The
"model" here is the in-memory UI state and the value objects the pure
helper operates on.

## Value objects

### YearBounds
The fixed selectable extent, discovered at runtime from the loaded
backdrop (NOT hardcoded).

| Field | Type | Notes |
|-------|------|-------|
| `lo` | `number` | Minimum publication year in the loaded corpus (`0` before load) |
| `hi` | `number` | Maximum publication year in the loaded corpus (`0` before load) |

Invariants: `lo <= hi`. The degenerate `lo === hi` case (incl. pre-load
`{0,0}`) is valid and renders a single fixed position.

Source: derived in `+page.svelte` (`yearBounds`) — **unchanged** by this
feature.

### YearWindow (internal slider state)
The concrete start/end the slider renders. Always materialized within
bounds.

| Field | Type | Notes |
|-------|------|-------|
| `start` | `number` | Lower endpoint, `lo <= start <= end` |
| `end` | `number` | Upper endpoint, `start <= end <= hi` |

Invariants: `lo <= start <= end <= hi` after every operation
(`resolveSpan` guarantees ordering; `clampYear` guarantees bounds).

### YearFilter (app-facing state)
The shape the rest of the app already consumes — **unchanged**.

| Field | Type | Notes |
|-------|------|-------|
| `min_year` | `number \| null` | `null` ⇒ unbounded below (full-span start) |
| `max_year` | `number \| null` | `null` ⇒ unbounded above (full-span end) |

Mapping (`toFilter`): a `YearWindow` whose `start === lo` ⇒ `min_year =
null`; whose `end === hi` ⇒ `max_year = null`. When both, the year filter
is **inactive** (FR-007). Otherwise the concrete year is emitted.

## State transitions (pure helper)

Given `bounds: YearBounds` and a current `window: YearWindow`:

| Operation | Input | Result | Rule |
|-----------|-------|--------|------|
| `setStart(window, year, bounds)` | proposed start year | new window | clamp `year` to `[lo, hi]`; if it exceeds `end`, resolve via `resolveSpan` (start/end swap so `start <= end`) |
| `setEnd(window, year, bounds)` | proposed end year | new window | clamp `year` to `[lo, hi]`; if below `start`, resolve via `resolveSpan` |
| `moveWindow(window, deltaYears, bounds)` | signed year delta | new window | shift both ends by `delta`; if a leading edge would pass a bound, clamp the shift so the **width is preserved** and the window stops at the bound (FR-004, SC-002) |
| `resolveSpan(a, b)` | two years | ordered `{start,end}` | `{ start: min(a,b), end: max(a,b) }` (FR-009) |
| `isFullSpan(window, bounds)` | — | `boolean` | `start <= lo && end >= hi` (drives inactive state, FR-007) |
| `toFilter(window, bounds)` | — | `YearFilter` | per mapping above |

All operations are total (never throw) and idempotent at the bounds.
Degenerate `lo === hi`: every operation returns `{ start: lo, end: lo }`.

## Relationship to existing state

```
+page.svelte
  filterMinYear / filterMaxYear  ──┐ (YearFilter, unchanged)
  yearBounds {lo,hi}  ─────────────┤
                                    ▼
        <NeuroscapeFacets minYear maxYear yearBounds>
                                    ▼
            <YearRangeSlider>  (derives YearWindow from minYear/maxYear/bounds
                                via the inverse of toFilter; emits YearFilter on change)
                                    │ update {min_year,max_year}
                                    ▼
        NeuroscapeFacets dispatches update {cluster_ids,min_year,max_year}
                                    ▼
        +page.svelte sets filterMinYear/filterMaxYear  (UNCHANGED handler)
```

No change to the corpus, the parquet schema, the manifest, or any
provenance artifact.
