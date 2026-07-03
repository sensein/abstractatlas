---

description: "Task list for Abstract Atlas Rename + Pluggable LinkML Ingestors"
---

# Tasks: Abstract Atlas Rename + Pluggable LinkML Ingestors

**Input**: Design documents from `/specs/027-abstractatlas-rename-ingestors/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: REQUIRED — behavior + contract change (CA-002). The rename is
verified by the full existing suite passing under new names + identical
fixture artifacts; the ingest work has failing-first unit tests
(registry/contract, LinkML validation, port fidelity).

**Organization**: US1 (rename) is the shippable MVP and is **foundational**
— US2 (ingestor architecture) and US3 (schema validation) build on the
renamed package and must follow it. Sequence: Setup → baseline → US1 → US2 → US3 → Polish.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: different files, no dependency on incomplete tasks
- Python paths under `src/abstractatlas/` (post-rename); tests under `tests/`

## Path Conventions

- Package: `src/abstractatlas/` (renamed from `src/ohbm2026/`)
- Ingest subpackage: `src/abstractatlas/ingest/{base,registry,schema,conference_ohbm,literature_neuroscape}.py`
- New tests: `tests/test_ingest_registry.py`, `tests/test_ingest_schema.py`, `tests/test_ingestor_ports.py`
- Run tests: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests` (venv-only, CA-001)

---

## Phase 1: Setup

- [x] T001 Refresh the repo-local venv and add the schema tool: `UV_CACHE_DIR=.uv-cache uv venv --python 3.14 .venv` (if needed) + `uv pip install --python .venv/bin/python linkml`. Confirm `linkml` validation tooling is importable (already used by `scripts/validate_ui_data.sh`).

---

## Phase 2: Foundational (Blocking Prerequisite for US1 verification)

**Purpose**: Capture a pre-rename baseline so the rename can be proven byte-identical (SC-001).

- [x] T002 Capture pre-rename baseline: run a small fixture subcommand under the CURRENT `ohbmcli` (e.g. `refresh-assets`/`title-audit` on a fixture, or an existing unit-covered path) and save its produced artifacts + `git rev-parse HEAD` to a scratch location outside version control, to diff against after the rename (SC-001). Record the current full-suite pass state (`PYTHONPATH=src .venv/bin/python -m unittest discover -s tests`) as the SC-002 baseline.

**Checkpoint**: baseline recorded — the rename can now be verified against it.

---

## Phase 3: User Story 1 - Rename with no behavior change (Priority: P1) 🎯 MVP

**Goal**: `ohbm2026`→`abstractatlas`, `ohbmcli`→`aacli`, everything behaves identically, data preserved.

**Independent Test**: `aacli <subcommand>` reproduces `ohbmcli <subcommand>` artifacts exactly; full suite green under new names; `import abstractatlas` works; legacy names emit labeled deprecation; no `data/**` path or published name changed.

### Implementation for User Story 1

- [x] T003 [US1] `git mv src/ohbm2026 src/abstractatlas`, then rewrite `ohbm2026`→`abstractatlas` across all imports/refs in `src/` (per `contracts/rename-map.md`). Do NOT touch data-identity strings in the rename-map "NOT renamed" table (data paths, state-keys, `ohbm2026.parquet`, `/ohbm2026/` route, `SITE_MODE='ohbm'`, `OHBM2026_*`).
- [x] T004 [US1] Update `pyproject.toml`: `name` `ohbm2026`→`abstractatlas`; `[project.scripts]` `ohbmcli`→`aacli = "abstractatlas.cli:main"`; rename `ohbm-*` entry points to `aa-*` where still used or drop them (record disposition per rename-map). Keep `package-dir`/`packages.find` under `src`.
- [x] T005 [US1] HARD CUTOVER — no deprecation shims (per requester). Remove the `ohbmcli` entry point (pyproject keeps only `aacli`), the legacy `ohbm-*` scripts, and rename all `ohbmcli` string literals in `src/` (argparse `prog=`, provenance `command_line`, help/error text) → `aacli`. Reinstall the venv package so a previously pip-installed `ohbm2026` dist is replaced by `abstractatlas` (`uv pip uninstall ohbm2026 && uv pip install -e .`), so `import ohbm2026` fails with `ModuleNotFoundError` and `ohbmcli` is `command not found` (FR-003/SC-007).
- [x] T006 [P] [US1] Rewrite `ohbm2026`→`abstractatlas` imports/refs across `tests/` and `scripts/`; update `PYTHONPATH=src -m ohbm2026.cli`→`-m abstractatlas.cli` in scripts + `.github/workflows/**` + `.githooks/`.
- [x] T007 [P] [US1] Update the few `ohbm2026` string refs in `site/src/**` tests that name the PACKAGE (not the `ohbm2026` data/route/site-mode identity). — VERIFIED NO-OP: audited `site/src` — every `ohbm2026` ref is data/route/storage-key identity (`/ohbm2026/` routes, `ohbm2026.parquet`, `ohbm2026.ui.*`/`ohbm2026.analytics.*` localStorage keys, conference `kind`); the TypeScript site never imports the Python package, so nothing to rename (2 stale comment path-mentions left as historical, like the src ones).
- [x] T008 [US1] Verify the rename: `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests` fully green (SC-002); re-run the T002 fixture under `aacli` and diff artifacts — identical (SC-001); `ohbmcli`/`import ohbm2026` emit the labeled deprecation and still succeed (SC-007); confirm an existing `data/cache/**` (or checkpoint) entry created before the rename is still discovered/reused — no forced recompute from the name change (Constitution III / spec edge case); `git grep -n 'ohbm2026\|ohbmcli'` returns only intentional data-identity names, shims, and historical spec docs.

