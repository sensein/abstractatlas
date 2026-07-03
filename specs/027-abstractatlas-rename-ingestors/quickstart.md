# Quickstart: Abstract Atlas Rename + Pluggable LinkML Ingestors

Python component change (Track A) + a few site test-string updates. Data is
preserved — no regeneration, no re-publish.

## Prerequisites

```bash
UV_CACHE_DIR=.uv-cache uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python linkml   # ingest-schema validation (already used for UI contracts)
```

## Implement (sequenced so the mechanical rename is verified first)

### Slice 1 — Rename (mechanical, verify identical before proceeding)

1. `git mv src/ohbm2026 src/abstractatlas`.
2. Rewrite imports/refs `ohbm2026`→`abstractatlas` across `src/`, `tests/`,
   `scripts/`, docs; update `pyproject.toml` (`name`, `[project.scripts]`:
   `aacli = "abstractatlas.cli:main"`, `ohbm-*`→`aa-*`/drop per rename-map),
   and `PYTHONPATH=src -m ohbm2026.cli` → `-m abstractatlas.cli` in docs/CI.
3. Add the deprecation shims: `ohbmcli` delegating entry point + an
   `ohbm2026` import shim (labeled, follow-up to remove).
4. **Preserve** all data names (rename-map "NOT renamed" table) — do NOT
   touch `data/**` paths, state-keys, or `ohbm2026.parquet`.
5. Verify BEFORE any ingestor work:

   ```bash
   PYTHONPATH=src .venv/bin/python -m unittest discover -s tests   # SC-002
   # SC-001: run a fixture subcommand under aacli, diff artifacts vs a pre-rename run
   git grep -n 'ohbm2026\|ohbmcli'   # only data-identity names, shims, historical specs remain
   ```

### Slice 2 — Ingest package (tests first)

6. Write failing tests (`tests/test_ingest_registry.py`,
   `test_ingest_schema.py`) per `contracts/ingestor-interface.md`.
7. Add `abstractatlas/ingest/{base,registry,schema}.py` +
   `contracts/ingest-schema.linkml.yaml` (copy into the package or load from
   contracts) to green them.

### Slice 3 — Port the two sources

8. Write `tests/test_ingestor_ports.py` (OHBM output byte-identical) —
   failing first.
9. Add `ingest/conference_ohbm.py` (wraps `fetch/stage.py` +
   `assets.normalize_abstract`) and `ingest/literature_neuroscape.py`
   (wraps NeuroScape normalization); register both. Green the port tests.
10. Wire `aacli ingest --source` / `list-ingestors`; existing subcommands
    unchanged.

### Slice 4 — Docs

11. Update README, CLAUDE.md, and constitution naming references (FR-012);
    document the intentional `ohbm2026.parquet` divergence.

## Verify

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests   # full suite green (SC-002)
PYTHONPATH=src .venv/bin/python -m unittest tests.test_ingest_registry tests.test_ingest_schema tests.test_ingestor_ports -v
.specify/scripts/bash/constitution-check.sh --full
cd site && pnpm exec vitest run                                # renamed string refs
```

## Done-when

- Full suite green under `abstractatlas`/`aacli`; fixture artifacts identical to pre-rename (SC-001/002).
- Both sources are registered ingestors; ports touched zero downstream stage logic (SC-004); outputs validate against the schema (SC-005).
- Published data byte-identical, no re-publish (SC-003); legacy names emit labeled deprecation (SC-007).
- `git grep 'ohbm2026'` shows only intentional data-identity names, shims, and historical specs.
