# Feature Specification: NeuroScape Atlas Year-Aware Backdrop Density

**Feature Branch**: `026-neuroscape-year-density`  
**Created**: 2026-07-01  
**Status**: Draft  
**Input**: User description: "year-aware backdrop density for the NeuroScape atlas — when a year filter is active, sample the scatter backdrop so each year contributes dots proportional to sqrt(count-in-window), reusing lod_level for within-year blue-noise; client-side only, no data rebuild."

## User Scenarios & Testing *(mandatory)*

The NeuroScape atlas (`/neuroscape/`) shows a scatter "backdrop" of the
~461k-article PubMed corpus, colour-coded by cluster. Visitors narrow it
by publication year with the year range slider. Because publication volume
grows steeply from 1999→2023, and the rendered backdrop is a *spatial*
sample, a narrow year window shows wildly non-uniform dot density: sliding
a fixed-width window from the early years (sparse) to recent years (dense)
makes the map look almost empty then suddenly crowded, which obscures the
spatial structure the visitor is trying to read within their chosen window.

This feature makes the backdrop's rendered density *year-aware* while a
year filter is active, so the visible dots are distributed more evenly
across the window's years — tempering (not erasing) the real growth in
volume — so a visitor sliding a fixed-width window sees a legible,
comparable map at every position.

### User Story 1 - Legible, comparable density while sliding a year window (Priority: P1)

A visitor narrows the year slider to a span (e.g. 3 years) and slides it
across the timeline. At every position the backdrop shows a legible dot
density that reflects the spatial shape of that window's articles, without
the early-years window looking near-empty or the recent-years window
looking saturated.

**Why this priority**: This is the entire feature and the fix for the
reported problem. It stands alone and delivers the value.

**Independent Test**: On `/neuroscape/`, select a fixed-width year window,
read the on-screen backdrop density, slide the window across several eras,
and confirm the visible dot count stays within a bounded band (not the
order-of-magnitude swing seen today) while each window still shows a
recognizable spatial cover.

**Acceptance Scenarios**:

1. **Given** the NeuroScape backdrop is loaded and no year filter is active, **When** the visitor views the default landing scatter, **Then** the backdrop is rendered exactly as today (no change to the full-span view).
2. **Given** a year window narrower than the full span is active, **When** the backdrop renders, **Then** each year within the window contributes dots in proportion to the square root of that year's article count in the window (higher-volume years still show more, but the ratio is compressed).
3. **Given** a fixed-width year window, **When** the visitor slides it from an early era to a recent era, **Then** the total visible backdrop dot count stays within a bounded tolerance band across positions (no order-of-magnitude swing).
4. **Given** a year window is active, **When** dots are chosen within each year, **Then** the selection preserves the spatial shape of that year's articles (a spatially-representative cover, not a spatial cluster or a raw prefix).
5. **Given** the visitor clears the year filter (returns to full span), **When** the backdrop re-renders, **Then** it returns to the default spatial sample identical to before any filtering.

---

### Edge Cases

- **Single-year window** (start == end): the backdrop shows a spatially-representative sample of that one year, bounded by the same overall dot budget.
- **Very sparse window** (fewer articles than the per-year budget): every article in the window is shown; nothing is fabricated or duplicated.
- **Empty window** (no articles in range): the backdrop is empty; no error.
- **Cluster + year filters combined**: year-aware density operates on the set already narrowed by any active cluster filter; both filters compose without one overriding the other.
- **Zoom/pan while a year window is active**: the existing viewport detail behaviour continues to work and also respects the active year window (no out-of-window dots appear when zoomed).
- **Result list and counts**: unaffected — they continue to report the true number of articles in the window, independent of how many dots the backdrop renders.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: While a year filter is active on `/neuroscape/`, the backdrop's rendered base sample MUST distribute dots across the window's years so that each year contributes dots proportional to the square root of that year's article count within the active window (compressed-proportional).
- **FR-002**: Within each year, the dots shown MUST be a spatially-representative (shape-preserving) subset of that year's articles in the window, reusing the existing per-point spatial ordering.
- **FR-003**: The total rendered backdrop dot count MUST be bounded by an overall budget comparable to today's rendered sample size, so on-screen density stays in a legible range regardless of window position.
- **FR-004**: The year-aware density MUST apply ONLY while a year filter is active. When the year filter is inactive (full span), the backdrop MUST render exactly as it does today.
- **FR-005**: Clearing the year filter MUST restore the default backdrop sample with no residual effect from prior filtering.
- **FR-006**: The feature MUST NOT change filtering semantics: the article result list and all facet counts MUST continue to reflect the true set of articles in the window, independent of backdrop rendering density.
- **FR-007**: The feature MUST be confined to NeuroScape mode. The atlas-root and `/ohbm2026/` surfaces MUST be unaffected.
- **FR-008**: The zoom/pan viewport detail behaviour MUST continue to function and MUST respect the active year window (no dots outside the window appear at any zoom level).
- **FR-009**: The feature MUST be client-side only: it MUST NOT require regenerating the NeuroScape data package or re-publishing data; the published data bytes remain identical.
- **FR-010**: Interacting with the year slider (including dragging) with the feature active MUST remain responsive — no worse than today's year-filter recompute.

