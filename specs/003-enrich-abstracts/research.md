# Research: Stage 2 Design Decisions

Phase 0 of `/speckit-plan`. The user explicitly directed an empirical
benchmark before pinning a storage format. That benchmark anchors §1
below; every other open question gets a Decision / Rationale /
Alternatives entry.

## 1. Enriched-corpus storage format — empirical benchmark

**Benchmark setup**: the existing `data/primary/abstracts_enriched.json`
(66.3 MB, 3333 enriched records from a prior Mar 13 pipeline run) was
loaded and written into each candidate format. 100 random abstract
IDs were sampled with `random.seed(42)` and looked up individually.
Each format's full corpus was also scanned sequentially. Test
machine: a typical developer laptop (macOS). Script:
`tmp/benchmark_storage_formats.py` (gitignored, but reproducible).

The original benchmark covered six stdlib-only formats. The user
challenged the no-third-party-deps filter, so the benchmark was
re-run with two Parquet variants added (the de-facto analytics
columnar format; requires `pyarrow`). Updated table:

| Format | Size | Write | Random avg | Random p95 | Seq read |
|---|---|---|---|---|---|
| JSON (baseline) | 58.64 MB | 511 ms | **178 ms** | 193 ms | 172 ms |
| JSONL | 58.64 MB | 209 ms | 80 ms | 152 ms | 163 ms |
| JSONL.gz | 14.99 MB | 1626 ms | 121 ms | 229 ms | 247 ms |
| JSONL + .idx.json | 58.7 MB | 210 ms | **0.06 ms** | 0.08 ms | 162 ms |
| SQLite raw blob | 61.2 MB | 305 ms | **0.06 ms** | 0.07 ms | 160 ms |
| **SQLite zlib blob** ⭐ | **21.1 MB** | 1278 ms | **0.09 ms** | 0.11 ms | 250 ms |
| Parquet snappy | 25.2 MB | 405 ms | 30.7 ms | 31.5 ms | 174 ms |
| Parquet zstd | **13.0 MB** | 728 ms | 45.6 ms | 46.6 ms | 188 ms |

**Decision**: **SQLite with per-row zlib-compressed JSON blob.**
Single file, primary key = abstract `id`, payload = zlib-compressed
JSON bytes.

**Rationale**:

- The user's brief had two constraints: minimize storage AND minimize
  random seeks. On a Pareto-frontier basis, SQLite zlib **dominates**:
  nothing beats it on random reads at its size point. Parquet zstd
  is the most compact (13 MB) but is Pareto-strictly worse on random
  reads (45 ms vs 0.09 ms — 500× slower).
- SC-006 ("under 10 ms random by ID"): SQLite zlib at 0.09 ms gives
  a 100× margin. Parquet at 30–46 ms would **fail** this SC as
  currently written.
- SC-007 ("at least 30% smaller than verbose JSON"): SQLite zlib at
  64% reduction, Parquet zstd at 78%. Both pass; the 8 MB absolute
  difference is small.
- Stdlib-only: `sqlite3` and `zlib` are both built-in. Parquet adds
  `pyarrow` (≈ 33 MB install). The dependency cost isn't zero; we'd
  take it on if it bought a meaningful win, but it doesn't.
- For Stage 2's downstream consumers — UI per-record lookups, search
  + embedding sequential scans — random-by-ID latency is the hotter
  axis. SQLite zlib hits both axes; Parquet sacrifices one for the
  other.

**Alternatives considered**:

- **Parquet (snappy or zstd)**: empirically tested. Parquet zstd is
  the most compact format in the benchmark (13 MB, 78% smaller than
  JSON). Rejected as the canonical Stage 2 output on random-read
  latency: 30–46 ms vs SQLite zlib's 0.09 ms — Parquet's row-group
  / predicate-pushdown scan model is ~500× slower than SQLite's
  B-tree primary-key index for this point-lookup workload. The
  compression win (8 MB absolute) is small relative to the latency
  penalty (×500 random reads). However, Parquet is **kept as an
  optional conversion target** via `--export-parquet PATH` per
  FR-017, because (a) it's the de-facto analytics format, (b)
  upcoming embedding-vector work will likely prefer columnar
  storage with strong compression, and (c) tools downstream of
  Stage 2 (DuckDB, pandas, polars, browser-side WASM engines like
  DuckDB-Wasm) read Parquet natively. The Parquet writer
  lazy-imports `pyarrow` so the optional dependency only enters
  the picture when the operator opts in.
