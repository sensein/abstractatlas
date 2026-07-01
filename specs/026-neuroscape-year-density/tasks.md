---

description: "Task list for NeuroScape Atlas Year-Aware Backdrop Density"
---

# Tasks: NeuroScape Atlas Year-Aware Backdrop Density

**Input**: Design documents from `/specs/026-neuroscape-year-density/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: REQUIRED — UI behaviour change (CA-002). The pure sampler is
covered by failing-first `vitest` unit tests; the slide-the-window density
band by a failing-first Playwright e2e. No Python / data tests (client-side
only, no data re-publish).

**Organization**: One user story (US1 — legible, comparable density while
sliding a year window). The pure sampler is its foundation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: different files, no dependency on incomplete tasks
- All paths under `site/` (SvelteKit project, neuroscape mode only)

## Path Conventions

- Pure sampler: `site/src/lib/atlas/year_density.ts`
- Wiring (edited): `site/src/routes/+page.svelte` (`scatterBackdropForMap`, `:840`)
- Unit tests: `site/src/tests/unit/year_density.test.ts`
- e2e: `site/src/tests/e2e/neuroscape_year_density.spec.ts`
- Run unit with `vitest run` (NEVER `pnpm test:unit -- --run` — hangs in watch mode)

---

## Phase 1: Setup

**Purpose**: Orient on the seam; confirm no new dependency.

- [x] T001 Smoke the NeuroScape dev build (`cd site && VITE_SITE_MODE=neuroscape pnpm dev`); confirm the baseline: `scatterBackdropForMap` (`+page.svelte:840`) currently returns `scatterBackdrop.filter(lod_level ≤ neuroscapeLodCap)`, and each backdrop point carries `year` + `lod_level`. Confirm no new npm dependency is needed (pure array math).

---

## Phase 2: Foundational (Blocking Prerequisite)

**Purpose**: The pure compressed-proportional sampler US1 depends on.

**⚠️ CRITICAL**: The wiring (US1) calls this module — it must land first.

- [x] T002 [P] Write failing-first unit tests in `site/src/tests/unit/year_density.test.ts` covering the 9 cases in `contracts/year-density-sampler.md` (√ compression, monotonic quota, budget bound, within-year `lod_level` order + `pubmed_id` tiebreak, sparse year = all shown, single-year window, empty input, legacy no-`lod_level` determinism, overall determinism). Run red: `cd site && pnpm exec vitest run src/tests/unit/year_density.test.ts`.
- [x] T003 Implement `site/src/lib/atlas/year_density.ts` (`DensityPoint`/`DensityCalibration` types, `calibrate(fullCorpus, targetBudget)`, `yearQuota(countY, k)`, `yearAwareSample(points, calib)`) to make T002 green. Pure, no DOM, total (never throws); `quota_y = min(count_y, round(k·√count_y))`, within-year selection = smallest `lod_level` (tiebreak `pubmed_id`), legacy fallback = deterministic stride.

**Checkpoint**: Sampler green — wiring can begin.

---

## Phase 3: User Story 1 - Legible, comparable density while sliding a year window (Priority: P1) 🎯 MVP

**Goal**: When a year filter is active, the neuroscape backdrop base sample uses the compressed-proportional per-year sampler, so a fixed-width window shows comparable density as it slides; full-span, atlas-root, `/ohbm2026/` unchanged.

**Independent Test**: On `/neuroscape/`, pick a fixed-width year window, record the rendered backdrop dot count at several era positions, confirm the max/min ratio is within the band; confirm full-span view and `result-count` are unchanged.

### Tests for User Story 1 (write FIRST, ensure they FAIL) ⚠️

- [x] T004 [P] [US1] Add failing-first Playwright e2e `site/src/tests/e2e/neuroscape_year_density.spec.ts` covering B1–B6 from `contracts/render-integration.md`: full-span baseline (B1), fixed-width early-vs-recent window backdrop dot count within a bounded ratio (B2/SC-001), result-count still reflects true volume recent≫early (B4/FR-006), clear restores full-span backdrop (B5). Authored (reads the plotly 2D trace point count + result-count).

### Implementation for User Story 1

- [x] T005 [US1] In `site/src/routes/+page.svelte`, compute + memoize `densityCalibration` when the corpus + `neuroscapeLodCap` are resident: `targetBudget = count(atlasBackdrop where lod_level ≤ cap)`, then `calibrate(atlasBackdrop, targetBudget)`; `null` until ready. (depends on T003)
- [x] T006 [US1] Edit `scatterBackdropForMap` (`+page.svelte:840`) per `contracts/render-integration.md`: when a year filter is active (`filterMinYear !== null || filterMaxYear !== null`) and `densityCalibration !== null`, return `yearAwareSample(scatterBackdrop, densityCalibration)`; otherwise keep today's `lod_level ≤ cap` path verbatim (FR-004). Update the derivation's doc comment. (depends on T005)
- [~] T007 [US1] Make T004 green; run `cd site && pnpm exec vitest run` and `pnpm exec playwright test src/tests/e2e/neuroscape_year_density.spec.ts`. Confirm `UmapPanel.svelte`, the result-list derivations, and `backdropFull` were NOT modified. — DONE: unit 308/308, svelte-check 0/0, build ✓, `UmapPanel`/`backdropFull`/result-list derivations confirmed unchanged (only `scatterBackdropForMap` + calibration memo edited). Playwright deferred to CI/PR-preview (needs the deployed neuroscape 461k corpus — cannot run locally).

**Checkpoint**: Feature complete — year-aware density active only under a year filter.

---

## Phase 4: Polish & Cross-Cutting Concerns

- [x] T008 [P] Run the full unit suite `cd site && pnpm exec vitest run` (incl. `year_density`) — all green — and `pnpm run check` (svelte-check 0/0).
- [x] T009 [P] Run `cd site && pnpm run build` for all three modes; confirm atlas-root and `/ohbm2026/` are unaffected (feature guarded by `SITE_MODE === 'neuroscape'` + year-active — FR-007/SC-006).
- [~] T010 Run the `quickstart.md` manual checks: full-span identical; slide a 3-year window early→recent (comparable density); clear restores default; zoom while windowed shows only in-window detail (FR-008). — PENDING: requires a live neuroscape preview with the loaded corpus; the automated e2e (T004) covers B1/B2/B4/B5; final manual sign-off on the PR preview.
- [x] T011 Confirm no `data/` writes and no parquet/manifest/provenance change (byte-identical data-package guarantee — CA-005/CA-008), and no filtering-semantics change (result-list counts unchanged — FR-006/SC-004).
- [x] T012 Run `.specify/scripts/bash/constitution-check.sh --full` and resolve any reported violations.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: none.
- **Foundational (T002–T003)**: blocks US1 (shared sampler).
- **US1 (T004–T007)**: after Foundational. MVP + the whole feature.
- **Polish (T008–T012)**: after US1.

### Within US1

- Test (T004) written FIRST and must FAIL before implementation.
- Calibration (T005) before the seam edit (T006); T006 before verify (T007).

### Parallel Opportunities

- T002 (foundational unit tests) runs before T003.
- T004 (e2e) is [P] vs the T002 unit file (different files); authored while the sampler lands.
- Polish T008 and T009 are [P].

---

## Parallel Example: User Story 1

```bash
# Author the two failing-first test files together:
Task: "Unit tests for the sampler in site/src/tests/unit/year_density.test.ts"
Task: "e2e B1–B6 in site/src/tests/e2e/neuroscape_year_density.spec.ts"
```

---

## Implementation Strategy

### MVP (the whole feature)

1. T001 setup orientation.
2. T002–T003 pure sampler (red → green).
3. T004–T007 wire into `scatterBackdropForMap`, verify.
4. **STOP and VALIDATE**: full-span unchanged; fixed-width window density comparable while sliding; result counts unchanged.
5. Polish → full suite, all three builds, constitution check.

---

## Notes

- All work is client-side under `site/`; no Python, no `.venv`, no `data/` writes.
- `scatterBackdrop`, result-list derivations, `backdropFull`, and `UmapPanel` are REUSED UNCHANGED — the only edit is `scatterBackdropForMap` + the calibration memo.
- Full-span path is byte-identical to today (FR-004); the feature is strictly additive + reversible.
- Calibration `k` is runtime-derived from the loaded corpus (never a hardcoded 1999–2023 table — CA-007).
- Commit per verified slice (sampler+tests, then wiring, then e2e) and push the branch.
- No data-package re-publish; byte-identical guarantee preserved.
