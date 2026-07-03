# Contract: rename map (identity change, data preserved)

The authoritative old→new mapping. **Data names are deliberately NOT
renamed** (FR-004). Verified by SC-001 (identical artifacts) + SC-002 (suite
green) + SC-003 (byte-identical published data).

## Renamed (code / CLI / docs)

| Kind | Old | New |
|------|-----|-----|
| Python package | `src/ohbm2026/` | `src/abstractatlas/` (`git mv`) |
| Import root | `ohbm2026.*` | `abstractatlas.*` |
| pyproject `name` | `ohbm2026` | `abstractatlas` |
| Canonical CLI | `ohbmcli` | `aacli` |
| Module invocation | `python -m ohbm2026.cli` | `python -m abstractatlas.cli` |
| Legacy scripts | `ohbm-ingest`, `ohbm-authors`, `ohbm-enrich`, `ohbm-analyze-figures`, `ohbm-embed-stage2`, `ohbm-apply-published-stage2`, `ohbm-cluster-benchmark`, `ohbm-semantic-analysis`, `ohbm-umap-plot`, `ohbm-compare-projections`, `ohbm-optimize-projections`, `ohbm-analyze-stage2`, `ohbm-reference-metadata`, `ohbm-write-manifest` | `aa-*` **iff still used**; otherwise dropped (functions stay importable). Disposition recorded per script in tasks. |
| Docs | README, CLAUDE.md, constitution naming refs | updated to `abstractatlas`/`aacli` (FR-012) |
| Site test strings | `ohbm2026` refs in `site/src/**` tests | updated where they name the package (NOT the `ohbm2026` data/site-mode/route which is the source identity) |

## Deprecated shims (one transition period)

| Legacy | Behavior |
|--------|----------|
| `ohbmcli` entry point | prints "renamed to `aacli`" deprecation notice, then delegates to `aacli` |
| `import ohbm2026` | thin shim re-exporting `abstractatlas` with a `DeprecationWarning`; labeled + follow-up to remove |

Shims MUST be labeled in code with root cause + removal follow-up
(Constitution VI). Neither may partially work in a confusing way (FR-003).

## NOT renamed (data identity — FR-004)

| Preserved | Why |
|-----------|-----|
| `data/primary/`, `data/cache/`, `data/inputs/`, `data/outputs/` paths | no data regeneration |
| state-key / cache-key / checkpoint naming (incl. embedded `ohbm2026`) | prior expensive work stays discoverable/resumable |
| published `ohbm2026.parquet` (+ site data-package names) | byte-identical site data; no re-publish; the name is the OHBM *source's* data identity, not the component |
| `/ohbm2026/` site route, `SITE_MODE='ohbm'`, `OHBM2026_*` CI vars | source/deployment identity, out of rename scope |

## Verification hooks

- SC-001: fixture run under `aacli` produces artifacts identical (path+content) to a pre-rename run.
- SC-002: `.venv/bin/python -m unittest discover -s tests` fully green under new names.
- SC-007: invoking `ohbmcli` / `import ohbm2026` emits the labeled deprecation, never a silent/partial success.
- `git grep -n 'ohbm2026\|ohbmcli'` after the rename returns only: (a) intentional data-identity names in the NOT-renamed table, (b) the deprecation shims, (c) historical spec docs.