### Key Entities *(include if feature involves data)*

- **Active year window**: the start/end years currently selected; "full span" denotes the inactive state in which the feature does nothing.
- **Per-year article group**: the articles of a single publication year within the active window, each carrying a spatial-ordering key (the existing level-of-detail rank) used to pick a shape-preserving subset.
- **Backdrop dot budget**: the overall cap on rendered backdrop dots, apportioned across the window's years by the compressed-proportional rule.

### Constitution Alignment *(mandatory)*

- **CA-001**: No Python execution; this is a client-side UI change in the SvelteKit site under `site/`. The `.venv`-only rule is unaffected.
- **CA-002**: Behaviour-changing logic (the per-year compressed-proportional sampler) is covered by failing-first unit tests via `vitest run` before implementation, plus a NeuroScape e2e that verifies the visible dot count stays within a tolerance band as a fixed-width window slides across eras.
- **CA-003**: No canonical defaults, inputs, or outputs change. Doc surfaces to update in the same change are the in-file component/module docs and this spec's companions; no README/CLAUDE.md default changes.
- **CA-004**: No credentials or secrets involved.
- **CA-005**: No new dataset, cache, export, or downloaded asset; no generated data tracked.
- **CA-006**: Error paths are explicit at the UI level: empty/sparse/single-year windows and degenerate inputs resolve to a valid (possibly empty) sample without throwing; no verification gate is bypassed.
- **CA-007**: The sampler discovers the window's per-year counts and bounds at runtime from the loaded corpus (never a hardcoded 1999–2023 span); a corpus with different years drives the sampling accordingly.
- **CA-008**: No organizer-facing or downstream-consumer artifact is produced and no data package is re-published; the byte-identical data-package guarantee is preserved. No new provenance file required.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With a fixed-width year window, the visible backdrop dot count varies by no more than a bounded factor (target: ≤ ~2×) between the sparsest and densest window positions across the corpus timeline — versus the order-of-magnitude (10×+) swing today.
- **SC-002**: Higher-volume years within a window still render more dots than lower-volume years (the density is compressed, not flattened): the per-year dot counts remain monotonic in the per-year article counts.
- **SC-003**: The full-span (no year filter) backdrop is visually identical to today — zero change to the default landing view.
- **SC-004**: The article result list count for any given year window is identical to today (no filtering-semantics regression).
- **SC-005**: Sliding the year window with the feature active remains responsive, with no perceptible added lag over today's year-filter behaviour.
- **SC-006**: atlas-root and `/ohbm2026/` render identically to today (no cross-surface regression).

## Assumptions

- The change is scoped to NeuroScape mode; atlas-root has no year facet and `/ohbm2026/` uses a different backdrop, so both are out of scope.
- The NeuroScape browser corpus already carries, per point, publication year and a spatial level-of-detail ordering — so year-aware sampling needs no new data.
- Density operates at whole-year granularity, matching the corpus' year-level data and the slider's whole-year steps.
- The overall dot budget is chosen to approximate today's rendered sample size so the change is a redistribution, not a wholesale increase or decrease in on-screen density.
- Client-side-only; no corpus/pipeline rerun and no data-package re-publish.