- **JSONL + .idx.json**: strong second choice. Slightly faster
  random, human-readable for grep/awk. Rejected for the corpus
  use case because the 2.8× size penalty matters at scale and
  the operator-visibility win is small (the corpus is read
  programmatically by Stage 3+ tools, not line-by-line).
- **JSONL.gz**: maximum compression but no random access without a
  full decompress. Rejected — directly conflicts with the random-
  seek requirement.
- **MessagePack / CBOR**: ~30% smaller than raw JSON before
  compression, but no built-in index. Combined with zlib + an
  index, equivalent to SQLite zlib but more moving parts.
  Rejected for simplicity.
- **Raw SQLite (no compression)**: 61 MB; faster random (0.06 ms)
  but loses the size win. Rejected on size.

## 1b. Browser-readability check for SQLite+zlib

**Concern raised**: the future gated-atlas / static-site UI runs in a
browser. If the canonical Stage 2 output is SQLite+zlib, the browser
needs to read it.

**Decision**: SQLite+zlib is browser-readable end-to-end. Production
path:

- **SQLite in the browser**: `sql.js` or `@sqlite.org/sqlite-wasm`
  (~1 MB JS+WASM bundle). Supports HTTP Range "lazy" mode — only
  the bytes needed for the running query are fetched. GitHub Pages
  serves HTTP Range headers, so a static deploy works.
- **zlib decompression in the browser**: `pako` library (~30 KB
  minified), a mature DEFLATE/zlib implementation. Browsers also
  ship native `DecompressionStream` for the gzip and deflate-raw
  formats; standard zlib framing (RFC 1950) needs pako.

End-to-end latency in-browser: ~5–30 ms per random lookup
(WASM overhead + range fetch + pako decompress). Slower than
native SQLite's 0.09 ms but still well under the SC-006 informal
budget for "browse the atlas interactively". The alternative
(load full corpus JSON upfront) would download 60+ MB before the
first lookup completes.

**Rationale**: keeping the format consistent across native and
browser consumers avoids a build-time conversion step and keeps
provenance directly attached to the canonical artifact. The
optional Parquet export (FR-017) still exists for tools that
prefer columnar; the browser path uses the canonical SQLite.

**Alternatives considered**:

- Convert SQLite to JSONL at UI-build time: rejected; loses the
  random-by-id win and bloats the static-site bundle.
- Convert SQLite to Parquet at UI-build time: viable but adds a
  Parquet decoder to the browser bundle (DuckDB-Wasm is ~3 MB).
  Sql.js + pako is smaller; reserve Parquet for downstream
  analytics that don't run in the browser.


## 2. Per-component cache key derivation

**Decision**: cache key = `sha256(component_input)` joined with
`model_id` (or `strategy_id` for references). Both pieces are
required parts of the key. The component_input is:

- **figures**: the binary content of the figure asset file (one
  cache entry per (asset, model) pair).
- **claims**: the canonical markdown manuscript built from the
  abstract's title + introduction + methods + results + conclusion
  + any cached figure-text (matches the existing claim-prompt
  construction in `enrichment.py`).
- **references**: the raw reference markdown block before LLM-
  assisted splitting (so the cache survives downstream resolution
  changes too).

**Rationale**: matches the existing cache layout (figure_analysis,
claim_analysis) and keys both content and model. Changing either
invalidates the cache for that component without disturbing the
other two.

**Alternatives considered**:

- Key by `(abstract_id, model_id)` only: rejected because content
  edits (e.g., upstream reformatting an abstract) wouldn't
  invalidate the cache.
- Key by abstract content only, model in the value: rejected
  because model changes wouldn't invalidate.

