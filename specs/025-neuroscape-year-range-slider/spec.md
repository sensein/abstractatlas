# Feature Specification: NeuroScape Atlas Year Range Slider

**Feature Branch**: `025-neuroscape-year-range-slider`  
**Created**: 2026-06-29  
**Status**: Draft  
**Input**: User description: "change range ui for neuroscape atlas to use a slider ui that allows setting slider end points (range) and move the slider given a range."

## User Scenarios & Testing *(mandatory)*

The NeuroScape atlas (`/neuroscape/`) filters its ~461k-article PubMed
corpus by publication year. Today the "Years" facet exposes two free-text
number boxes ("From" / "To"). A visitor must read the corpus bounds, type
a start year, then type an end year, and there is no visual sense of where
the chosen window sits inside the full 1999–2023 span. This feature
replaces those two boxes with a **dual-handle range slider** so the same
filter can be set and adjusted by direct manipulation.

### User Story 1 - Set both ends of the year window with a slider (Priority: P1)

A visitor browsing the NeuroScape atlas wants to narrow results to a span
of years (e.g. 2015–2020). Instead of typing two numbers, they drag the
two handles of a single slider track to the desired start and end years.
The slider is bounded by the corpus' minimum and maximum publication year,
and the currently-selected span is shown numerically next to the track.

**Why this priority**: This is the core of the request — it is the
replacement for the existing two-box control and delivers the primary
value (faster, lower-friction year filtering) on its own. Shipping only
this story already produces a usable, viable filter.

**Independent Test**: Load the NeuroScape atlas, open the "Years" facet,
drag the lower handle to a later year and the upper handle to an earlier
year, and confirm the article list / scatter narrows to articles within
the selected span and the displayed span text matches the handle
positions.

**Acceptance Scenarios**:

1. **Given** the NeuroScape atlas is loaded with the full corpus, **When** the visitor opens the "Years" facet, **Then** a range slider is shown with both handles at the corpus minimum and maximum year and the results are unfiltered by year.
2. **Given** the year slider is at full span, **When** the visitor drags the lower (start) handle to a later year, **Then** the results update to exclude articles published before the new start year and the displayed span updates to the new start year.
3. **Given** the year slider is at full span, **When** the visitor drags the upper (end) handle to an earlier year, **Then** the results update to exclude articles published after the new end year and the displayed span updates to the new end year.
4. **Given** both handles have been moved inward, **When** the visitor uses "Clear" (the facet clear action), **Then** both handles return to the corpus minimum and maximum and the year filter is removed.

---

### User Story 2 - Move the whole selected window along the range (Priority: P2)

Having selected a span of years (e.g. a 5-year window 2010–2015), the
visitor wants to slide that same-width window earlier or later (e.g. to
2012–2017) without re-setting each end. They grab the selected band
between the two handles and drag it; the window keeps its width and shifts
along the track, clamped at the corpus bounds.