**Checkpoint**: Rename landed + verified. Shippable MVP. US2/US3 build on this.

---

## Phase 4: User Story 2 - Pluggable ingestor architecture + port existing sources (Priority: P2)

**Goal**: A common `Ingestor` contract + runtime registry; OHBM + NeuroScape wrapped as the first two ingestors with byte-identical outputs and zero downstream change.

**Independent Test**: registry lists both ingestors; `get(unknown)` errors with the known list; each ingestor reproduces its prior normalized output; porting touched zero downstream stage logic.

### Tests for User Story 2 (write FIRST, ensure they FAIL) ⚠️

- [ ] T009 [P] [US2] Failing-first `tests/test_ingest_registry.py`: registry runtime-discovers registered ingestors (both ports present), `get(unknown)` raises `IngestorNotFound` listing known names, registration idempotent (contracts/ingestor-interface.md tests 1,5).
- [ ] T010 [P] [US2] Failing-first `tests/test_ingestor_ports.py`: `ConferenceOHBMIngestor.normalize` reproduces the prior OHBM normalized corpus byte-for-byte on a fixture (SC-003/SC-004); both ingestors expose correct `name`/`source_type`.

### Implementation for User Story 2

- [ ] T011 [US2] Add `src/abstractatlas/ingest/base.py`: `SourceType` enum + `Ingestor` ABC (`name`, `source_type`, `pull`, `normalize`, `ingest`) per contracts/ingestor-interface.md. Extend the (renamed) exception hierarchy with an `IngestError` subtree (`IngestorNotFound`, `IngestSchemaValidationError`).
- [ ] T012 [US2] Add `src/abstractatlas/ingest/registry.py`: runtime-discoverable name→Ingestor registry (`register`/`get`/`names`), no hardcoded source list (CA-007). Make T009 green.
- [ ] T013 [US2] Add `src/abstractatlas/ingest/conference_ohbm.py`: `ConferenceOHBMIngestor` (`name="ohbm-2026"`, conference) WRAPPING `fetch/stage.py` + `assets.normalize_abstract` (no logic rewrite). Register it. Make T010 green.
- [ ] T014 [US2] Add `src/abstractatlas/ingest/literature_neuroscape.py`: `LiteratureNeuroscapeIngestor` (`name="neuroscape-pubmed"`, literature_index). FIRST scout `atlas_package` (orchestrator + inputs) for a wrappable record-normalization seam — NeuroScape is a vendored release (HDF5/CSV), so a discrete `normalize` fn like `assets.normalize_abstract` may NOT exist. If a clean seam exists, wrap it; if not, scope this ingestor as a THIN adapter that reads the existing NeuroScape build inputs and emits `LiteratureDocument` records (documents the source without refactoring `atlas_package`) — do NOT rewrite `atlas_package` here (that would risk downstream drift and exceed the foundation scope). Register it either way.
- [ ] T015 [US2] Wire the CLI: `aacli ingest --source <name>` (runs a registered ingestor; unknown → precise error) + `aacli list-ingestors` (prints the runtime registry) per contracts/cli-aacli.md. Existing subcommands (`fetch-abstracts`, `build-atlas-package`) unchanged.
- [ ] T016 [US2] Verify zero downstream drift: confirm the diff for T011–T015 touches only `ingest/` + CLI wiring (no edits to `enrich/`, `embed/`, `analyze/`, `ui_data/`, `atlas_package/` stage logic — SC-004); full suite still green.

**Checkpoint**: Two sources are registered ingestors behind the common contract; runnable via `aacli ingest`.

---

## Phase 5: User Story 3 - Standardized LinkML ingest schema + validation (Priority: P3)

**Goal**: All ingestors validate emitted records against the LinkML schema; malformed records rejected loudly.

**Independent Test**: valid records pass; a malformed record is rejected with a precise, source-attributed error; the ported OHBM output validates unchanged.

