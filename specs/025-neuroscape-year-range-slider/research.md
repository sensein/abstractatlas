# Phase 0 Research: NeuroScape Atlas Year Range Slider

All Technical Context unknowns were resolvable from the existing codebase
and standard web-platform practice; none remain marked NEEDS CLARIFICATION.

## R1 — Dual-handle slider with a draggable band: build vs. depend

**Decision**: Build a self-contained `YearRangeSlider.svelte` from native
DOM + pointer/keyboard handlers. No new npm dependency.

**Rationale**:
- The repo already ships exactly one slider (`BackdropDensitySlider.svelte`)
  as a thin wrapper over a native `<input type="range">` — there is a
  precedent for hand-rolled, dependency-free slider UI.
- A *single* native range input cannot express two thumbs. The common
  "two overlaid native range inputs" trick gives two thumbs cheaply and
  with free keyboard support, **but it cannot express a draggable band**
  (FR-004 "move the whole window") — dragging the colored fill between the
  thumbs is not something native range inputs do. Since band-drag is a
  first-class requirement, a pure-overlay approach is insufficient on its
  own.
- A pointer-event-driven custom track (a `<div>` track with two
  `role="slider"` thumb buttons and a draggable fill element) handles all
  three gestures — set-start, set-end, move-band — and lets us add
  `role="slider"` + `aria-valuemin/max/now/text` for keyboard/AT support
  (FR-010). Pointer Events (`pointerdown`/`pointermove`/`pointerup` +
  `setPointerCapture`) cover mouse and touch with one code path (FR-011),
  which also keeps this consistent with the Stage-24 WebKit/iOS focus.
- A dependency (e.g. a range-slider library) would add bundle weight and a
  maintenance surface for a ~one-screen control; the in-house version is
  small and fully under test.

**Alternatives considered**:
- *Two overlaid native range inputs* — simplest for endpoints + free a11y,
  rejected as the sole mechanism because it cannot do band-drag. (We may
  still keep native inputs as the *keyboard* affordance for the two thumbs;
  see R3.)
- *3rd-party range-slider component* — rejected: new dependency for a
  small control, and we want full control of the band-drag + a11y wiring.

## R2 — Pure math vs. component logic split

**Decision**: Put all window arithmetic in a pure module
`site/src/lib/filter/year_range.ts`; the component only translates
pointer/keyboard events into calls on that module and renders the result.

**Rationale**: The behavior that matters (clamping to bounds, preserving
window width on a move, resolving crossed handles into an ordered span,
treating full-span as "inactive") is exactly the part that needs
`vitest run` coverage and is painful to test through the DOM. Keeping it
pure mirrors the existing `$lib/filter` (`normalize`) and `$lib/selection`
(`compose`, `cart_scope`) pattern of pure helpers + thin components, and
satisfies the Constitution's verification-first gate cleanly.

**Functions** (see contracts/year-range-helper.md):
`clampYear`, `setStart`, `setEnd`, `moveWindow`, `resolveSpan`,
`isFullSpan`, and a `toFilter` mapper that converts an internal `(start,
end)` window into the `(min_year, max_year)` the rest of the app expects
(full span ⇒ `null`/`null`).

## R3 — State semantics & wiring (reuse, don't reshape)

**Decision**: Keep the exact existing state contract. `+page.svelte` owns
`filterMinYear: number | null`, `filterMaxYear: number | null`, and the
derived `yearBounds: { lo, hi }` (min/max year over the loaded backdrop).
`NeuroscapeFacets.svelte` keeps emitting `update` with
`{ cluster_ids, min_year, max_year }`. The slider lives *inside*
`NeuroscapeFacets` and is fed `minYear`, `maxYear`, `yearBounds`; on change
it emits the same payload the number boxes did.

**Rationale**: This is the smallest correct change and guarantees no
behavioral regression in filtering (SC-003): the downstream filter at
`+page.svelte:661,798,818,1385` (`yLo = filterMinYear ?? yearBounds.lo`,
`yHi = filterMaxYear ?? yearBounds.hi`) is untouched. `null` continues to
mean "unbounded on that side"; the slider maps full-span handle positions
back to `null`/`null` so the active-filter badge (`activeCount`, which
already tests `minYear > lo` / `maxYear < hi`) keeps working unchanged
(FR-007, SC-006).

**Keyboard model**: Each thumb is a `role="slider"` element; ArrowLeft/Down
decrements, ArrowRight/Up increments, Home/End jump to the bound, by one
year per step (FR-010). Band-move is primarily a pointer/touch gesture
(FR-004/FR-011); a keyboard equivalent for moving the whole window is
**optional** (PgUp/PgDn could shift the window) and is not required to
satisfy the spec — recorded here so the implementer knows it is a nice-to-
have, not a gap.

## R4 — Degenerate & edge inputs

**Decision**: Handle these in the pure helper so the component cannot
throw:
- `yearBounds.lo === yearBounds.hi` (single-year corpus, or pre-load `0/0`):
  the slider renders a single fixed position; any "move"/"set" is a no-op
  that resolves to that one year (Edge: degenerate bounds).
- Crossed handles: `resolveSpan` always returns `start <= end` by swapping
  if needed (FR-009, Edge: crossed handles).
- Single-year selection (`start === end`) is valid and filterable (Edge).
- Pre-load `yearBounds = {0,0}`: the Years facet already only renders
  meaningfully once `atlasBackdrop.length > 0`; the slider must no-op
  safely at `0/0` and not emit a spurious filter.

**Rationale**: Pushing every boundary into the pure, tested helper keeps
the gesture component dumb and keeps the "fail loudly but never crash on
valid-if-unusual data" Constitution posture.

## R5 — Visual & layout fit

**Decision**: Reuse the existing Years `<section class="facet">` shell and
OHBM facet visual tokens (`--border`, `--bg-elevated`, `--accent`,
`--text-faint`, `tabular-nums`). The slider replaces the `.year-row`
two-input block; the numeric span readout (`start–end`) sits where the
inputs were, styled like the existing `.facet-count`. On the mobile layout
the facet sidebar opens via the existing "🔍 Filters" toggle — no new
responsive plumbing needed.

**Rationale**: Keeps the change visually consistent with the sibling
facets and avoids touching shared layout. Matches the spec's "OHBM `.opt`
rail visual" note.