**Why this priority**: This is the second half of the request ("move the
slider given a range"). It is a meaningful convenience on top of P1 but
the filter is already usable without it, so it is independently testable
and deferrable.

**Independent Test**: Set a fixed-width year window, then drag the band
between the handles and confirm the window width is preserved while both
the start and end years shift together, and that dragging past a corpus
bound stops the window at that bound (width preserved).

**Acceptance Scenarios**:

1. **Given** a year window narrower than the full span is selected, **When** the visitor drags the band between the two handles toward later years, **Then** both the start and end years increase by the same amount and the window width is unchanged.
2. **Given** a year window is being dragged toward a corpus bound, **When** the leading edge reaches the corpus minimum or maximum, **Then** the window stops at that bound and retains its width rather than shrinking.

---

### Edge Cases

- **Crossed handles**: If the visitor drags the start handle past the end handle (or vice versa), the selection MUST resolve to a valid ordered span (start ≤ end) rather than an inverted or empty range.
- **Zero-width / single-year window**: The visitor MUST be able to select a single year (start year == end year); the displayed span and the filtered results MUST reflect that single year.
- **Full span == no filter**: When both handles sit at the corpus bounds, the year filter MUST be treated as inactive (it does not count toward the active-filter badge and does not exclude any articles).
- **Keyboard / non-pointer use**: The control MUST be operable without a pointer (e.g. focus a handle and adjust it with arrow keys), since dual-handle sliders are otherwise inaccessible.
- **Degenerate corpus bounds**: If the corpus min and max year are equal (single-year corpus), the slider MUST render without error and behave as a fixed single-year selection.
- **Touch / mobile**: Handles and the draggable band MUST be operable by touch on the mobile layout where the facet sidebar opens via the "🔍 Filters" toggle.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The NeuroScape atlas "Years" facet MUST present a dual-handle range slider as its primary year-filter control, replacing the two free-text number inputs.
- **FR-002**: The slider's selectable extent MUST be bounded by the corpus' minimum and maximum publication year (discovered from the loaded corpus, not hardcoded).
- **FR-003**: Visitors MUST be able to independently set the start (lower) endpoint and end (upper) endpoint by dragging the corresponding handle.
- **FR-004**: Visitors MUST be able to move the entire selected window — preserving its width — by dragging the band between the two handles, clamped to the corpus bounds. This window-move is a pointer/touch gesture; keyboard users still reach any window by adjusting the two endpoint handles (a dedicated keyboard "move whole window" shortcut is optional, not required).
- **FR-005**: The control MUST display the currently-selected year span numerically (start–end) adjacent to the slider.
- **FR-006**: Adjusting the slider MUST drive the same downstream year filter the previous control drove (start year and end year applied to the article list, scatter, and facet counts) with no change to filtering semantics other than the input mechanism.
- **FR-007**: When both handles sit at the corpus bounds, the year filter MUST be inactive (no articles excluded, not counted in the active-filter total).
- **FR-008**: The facet's "Clear" action MUST reset both handles to the corpus bounds and remove the year filter.
- **FR-009**: The control MUST keep the start endpoint ≤ the end endpoint at all times, resolving any attempt to cross the handles into a valid ordered span.
- **FR-010**: The control MUST be keyboard-operable (each handle focusable and adjustable via keyboard) and expose accessible labels/values for assistive technology.
- **FR-011**: The control MUST be operable via touch on the mobile facet layout.
- **FR-012**: The change MUST be confined to the NeuroScape atlas mode; the atlas-root and `/ohbm2026/` surfaces (which expose no year facet) MUST be unaffected.

### Key Entities *(include if feature involves data)*

- **Year window**: The visitor-selected filter state — a start year and an end year, each within the corpus bounds; "full span" denotes the inactive state.
- **Corpus year bounds**: The minimum and maximum publication year present in the loaded NeuroScape corpus, used as the slider's fixed extent.

### Constitution Alignment *(mandatory)*

- **CA-001**: No Python execution is introduced by this feature; it is a client-side UI change in the SvelteKit site under `site/`. The repository's `.venv`-only rule is unaffected.
- **CA-002**: Behavior-changing stories are covered by failing-first tests before implementation: unit tests for the year-window state logic (endpoint setting, window-move clamping, crossed-handle resolution, full-span-as-inactive) run via `vitest run`, and a Playwright check exercises the slider in the NeuroScape build (set endpoints, drag the band, verify the filtered result count and displayed span).
- **CA-003**: No canonical defaults, inputs, or outputs change. The only doc surfaces to update in the same change are the in-file component documentation comment in the facet component and any quickstart/notes added under this spec directory; no README/CLAUDE.md default changes are expected.
- **CA-004**: No credentials or secrets are involved.
- **CA-005**: No new dataset, cache, export, or downloaded asset is produced; no generated data is tracked.
- **CA-006**: Error paths are explicit at the UI level: invalid/crossed handle states resolve to a valid ordered span rather than silently producing an empty or inverted filter; degenerate corpus bounds render without throwing. No verification gate is bypassed.
- **CA-007**: The slider extent is discovered at runtime from the loaded corpus' year bounds (the existing `yearBounds` derivation), never matched against a hardcoded 1999–2023 list; a corpus whose bounds differ MUST drive the slider extent accordingly.
- **CA-008**: This feature produces no organizer-facing or downstream-consumer artifact and re-publishes no data package; the byte-identical data-package guarantee is preserved. No new provenance file is required.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A visitor can set a bounded year window (both ends) using only the slider, without typing, in a single drag gesture per handle.
- **SC-002**: A visitor can shift a fixed-width year window to an adjacent span by a single band-drag gesture, with the window width preserved to the exact same number of years before and after the drag.
- **SC-003**: The year filter produces the same result set for a given (start, end) window as the previous two-box control did for the same start/end values (no behavioral regression in filtering).
- **SC-004**: The displayed numeric span always matches the handle positions and the applied filter (no drift between what is shown and what is filtered) across all acceptance scenarios.
- **SC-005**: The slider is fully operable by keyboard and by touch, verified on the desktop and mobile facet layouts.
- **SC-006**: When both handles are at the corpus bounds, the active-filter badge does not count the year filter and no articles are excluded by year.

## Assumptions

- The change is scoped to the NeuroScape atlas mode only; the atlas-root and `/ohbm2026/` surfaces have no year facet and are out of scope.
- The slider operates at whole-year granularity (one year per step), matching the corpus' year-level data and the existing filter semantics.
- The slider fully replaces the two `From`/`To` number inputs — typed numeric entry is NOT retained (the slider alone satisfies the request). A numeric `start–end` span readout is kept for legibility. If a future need for precise keyboard year entry arises, it would be added as a follow-up, not in this change.
- The downstream filter plumbing (`filterMinYear` / `filterMaxYear` against `yearBounds`, with `null`/full-span meaning "inactive") is reused unchanged; only the input control is replaced.
- This is a client-side-only change requiring no corpus or pipeline rerun and no data-package re-publish.
