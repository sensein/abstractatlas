# Implementation Plan: Multi-Source Ingest Foundation (Arc A)

**Branch**: `claude/abstract-atlas-architecture-review-rp9ob9` · **Spec**: `./spec.md`

## Summary

Introduce the source-neutral seam the pipeline lacks — a typed
`AbstractRecord` with global identity (`record_uid = "<source>:<native_id>"`)
and provenance, plus an `AbstractSource` interface — and prove it with a
concrete non-OHBM source (`BiorxivSource`). Additive and inert: the OHBM
`fetch/` + `assets.py` ingest and the NeuroScape loader are untouched in this
slice. This is Arc A of the three-arc roadmap from the architecture review; it
is the precondition for Arc B (pluggable embedding/projection, which #66 shows
is needed because the NeuroScape-64d projector failed) and for the knowledge-
graph and frontend arcs.

## Technical context

- **Language/runtime**: Python ≥3.11 via `.venv/bin/python` (Principle I).
- **New package**: `src/ohbm2026/sources/` (`base.py`, `biorxiv.py`,
  `__init__.py`). Stdlib only (`urllib`, `hashlib`, `dataclasses`, `typing`).
- **Errors**: `SourceError(OhbmStageError)` → `SourceNormalizationError`,
  mirroring the Stage 1/2/3 subtrees in `exceptions.py`.
- **Tests**: `tests/test_sources_base.py`, `tests/test_sources_biorxiv.py`
  (`unittest`, offline via injected `fetch_page`).

## Constitution check

| Principle | How satisfied |
| --- | --- |
| I venv-only | venv created; all runs via `.venv/bin/python` |
| II immutable evidence / no committed data | code + tests only; no `data/` writes |
| III resumable/auditable | `fetched_at` injected (no inline clock); deterministic `raw_digest` |
| IV plan/test-first | tests written first, confirmed failing, then implemented |
| V secret-safe | public unauthenticated API; no secrets |
| VI fail loudly | typed `SourceNormalizationError`; no bare except / silent skip |
| VII discover external state | bioRxiv fields + pagination discovered per-payload |
| VIII provenance | every record carries `SourceProvenance` (CA-008), no abs paths |

## Phases

### Phase 1 — Landed (this slice)

1. `sources/base.py` — record, value types, identity/digest helpers,
   Protocol + `BaseAbstractSource`, exceptions. ✅
2. `sources/biorxiv.py` — `BiorxivSource` (injectable fetch, cursor
   pagination, loud normalization). ✅
3. Tests first (23 cases), green. ✅
4. This spec set (`spec/research/data-model/contracts/quickstart/plan`). ✅

### Phase 2 — Adapt the incumbents (FR-008, next spec)

5. `OhbmSource` adapter over `assets.normalize_abstract` → `AbstractRecord`
   (map `poster_id`→`display_id`, `responses` by `question_name`→`sections`).
6. `NeuroScapeSource` adapter over `ArticleHeader` → `AbstractRecord`.
7. Both assert byte-stability of existing on-disk artifacts (no regression).

### Phase 3 — Corpus dimension in paths/state-keys (FR-009, next spec)

8. Add `source`/`conference` to `artifacts.build_dependency_basis` and the
   path builders (`data/primary/<source>/…`).
9. Replace one-corpus-per-tree guards (`analyze/stage.py:158-162`,
   `ui_data/state_key.py:85-90`) with one-per-source guards.

### Later arcs (separate specs, out of scope here)

- **Arc B**: pluggable embedder/projector; land a natively-aligned embedder so
  new abstracts no longer require Voyage + a fragile learned projection into
  NeuroScape's fixed 64-dim space.
- **KG arc**: converge ECO claims + Stage-23 dimensions + structsense onto a
  graph schema keyed by `record_uid` (BioCypher-style).
- **Frontend arc**: per-site config registry to collapse the ~186
  `SITE_MODE ===` conditionals; decompose the 2,500-line `+page.svelte`.

## Risks

- **Sequencing**: adding a 3rd conference through the current `atlas_package`
  path (two-corpus enumeration tuples that `raise` on an unexpected parquet)
  would harden the debt. Do Phases 2–3 first (research.md R7).
- **API drift**: bioRxiv payload shape is discovered per-payload, so drift
  surfaces as `SourceNormalizationError`, not a silent skip.
