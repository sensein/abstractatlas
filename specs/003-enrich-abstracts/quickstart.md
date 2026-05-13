# Quickstart — Stage 2: Enrich Abstracts

How to run Stage 2 from a Stage-1-complete state, what files it
produces, and how to verify success. This is the operator's primary
reference; the README's Stage 2 section is updated to mirror it.

## Prerequisites

- Stage 1 has produced `data/primary/abstracts.json`
  (`ohbmcli fetch-abstracts` has run successfully).
- Python 3.11 + `uv` + `.venv` already set up.
- API keys for the configured backends in `.env`:
  - `OPENAI_API_KEY` (figures + claims + reference splitting).
  - `OPENALEX_API` (optional but recommended for reference resolution).

## Run Stage 2

The canonical invocation, copy-pasteable:

```bash
PYTHONPATH=src .venv/bin/python scripts/run_enrich_abstracts.py
```

Equivalent through `ohbmcli`:

```bash
PYTHONPATH=src .venv/bin/python -m ohbm2026.cli enrich-abstracts
```

On a fresh run with empty caches, the stage:

1. Hashes the source corpus (`data/primary/abstracts.json`),
   derives the state-key.
2. For each accepted abstract:
   - For each figure URL → check `data/cache/figure_analysis/`;
     cache hit reuses, miss invokes the vision model and writes a
     new cache entry atomically.
   - Build the claim-prompt manuscript → check
     `data/cache/claim_analysis/`; hit reuses, miss invokes the
     claims LLM, writes a new cache entry.
   - For each reference → check
     `data/cache/reference_metadata/`; hit reuses, miss runs the
     multi-stage resolution strategy.
3. Assembles the enriched record (Stage 1 fields + three
   enrichment lists) for each abstract.
4. Writes the full enriched corpus to
   `data/primary/abstracts_enriched.sqlite.<run-id>.tmp`, then
   atomically renames to `data/primary/abstracts_enriched.sqlite`.
5. Writes provenance to
   `data/inputs/abstracts_enrich_provenance__<state-key>.json`.
6. Prints a single JSON summary to stdout
   (see `contracts/cli.md`).

## Component-targeted refresh

To force-invalidate just one component's cache (e.g., new figure
model):

```bash
PYTHONPATH=src .venv/bin/python scripts/run_enrich_abstracts.py \
  --invalidate figures \
  --figure-model-id gpt-4o
```

The other two components reuse cache hits intact. Use the same
pattern with `--invalidate claims` or `--invalidate references`.

## Verify a successful run

```bash
ls -la data/primary/abstracts_enriched.sqlite \
       data/inputs/abstracts_enrich_provenance__*.json
```

Inspect the provenance record:

```bash
.venv/bin/python -m json.tool \
  data/inputs/abstracts_enrich_provenance__*.json | less
```

Confirm:

- `abstract_count` matches the accepted-corpus size (3244 today).
- `components` lists all three with model identifiers and
  cache hit/miss counts.
- `delta_vs_previous` reflects how the enriched set changed since
  the last run (after a fresh run with no prior corpus this is
  `null`).
- All path fields are project-relative.

Random-lookup smoke check (the SC-006 spot-check):

```bash
.venv/bin/python -c "
import sqlite3, zlib, json
con = sqlite3.connect('data/primary/abstracts_enriched.sqlite')
row = con.execute('SELECT payload FROM abstracts WHERE id = ?', (1246274,)).fetchone()
rec = json.loads(zlib.decompress(row[0]))
print(rec['id'], rec.get('poster_id'), 'claims:', len(rec.get('claims', [])), 'figures:', len(rec.get('figure_interpretation', [])))
"
```

## Re-run hygiene

Stage 2 is idempotent: a second run with the same source corpus and
same models reuses every cache, makes zero LLM calls, and produces
a byte-identical SQLite file (modulo provenance run-id and
timestamp).

If you see differing outputs without an obvious upstream change,
that's a Stage 2 bug — file an issue and attach both provenance
records.

## Test it locally

```bash
PYTHONPATH=src .venv/bin/python -m unittest \
  tests.test_enrich_stage \
  tests.test_enrich_storage \
  tests.test_enrichment \
  tests.test_openalex \
  -v
```

The full project test suite should remain green:

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

And the constitution lint:

```bash
.specify/scripts/bash/constitution-check.sh --full
```

## What's NOT in Stage 2

For future `/speckit-specify` rounds:

- Embeddings, clustering, projections — Stage 3+.
- Astro UI rewrite.
- Enrichment of the withdrawn corpus (cache layout will already
  support it when the time comes).
- Splitting `enrichment.py` into smaller modules.

See `specs/003-enrich-abstracts/spec.md` "Future Work" for the
full deferred list.
