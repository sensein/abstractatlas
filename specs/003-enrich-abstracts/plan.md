# Implementation Plan: Stage 2 — Enrich Abstracts (Figures, Claims, References)

**Branch**: `003-enrich-abstracts` | **Date**: 2026-05-13 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/003-enrich-abstracts/spec.md`

## Summary

Stage 2 reads the Stage-1-produced accepted corpus
(`data/primary/abstracts.json`) and produces a compact, randomly-
accessible enriched corpus at `data/primary/abstracts_enriched.sqlite`
plus a machine-readable provenance sidecar. Three independent
enrichment components — **figure interpretation** (vision LLM over
local methods/results figure assets), **claims extraction** (LLM over
markdown-converted abstract text), and **reference resolution**
(multi-backend DOI / PMID / OpenAlex / Semantic Scholar) — run with
per-component caching keyed by `(content_hash, model_id)`. Changing
one component's model identifier invalidates only that component;
the other two reuse cache hits intact.

The Phase 0 benchmark (research.md §1) measured six candidate
storage formats on the actual 3333-record enriched corpus. **SQLite
with per-row zlib-compressed JSON blob** won decisively: 21 MB on
disk (64% smaller than verbose JSON), 0.09 ms average random-access
lookup, stdlib-only (`sqlite3` + `zlib`). Sequential reads stay
comparable to JSONL (~240 ms for the full corpus). This format
satisfies FR-009 (single file, O(1) random by ID, compact), SC-006
(under 10 ms random lookup — observed 0.09 ms, 100× margin), and
SC-007 (at least 30% smaller than verbose JSON — observed 64%).

The Stage-1 per-stage pattern (input / output / provenance / error /
resumability / discovery contracts) applies unchanged. Stage 2 is
the canonical multi-component reference instance of the pattern.

No new third-party dependencies. The orchestrator reuses
`enrichment.py` building blocks (figure analysis, claim extraction,
reference resolution) but wires them through Stage 2's contracts —
the heavyweight refactor of `enrichment.py` itself is OUT of scope
per spec Future Work.

## Technical Context

**Language/Version**: Python 3.11.
**Primary Dependencies**: stdlib only for the new orchestrator
  (`sqlite3`, `zlib`, `hashlib`, `json`, `dataclasses`, `argparse`,
  `pathlib`, `tempfile`, `os`). Existing modules: `ohbm2026.artifacts`,
  `ohbm2026.exceptions`. The heavyweight enrichment building blocks
  already live in `ohbm2026.enrichment` (figure analysis, claim
  extraction) and `ohbm2026.openalex` (reference resolution); Stage 2
  wires them rather than rewriting.
**Storage**:
  - Enriched corpus: SQLite at `data/primary/abstracts_enriched.sqlite`
    with one row per abstract, primary key = `id`, payload column =
    zlib-compressed JSON of the enriched record. Stdlib only.
  - Provenance: JSON at
    `data/inputs/abstracts_enrich_provenance__<state-key>.json`.
  - Per-component caches: existing
    `data/cache/figure_analysis/`, `data/cache/claim_analysis/`,
    and a new `data/cache/reference_metadata/` namespace.
**Testing**: existing `unittest` suite under `tests/`; new modules
  follow the patching patterns established in `test_fetch_stage.py`.
**Target Platform**: macOS / Linux developer workstations and CI.
**Project Type**: single-project Python CLI + library (same as Stage 1).
**Performance Goals**:
  - Random lookup by abstract ID: under 10 ms (SC-006). Benchmark
    measured 0.09 ms, ample headroom.
  - Storage: at least 30% smaller than verbose JSON (SC-007).
    Benchmark measured 64% reduction.
  - Sequential scan of all records: under 1 second for the full
    corpus (no SC, but informally tracked; benchmark measured
    ~240 ms).
**Constraints**:
  - Accepted-corpus only (FR-002); withdrawn corpus is read-only
    input to Stage 1, not enriched here.
  - Per-component cache invalidation MUST be independent (FR-005).
  - Idempotency on unchanged inputs + unchanged models (FR-006).
  - Movement between accepted and withdrawn across runs handled
    idempotently (FR-008); cache entries SURVIVE for dropped
    abstracts so future restoration is cheap.
  - No new third-party deps.
**Scale/Scope**: 3244 accepted abstracts (current OHBM 2026 state);
  ~4800 figure assets; each abstract has 0–30 references and 0–10
  claims. Enriched corpus payload per abstract: ~5–30 KB before
  zlib, ~1–6 KB after.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Python execution uses `.venv/bin/python` or `uv` targeting it;
  no system Python.** PASS — FR-013, CA-001.
- **Verification named first; expected to fail or be missing before
  implementation.** PASS — every user story has acceptance scenarios
  that become test cases; the tasks.md (Phase 2 output) will land
  test files in their own phase before the implementation modules.
- **Output paths preserve auditability; canonical raw data not
  silently rewritten; recorded outputs go to fresh directories.**
  PASS — enriched corpus at a single canonical path; provenance
  sidecar per run uses a state-key namespace. Stage 1 outputs are
  read-only inputs (FR-015).
- **All generated artifacts land in gitignored roots; no new tracked
  artifact root.** PASS — `data/primary/`, `data/inputs/`,
  `data/cache/` are already gitignored.
- **Error handling is explicit and loud; no bare excepts, silent
  fallbacks, or verification-gate bypasses.** PASS — FR-010 + CA-006
  enumerate every failure mode; typed exception hierarchy mirrors
  Stage 1 (Stage2Error + subclasses).
- **External-state dependencies discovered at runtime; mismatches
  surface as precise errors, not silent skips.** PASS — CA-007
  applies to two surfaces: LLM response schemas (parsed against
  expected shape; mismatch raises) and backend-availability matrix
  (which API keys present, which optional deps installed).
- **Organizer-facing outputs ship machine-readable provenance with
  no absolute or user-home paths.** PASS — FR-007, CA-008. The
  enriched corpus is secondary data that IS organizer-facing
  (downstream of every UI / poster artifact); the provenance record
  follows the Stage 1 contract exactly.
- **Secrets in `.env` or env vars only; named, not embedded.** PASS
  — CA-004. `env_vars_consulted` in provenance lists names only.
- **README/docs/plan updates included when defaults/commands change.**
  PASS — FR-016 + CA-003.
- **Delivery commits each verified slice with descriptive message;
  pushed once requested change is complete.** PASS — same cadence
  as Stage 1.

**Result: no violations. No Complexity Tracking rows required.**

## Project Structure

### Documentation (this feature)

```text
specs/003-enrich-abstracts/
├── plan.md              # This file (/speckit.plan output)
├── research.md          # Phase 0 — design decisions + storage benchmark
├── data-model.md        # Phase 1 — entity field-level schemas
├── quickstart.md        # Phase 1 — operator how-to-run Stage 2
├── contracts/           # Phase 1
│   ├── cli.md
│   ├── enriched_record.schema.json
│   ├── enrich_provenance.schema.json
│   └── cache_entry.schema.json
├── spec.md              # /speckit-specify output (already on disk)
├── checklists/
│   └── requirements.md  # spec quality checklist
└── tasks.md             # /speckit-tasks output — NOT created here
```

### Source Code (repository root)

```text
src/ohbm2026/
├── enrich_stage.py         # NEW — Stage 2 orchestrator: entry point,
│                           #   per-component cache + invocation,
│                           #   SQLite-write with zlib payload,
│                           #   provenance writer, movement-aware
│                           #   accepted-corpus → enriched-corpus diff.
├── enrich_storage.py       # NEW — small SQLite read/write helper
│                           #   (write_enriched_corpus, read_one_by_id,
│                           #   iter_enriched). Pure I/O; no orchestration.
├── enrichment.py           # extended: signatures stable; reused by
│                           #   enrich_stage as the heavyweight building
│                           #   blocks for figures + claims. No refactor
│                           #   of the oversized module here (Future Work).
├── openalex.py             # extended: signature stable; reused for
│                           #   the reference-resolution component.
├── exceptions.py           # extended: add Stage2Error + subclasses
│                           #   (EnrichmentError, CacheVersionError,
│                           #   ComponentFailureThresholdError).
├── artifacts.py            # extended: build_enriched_corpus_path,
│                           #   build_enrich_provenance_path,
│                           #   build_enrich_cache_path(component, key).
└── cli.py                  # `enrich`, `analyze-figures`, `extract-claims`,
                            #   `reference-metadata` REMOVED;
                            #   `enrich-abstracts` ADDED (FR-014).

