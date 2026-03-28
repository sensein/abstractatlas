# Implementation Plan: Refactor Shared Utils And Cache Governance

**Branch**: `001-refactor-cache-utils` | **Date**: 2026-03-28 | **Spec**: [/Users/satra/software/temp/ohbm2026/specs/001-refactor-cache-utils/spec.md](/Users/satra/software/temp/ohbm2026/specs/001-refactor-cache-utils/spec.md)
**Input**: Feature specification from `/specs/001-refactor-cache-utils/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See
`.specify/templates/plan-template.md` for the execution workflow.

## Summary

Introduce a shared artifact-governance layer for expensive workflows so the
repository can classify GraphQL-fetched inputs, resumable caches, and
regenerable outputs consistently. The implementation will extract reusable path
and metadata helpers, store fetched abstract inputs under `data/inputs/`, move
resumable caches to deterministic `data/cache/` locations, group outputs under
`data/outputs/experiments/`, `data/outputs/exported-sites/`, and
`data/outputs/proposals/`, keep all of those locations gitignored, and define
direct lookup plus invalidation rules for enrichment, reference metadata,
embedding-manifest, exported-site, and proposal-adjacent flows.

## Technical Context

**Language/Version**: Python 3.11+  
**Primary Dependencies**: Python standard library (`argparse`, `pathlib`, `json`, `hashlib`, `datetime`), existing `ohbm2026` pipeline modules, NumPy-backed downstream consumers already present in the repo  
**Storage**: Local JSON/filesystem artifacts under ignored `data/`, `export/`, `tmp/`, and experiment directories  
**Testing**: `unittest` via `PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v`, plus targeted path/ignore/metadata tests  
**Target Platform**: Local macOS/Linux command-line environments using the repository-local `.venv`  
**Project Type**: Python CLI/data-pipeline project with operator-facing filesystem contracts  
**Performance Goals**: Compute cache/output paths directly from artifact family and state key without directory scans; resume expensive work without recomputing unaffected artifacts; keep lookup overhead negligible relative to the expensive workflow itself  
**Constraints**: Preserve canonical raw-data traceability while introducing `data/inputs/` for GraphQL-fetched abstract snapshots; do not commit `data/inputs/`, `data/cache/`, `data/outputs/`, `export/`, or scratch outputs to git; keep credentials out of cache metadata; keep current CLI behavior backward-compatible or documented when defaults move; use `.venv` for all Python execution  
**Scale/Scope**: First slice covers shared artifact utilities and the highest-leverage expensive workflows currently centered in `assets.py`, `enrichment.py`, `openalex.py`, `neuroscape.py`, `poster_layout.py`, `poster_sequencing.py`, and `ui.py`, with matching test and doc updates

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Pre-design gate status: PASS
- Post-design gate status: PASS
- Python execution uses the repository-local `.venv/bin/python` interpreter, or
  `uv` explicitly targeting that interpreter; no system Python steps appear in
  the design artifacts.
- Verification is defined first: add shared artifact utility tests plus focused
  regression coverage for enrichment, reference metadata, manifest, exported
  site, and proposal lookup behavior before implementation changes land.
- Output paths preserve auditability by keeping canonical raw data immutable,
  storing fetched GraphQL input snapshots under `data/inputs/`, moving resumable
  caches to deterministic `data/cache/` locations, and moving regenerable
  derived artifacts to deterministic `data/outputs/` families.
- Git hygiene is explicit: `data/`, `data/inputs/`, `data/cache/`,
  `data/outputs/`, `export/`, and scratch outputs stay uncommitted, and the
  implementation includes checks that these paths remain ignored.
- Secret boundaries remain outside the repo: cache metadata records env-var
  names, model identifiers, and state keys, never token values.
- README/docs/plan updates are part of scope because default paths and operator
  recovery guidance will change.
- The implementation closes with local verification, a descriptive commit, and a
  push, consistent with the constitution.

## Project Structure

### Documentation (this feature)

```text
specs/001-refactor-cache-utils/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── artifact-layout.md
│   └── cache-metadata.md
└── tasks.md
```

### Source Code (repository root)

```text
src/ohbm2026/
├── assets.py
├── cli.py
├── enrichment.py
├── openalex.py
├── neuroscape.py
├── poster_layout.py
├── poster_sequencing.py
├── ui.py
└── artifacts.py              # new shared artifact/cache/input/output utility module

tests/
├── test_artifacts.py         # new shared utility and path-resolution coverage
├── test_assets.py
├── test_enrichment.py
├── test_openalex.py
├── test_neuroscape.py
├── test_poster_layout.py
├── test_poster_sequencing.py
└── test_ui.py

docs/
├── reproducibility-vision.md
└── README.md

.gitignore
README.md
```

**Structure Decision**: Keep the existing single-project Python layout and add a
single shared artifact-governance module rather than scattering new helpers
across the already-large workflow files. The first implementation slice updates
the highest-cost workflow entrypoints to depend on that shared layer while
preserving their domain logic in place.

## Complexity Tracking

No constitution violations are expected for this design. The planned complexity
is intentionally limited to one reusable artifact-governance layer plus
targeted integration updates for existing expensive workflows.
