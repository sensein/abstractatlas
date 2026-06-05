---
description: "Task list for Atlas Research-Classification Dimensions"
---

# Tasks: Atlas Research-Classification Dimensions

**Input**: Design documents from `specs/023-atlas-research-dimensions/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: INCLUDED — this is a pipeline + UI behavior change (Constitution IV
+ CA-002 mandate verification-first). Write each test before its implementation
and confirm it FAILS first.

**Organization**: grouped by the three user stories. Setup adds the **distiller**
(full `abstracts.detail.json` → slim `dimensions.slim.json`, the build input —
per Clarifications). A shared Foundational phase puts the four dimension lists
onto each exported record's `facets` STRUCT (both US1 and US2 read
`record.facets[key]`); the stories then layer the detail UI (US1), the facet UI
+ catalog (US2), and ingestion robustness + provenance (US3) on top.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no incomplete-task dependency)
- **[Story]**: US1 / US2 / US3 (Setup / Foundational / Polish carry no story label)

## Path Conventions

Two-track repo: Python under `src/ohbm2026/`, tests under `tests/`; SvelteKit
site under `site/`. Python runs via `.venv/bin/python` (Constitution I); site
tests via `pnpm exec vitest run` (never watch mode).

---

## Phase 1: Setup (Distiller + input prep)

**Purpose**: Land the raw file and build the distiller that produces the slim
build input.

- [x] T001 Place the operator-supplied full file at `data/inputs/neuroscape-dimensions/abstracts.detail.json` and confirm gitignored (`git check-ignore …`); the ~120 MB raw file MUST NOT be staged (Constitution II / CA-005)
- [x] T002 [P] Create `tests/test_ui_data_dimensions.py` with the distiller test (FAIL — module absent): `distill_dimensions(full, slim)` writes a slim file with the data-model §2c wrapper (`schema_version: "dimensions.slim.v1"` + a `dimensions` map of `{id: {4 dimension lists}}`) and NO other per-abstract fields; two runs are byte-identical (deterministic); a full file missing the `abstracts` map / join key / all dimension fields raises `DimensionInputError`
- [x] T003 Create `src/ohbm2026/ui_data/dimensions.py` with `DIMENSION_KEYS`, `DIMENSION_LABELS`, `class DimensionInputError(Stage6BuildError)`, and `distill_dimensions(full_path, slim_path)` (data-model §2b); add the `scripts/distill_dimensions.py --in --out` CLI (per `contracts/dimension-input.md`)
- [x] T004 Run the distiller to produce `data/inputs/neuroscape-dimensions/dimensions.slim.json` and confirm it is gitignored and far smaller than the source

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Get the four dimension lists onto each exported abstract's `facets`
dict and round-tripping through `ohbm2026.parquet`, reading the **slim** file.
BLOCKS US1 and US2.

**⚠️ CRITICAL**: No user-story UI work can begin until this phase is complete.

### Tests first (write, run, confirm FAIL)

- [x] T005 [P] Extend `tests/_ui_data_fixtures.py`: add the four dimension fields to fixture corpus records (one with all four, one missing `theory_scope`, one absent from the dimension file) and write a tiny **slim** `dimensions.slim.json`-shaped fixture keyed by submission id
- [x] T006 [P] Extend `tests/test_ui_data_dimensions.py`: `load_research_dimensions(slim_fixture)` returns `{submission_id: {dim_key: [labels]}}` for the four keys (FAIL — function absent)
- [x] T007 Extend `tests/test_ui_data_abstracts.py`: with a `research_dimensions` map, exported records' `facets` carry the four keys with correct labels; an abstract absent from the file gets `[]`; omitting the map ⇒ all four empty (D4) (FAIL)
- [x] T008 Extend `tests/test_ui_data_parquet_single.py`: an abstract with non-empty dimensions round-trips through the abstracts STRUCT with all four keys; an empty dimension round-trips as `[]` (FAIL)

### Implementation

- [x] T009 [P] Add `load_research_dimensions(slim_path) -> dict[int, dict[str, list[str]]]` to `src/ohbm2026/ui_data/dimensions.py` (reads the slim file; restrict to the four keys, de-dup + strip labels, coerce id→int) — `contracts/dimension-input.md`
- [x] T010 [P] Extend `FacetValues` TypedDict in `src/ohbm2026/ui_data/types.py` with `focus`, `research_modality`, `theory_scope`, `epistemic_basis` (`list[str]`) — data-model §4
- [x] T011 Add the four keys to the `keys` tuple in `_facets_to_arrow` in `src/ohbm2026/ui_data/formats/parquet_single.py` (else the columns are silently dropped)
- [x] T012 Add a `research_dimensions: Mapping[int, dict] | None` param to `iter_abstracts` / `build_abstracts_records` / `build_abstracts` in `src/ohbm2026/ui_data/abstracts.py`; inject the four lists into each record's `facets` from `research_dimensions.get(abstract_id, {})`, defaulting each missing dimension to `[]`
- [x] T013 Wire `src/ohbm2026/ui_data/builder.py` + `scripts/build_ui_data.py`: add the optional `--dimensions PATH` arg pointing at the **slim** file, load via `load_research_dimensions` when present (else `None`), thread `research_dimensions=...` into `build_abstracts(...)`; log "dimensions: not supplied" when absent (opt-in default, not a silent fallback)

**Checkpoint**: `unittest tests.test_ui_data_dimensions tests.test_ui_data_abstracts tests.test_ui_data_parquet_single` green; a built parquet's abstracts carry the four facet lists.

---

## Phase 3: User Story 1 — Per-abstract computed insights (Priority: P1) 🎯 MVP

**Goal**: The four dimensions appear in each abstract's detail view as labelled chip groups in the computed-insights zone; an empty dimension is omitted.

**Independent Test**: Open a detail view for an abstract classified on all four dimensions → all four labelled chip groups render; open one missing `theory_scope` → that group is absent, the other three render.

### Tests first (write, run, confirm FAIL)

- [x] T014 [P] [US1] Extend `site/src/tests/e2e/detail-extra-fields.spec.ts`: open an abstract with all four dimensions → assert `extra-focus`, `extra-research_modality`, `extra-theory_scope`, `extra-epistemic_basis` blocks render with values; open one missing a dimension → assert that block is absent (FAIL)

### Implementation

- [x] T015 [US1] Add four labelled chip blocks to `site/src/lib/components/DetailPanel.svelte` in the computed-insights zone (`data-zone="computed"`, near line 489), template = the Methods chip block (line 725): each reads `abstract.facets[key]` (coerce string→[string]), renders `<h2>{label}</h2>` + `<ul class="chips">`, `data-testid="extra-{key}"`, and renders nothing when the list is empty (FR-007); reuse the existing `.chips`/`.extra` CSS

**Checkpoint**: US1 fully functional — detail view shows the four dimensions; MVP demoable.

---

## Phase 4: User Story 2 — Filterable facets (Priority: P2)

**Goal**: The four dimensions appear as facets in the sidebar with option counts and multi-select OR-membership, narrowing the corpus like every other block facet.

**Independent Test**: Open the facet sidebar → the four facets appear with option counts; select an option → the abstract set + counts narrow; a multi-label abstract matches when any one of its labels is selected.

### Tests first (write, run, confirm FAIL)

- [x] T016 [P] [US2] Extend `site/src/tests/unit/facets.test.ts`: fixtures gain the four facet keys; assert `valuesFor` returns the labels, the facet-count maps include the four facets with correct per-option counts, and OR-membership holds for a multi-label record (FAIL)
- [x] T017 [P] [US2] Extend `tests/test_ui_data_manifest.py`: the four facets appear in `manifest["facets"]` with non-empty `options` matching the fixture labels (FAIL)

### Implementation

- [x] T018 [P] [US2] Add the four keys to `FACET_KEYS` and `FACET_LABELS` in `src/ohbm2026/ui_data/manifest.py` (labels from `DIMENSION_LABELS`); `_facet_options` then auto-discovers options
- [x] T019 [US2] Add the four keys to `site/src/lib/facets.ts`: append to `FACETS_FROM_BLOCK`, insert into `FACET_KEYS_ORDERED` (after `brain_networks`, before `keywords`), and add the four `FACET_LABELS` entries (`valuesFor` needs no change)
- [x] T020 [P] [US2] Extend `site/src/tests/e2e/facets.spec.ts`: the four `facet-{key}` sections render and selecting an option narrows the result count

**Checkpoint**: US1 AND US2 both work independently — facets filter, detail displays.

---

## Phase 5: User Story 3 — Reproducible, provenance-tracked ingestion (Priority: P3)

**Goal**: Fail-loud on bad/missing input; per-dimension coverage reported and recorded in the manifest provenance; unmatched file entries counted, never added; deterministic rebuild.

**Independent Test**: Run the build with the slim file present → per-dimension coverage logged and a `research_dimensions` block in the manifest; run with `--dimensions` pointing at a missing/corrupt file → `DimensionInputError`; rebuild twice with identical inputs → byte-identical parquet.

### Tests first (write, run, confirm FAIL)

- [x] T021 [P] [US3] Extend `tests/test_ui_data_dimensions.py` with error-path + coverage tests: missing-file / bad-JSON / wrong-shape / no-dimension-fields / non-list value → `DimensionInputError`; `compute_dimension_coverage` returns `matched + no_value == corpus_count` per dimension (D1) and counts `unmatched_in_file` adding zero abstracts (D3) (FAIL)
- [x] T022 [P] [US3] Extend `tests/test_ui_data_builder.py`: a build with the slim file records the `research_dimensions` provenance block (source basename + sha256 + per-dimension matched/no_value + unmatched_in_file, no absolute/home paths); a second build with identical inputs is byte-identical (SC-005 / D5); omitting `--dimensions` ⇒ no provenance block, build still succeeds (D4) (FAIL)

### Implementation

- [x] T023 [US3] Harden `load_research_dimensions` in `src/ohbm2026/ui_data/dimensions.py`: raise `DimensionInputError` for each failure condition in `contracts/dimension-input.md` (layout discovered at runtime, not assumed — CA-007); no bare except
- [x] T024 [P] [US3] Add `compute_dimension_coverage(dimensions, exported_submission_ids, *, source_file, source_sha256)` to `src/ohbm2026/ui_data/dimensions.py` returning the data-model §3 block
- [x] T025 [US3] In `src/ohbm2026/ui_data/builder.py` compute the slim-file sha256 (streamed) + basename and `compute_dimension_coverage` against the exported `abstract_ids`; thread `dimension_coverage=...` into `build_manifest`; in `src/ohbm2026/ui_data/manifest.py` emit the `research_dimensions` provenance block (omitted when no file) and log `unmatched_in_file` (FR-010 / FR-012 / CA-008)

**Checkpoint**: All three stories independently functional; ingestion is auditable and fail-loud.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [x] T026 [P] Update `README.md` with the distiller (`distill_dimensions.py`), the `--dimensions` flag pointing at the slim file, the input locations, and the coverage/provenance behavior
- [x] T027 [P] Update the `AbstractRecord.facets` slot description in `specs/008-ui-rewrite/contracts/ui_data.linkml.yaml` ("the 11 …lists" → "the 15 …lists"); run `scripts/validate_ui_data.sh` against a freshly built parquet to confirm it still validates
- [x] T028 Run the full Python suite `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v` and the site suite `cd site && pnpm exec vitest run && pnpm exec playwright test detail-extra-fields facets` — all green; confirm no existing Stage 6 invariant or `test_ohbm2026_parquet_rename` regression (FR-014 / SC-006)
- [x] T029 Run `quickstart.md` end-to-end: distill → build with `--dimensions`, verify logged coverage matches the source distribution (≈ focus 3329 / modality 3326 / theory_scope 2890 / epistemic 3325), build twice and `cmp` for byte-identity
- [x] T030 Constitution sweep: `.specify/scripts/bash/constitution-check.sh --full`; manually confirm no bare excepts / silent fallbacks / gate bypasses (VI), external layout discovered not hardcoded (VII), provenance has no absolute/home paths (VIII), and no data/caches/large input were committed (II/V)

---

## Dependencies & Execution Order

### Phase dependencies

- **Setup (P1)**: distiller (T002→T003→T004) produces the slim build input; T003 also creates `dimensions.py` with the shared constants + error type.
- **Foundational (P2)**: depends on Setup (`dimensions.py` exists). **BLOCKS US1 and US2** (data substrate).
- **US1 (P3 phase)**: depends only on Foundational. Independent of US2/US3.
- **US2 (P4 phase)**: depends only on Foundational. Independent of US1.
- **US3 (P5 phase)**: depends on Foundational + Setup `dimensions.py`; shares `manifest.py` with US2 (different functions — sequence if same dev).
- **Polish (P6)**: depends on all desired stories.

### Within each story

- Tests written first and FAIL before implementation (Constitution IV).
- Distiller before Foundational load (the load reads the slim file the distiller produces; unit tests use a slim fixture so they don't need the real file).

### Parallel opportunities

- Setup T002 [P] alongside other prep; T003→T004 sequential.
- Foundational tests T005/T006 [P]; impl T009/T010 [P]; T011→T012→T013 sequential (parquet→abstracts→builder chain).
- After Foundational, **US1 (T014–T015) and US2 (T016–T020) run in parallel** by different devs.
- US2 internals T016/T017/T018/T020 [P]; T019 (site facets.ts) independent of the Python T018.
- US3 T021/T022 [P]; T024 [P]; T023→T025 sequenced.

---

## Parallel Example: after Foundational completes

```bash
# Dev A — US1 (detail):
Task: "Extend detail-extra-fields.spec.ts for the 4 dimension blocks"
Task: "Add 4 chip blocks to DetailPanel.svelte"