## 3. Cache versioning (cache_entry schema evolution)

**Decision**: every cache entry carries a `cache_version` field.
When Stage 2's cache schema evolves (e.g., adding a new field per
cached enrichment), the version bumps. Loading a cache entry with
an unrecognized `cache_version` is treated as a **cache miss** —
the component re-runs and the new entry overwrites. No silent
migration, no in-place rewrite of older entries.

**Rationale**: matches Principle VI (fail loudly) — silent migration
across versions risks producing records that mix old and new
shapes. Treating it as a miss is the conservative answer.

**Alternatives considered**:

- Migrate on read: rejected; opens a class of subtle correctness
  bugs.
- Refuse to load if version mismatches and require explicit
  operator `--rebuild-cache`: rejected as too rigid for routine
  changes.

## 4. LLM response schema drift detection (Principle VII applied)

**Decision**: each LLM-backed component (figures, claims) defines
the expected response shape as a small explicit schema (Python
dataclass or `TypedDict`). The component's parser validates the LLM
response against this shape and raises `EnrichmentError` on
mismatch (e.g., the model returned a different JSON structure).
The orchestrator catches `EnrichmentError`, counts it against the
component's failure threshold, and surfaces it in provenance.

**Rationale**: Principle VII applies not only to upstream GraphQL
schemas (Stage 1) but to any "external state" the pipeline
consumes — including LLM response shapes. Mismatches surface as
precise errors with the offending response captured in provenance,
never silent skips.

**Alternatives considered**:

- Validate via `jsonschema` library: rejected — new dependency for
  what's a small per-component shape.
- Best-effort parsing with default fallbacks: rejected — exactly the
  silent-fallback pattern Principle VI prohibits.

## 5. Backend-availability discovery

**Decision**: the set of supported backends for each component is
**discovered at runtime** by inspecting which optional dependencies
are importable and which API-key env vars are set:

- Figure interpretation: OpenAI requires `OPENAI_API_KEY`; Ollama
  requires the `ollama` binary on `PATH` (already the pattern in
  `enrichment.py`).
- Claims extraction: OpenAI / Anthropic via `cllm`; requires the
  cllm package installed and the appropriate API key.
- Reference resolution: always-on lexical splitting + DOI/PMID;
  OpenAlex enriched if `OPENALEX_API` is set; Semantic Scholar
  fallback requires no key.

The orchestrator builds the supported-backends matrix on startup
and refuses to invoke a component whose required backend is
missing — with a precise error naming the missing backend and the
env var or dependency that would enable it.

**Rationale**: matches Principle VII. The pipeline doesn't hardcode
"OpenAI is always available"; it discovers what's there.

**Alternatives considered**:

- Hardcoded support matrix per stage release: rejected.
- Lazy discovery (try the backend; if it errors, skip): rejected —
  silent fallback.

## 6. Atomic write strategy for the enriched corpus

**Decision**: write the SQLite database to a temporary path within
the same directory (`abstracts_enriched.sqlite.tmp.<run-id>`), let
SQLite commit, then `os.replace` it onto the final path. SQLite's
write-ahead log auto-checkpoints on close; the rename is atomic on
POSIX.

