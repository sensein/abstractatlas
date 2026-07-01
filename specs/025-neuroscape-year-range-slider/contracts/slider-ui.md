# Contract: `YearRangeSlider.svelte` + facet integration

Component: `site/src/lib/components/YearRangeSlider.svelte`. Consumed by
`site/src/lib/components/NeuroscapeFacets.svelte` (neuroscape mode only).

## Props

| Prop | Type | Meaning |
|------|------|---------|
| `minYear` | `number \| null` | Current start filter (`null` ⇒ unbounded below) |
| `maxYear` | `number \| null` | Current end filter (`null` ⇒ unbounded above) |
| `bounds` | `{ lo: number; hi: number }` | Slider extent (corpus year bounds) |

The component derives its internal `YearWindow` via `fromFilter(minYear,
maxYear, bounds)` so the parent stays the single source of truth.

## Events

```ts
dispatch('change', { min_year: number | null; max_year: number | null })
```

Fired on handle-drag, band-drag, and keyboard adjustment. Payload is
produced by `toFilter(window, bounds)` — full span ⇒ `null/null`.

## Facet wiring (NeuroscapeFacets.svelte)

- Replaces the `.year-row` two-`<input type=number>` block (current
  `:126–151`).
- On the slider's `change`, the facet re-emits its existing `update`
  payload `{ cluster_ids: selectedClusterIds, min_year, max_year }` — the
  `+page.svelte` handler is **unchanged**.
- The `activeCount` / "Clear" logic in the facet is unchanged: it already
  treats `minYear > lo` / `maxYear < hi` as the active condition, and
  "Clear" already emits `min_year: null, max_year: null` which the slider
  renders as full span.

## Behavior contract (verified by e2e `neuroscape_year_slider.spec.ts`)

| ID | Behavior |
|----|----------|
| U1 | Renders two handles at `lo`/`hi` and a numeric `start–end` readout on first open; no year filter active. |
| U2 | Dragging the start handle right raises `min_year`; results exclude earlier articles; readout updates (FR-003, US1). |
| U3 | Dragging the end handle left lowers `max_year`; results exclude later articles (FR-003, US1). |
| U4 | Dragging the band between handles shifts both ends by the same amount, width preserved; stops at a bound without shrinking (FR-004, US2). |
| U5 | "Clear" resets both handles to `lo`/`hi`; year filter inactive; badge no longer counts it (FR-007/FR-008). |
| U6 | Readout always matches handle positions and applied filter (SC-004). |

## Accessibility / input contract

- Each handle is `role="slider"` with `aria-valuemin={lo}`,
  `aria-valuemax={hi}`, `aria-valuenow`, `aria-label` ("Start year" /
  "End year"), and is keyboard-focusable.
- Arrow keys ±1 year, Home/End jump to bound (FR-010).
- Pointer Events (`pointerdown`/`move`/`up` + `setPointerCapture`) drive
  both mouse and touch on one path (FR-011).
- Crossed handles resolve to an ordered span via the helper (FR-009).

## Test data attributes (for e2e selectors)

- `data-testid="neuroscape-year-slider"` — container.
- `data-testid="neuroscape-year-handle-start"` / `-handle-end` — thumbs.
- `data-testid="neuroscape-year-band"` — draggable fill.
- `data-testid="neuroscape-year-readout"` — `start–end` text.

## Out of scope (unchanged)

- `+page.svelte` filter math and `update` handler.
- atlas-root and `/ohbm2026/` surfaces (no year facet) — FR-012.
- Data package / parquet / provenance — byte-identical.
