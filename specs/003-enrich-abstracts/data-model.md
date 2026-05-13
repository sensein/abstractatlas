# Data Model — Stage 2 Artifacts

Phase 1 of `/speckit-plan`. Field-level schemas for each new or
extended entity Stage 2 produces. Stage 1 outputs (corpus snapshot,
schema artifact, fetch provenance, etc.) remain read-only inputs and
are not redefined here.

## Path Layout

| Artifact | Path |
|---|---|
| Enriched corpus (SQLite + zlib) | `data/primary/abstracts_enriched.sqlite` |
| Enrich provenance record | `data/inputs/abstracts_enrich_provenance__<state-key>.json` |
| Figure-interpretation cache | `data/cache/figure_analysis/<cache-key>.json` (existing) |
| Claims cache | `data/cache/claim_analysis/<cache-key>.json` (existing) |
| Reference-resolution cache | `data/cache/reference_metadata/<cache-key>.json` |

State-key derivation: same scheme as Stage 1 (`artifacts.build_state_key`
over the input fingerprint). Stage 2's input fingerprint is the
combination of: source corpus path + its content hash + model
identifiers of all three components + cache_version.

## 1. Enriched Corpus (SQLite database)

Single SQLite file. One table, primary-key indexed on `id`. Payload
column is zlib-compressed JSON bytes of the per-abstract enriched
record.

**Schema**:

```sql
CREATE TABLE abstracts (
  id            INTEGER PRIMARY KEY,
  payload       BLOB    NOT NULL,    -- zlib(json(EnrichedAbstractRecord))
  content_hash  TEXT    NOT NULL,    -- sha256 of the input abstract JSON
  enriched_at   TEXT    NOT NULL     -- ISO-8601 UTC
);
CREATE INDEX abstracts_content_hash ON abstracts(content_hash);

CREATE TABLE corpus_metadata (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
-- Seeded with:
--   ('storage_version', 'enrich.storage.v1')
--   ('corpus_kind',     'accepted')
--   ('built_at',        '<ISO-8601 UTC>')
--   ('state_key',       '<12 hex chars>')
--   ('source_corpus_hash', '<sha256 of data/primary/abstracts.json>')
```

**Validation rules**:

- Every row in `abstracts` MUST correspond to a currently-accepted
  abstract (i.e., its `id` appears in `data/primary/abstracts.json`).
- Decompressing `payload` MUST yield valid UTF-8 JSON.
- The JSON document MUST conform to `EnrichedAbstractRecord` (§2).
- `corpus_metadata.storage_version` MUST be `enrich.storage.v1`.

## 2. Enriched Abstract Record (the JSON inside each `payload`)

Each row's decompressed JSON has this shape:

| Field | Type | Description |
|---|---|---|
| All Stage 1 fields | (unchanged) | `id`, `poster_id`, `title`, `accepted_for`, `authors`, `responses`, `external_urls`, `figure_urls`, `program_sessions`, `local_assets` — verbatim from Stage 1 |
| `figure_interpretation` | `array<FigureInterpretation>` | One entry per figure URL. Empty list when the abstract has zero methods/results figures. |
| `claims` | `array<Claim>` | List of extracted claim records. Empty list when extraction returns no claims. |
| `references` | `array<ReferenceResolution>` | List of resolved reference records. Empty list when the abstract has no references section. |

### FigureInterpretation entry

| Field | Type | Description |
|---|---|---|
| `figure_url` | `string` | The upstream source URL of the figure. |
| `local_path` | `string \| null` | Project-relative path under `data/primary/assets/` if download succeeded; `null` otherwise. |
| `question_name` | `string` | The upstream question (e.g., "Methods Figure (Optional)"). |
| `interpretation` | `string \| null` | The model's natural-language interpretation; `null` if the cache entry is a hard failure. |
| `model_id` | `string` | e.g., `"gpt-4.1-mini"`, `"qwen3.5:35b"`. |
| `cache_key` | `string` (64 hex) | `sha256(figure_bytes || model_id)`. |

### Claim entry

| Field | Type | Description |
|---|---|---|
| `claim_text` | `string` | One extracted claim, free-text. |
| `confidence` | `number \| null` | Optional confidence score if the model returns one. |
| `model_id` | `string` | e.g., `"gpt-4o-2024-08-06"`. |
| `cache_key` | `string` (64 hex) | `sha256(manuscript_markdown || model_id)`. Shared across all claims for the same abstract. |

### ReferenceResolution entry

| Field | Type | Description |
|---|---|---|
| `raw_reference` | `string` | The original reference text. |
| `doi` | `string \| null` | DOI if resolved. |
| `pmid` | `string \| null` | PMID if resolved. |
| `openalex_id` | `string \| null` | OpenAlex Work ID if resolved. |
| `title` | `string \| null` | Resolved canonical title. |
| `authors` | `array<string> \| null` | Resolved canonical author names. |
| `year` | `integer \| null` | Resolved publication year. |
| `resolution_status` | `enum("resolved","partial","unresolved")` | Final status. |
| `resolution_source` | `string \| null` | e.g., `"doi"`, `"openalex_title"`, `"semantic_scholar"`. |
| `strategy_id` | `string` | The reference-resolution strategy version, e.g., `"refs.v1+openai-gpt-5-nano"`. |
| `cache_key` | `string` (64 hex) | `sha256(raw_reference || strategy_id)`. |

## 3. Enrich Provenance Record

Sidecar JSON at
`data/inputs/abstracts_enrich_provenance__<state-key>.json`.

