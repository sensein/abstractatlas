# CLI Contract — Stage 2: Enrich Abstracts

Stage 2 exposes one canonical surface in two equivalent forms; both
route through `ohbm2026.enrich_stage.main(argv) -> int`.

## Primary form: `ohbmcli enrich-abstracts`

```text
.venv/bin/python -m ohbm2026.cli enrich-abstracts [OPTIONS]
```

The following legacy subcommands are REMOVED in this change (FR-014;
parallel to Stage 1's removals of `ingest` and `authors`):

- `ohbmcli enrich` — replaced.
- `ohbmcli analyze-figures` — replaced (use `--invalidate figures` to refresh only).
- `ohbmcli extract-claims` — replaced (use `--invalidate claims` to refresh only).
- `ohbmcli reference-metadata` — replaced (use `--invalidate references` to refresh only).

## Wrapper form: `scripts/run_enrich_abstracts.py`

```text
.venv/bin/python scripts/run_enrich_abstracts.py [OPTIONS]
```

## Options

| Option | Type | Default | Purpose |
|---|---|---|---|
| `--env-file PATH` | path | `.env` | dotenv file scanned for component API keys. |
| `--source-corpus PATH` | path | `data/primary/abstracts.json` | Stage-1 accepted corpus to enrich. MUST exist. |
| `--enriched-output PATH` | path | `data/primary/abstracts_enriched.sqlite` | SQLite output path. MUST land under a gitignored root. |
| `--figure-model-id ID` | string | `gpt-4.1-mini` | Vision model identifier; part of the figures cache key. |
| `--claims-model-id ID` | string | `gpt-4o-2024-08-06` | Claims-extraction model; part of the claims cache key. |
| `--reference-strategy-id ID` | string | `refs.v1+openai-gpt-5-nano` | Reference-resolution strategy version; part of the references cache key. |
| `--invalidate {figures,claims,references}` | string (repeatable) | none | Force-invalidate one or more component caches. Other components reuse hits intact. |
| `--figure-failure-threshold FLOAT` | float | `0.05` | Component-failure threshold (fraction). Run exits 5 if exceeded. |
| `--claim-failure-threshold FLOAT` | float | `0.05` | Same, for claims. |
| `--reference-failure-threshold FLOAT` | float | `1.0` | Same, for references — defaults to 1.0 because reference resolution always has some unresolvable entries. Operator can tighten. |
| `--export-parquet PATH` | path | unset | OPTIONAL (FR-017). When set, ALSO writes a Parquet copy of the enriched corpus to PATH after the canonical SQLite atomic commit succeeds. `pyarrow` is lazy-imported only when this flag is used. PATH MUST land under a gitignored root. |

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Success — enriched corpus + provenance written. |
| `1` | Generic upstream / LLM error (`EnrichmentError`). Partial cache entries remain on disk for the next run. |
| `2` | LLM response schema drift (`SchemaContractError` from a component). |
| `4` | Output-boundary violation (`ProvenanceError` — absolute / `~` path detected). |
| `5` | Component failure rate exceeded its threshold (`ComponentFailureThresholdError`). Enriched corpus NOT overwritten. |
| `6` | Semantically empty source corpus (matches Stage 1's `EXIT_EMPTY_CORPUS`). |
| `7` | Cache version mismatch surfaced loudly without auto-migration (`CacheVersionError`). |

## Stdout contract

On success, prints a single JSON object to stdout:

```json
{
  "enriched_corpus": "data/primary/abstracts_enriched.sqlite",
  "provenance_record": "data/inputs/abstracts_enrich_provenance__<state-key>.json",
  "state_key": "<12 hex>",
  "abstract_count": 3244,
  "components": [
    {"component": "figures", "model_id": "gpt-4.1-mini", "cache_hit_count": 4690, "cache_miss_count": 0, "failure_count": 0},
    {"component": "claims", "model_id": "gpt-4o-2024-08-06", "cache_hit_count": 3244, "cache_miss_count": 0, "failure_count": 0},
    {"component": "references", "model_id": "refs.v1+openai-gpt-5-nano", "cache_hit_count": 30000, "cache_miss_count": 0, "failure_count": 0}
  ],
  "delta_vs_previous": {"added_count": 0, "removed_count": 0, "unchanged_count": 3244}
}
```

On failure, error details go to stderr; stdout receives no JSON.

## Stderr contract

- Cache misses log an informational line with the component and the
  cache key.
- LLM call failures log a typed error with abstract id + component
  + reason.
- Threshold breaches print a summary of which component exceeded
  what threshold.
- No secrets ever appear in stderr (API key values never logged;
  env-var NAMES only).

## Side effects

Stage 2 writes ONLY under the gitignored roots:

- `data/primary/abstracts_enriched.sqlite` (overwrite atomically
  on full completion).
- `data/inputs/abstracts_enrich_provenance__<state-key>.json`
  (new per state-key).
- `data/cache/figure_analysis/<cache-key>.json` (existing namespace;
  Stage 2 may add new entries).
- `data/cache/claim_analysis/<cache-key>.json` (existing namespace).
- `data/cache/reference_metadata/<cache-key>.json` (new namespace).

If any write would land outside a gitignored root, Stage 2 aborts
(exit 4) without writing anywhere.
