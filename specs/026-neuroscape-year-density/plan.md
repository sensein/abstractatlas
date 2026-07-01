# Implementation Plan: NeuroScape Atlas Year-Aware Backdrop Density

**Branch**: `026-neuroscape-year-density` | **Date**: 2026-07-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/026-neuroscape-year-density/spec.md`

## Summary

When a year filter is active on `/neuroscape/`, choose the scatter
backdrop's base sample so each year contributes dots ∝ √(that year's count
in the filtered set) — a compressed-proportional density that tempers the
1999→2023 volume growth without flattening it — and pick each year's dots
by ascending `lod_level` so the selection stays a shape-preserving spatial
cover. Fully client-side: the change is a new pure module
`site/src/lib/atlas/year_density.ts` wired into the existing
`scatterBackdropForMap` derivation (`+page.svelte:840`), which today does a
plain `lod_level ≤ cap` spatial filter. Full-span (no year filter),
atlas-root, and `/ohbm2026/` are untouched. No `neuroscape.parquet`
rebuild, no data re-publish (byte-identical preserved).

## Technical Context

**Language/Version**: TypeScript 5 / Svelte 4 (SvelteKit) — the existing `site/` project
**Primary Dependencies**: SvelteKit, Vite; **no new dependency** (pure array math over the already-loaded corpus)
**Storage**: N/A (in-memory; corpus already resident on `/neuroscape/`)
**Testing**: `vitest run` (unit, pure sampler) + Playwright (e2e, dot-count-band while sliding)
**Target Platform**: static gh-pages site; desktop + mobile browsers
**Project Type**: web frontend (SvelteKit, three build modes; this touches `neuroscape` mode only)
**Performance Goals**: sampler runs on year-window change (slider drag); O(n) bucket + per-year partial-select over the filtered set (≤461k), no worse than today's filter recompute (FR-010 / SC-005)
**Constraints**: whole-year granularity; only active when a year filter is set; no change to filtering semantics or the full-span view; no data re-publish
**Scale/Scope**: one new pure module + one edited derivation in `+page.svelte`; `UmapPanel` unchanged (it renders whatever `backdropPoints` it's given)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Venv-only Python** — N/A; client-side only, `pnpm` in `site/`. PASS.
- **Verification-first** — failing-first `vitest` unit tests for the pure `year_density` sampler (per-year √ quota, budget bound, within-year `lod_level` order, full-span bypass, single-year/sparse/empty windows) and a failing-first Playwright check (dot count stays within a tolerance band as a fixed-width window slides across eras) are named here and authored before the code. PASS.
- **Immutable evidence / no committed data** — no `data/` writes, no parquet/manifest change. PASS.
- **Resumable pipelines** — N/A. PASS.
- **Plan-first, test-first** — spec + plan precede code; tests precede implementation. PASS.
- **Secret-safe** — no credentials. PASS.
- **Fail loudly, no shortcuts** — empty/sparse/single-year windows resolve to a valid (possibly empty) sample without throwing; no bare catches masking bugs; no gate bypass. PASS.
- **Discover external state** — per-year counts + bounds discovered at runtime from the loaded corpus; the density-calibration constant is derived from the corpus, never a hardcoded 1999–2023 table. PASS.
- **Provenance** — no organizer-facing artifact, no data re-publish; byte-identical preserved. PASS.
- **Docs in same change** — in-file module/derivation docs updated; CLAUDE.md SPECKIT pointer updated; no README default changes. PASS.
- **Commit per slice + push** — helper+tests, then wiring, then e2e, as verified slices; push the branch. PASS.

No violations → Complexity Tracking empty.

## Project Structure

### Documentation (this feature)

```text
specs/026-neuroscape-year-density/
├── plan.md              # This file
├── spec.md              # Feature spec
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── year-density-sampler.md   # Pure sampler contract + unit cases
│   └── render-integration.md     # How it wires into scatterBackdropForMap
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
site/
├── src/
│   ├── lib/
│   │   └── atlas/
│   │       └── year_density.ts        # NEW — pure compressed-proportional sampler
│   ├── routes/
│   │   └── +page.svelte               # EDIT — scatterBackdropForMap (:840) calls the sampler when a year filter is active
│   ├── lib/components/
│   │   └── UmapPanel.svelte           # UNCHANGED — renders whatever backdropPoints it receives
│   └── tests/
│       ├── unit/
│       │   └── year_density.test.ts   # NEW — vitest unit tests
│       └── e2e/
│           └── neuroscape_year_density.spec.ts  # NEW — dot-count-band e2e
```

**Structure Decision**: Web-frontend layout, all under `site/`. The math is
isolated in a pure `site/src/lib/atlas/year_density.ts` (co-located with the
existing atlas helpers `opacity.ts`, `lod3d.ts`), unit-testable without a
browser. `+page.svelte`'s `scatterBackdropForMap` derivation is the single
edit: when `isFullSpan` (no year filter) it keeps today's `lod_level ≤ cap`
path unchanged (FR-004); otherwise it delegates to the sampler.
`backdropFull` (the viewport rest-tier detail source, `:643`) is **already**
year+cluster filtered, so FR-008 needs no change. `UmapPanel` is untouched.

## Complexity Tracking

> No Constitution Check violations — section intentionally empty.
