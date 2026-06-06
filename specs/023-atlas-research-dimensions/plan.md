# Implementation Plan: Atlas Research-Classification Dimensions

**Branch**: `023-atlas-research-dimensions` | **Date**: 2026-06-05 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `specs/023-atlas-research-dimensions/spec.md`

## Summary

Ingest four externally-computed research-classification dimensions (`focus`,
`research_modality`, `theory_scope`, `epistemic_basis`) — Mario's "NeuroScape
dimension analysis" output, supplied as `abstracts.detail.json` keyed by Oxford
submission id — and surface them in the `/ohbm2026/` atlas as new per-abstract
**computed insights** and **filterable facets**.

The integration is a clean left-join inside the existing Stage 6 UI-data
builder: `ui_data/abstracts.iter_abstracts` already yields each exported
record with its Oxford `abstract_id` (the join key) and a per-record `facets`
dict. We add the four dimensions as four more list-of-string entries in that
`facets` dict, keyed off `abstract_id`. Because `iter_abstracts` only iterates
the *accepted, deduped, exported* corpus, the join is inherently one-
directional (Clarification 1): dimension-file entries with no matching
exported abstract are counted and logged, never added. From there the four
keys ride the existing facet machinery: the parquet `facets` STRUCT, the
manifest's discovered facet catalog, and the site's generic facet loader. The
only edits are (a) widening four fixed key tuples/labels on the Python side,
(b) adding the four keys to the site's `facets.ts` constants, and (c) adding
four labelled chip blocks to `DetailPanel.svelte`'s computed-insights zone.

No new pipeline stage, no new credentials, no parquet *schema* break (the
`facets` LinkML slot is already `range: Any`), and no change to atlas-root /
neuroscape (they don't consume `ohbm2026.parquet`'s facets).

## Technical Context

