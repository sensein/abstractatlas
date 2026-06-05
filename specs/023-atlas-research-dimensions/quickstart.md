# Quickstart — Atlas Research-Classification Dimensions

## 0. Land the input + distill to slim (gitignored)

```bash
mkdir -p data/inputs/neuroscape-dimensions
cp ~/Downloads/abstracts.detail.json data/inputs/neuroscape-dimensions/abstracts.detail.json

# Reduce the ~120 MB detail file to a slim {id + 4 dimensions} file (the build input)
PYTHONPATH=src .venv/bin/python scripts/distill_dimensions.py \
  --in  data/inputs/neuroscape-dimensions/abstracts.detail.json \
  --out data/inputs/neuroscape-dimensions/dimensions.slim.json
```

`data/inputs/` is gitignored (`.gitignore:8`) — neither the ~120 MB detail file
nor the slim file is committed; the distiller regenerates the slim file on demand.

## 1. Write the failing tests first (Constitution IV)

```bash
# Python — new + extended
PYTHONPATH=src .venv/bin/python -m unittest tests.test_ui_data_dimensions -v
PYTHONPATH=src .venv/bin/python -m unittest tests.test_ui_data_abstracts -v
PYTHONPATH=src .venv/bin/python -m unittest tests.test_ui_data_manifest -v
PYTHONPATH=src .venv/bin/python -m unittest tests.test_ui_data_parquet_single -v

# Site (run-mode — never watch; see memory feedback_vitest_run_mode)
cd site && pnpm exec vitest run src/tests/unit/facets.test.ts
```

All should FAIL before implementation (keys/module/blocks don't exist yet).

## 2. Implement (commit each verified slice)

1. `src/ohbm2026/ui_data/dimensions.py` — `distill_dimensions` (full→slim) + load/validate/coverage + `DimensionInputError`; `scripts/distill_dimensions.py` CLI.
2. `ui_data/abstracts.py` — `research_dimensions` param; inject 4 lists into facets.
3. `ui_data/types.py` + `formats/parquet_single.py` — 4 new facet keys.
4. `ui_data/manifest.py` — 4 keys/labels + `research_dimensions` provenance.
5. `ui_data/builder.py` + `scripts/build_ui_data.py` — load once, thread map + coverage.
6. `site/src/lib/facets.ts` — 4 keys in the 3 constants.
7. `site/src/lib/components/DetailPanel.svelte` — 4 computed-insights chip blocks.
8. Docs: `CLAUDE.md`, `README.md`, LinkML `facets` description.

## 3. Build the data package with dimensions

```bash
PYTHONPATH=src .venv/bin/python scripts/build_ui_data.py \
  --corpus data/primary/abstracts.json \
  --withdrawn data/primary/abstracts_withdrawn.json \
  --authors data/primary/authors.json \
  --enriched data/primary/abstracts_enriched.sqlite \
  --analysis-root data/outputs/experiments/analysis --discover-rollup \
  --minilm-root data/outputs/embeddings/minilm \
  --dimensions data/inputs/neuroscape-dimensions/dimensions.slim.json \
  --output data/outputs/exported-sites/ui-data-package
```

Expect a log line with per-dimension coverage (≈ focus 3329, modality 3326,
theory_scope 2890, epistemic 3325) and `unmatched_in_file`.

## 4. Verify

```bash
# Schema still validates
scripts/validate_ui_data.sh data/outputs/exported-sites/ui-data-package/ohbm2026.parquet

# Determinism (SC-005): build twice, compare bytes
PYTHONPATH=src .venv/bin/python scripts/build_ui_data.py ... --output /tmp/b1
PYTHONPATH=src .venv/bin/python scripts/build_ui_data.py ... --output /tmp/b2
cmp /tmp/b1/ohbm2026.parquet /tmp/b2/ohbm2026.parquet && echo "byte-identical ✓"

# Full Python suite + site
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
cd site && pnpm exec vitest run && pnpm exec playwright test detail-extra-fields facets
```

## 5. Local UI smoke

Point the site at the freshly built parquet (see memory `local_dev_env`),
`VITE_SITE_MODE=ohbm2026 pnpm dev`, then:
- facet sidebar shows Focus / Research modality / Theory scope / Epistemic basis;
- selecting an option narrows the corpus + scatter;
- a detail view shows the four dimensions as chips (and omits an empty one).

## Edge checks

- Omit `--dimensions` → build succeeds, 4 facets empty, no provenance block (D4).
- Corrupt the file (e.g. `[]`) → `DimensionInputError` with a precise message.