| Field | Type | Required | Description |
|---|---|---|---|
| `provenance_version` | `string` | yes | `"enrich.provenance.v1"`. |
| `run_id` | `string` (UUID4) | yes | Unique per invocation. |
| `state_key` | `string` (12 hex) | yes | Matches the artifact namespace. |
| `run_timestamp` | `string` (ISO-8601 UTC) | yes | When this run started. |
| `code_revision` | `object` | yes | `{ "git_sha": <hex>, "dirty": <bool> }`. |
| `command_line` | `array<string>` | yes | `sys.argv` of this run. |
| `env_vars_consulted` | `array<string>` | yes | Names of env vars Stage 2 read. NEVER values. |
| `source_corpus_path` | `string` (project-relative) | yes | Pointer to the accepted corpus that fed this run. |
| `source_corpus_hash` | `string` (64 hex) | yes | SHA-256 of the source corpus content. |
| `enriched_corpus_path` | `string` (project-relative) | yes | Pointer to the SQLite output. |
| `corpus_kind` | `enum("accepted")` | yes | Always `"accepted"` in v1; reserved for future. |
| `abstract_count` | `integer` | yes | Total enriched records in the output. |
| `components` | `array<ComponentSummary>` | yes | One per component; see below. |
| `delta_vs_previous` | `object \| null` | yes | `null` if no prior enriched corpus existed; else `{added_count, removed_count, unchanged_count}`. |
| `figure_failure_count` | `integer` | yes | Per-figure failures across the corpus. |
| `claim_failure_count` | `integer` | yes | Per-abstract claim-extraction failures. |
| `reference_failure_count` | `integer` | yes | Per-reference unresolved-after-all-backends count. |
| `parquet_export_path` | `string \| null` (project-relative) | yes | Set to the project-relative path written when `--export-parquet PATH` was passed (FR-017); `null` otherwise. Field is always present so consumers can detect "was a Parquet copy emitted?" without inspecting argv. |

### ComponentSummary entry

| Field | Type | Description |
|---|---|---|
| `component` | `enum("figures","claims","references")` | The component name. |
| `model_id` | `string` | The model / strategy identifier used. |
| `cache_version` | `string` | The cache schema version (`"enrich.cache.v1"` at v1). |
| `cache_hit_count` | `integer` | Number of cache hits this run. |
| `cache_miss_count` | `integer` | Number of cache misses (i.e., new computations). |
| `cache_invalidated` | `boolean` | True if `--invalidate <component>` was passed for this component. |
| `failure_count` | `integer` | Component-specific failure count. |

**Validation rules**:

- Every path field MUST be project-relative (no absolute, no `~`).
- `env_vars_consulted` contains NAMES only.
- `components` MUST have exactly three entries (figures, claims,
  references), even if a component had zero work to do (all
  empty input).
- `cache_hit_count + cache_miss_count` MUST equal the count of
  abstracts that needed work in that component (i.e., the abstracts
  with figures for `figures`; abstracts that produced claims for
  `claims`; abstracts with references for `references`).

## 4. Component Cache Entry

JSON file at `data/cache/<component>/<cache-key>.json`. One file per
cache key. Atomic write (temp + rename).

**Shape**:

```json
{
  "cache_version": "enrich.cache.v1",
  "component":     "figures",
  "cache_key":     "<64 hex>",
  "model_id":      "<model identifier>",
  "input_hash":    "<sha256 of the component input>",
  "computed_at":   "<ISO-8601 UTC>",
  "payload":       { ... component-specific output ... }
}
```

**Validation rules**:

- `cache_key` MUST equal `sha256(input || model_id)`. Mismatch
  during validation raises `EnrichmentError` (do not silently
  trust filename).
- `cache_version` mismatch with the current Stage 2 version is
  treated as a **cache miss** (Principle VI: fail loudly; do not
  migrate silently).
- `input_hash` MUST match the recomputed hash of the actual input
  on read; mismatch raises `EnrichmentError` (the cache file may
  have been tampered).
- `payload` shape is component-specific:
  - **figures**: matches `FigureInterpretation` minus `cache_key`
    (which is redundant with the filename).
  - **claims**: `{ "claims": [Claim, ...] }`.
  - **references**: matches `ReferenceResolution` minus `cache_key`.

## State Transitions

### Per-abstract enrichment lifecycle

```
[abstract in accepted corpus]
        │
        ▼
─ for each component:
    ├─ compute cache_key from (input, model_id)
    ├─ cache hit?
    │    ├─ yes: load payload from disk; no LLM/API call
    │    └─ no:  call component → write cache entry atomically
    │             └─ component failure?
    │                  ├─ within threshold: record failure, continue
    │                  └─ over threshold:  raise; halt run
    ▼
─ assemble EnrichedAbstractRecord (Stage 1 fields + 3 enrichment lists)
        │
        ▼
─ pending until all abstracts processed (final SQLite write is atomic)
```

### Run lifecycle

```
[no prior enriched corpus]
        │
        ▼
─ load source corpus from data/primary/abstracts.json
─ compute state_key from input fingerprint
─ load existing enriched corpus (if any) for delta-vs-previous only
        │
        ▼
─ for each accepted abstract: run per-abstract lifecycle above
        │
        ▼
─ atomic SQLite write: temp → os.replace → canonical path
─ write provenance record atomically
─ print summary JSON
```

An interruption between the start and the final SQLite write leaves:

- The previous enriched corpus on disk (unchanged).
- Cache entries populated so far (so the next run is cheap).
- The temp SQLite file (named with `run_id`) abandoned on disk; the
  next run ignores it (canonical path resolution is by name).

No separate checkpoint file is needed; the per-component caches ARE
the checkpoint.