**Rationale**: matches Stage 1's atomic-write pattern. A torn write
during an interruption either leaves the previous good corpus in
place OR leaves the temp file (which Stage 2 ignores on next
startup — it sees the canonical path is unchanged and the temp file
is named by run-id so it can't be confused with a real partial).

**Alternatives considered**:

- In-place open + write: rejected; an interruption leaves a torn
  SQLite file in the canonical location.
- WAL-only writes without rename: rejected; SQLite's WAL doesn't
  give us file-level atomicity across the whole batch.

## 7. Movement handling between accepted/withdrawn (FR-008)

**Decision**: each Stage 2 run is **stateless with respect to prior
Stage 2 state**. The orchestrator does NOT read the previous
enriched corpus to compute a delta. It reads the current Stage 1
accepted corpus and writes a fresh enriched corpus from scratch
each run.

The "movement handled gracefully" guarantee comes from the cache:

- Abstract A that was accepted, now withdrawn → not in the current
  accepted corpus → not enriched this run → not in the output
  enriched corpus. A's cache entries SURVIVE on disk (no purge).
- Abstract B that was withdrawn, now accepted → in the current
  accepted corpus → enriched this run. If its content hash
  matches a cached entry, the cache hits → zero LLM call.
- Abstract C unchanged → cache hits everywhere → byte-identical
  in the new corpus.

For the provenance's "delta vs previous run" summary (FR-007), the
orchestrator opens the previous enriched corpus (if present) and
diffs the ID sets. This is the ONLY read of the previous corpus and
it's used only for the provenance summary, not for output content.

**Rationale**: stateless-with-cache is the simpler design and
produces the same on-disk outputs as a state-tracking design. The
cache layer carries the cheap-restoration property.

**Alternatives considered**:

- Maintain an explicit Stage 2 "state" object across runs: rejected
  as redundant with the cache.
- Lazy-delete: leave dropped abstracts in the corpus until next
  full rebuild. Rejected — corrupts FR-002 (accepted only).

## 8. Resumability mid-run (SC-009)

**Decision**: cache entries written DURING a run are immediately
visible to subsequent operations within the same run (because each
component's cache write is atomic via temp-file + rename). An
interrupted run can be resumed: the next invocation iterates the
accepted corpus again, but every abstract whose component caches
are populated short-circuits to cache hits — zero re-work.

The enriched corpus SQLite file is only written at the end of the
run, as one atomic commit, AFTER all components for all abstracts
have resolved. An interruption before that final commit leaves the
previous enriched corpus on disk (if any) and the cache entries
collected so far on disk — the next run picks them up.

**Rationale**: re-uses the existing per-component cache pattern.
The orchestrator doesn't need a separate checkpoint file because
the caches ARE the checkpoint.

**Alternatives considered**:

- Per-record write to SQLite as each abstract finishes: rejected;
  partial corpus on disk is harder to reason about than "all or
  previous".
- Checkpoint file like Stage 1's resume checkpoint: rejected as
  redundant with the per-component caches.

## 9. enrichment.py heavyweight module — wrap vs refactor

**Decision**: WRAP. The existing `enrichment.py` (62 KB) holds the
figure-analysis and claims-extraction building blocks. Stage 2's
orchestrator (`enrich_stage.py`) calls into those building blocks
through their existing public signatures. The orchestrator owns
the contracts (input/output/provenance/error/resume/discovery);
the heavyweight module owns the LLM interaction details.

A future refactor of `enrichment.py` can happen in its own spec
round without touching the Stage 2 contract.

**Rationale**: Stage 2's scope is the orchestrator + storage +
caching contract; the heavyweight LLM-interaction code already
works and is tested. Refactoring 62 KB of code in-scope would
balloon the work and the review surface.

**Alternatives considered**:

- Split `enrichment.py` into `figures.py` + `claims.py` + a small
  shared helper: rejected for this spec; queued as Future Work.
- Rewrite the figure / claims code from scratch in
  `enrich_stage.py`: rejected — the existing code is the result
  of months of OpenAI/Anthropic prompt tuning and we'd lose it.

## 10. Removed CLI subcommands (FR-014)

**Decision**: `enrich`, `analyze-figures`, `extract-claims`,
`reference-metadata` are all REMOVED. Operators run
`ohbmcli enrich-abstracts` which does the work of all four,
respecting per-component caches. Focused re-runs of a single
component happen via `--invalidate <component>` flags rather than
separate subcommands.

**Rationale**: parallel to FR-014 in Stage 1 (`ingest` removed) and
FR-024 (`authors` removed). One canonical entry per stage.
Operators who really need to refresh just one component can use
`--invalidate figures` (or claims, references) to force-invalidate
just that component's cache.

**Alternatives considered**:

- Keep the four legacy subcommands as targeted-refresh shims:
  rejected as redundant with `--invalidate`. Two routes to do the
  same thing is a foot-gun.
- Soft-deprecate the four with warnings: rejected — no
  backward-compat alias, parallel to the Stage 1 precedent.