**Language/Version**: Python 3.14 (`.venv/bin/python`); TypeScript/Svelte 5 (SvelteKit) for `site/`
**Primary Dependencies**: pyarrow (parquet emit), stdlib json; site: hyparquet decoder, Vitest, Playwright
**Storage**: gitignored inputs under `data/inputs/neuroscape-dimensions/` — full `abstracts.detail.json` (distiller input) → slim `dimensions.slim.json` (build input); output `ohbm2026.parquet` (gitignored, Dropbox/R2-hosted at runtime)
**Testing**: `PYTHONPATH=src .venv/bin/python -m unittest` for Python; `pnpm exec vitest run` + Playwright for site
**Target Platform**: static gh-pages SvelteKit site (`/ohbm2026/`); local build pipeline
**Project Type**: data pipeline + static web app (existing two-track repo)
**Performance Goals**: build adds one ~120 MB JSON read + an in-memory dict join (~3.3 K records) — sub-second overhead; no UI runtime cost beyond 4 more facet columns in the abstracts STRUCT
**Constraints**: deterministic rebuild (byte-identical for unchanged inputs — Invariant 6 / `DETERMINISTIC_MTIME`); fail-loud on missing/malformed input; no absolute paths in provenance
**Scale/Scope**: 3333 OHBM 2026 abstracts; 4 dimensions; ~2–7 categorical labels each (vocabulary discovered, not curated)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Venv execution**: ✅ All Python runs via `.venv/bin/python` / `uv` targeting it (build CLI, tests). No system Python.
- **Verification-first**: ✅ Plan names the failing tests to add first (see Phase 1 / quickstart): `tests/test_ui_data_dimensions.py` (distiller full→slim determinism + layout-mismatch error, slim load + coverage + missing-file error + unmatched-id report), extend `tests/test_ui_data_abstracts.py` (facets carry the 4 keys) + `tests/test_ui_data_manifest.py` (4 facets discovered) + `tests/test_ui_data_parquet_single.py` (STRUCT carries 4 keys); site `facets.test.ts` (valuesFor + counts for new keys) + a Playwright detail/facet check. All fail before implementation (the keys don't exist yet).
- **Auditability / immutable evidence**: ✅ Canonical `abstracts.json` is not rewritten. The dimension file is a read-only side input; the build re-emits `ohbm2026.parquet` (rebuild-in-place is the existing Stage 6 contract, deterministic mtime preserved).
- **Gitignored artifacts**: ✅ Input lands under `data/inputs/neuroscape-dimensions/` (`data/inputs/` already gitignored, `.gitignore:8`). The 121 MB raw file is never committed. Output parquet under `data/` (gitignored).
- **Fail loudly**: ✅ New typed `DimensionInputError(Stage6BuildError)`; precise errors for missing-when-enabled, unreadable, malformed-shape, missing expected dimension fields, non-resolvable join key. No bare except, no silent fallback, no gate bypass.
- **Discover external state**: ✅ The four dimension field names and the join-key field are discovered/validated against the file at runtime (CA-007); a file missing the expected dimension fields or join key surfaces a precise error rather than matching a hardcoded layout. Category vocabulary is discovered from the data (FR-004), not enumerated in code.
- **Provenance**: ✅ The data package's machine-readable provenance is the manifest (`build_info` + manifest table, co-located in `ohbm2026.parquet`). We extend the manifest with a `research_dimensions` provenance block: source filename + sha256 (NOT an absolute/home path), per-dimension matched count, abstracts-with-no-value count, and unmatched-in-file count.
- **Secrets**: ✅ None introduced. The dimension file is local operator input; no env vars, no tokens.
- **Docs in same change**: ✅ Update `CLAUDE.md` (default-pipeline + artifact-layout notes, SPECKIT plan pointer), `README.md` (new `--dimensions` build flag + input location), the LinkML `facets` slot description (11 → 15 lists), and this spec's quickstart.
- **Commit slices + push**: ✅ Delivery commits each verified slice (loader+tests, builder wiring, parquet/manifest/types, site facets, site detail, docs) and pushes; a `deploy-production` label gates the live cutover per existing workflow.

**Result: PASS — no violations. Complexity Tracking not required.**

## Project Structure

### Documentation (this feature)

```text
specs/023-atlas-research-dimensions/
├── plan.md              # This file
├── spec.md              # Feature spec (+ Clarifications)
├── research.md          # Phase 0 — integration-point + join-key decisions
├── data-model.md        # Phase 1 — dimension entity, facet/provenance shapes
├── quickstart.md        # Phase 1 — build + test invocations
├── contracts/
│   ├── dimension-input.md       # Input file shape + load/validate contract
│   └── facets-and-detail.md     # Facet + DetailPanel UI contract
├── checklists/
│   └── requirements.md  # Spec quality checklist (from /speckit-specify)
└── tasks.md             # Phase 2 — created by /speckit-tasks (NOT here)
```

### Source Code (repository root)

```text
src/ohbm2026/ui_data/
├── dimensions.py        # NEW — distill_dimensions() (full→slim), load_research_dimensions()
│                        #       (reads slim), DIMENSION_KEYS/LABELS,
│                        #       compute_dimension_coverage(), DimensionInputError
├── abstracts.py         # EDIT — iter_abstracts/build_abstracts/build_abstracts_records:
│                        #        new `research_dimensions` param; inject 4 lists into facets
├── manifest.py          # EDIT — add 4 keys to FACET_KEYS + FACET_LABELS;
│                        #        embed research_dimensions provenance block
├── builder.py           # EDIT — load dimensions once, compute coverage vs exported
│                        #        submission ids, thread map + provenance through
├── types.py             # EDIT — FacetValues TypedDict gains 4 list fields
└── formats/
    └── parquet_single.py  # EDIT — _facets_to_arrow keys tuple gains 4 keys

scripts/
├── distill_dimensions.py  # NEW — full abstracts.detail.json → slim dimensions.slim.json
└── build_ui_data.py     # EDIT — new `--dimensions PATH` CLI arg pointing at the SLIM
                         #        file (optional; when absent the 4 facets are empty)

specs/008-ui-rewrite/contracts/
└── ui_data.linkml.yaml  # EDIT — facets slot description doc note (11 → 15 lists)

site/src/lib/
├── facets.ts            # EDIT — add 4 keys to FACETS_FROM_BLOCK, FACET_KEYS_ORDERED, FACET_LABELS
└── components/
    └── DetailPanel.svelte  # EDIT — 4 labelled chip blocks in the computed-insights zone

tests/
├── test_ui_data_dimensions.py   # NEW — load/join/coverage/error tests
├── test_ui_data_abstracts.py    # EDIT — facets carry the 4 keys after join
├── test_ui_data_manifest.py     # EDIT — 4 facets discovered with options
├── test_ui_data_parquet_single.py  # EDIT — STRUCT round-trips the 4 keys
└── _ui_data_fixtures.py         # EDIT — fixture corpus + a tiny dimension file

site/src/tests/
├── unit/facets.test.ts          # EDIT — valuesFor + counts for the 4 new keys
└── e2e/(facets|detail-extra-fields).spec.ts  # EDIT — sidebar + detail render
```

**Structure Decision**: Reuse the existing Stage 6 UI-data builder and the
site's generic facet machinery — the four dimensions are peers of the existing
`facets` lists, so the change is additive plumbing plus a small UI surface, not
a new subsystem. One new Python module (`dimensions.py`) isolates the
load/validate/coverage logic; everything else is a narrow edit to a fixed key
list/label map.

## Complexity Tracking

> No Constitution Check violations — section intentionally empty.
