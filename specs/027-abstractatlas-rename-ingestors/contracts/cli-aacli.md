# Contract: `aacli` command surface + deprecation

`aacli` replaces `ohbmcli` with an identical subcommand surface and options
(FR-002). Behavior is byte-for-byte the former `ohbmcli` for every existing
subcommand (SC-001).

## Surface

- `aacli <subcommand>` — every existing subcommand (fetch-abstracts,
  fetch-withdrawn, refresh-assets, enrich-abstracts, title-audit,
  embed-matrix, semantic-analysis, cluster-benchmark, umap-plot,
  compare-projections, optimize-projections, build-atlas-package,
  upload-atlas-package, compare-data-hosting, book, write-manifest, …) —
  unchanged names, args, and behavior.
- Module form: `python -m abstractatlas.cli <subcommand>` (docs/CI updated
  from `-m ohbm2026.cli`).

## New ingestor-facing surface (additive)

- `aacli ingest --source <name>` — run a registered ingestor by name
  (e.g. `ohbm-2026`, `neuroscape-pubmed`). Unknown name → precise error
  listing registered names (FR-010).
- `aacli list-ingestors` — print the runtime-discovered registry (names +
  source_type). Optional convenience; the existing per-source subcommands
  (`fetch-abstracts`, `build-atlas-package`) continue to work unchanged and
  may delegate to their ingestor internally.

> The existing subcommands remain the canonical way to run the two current
> sources (no behavior change); `ingest`/`list-ingestors` are the general
> surface that makes future sources first-class without new bespoke
> subcommands.

## Deprecation

- `ohbmcli <args>` → stderr: `ohbmcli is deprecated; use 'aacli'. Delegating…`
  then runs `aacli <args>`. Removed next cycle.
- `python -m ohbm2026.cli` → shim module warns + delegates.

## Verification

- SC-001: for each existing subcommand, `aacli <sub>` output + written
  artifacts identical to the pre-rename `ohbmcli <sub>` on fixtures.
- `aacli ingest --source ohbm-2026` reproduces `fetch-abstracts` normalized
  output; `--source nope` errors with the known-names list.
- `ohbmcli` emits the deprecation notice and still succeeds (SC-007).
