# Implementation Plan: Abstract Atlas Rename + Pluggable LinkML Ingestors

**Branch**: `027-abstractatlas-rename-ingestors` | **Date**: 2026-07-02 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/027-abstractatlas-rename-ingestors/spec.md`

## Summary

Two coupled changes, sequenced so the risky-but-mechanical part lands and
is verified before the additive part:

1. **Rename** the Python component `ohbm2026` → `abstractatlas` and the CLI
   `ohbmcli` → `aacli` (plus the legacy `ohbm-*` entry points), updating
   every import, string reference, doc, and test — while **preserving all
   on-disk artifact paths, state-key/cache naming, and published
   data-package names** (incl. `ohbm2026.parquet`) so no data is
   regenerated and the live site needs no re-publish (byte-identical).
2. **Generalize ingestion** into a pluggable architecture: a new
   `abstractatlas/ingest/` subpackage with an `Ingestor` contract + a
   runtime-discoverable registry, and a **standardized LinkML ingest
   schema** (common core + per-source-type extensions) that every ingestor
   validates against. The two existing sources — the OHBM conference
   (Oxford Abstracts, via `fetch/` + `assets.normalize_abstract`) and the
   PubMed/NeuroScape corpus (via `atlas_package` inputs) — are **wrapped**
   as the first two ingestor instances *without changing their outputs* or
   any downstream stage.

New source ingestors (arXiv/bioRxiv/medRxiv, other conferences) are
explicitly out of scope — the foundation makes them straightforward
follow-on specs.

## Technical Context

**Language/Version**: Python 3.14 via repo-local `.venv` (uv-managed); TypeScript site is only touched for a handful of `ohbm2026` string refs in tests
**Primary Dependencies**: existing (Oxford Abstracts GraphQL client, OpenAI, boto3, pyarrow, hyparquet on the site); **LinkML** for the ingest schema + validation (already the schema language for UI/export contracts — `specs/008/010/012/*.linkml.yaml`, validated via `scripts/validate_ui_data.sh`)
**Storage**: unchanged — `data/primary/`, `data/cache/`, `data/outputs/`, published parquet names all preserved (FR-004)
**Testing**: `.venv/bin/python -m unittest discover -s tests` (renamed test imports) + new unit tests for the ingestor registry/contract and LinkML validation; site `vitest run` for the few renamed string refs
**Target Platform**: local pipeline (CLI) + static site; no runtime/platform change
**Project Type**: Python package + CLI (Track A canonical pipeline) with a coupled SvelteKit site
**Performance Goals**: none changed — the rename is behavior-preserving; the ingestor wrap adds a validation pass over already-normalized records (bounded, one-time per ingest run)
**Constraints**: byte-identical published data (no re-publish); zero downstream-stage behavior change for existing sources; legacy names fail loudly or via a labeled-deprecated alias (no partial success)
**Scale/Scope**: ~86 Python files reference `ohbm2026`; ~15 `ohbm-*` entry points + `ohbmcli`; 3 governance/doc surfaces (README, CLAUDE.md, constitution) + a few site test strings; 2 sources ported

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Venv-only Python** — all commands run through `.venv/bin/python` / `uv`; the rename updates `PYTHONPATH=src -m ohbm2026.cli` → `-m abstractatlas.cli` in docs/CI, still venv-scoped. PASS.
- **Immutable evidence / no committed data** — the rename **preserves** raw + derived artifact paths and published data names; no data is rewritten or regenerated; artifact roots stay gitignored. This is the central FR-004 guarantee. PASS.
- **Resumable pipelines** — state-key/cache/checkpoint keys are preserved verbatim, so prior expensive work is still discovered and reused after the rename (edge case). PASS.
- **Plan-first, test-first** — spec + this plan precede code; verification identified: full suite passes under new names (SC-002), ingestor/registry + LinkML-validation tests added failing-first (CA-002). PASS.
- **Secret-safe** — no credential change; env-var names for Oxford Abstracts / OpenAI / data host unchanged; commit in verified slices. PASS.
- **Fail loudly, no shortcuts** — schema-validation failures, unknown-ingestor lookups, and legacy-name usage raise precise typed errors (no silent skip/partial success); no `--no-verify`/skipped tests to force the rename green. PASS.
- **Discover external state** — the ingestor registry is runtime-discovered from registration/metadata, never a hardcoded source allow-list; unknown source → precise error naming what was searched (FR-010/CA-007). PASS.
- **Provenance** — each ingested record carries source/ingestor provenance; existing artifact provenance is preserved and remains interpretable; no absolute/home paths (FR-011/CA-008). PASS.
- **Docs in same change** — README, CLAUDE.md, and the constitution's naming references updated in the same change (FR-012); constitution naming refs coordinated with `/speckit-constitution` where an amendment is required. PASS.
- **Commit per slice + push** — sequenced commits: (a) rename, (b) ingest package + registry + schema, (c) two ports, (d) docs; push the branch. PASS.

No violations. Complexity is high (blast radius) but not a constitution violation → Complexity Tracking notes the sequencing risk, not a gate failure.

## Project Structure

### Documentation (this feature)

```text
specs/027-abstractatlas-rename-ingestors/
├── plan.md              # This file
├── spec.md              # Feature spec
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── rename-map.md            # old→new name mapping (package, CLI, entry points, docs) + legacy-alias policy
│   ├── ingestor-interface.md    # the Ingestor contract + runtime registry
│   ├── ingest-schema.linkml.yaml # the standardized ingest schema (core + per-source extensions)
│   └── cli-aacli.md             # renamed command surface + deprecation behavior
└── checklists/
    └── requirements.md
```

### Source Code (repository root)

```text
src/abstractatlas/                 # RENAMED from src/ohbm2026/ (all modules moved, imports rewritten)
├── cli.py                         # dispatch unchanged in behavior; module path renamed
├── ingest/                        # NEW subpackage
│   ├── base.py                    #   Ingestor ABC/Protocol (pull → normalize → validated records) + source-type enum
│   ├── registry.py                #   runtime-discoverable name→ingestor registry (VII)
│   ├── schema.py                  #   loads + validates against contracts/ingest-schema.linkml.yaml
│   ├── conference_ohbm.py         #   wraps fetch/stage.py + assets.normalize_abstract (source: oxford-abstracts)
│   └── literature_neuroscape.py   #   wraps the NeuroScape/PubMed record normalization (source: pubmed-neuroscape)
├── fetch/  assets.py  enrich/  embed/  analyze/  ui_data/  atlas_package/  atlas_hosting/  book/  layout/  util/  data/  exceptions.py  artifacts.py  titles.py  standby.py
│                                  # all preserved; imports rewritten ohbm2026.* → abstractatlas.*

tests/                             # imports rewritten; behavior-identical
├── test_ingest_registry.py        # NEW — registry runtime discovery + unknown-source error
├── test_ingest_schema.py          # NEW — LinkML validation accepts valid / rejects malformed (loud)
└── test_ingestor_ports.py         # NEW — OHBM + NeuroScape ingestors reproduce prior normalized output

pyproject.toml                     # name ohbm2026→abstractatlas; scripts ohbmcli→aacli, ohbm-*→aa-* (or dropped); package-dir find
README.md, CLAUDE.md, .specify/memory/constitution.md   # naming references updated (FR-012)
site/src/**                        # only ohbm2026 string refs in a few tests updated
```

**Structure Decision**: Keep the existing module layout intact under the
renamed package (a move + import rewrite, not a re-architecture) so the
rename stays mechanical and diff-reviewable. Ingestion generalization is
**additive**: a new `abstractatlas/ingest/` subpackage introduces the
contract, registry, and schema, and *wraps* the existing OHBM and
NeuroScape normalization rather than rewriting it — guaranteeing byte-
identical outputs and zero downstream change (SC-003/SC-004/FR-009). The
published parquet keeps the historical `ohbm2026.parquet` name (documented
divergence, FR-004).

## Complexity Tracking

> No Constitution Check violations. Recorded here: the rename's large blast
> radius (~86 files) is the main risk. Mitigation: land the rename as an
> isolated, mechanical, fully-verified slice (SC-001 identical artifacts +
> SC-002 full suite green) BEFORE the additive ingestor work, so a rename
> regression can't be confused with an architecture regression.

| Risk | Why it's needed | Mitigation |
|------|-----------------|------------|
| Package/CLI rename touches ~86 files + entry points + docs + CI | The whole ask is re-framing the component name away from a single instance | Mechanical move + import rewrite in one slice; verify identical artifacts + full suite before any ingestor change; preserve all data names |
| Ingestor wrap could drift OHBM/NeuroScape outputs | Multi-source needs a common contract | Wrap (not rewrite) existing normalization; port test asserts byte-identical prior output |
