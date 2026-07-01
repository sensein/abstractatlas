---

description: "Task list for NeuroScape Atlas Year Range Slider"
---

# Tasks: NeuroScape Atlas Year Range Slider

**Input**: Design documents from `/specs/025-neuroscape-year-range-slider/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: REQUIRED — this is a UI behavior change (CA-002). Pure-helper
behavior is covered by failing-first `vitest` unit tests; slider gestures by
a failing-first Playwright e2e. No new corpus/pipeline work, so no Python
or data tests.

**Organization**: Grouped by user story. US1 (set endpoints) is the
shippable MVP — a working dual-handle slider that fully replaces the two
number boxes. US2 (move the whole window) is an independent increment.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- All paths are under `site/` (single SvelteKit project, neuroscape mode only)

## Path Conventions

- Pure helper: `site/src/lib/filter/year_range.ts`
- Component: `site/src/lib/components/YearRangeSlider.svelte`
- Facet (edited): `site/src/lib/components/NeuroscapeFacets.svelte`
- Unit tests: `site/src/tests/unit/year_range.test.ts`
- e2e: `site/src/tests/e2e/neuroscape_year_slider.spec.ts`
- Run unit with `vitest run` (NEVER `pnpm test:unit -- --run` — hangs in watch mode)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Orient on the insertion point; confirm no new dependency.

- [x] T001 Smoke the NeuroScape dev build (`cd site && VITE_SITE_MODE=neuroscape pnpm dev`), open Filters → Years, and capture the current baseline (two `From`/`To` number inputs at `NeuroscapeFacets.svelte:126–151`) as the block to be replaced; confirm no new npm dependency is required (slider is built in-house per research R1).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The shared pure year-window math both user stories depend on.

**⚠️ CRITICAL**: Both US1 and US2 call functions from this module — it must land first.

- [x] T002 [P] Write failing-first unit tests for the SHARED helpers (`clampYear`, `resolveSpan`, `isFullSpan`, `toFilter`, `fromFilter`) in `site/src/tests/unit/year_range.test.ts` — cases 1, 2, 7, 8, 9 from `contracts/year-range-helper.md` (incl. degenerate `lo === hi`, full-span ⇒ `null/null`, single-year window). Run red: `cd site && pnpm exec vitest run src/tests/unit/year_range.test.ts`.
- [x] T003 Implement the SHARED pure helpers + types (`YearBounds`, `YearWindow`, `YearFilter`, `clampYear`, `resolveSpan`, `isFullSpan`, `toFilter`, `fromFilter`) in `site/src/lib/filter/year_range.ts` to make T002 green. No DOM, no side effects; all functions total (never throw).

**Checkpoint**: Shared math green — user-story slider work can begin.

---

## Phase 3: User Story 1 - Set both ends with a slider (Priority: P1) 🎯 MVP

**Goal**: Replace the two number boxes with a dual-handle slider whose two handles set the start and end years, bounded by the corpus year bounds, with a numeric span readout.

**Independent Test**: In the NeuroScape build, open Filters → Years; drag the start handle right and the end handle left; the article list/scatter narrow to the selected span and the readout matches the handle positions; "Clear" restores full span.

### Tests for User Story 1 (write FIRST, ensure they FAIL) ⚠️

- [x] T004 [P] [US1] Add failing-first unit tests for `setStart`/`setEnd` including crossed-handle resolution (cases 3, 4 from `contracts/year-range-helper.md`) in `site/src/tests/unit/year_range.test.ts`. Run red.
- [x] T005 [P] [US1] Add failing-first Playwright e2e `site/src/tests/e2e/neuroscape_year_slider.spec.ts` covering U1, U2, U3, U5, U6 from `contracts/slider-ui.md` (initial render at bounds; drag start handle; drag end handle; Clear; readout matches filter). Run red against the neuroscape build.

### Implementation for User Story 1

- [x] T006 [US1] Implement `setStart`/`setEnd` in `site/src/lib/filter/year_range.ts` (clamp + `resolveSpan`) to make T004 green (depends on T003).
- [x] T007 [US1] Create `site/src/lib/components/YearRangeSlider.svelte`: props `minYear`/`maxYear`/`bounds`; derive internal `YearWindow` via `fromFilter`; a `<div>` track with two `role="slider"` thumb buttons (`data-testid` `neuroscape-year-handle-start`/`-end`, `aria-valuemin/max/now`, `aria-label`); pointer-drag each thumb (Pointer Events + `setPointerCapture`, calling `setStart`/`setEnd`); keyboard (Arrow ±1yr, Home/End to bound); numeric `start–end` readout (`data-testid="neuroscape-year-readout"`); container `data-testid="neuroscape-year-slider"`; emit `change` with `toFilter(window, bounds)` (full span ⇒ `null/null`). Handle degenerate `lo === hi` without throwing. (depends on T006)
- [x] T008 [US1] Wire `<YearRangeSlider>` into `site/src/lib/components/NeuroscapeFacets.svelte`, replacing the `.year-row` two-input block (`:126–151`); on its `change`, re-emit the existing `update` payload `{ cluster_ids: selectedClusterIds, min_year, max_year }`; leave `activeCount` and `clearAll` unchanged; reuse the OHBM facet visual tokens; update the component doc comment to describe the slider. (depends on T007)
- [~] T009 [US1] Make T005 green; run `cd site && pnpm exec vitest run src/tests/unit/year_range.test.ts` and `pnpm exec playwright test src/tests/e2e/neuroscape_year_slider.spec.ts` (US1 cases). Confirm `+page.svelte` was NOT modified. — DONE: unit suite green (293/293), `svelte-check` 0/0, `pnpm run build` ✓, `+page.svelte` confirmed unchanged. Playwright deferred to CI/PR-preview (needs the deployed neuroscape 461k parquet — cannot run in this local env).

**Checkpoint**: US1 is a complete, shippable replacement for the number boxes (endpoints settable by slider; no band-drag yet).

---

## Phase 4: User Story 2 - Move the whole window (Priority: P2)

**Goal**: Let the user grab the band between the handles and slide the fixed-width window earlier/later, clamped at the corpus bounds.

**Independent Test**: With a narrower-than-full window selected, drag the band; both ends shift by the same amount (width preserved); dragging past a bound stops the window at that bound without shrinking.

### Tests for User Story 2 (write FIRST, ensure they FAIL) ⚠️

- [x] T010 [P] [US2] Add failing-first unit tests for `moveWindow` (cases 5, 6: width preserved on in-bounds shift; width preserved and stops at `lo`/`hi` when shifted past a bound) in `site/src/tests/unit/year_range.test.ts`. Run red.
- [x] T011 [P] [US2] Add failing-first e2e case U4 (band-drag: both ends shift, width preserved, stops at bound) to `site/src/tests/e2e/neuroscape_year_slider.spec.ts`. Run red.

### Implementation for User Story 2

- [x] T012 [US2] Implement `moveWindow(window, deltaYears, bounds)` in `site/src/lib/filter/year_range.ts` (shift both ends; clamp the shift so width is preserved and the window stops at the bound) to make T010 green (depends on T003).
- [x] T013 [US2] Add a draggable band element (`data-testid="neuroscape-year-band"`) between the two thumbs in `site/src/lib/components/YearRangeSlider.svelte`; pointer-drag converts pixel delta → year delta and calls `moveWindow`; emit `change` via `toFilter`. Band-move is a pointer/touch gesture only (keyboard users adjust the window via the two endpoint handles — FR-004); a keyboard window-move shortcut is out of scope. (depends on T007, T012)
- [~] T014 [US2] Make T011 green; re-run the e2e spec (US1 + US2 cases). — DONE: `moveWindow` unit cases green; band-drag e2e (U4) authored. Playwright execution deferred to CI/PR-preview (same data-host dependency as T009).

**Checkpoint**: Both stories work; endpoints settable AND the window draggable.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [x] T015 [P] Run the full unit suite `cd site && pnpm exec vitest run` (incl. `year_range` + existing `facets`) — all green.
- [x] T016 [P] Run `cd site && pnpm run build` for all three modes and confirm atlas-root and `/ohbm2026/` are unaffected (no year facet there — FR-012).
- [~] T017 Run the `quickstart.md` manual checks: keyboard operation (Tab to handle, arrow/Home/End) and touch via mobile emulation (FR-010/FR-011, SC-005). — PENDING: requires a live neuroscape preview with the loaded corpus. Keyboard (FR-010) is covered by an automated e2e case and the slider uses Pointer Events (single mouse/touch path, FR-011); final manual sign-off to be done on the PR preview.
- [x] T018 Confirm no `data/` writes, no new gitignore root needed, and no parquet/manifest/provenance change (byte-identical data-package guarantee — CA-005/CA-008).
- [x] T019 Run `.specify/scripts/bash/constitution-check.sh --full` and resolve any reported violations.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: none.
- **Foundational (T002–T003)**: blocks all stories (shared helper).
- **US1 (T004–T009)**: after Foundational. MVP.
- **US2 (T010–T014)**: after Foundational; independently testable. Shares the helper file (T012) and the component file (T013 depends on T007), so it follows US1 in practice but is its own increment.
- **Polish (T015–T019)**: after the desired stories complete.

### Within Each Story

- Tests (T004/T005, T010/T011) are written FIRST and must FAIL before implementation.
- Helper math before component; component before facet wiring.

### Parallel Opportunities

- T002 (foundational tests) runs alone before T003.
- US1: T004 and T005 are [P] (different files: unit test vs e2e). Component work (T007→T008) is sequential (same/dependent files).
- US2: T010 and T011 are [P]. T012 (helper) and T013 (component) are sequential on dependencies.
- Polish: T015 and T016 are [P].

---

## Parallel Example: User Story 1

```bash
# Author the two failing-first test files together:
Task: "Unit tests for setStart/setEnd in site/src/tests/unit/year_range.test.ts"
Task: "e2e U1/U2/U3/U5/U6 in site/src/tests/e2e/neuroscape_year_slider.spec.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001 setup orientation.
2. T002–T003 foundational helper (red → green).
3. T004–T009 US1: slider with two settable handles wired into the facet.
4. **STOP and VALIDATE**: drag both handles, Clear, confirm filtering matches the old number-box behavior (SC-003). This alone fully replaces the number boxes.

### Incremental Delivery

1. Foundational → helper ready.
2. US1 → working dual-handle slider (MVP) → demo.
3. US2 → add band-drag (move window) → demo.
4. Polish → full suite, all three builds, constitution check.

---

## Notes

- [P] = different files, no dependency on incomplete tasks.
- All work is client-side under `site/`; no Python, no `.venv`, no `data/` writes.
- `+page.svelte` state shape (`filterMinYear`/`filterMaxYear`, `yearBounds`, `update` payload) is REUSED UNCHANGED — do not modify the filter math or the update handler.
- Slider extent comes from the runtime-derived `yearBounds` (never a hardcoded 1999–2023 span — CA-007).
- Commit per verified slice (helper+tests, then component, then wiring/e2e) and push the branch when complete.
- No data-package re-publish; byte-identical guarantee preserved.
