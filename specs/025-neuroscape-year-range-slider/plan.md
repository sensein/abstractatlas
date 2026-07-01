# Implementation Plan: NeuroScape Atlas Year Range Slider

**Branch**: `025-neuroscape-year-range-slider` | **Date**: 2026-06-29 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/025-neuroscape-year-range-slider/spec.md`

## Summary

Replace the NeuroScape atlas "Years" facet's two free-text number boxes
(`From`/`To`) with a **dual-handle range slider** that (a) sets the start
and end endpoints by dragging each handle and (b) shifts the whole
selected window — preserving its width — by dragging the band between the
handles. The change is confined to the SvelteKit site (`site/`), is
client-side only, and reuses the existing `filterMinYear` / `filterMaxYear`
+ `yearBounds` state plumbing in `+page.svelte` unchanged — only the input
control inside `NeuroscapeFacets.svelte` changes. The window math
(clamp, move-window, crossed-handle resolution, full-span-as-inactive) is
extracted into a pure, unit-tested helper module so the gesture component
stays thin and the behavior is verifiable without a browser.

## Technical Context

**Language/Version**: TypeScript 5 / Svelte 4 (SvelteKit), as used by the existing `site/` project
**Primary Dependencies**: SvelteKit, Vite; **no new runtime dependency** (the dual-handle slider is built in-house from native elements + pointer/keyboard handlers — see research.md R1)
**Storage**: N/A (in-memory filter state in `+page.svelte`; not persisted, matching the existing year filter)
**Testing**: `vitest run` (unit, for the pure year-window helper) + Playwright (e2e, for the slider gesture in the NeuroScape build)
**Target Platform**: Static gh-pages site; modern desktop + mobile browsers (incl. iOS Safari / WebKit per Stage 24)
**Project Type**: Web frontend (single SvelteKit project, three build modes; this feature touches the `neuroscape` mode only)
**Performance Goals**: Slider interaction is local DOM state — handle/band drag updates at interactive frame rates; the only downstream cost is the existing year-filter recompute over the loaded backdrop, unchanged from today
**Constraints**: Whole-year granularity (1 year/step); keyboard- and touch-operable; no behavioral change to filtering semantics; no data-package re-publish (byte-identical guarantee preserved)
**Scale/Scope**: One new component + one pure helper module + edits to one existing component (`NeuroscapeFacets.svelte`); `+page.svelte` wiring is unchanged in shape (same `update` event payload)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Venv-only Python** — N/A; no Python is touched. Site work runs through `pnpm` in `site/`. PASS.
- **Verification-first** — A failing-first `vitest` suite for the pure `year_range` helper (set-endpoint clamping, move-window clamping & width preservation, crossed-handle resolution, full-span ⇒ inactive) and a failing-first Playwright check (open Years facet → drag handles → drag band → assert filtered count + displayed span) are named here and authored before the component logic. PASS.
- **Immutable evidence / no committed data** — No data, cache, export, or asset is produced; nothing new is written under `data/`. PASS.
- **Resumable pipelines** — N/A (no pipeline run). PASS.
- **Plan-first, test-first** — This plan + spec precede implementation; tests precede component code. PASS.
- **Secret-safe** — No credentials involved. PASS.
- **Fail loudly, no shortcuts** — Invalid/crossed handle states resolve to a valid ordered span (explicit in the helper), degenerate corpus bounds (`lo == hi`) render without throwing; no bare excepts, no `--no-verify`, no skipped tests. PASS.
- **Discover external state** — The slider extent is read at runtime from the existing `yearBounds` derivation (min/max year over the loaded backdrop), never a hardcoded 1999–2023 span; a different corpus drives a different extent. PASS.
- **Provenance** — No organizer-facing or downstream-consumer artifact is produced; no data package is re-published, so no new provenance file is required. The byte-identical data-package guarantee is preserved. PASS.
- **Docs in same change** — The in-file component doc comment in `NeuroscapeFacets.svelte` (and the new component) is updated; no README/CLAUDE.md *default* changes (the only CLAUDE.md edit is the SPECKIT plan pointer). PASS.
- **Commit per slice + push** — Delivery commits the helper+tests, then the component, then the wiring/e2e as verified slices, and pushes the branch. PASS.

No violations → Complexity Tracking left empty.

## Project Structure

### Documentation (this feature)

```text
specs/025-neuroscape-year-range-slider/
├── plan.md              # This file
├── spec.md              # Feature spec (/speckit.specify output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── year-range-helper.md     # Pure helper function contract
│   └── slider-ui.md             # Component props/events + a11y/gesture contract
└── checklists/
    └── requirements.md  # Spec quality checklist (/speckit.specify output)
```

### Source Code (repository root)

```text
site/
├── src/
│   ├── lib/
│   │   ├── filter/
│   │   │   └── year_range.ts             # NEW — pure year-window math (clamp, moveWindow, resolveSpan, isFullSpan)
│   │   └── components/
│   │       ├── YearRangeSlider.svelte    # NEW — dual-handle slider + draggable band; keyboard + touch
│   │       └── NeuroscapeFacets.svelte    # EDIT — swap the two number inputs for <YearRangeSlider>
│   ├── routes/
│   │   └── +page.svelte                   # UNCHANGED state shape (filterMinYear/Max, yearBounds, update payload)
│   └── tests/
│       ├── unit/
│       │   └── year_range.test.ts        # NEW — vitest unit tests for the pure helper
│       └── e2e/
│           └── neuroscape_year_slider.spec.ts  # NEW — Playwright gesture + filter-result check
```

**Structure Decision**: Web-frontend layout. The feature lives entirely
under `site/`. The pure math is isolated in `site/src/lib/filter/year_range.ts`
(co-located with the existing `$lib/filter` `normalize` helper used by the
facet) so it is unit-testable in isolation; the Svelte component owns only
DOM/pointer/keyboard concerns. `NeuroscapeFacets.svelte` keeps its existing
`update` event payload (`{ cluster_ids, min_year, max_year }`), so
`+page.svelte` requires no change.

## Complexity Tracking

> No Constitution Check violations — section intentionally empty.