### Tests for User Story 3 (write FIRST, ensure they FAIL) ⚠️

- [ ] T017 [P] [US3] Failing-first `tests/test_ingest_schema.py`: a valid `IngestedDocument`/`ConferenceDocument`/`LiteratureDocument` validates; a record missing a core field or with a source-type/class mismatch (conference carrying literature-only slots) is rejected with `IngestSchemaValidationError` naming source + field (contracts/ingestor-interface.md tests 2,3; edge case).

### Implementation for User Story 3

- [ ] T018 [US3] Add the schema `src/abstractatlas/ingest/ingest_schema.linkml.yaml` (from `contracts/ingest-schema.linkml.yaml`) and `src/abstractatlas/ingest/schema.py` (load + validate via the `linkml` validator, mirroring `scripts/validate_ui_data.sh`). Make T017 green.
- [ ] T019 [US3] Wire validation into `Ingestor.ingest()`: after `normalize`, validate each record against the schema; on failure raise the precise source-attributed error, do NOT write/pass downstream (FR-008). Attach `SourceProvenance` (ingestor/source_type/origin, no absolute/home paths — CA-008).
- [ ] T020 [US3] Verify the ported OHBM output validates against the schema unchanged (SC-003 — schema captures the existing shape, does not reshape); the malformed-record path errors loudly (SC-005).

**Checkpoint**: Every ingestor's output is schema-validated; downstream consumes one contract.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T021 [P] Update docs (FR-012): README + CLAUDE.md to `abstractatlas`/`aacli`; document the intentional `ohbm2026.parquet` (+ `/ohbm2026/` route, `SITE_MODE`) divergence; add an "add an ingestor" guide referencing the two ports as worked examples (SC-006).
- [ ] T022 Update naming references in `.specify/memory/constitution.md` (`ohbmcli`, `src/ohbm2026/`, `data/abstracts.json`) — coordinate with `/speckit-constitution` if a formal amendment is required (FR-012).
- [ ] T023 [P] Run the full suite `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests` + `cd site && pnpm exec vitest run` — all green; confirm published data is byte-identical / no re-publish needed (SC-003).
- [ ] T024 Run `.specify/scripts/bash/constitution-check.sh --full` and resolve any reported violations; final `git grep -n 'ohbm2026\|ohbmcli'` audit matches the rename-map "NOT renamed" + shims + historical specs only.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)** → **Foundational baseline (T002)** → **US1 rename (T003–T008)**.
- **US2 (T009–T016)** depends on US1 (builds in the renamed package).
- **US3 (T017–T020)** depends on US2 (validates the ingestors' output; `ingest()` calls the validator).
- **Polish (T021–T024)** after US1–US3.

### Within Each Story

- US1: `git mv`+rewrite (T003) → pyproject (T004) → shims (T005) → tests/scripts/CI + site (T006/T007) → verify (T008). T006/T007 are [P] (different trees).
- US2: failing tests (T009/T010, [P]) FIRST → base (T011) → registry (T012) → ports (T013/T014) → CLI (T015) → drift check (T016).
- US3: failing test (T017) FIRST → schema+validator (T018) → wire into ingest() (T019) → verify (T020).

### Parallel Opportunities

- T006 ∥ T007 (tests/scripts/CI vs site). T009 ∥ T010; T021 ∥ T023.
- Note: the T003 mechanical rewrite is a single large atomic edit — not parallelizable with T004/T005 (same files/pyproject).

---

## Implementation Strategy

### MVP (US1 only) — shippable on its own

1. Setup + baseline (T001–T002).
2. Rename (T003–T007) → verify identical + green (T008).
3. **STOP and VALIDATE**: `aacli` reproduces `ohbmcli`; suite green; data untouched. This alone is a coherent, shippable rename.

### Incremental delivery

4. US2 → ingestor architecture + two ports (runnable `aacli ingest`).
5. US3 → schema validation gate.
6. Polish → docs, constitution refs, full audit.

Each story is a separate reviewable slice; US1 can ship before US2/US3 land.

---

## Notes

- Venv-only Python throughout (CA-001); commit per verified slice (rename; ingest arch; ports; schema; docs) and push.
- **Data preservation is the hard constraint** (FR-004): never touch `data/**` paths, state-keys, `ohbm2026.parquet`, the `/ohbm2026/` route, `SITE_MODE='ohbm'`, or `OHBM2026_*` — those are source/deploy identity, not the component name.
- Ingestors WRAP existing normalization; they must not rewrite it (guarantees byte-identical outputs + zero downstream change).
- No data regeneration, no site re-publish; byte-identical guarantee preserved.
- Fail loudly: unknown ingestor, schema-validation failure, and legacy-name use all raise precise typed errors — never silent/partial success.
