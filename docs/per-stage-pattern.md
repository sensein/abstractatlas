# Per-Stage Pattern

Every pipeline stage in this repo (Stage 1 fetch, Stage 2 figures,
Stage 3 enrichment, …) satisfies the same six contracts. This doc
defines them and points at the canonical reference implementation
— **Stage 1 (`src/ohbm2026/fetch_stage.py`)** — for each.

A new stage author should be able to read this page plus
`fetch_stage.py` and write the next stage script in the same style.
Adding a new stage means writing a new orchestrator module that
satisfies these six contracts, not inventing new ones.

## The Six Contracts

### 1. Input contract

What env vars + prior-stage artifacts the stage reads, by name and
by path.

- **Env vars** are named only (never logged with values). The
  orchestrator collects the list and records it in the provenance
  record's `env_vars_consulted`.
- **Prior-stage artifacts** are read from their canonical paths
  under the gitignored data roots.

Stage 1 reference:
- `fetch_stage._load_api_key` reads `OHBM2026_API` (name only) from
  `.env` (default) or environment.
- `fetch_stage._build_parser` declares the CLI surface (env-file,
  env-var, batch-size, timeouts, allow flags, output overrides).

### 2. Output contract

What artifacts the stage writes, at what paths, with what shape.

- Every output path is under the existing gitignored data roots
  (`data/primary/`, `data/inputs/`, `data/cache/`). The stage refuses
  to write outside the gitignored boundary even if explicitly
  directed to.
- The on-disk shape of canonical downstream-consumed artifacts is
  preserved across stage iterations; additive fields are OK,
  breaking changes need a separate spec.

Stage 1 reference:
- Corpus snapshot: `fetch_stage._write_corpus` →
  `data/primary/abstracts.json`.
- Schema artifact: `fetch_stage._write_schema_artifact` →
  `data/inputs/abstracts_graphql_schema__<state-key>.json`.
- Provenance: `fetch_stage._write_provenance` →
  `data/inputs/abstracts_fetch_provenance__<state-key>.json`.
- All three use `fetch_stage._atomic_write_json` (temp-file →
  `os.replace`) for crash safety.

### 3. Provenance contract

What the stage's provenance record contains, and how it is kept
portable.

- Required fields: `provenance_version`, `run_id`, `state_key`,
  `run_timestamp`, `code_revision`, `command_line`,
  `env_vars_consulted`, `endpoint_url` (where applicable),
  `query_count` / equivalent, `*_count` metrics, `*_path` pointers,
  `schema_hash`, `schema_diff_vs_previous` (where applicable),
  `checkpoint_path`, `resumed_from_previous_run`.
- All path fields are project-relative — no absolute paths, no
  `~`-prefix. Verified at write time; violations raise
  `ProvenanceError` (Principle VIII / CA-008).

Stage 1 reference:
- `fetch_stage._build_provenance_record` assembles the full record.
- `fetch_stage._assert_provenance_paths_safe` enforces the
  no-absolute / no-`~` rule.
- The exact field set is contract-tested against
  `specs/002-rewire-pipeline/contracts/abstracts_fetch_provenance.schema.json`.

### 4. Error-handling contract

What failures the stage surfaces loudly, with what typed cause,
and at what exit code.

- Typed exception hierarchy in `ohbm2026.exceptions` (Stage1Error
  base + `SchemaContractError`, `CheckpointError`,
  `ProvenanceError`, plus re-exported `GraphQLAPIError`). Stages
  add their own subclasses where appropriate.
- No bare `except`. No silent fallbacks. No "log and continue"
  around operations whose failure would corrupt downstream
  artifacts.
- Exit codes are documented in the stage's CLI contract doc.

Stage 1 reference:
- `fetch_stage.main` catches each typed exception and maps it to
  a documented exit code (1 GraphQL, 2 HARD drift, 3 checkpoint,
  4 provenance, 5 figure failure rate, 6 empty corpus).
- Exit codes documented in
  `specs/002-rewire-pipeline/contracts/cli.md`.

### 5. Resumability contract

Whether the stage is fully resumable from checkpoint, idempotent on
full re-run, or both. If checkpointed: what the checkpoint shape is,
how it validates, and what guarantees the worst-case redo bound.

- Idempotency on full re-run: identical input state produces
  identical primary outputs (only provenance run-id / timestamp
  differ).
- Checkpointing (where applicable): a single JSON file under a
  gitignored cache root, written atomically; carries enough
  state to (a) decide whether to resume, (b) know how far the
  previous run got, and (c) explain that to a human.

Stage 1 reference:
- `fetch_stage._load_or_init_checkpoint`,
  `fetch_stage._new_checkpoint`, `fetch_stage._atomic_write_json`.
- Dual granularity: page-level cursor (`completed_submission_ids`)
  + per-record markers within the in-flight page. Worst-case redo
  on interruption is bounded to records still in flight.
- Checkpoint self-validates against the schema artifact's hash
  (`bound_schema_hash`); mismatch raises `CheckpointError` unless
  `--allow-schema-change` is set.
- Schema in `specs/002-rewire-pipeline/contracts/abstracts_fetch_checkpoint.schema.json`.

### 6. Discovery contract

Which external state the stage discovers at runtime versus what it
treats as configuration.

- Upstream data shape (schema, available fields, available
  checkpoints, vendor enumerations) is discovered at runtime, never
  hardcoded as a separate file that can drift.
- Discovered state is persisted alongside the data so subsequent
  runs (or downstream stages) can diff against it (Principle VII).
- Mismatches surface as precise errors naming what was searched
  and what was found — never silent skips.

Stage 1 reference:
- `fetch_stage._run_introspection` fetches the live GraphQL
  schema; result persisted as the schema artifact.
- `schema_diff.flatten_introspection` + `compare` classify drift
  into HARD / SOFT / INFORMATIONAL.
- HARD set is derived from the live query body via
  `schema_diff.parse_hard_set_from_queries`. SOFT set is derived
  by importing consuming modules and unioning their
  `CONSUMED_ABSTRACT_FIELDS`. Neither set is a separately
  maintained allow-list.

## Adding a New Stage

When you write Stage N:

1. **Sketch the six contracts first.** Open a spec under
   `specs/<NNN>-<short-name>/spec.md` and name what each contract
   element will be: input env vars + prior-stage artifacts;
   output paths; provenance fields; error types; resume strategy;
   discovery surface.
2. **Author the test file first** (Principle IV). One test per
   contract element, organized into a class per contract.
3. **Implement the orchestrator** in
   `src/ohbm2026/<stage_name>.py`. Use Stage 1's `fetch_stage.py`
   as the layout reference. Share helpers via `artifacts.py`,
   `exceptions.py`, and `schema_diff.py` where possible.
4. **Add a CLI subcommand** in `cli.py` that delegates to your
   new `main(argv)`.
5. **Add a `scripts/run_<stage_name>.py` wrapper** for the README.
6. **Update the per-stage README section + this doc** so a future
   contributor can find your stage.

## Common Helpers

- `ohbm2026.artifacts.build_*_path(state_key)` — path derivation
  under gitignored roots.
- `ohbm2026.artifacts.build_dependency_basis` + `build_state_key` —
  deterministic state key from input fingerprint.
- `ohbm2026.exceptions.*` — typed exception hierarchy.
- `ohbm2026.schema_diff.*` — schema-diff / discovery primitives
  (reusable across stages that talk to GraphQL).
- The constitution lint at
  `.specify/scripts/bash/constitution-check.sh` catches the
  automatable subset of contract violations.