scripts/
└── run_enrich_abstracts.py # NEW — thin wrapper documenting the
                            #   canonical re-run command shown in README.

tests/
├── test_enrich_stage.py     # NEW — six-contract coverage:
│                            #   input, output, provenance, error,
│                            #   resumability, discovery. US1..US4
│                            #   acceptance scenarios.
├── test_enrich_storage.py   # NEW — SQLite read/write helper:
│                            #   round-trip, zlib correctness, O(1)
│                            #   random by id, sequential iteration.
├── test_enrichment.py       # augmented: stable building-block
│                            #   contracts the orchestrator depends on.
├── test_openalex.py         # augmented: reference-resolution helper
│                            #   contracts the orchestrator depends on.
└── test_cli.py              # augmented: `enrich-abstracts` wiring,
                             #   removal of the four legacy subcommands.

docs/
└── per-stage-pattern.md     # extended: Stage 2 now also cited as the
                             #   multi-component reference instance
                             #   (Stage 1 covered single-fetch).
```

**Structure Decision**: single Python project under `src/ohbm2026/`,
matching Stage 1. Two new modules: `enrich_stage.py` (orchestrator)
and `enrich_storage.py` (SQLite I/O — kept separate so the storage
contract is independently testable and swappable if a future spec
revisits the format choice).

`enrichment.py` and `openalex.py` are NOT refactored in this round
(per spec Future Work) — they remain heavyweight but are wrapped
behind clean function signatures the orchestrator depends on. The
heavyweight modules' tests are augmented only to pin the contracts
the orchestrator relies on, not to split or restructure them.

## Complexity Tracking

> Constitution Check passes with no violations. No rows required.