# Dev B — US2 (facets), in parallel:
Task: "Extend site facets.test.ts for the 4 new facet keys"
Task: "Add 4 keys to manifest.py FACET_KEYS/FACET_LABELS"
Task: "Add 4 keys to site facets.ts constants"
```

---

## Implementation Strategy

### MVP first (US1 only)

1. Phase 1 Setup (distiller → slim file) → Phase 2 Foundational (data into the parquet `facets`).
2. Phase 3 US1 (DetailPanel chips).
3. **STOP & VALIDATE**: open a detail view, confirm the four dimensions render and an empty one is omitted. Demoable MVP.

### Incremental delivery

1. Setup + Foundational → data flows into `facets`.
2. US1 → detail chips (MVP) → commit + (optionally) deploy.
3. US2 → sidebar facets → commit + deploy.
4. US3 → fail-loud + provenance + determinism → commit + deploy.
5. Polish → docs, schema note, full-suite + constitution sweep → push; add `deploy-production` label before merge for the live cutover.

## Notes

- Commit each verified slice with a descriptive message; do not batch (Constitution V). Push when complete unless asked otherwise.
- Never commit `abstracts.detail.json`, `dimensions.slim.json`, or any built parquet (Constitution II) — the distiller regenerates the slim file on demand.
- `--dimensions` absent ⇒ four empty facets + build succeeds — a documented opt-in default, logged, not a silent fallback.
- Atlas-root and `/neuroscape/` are out of scope and must stay byte-unchanged.
