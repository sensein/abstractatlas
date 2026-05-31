# Implementation Plan: Cloudflare R2 Migration & Content-Hashed Data Store

**Branch**: `020-cloudflare-r2-migration` | **Date**: 2026-05-31 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/020-cloudflare-r2-migration/spec.md`

## Summary

Add Cloudflare R2 (S3-compatible object store) as an alternative home for the
four atlas-package parquet artifacts, served to the browser through the
**existing** channel-registry mechanism — no change to `resolve-data-channel.sh`
or the site's fetch path, because R2 URLs are opaque to the loader and the
Dropbox-only rewrite leaves them untouched. Build a local `ohbmcli` uploader
that stores each artifact under a **content-addressed, immutable key**
(`<sha256>/<filename>`), is idempotent (skip-if-exists, zero re-upload on an
unchanged build), never overwrites prior versions, and emits a ready-to-paste
registry channel entry plus a machine-readable upload manifest (provenance).
Add a `compare-data-hosting` command that probes Dropbox vs R2 for byte-parity,
CORS, and Range support and writes a pass/fail report — the evidence for a
later, deferred production cutover.

Two new `ohbmcli` subcommands (`upload-atlas-package`, `compare-data-hosting`)
in a new `src/ohbm2026/atlas_hosting/` package, a new `Stage20Error` exception
subtree, a new optional `r2` dependency group (`boto3`), and one site-side
vitest test confirming R2 URLs pass through `normaliseDropboxUrl` unchanged.
The atlas-package build itself is unchanged — this feature only publishes its
output and validates the result.

## Technical Context

**Language/Version**: Python 3.11+ (repo-local `.venv`); TypeScript/Svelte for the single site-side test.
**Primary Dependencies**: `boto3` (NEW optional group `r2`, S3 client for R2); `requests>=2.31` (already present in the `ui` group) for the comparison probes; stdlib `hashlib`/`json`/`argparse`. Site: `hyparquet` (existing) — Range fetch via `asyncBufferFromUrl`; `vitest` (existing).
**Storage**: Cloudflare R2 bucket (S3 API), objects keyed by content hash; local upload manifests under `data/provenance/`, comparison reports under `data/outputs/` (both inside the gitignored `data/` root). R2 credentials in `.env`.
**Testing**: `unittest` (Python, mirrors `tests/test_atlas_*.py`, `TemporaryDirectory` fixtures, boto3 stubbed via `botocore.stub.Stubber`); `vitest run` for the site URL-passthrough test (per memory: `vitest run`, never `pnpm test:unit -- --run`).
**Target Platform**: Local operator machine (darwin/linux) for the CLI; the browser for the consuming site.
**Project Type**: CLI additions to an existing single-repo Python pipeline (`src/ohbm2026/`) plus one test in the self-contained `site/` SvelteKit subproject.
**Performance Goals**: Idempotent re-upload transfers zero artifact bytes (existence check via `head_object`); browser per-table Range fetch unchanged (~KB–few-hundred-KB, not full file); comparison is a one-shot validation run.
**Constraints**: No committed data (`data/` is gitignored); secrets only in `.env`, never logged or written into manifests/reports/channel snippets; uploaded objects are immutable (never overwritten/deleted); site code requires no structural change.
**Scale/Scope**: 4 artifacts per package (`ohbm2026`/`neuroscape`/`atlas` required + optional `neuroscape_vectors` ~hundreds of MB); a handful of package versions accumulate over time.

No `NEEDS CLARIFICATION` remain: the three scope decisions were resolved with the operator before the spec was written (add-channel + validate, defer cutover; build the uploader now; local CLI with `.env` creds), and the remaining technical choices have clear best-practice answers captured in `research.md`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Venv-only Python (I)**: ✅ Both new commands and all Python tests run via `.venv/bin/python -m ohbm2026.cli …` / `PYTHONPATH=src .venv/bin/python -m unittest …`. `boto3` installed into `.venv` via the `r2` extra. No system Python.
- **Plan-first, test-first (IV)**: ✅ Phase 1 names the failing tests to add first (see `data-model.md` validation table + the per-story test list in `quickstart.md` §Tests). Behavior tests: content-hash key derivation, `head_object` skip-if-exists dedup, non-destructive upload, missing-artifact discovery error, manifest schema + no-absolute-paths, channel-entry emission, comparison verdicts + fail-loud aggregation, and the site URL-passthrough test — each written and red before implementation.
- **Immutable evidence / auditability (II, III)**: ✅ R2 objects are content-addressed → publishing never overwrites; manifests are append-only, one per upload keyed by an upload-state-key (`atlas_upload_provenance__<key>.json`). The build is unchanged.
- **No committed data (II)**: ✅ Manifests (`data/provenance/`) and reports (`data/outputs/`) live inside the gitignored `data/` root (`.gitignore:7` `data/`). A stage-specific ignore line (`data/provenance/atlas_upload_provenance__*.json`, `data/outputs/data-hosting-comparison__*.json`) is added for convention before any write. No parquet/manifest/report is tracked.
- **Fail loudly, no shortcuts (VI)**: ✅ New typed `Stage20Error` subtree; `head_object` 404 is caught precisely via `botocore.exceptions.ClientError` (code `404`/`NoSuchKey`), never a bare except; missing creds, hash mismatch, partial-upload, and failed probes re-raise with context. Dedup skips are logged, not silent. No `--no-verify`, no skipped tests.
- **Discover external state (VII)**: ✅ Existence is discovered at runtime (`head_object` per content-addressed key) — not a hardcoded "already uploaded" list; the package's artifact set is discovered by listing the build output dir (required set validated, optional `neuroscape_vectors` detected, unexpected files flagged); Range/CORS are probed against the live endpoint, never assumed.
- **Provenance (VIII)**: ✅ The upload manifest is the data bundle's machine-readable provenance (source build `state_key`s, per-artifact content hash/size/key/URL, `code_revision`, `command_line`, `uploaded_utc`); paths run through the reused `provenance.normalise_path` rejecting absolute/`~` paths.
- **Secret-safe (V)**: ✅ R2 creds referenced by env-var name only (`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`, `R2_PUBLIC_BASE_URL`), read via the existing `get_api_key(env_path, env_var)` helper (`fetch/graphql_api.py:201`); never logged, never written to manifest/report/snippet. The emitted channel snippet contains only public URLs + content hashes.
- **Docs sync (IV)**: ✅ Same-change updates: `README.md` (new subcommands + R2 publish runbook + env vars), `CLAUDE.md` (data-hosting note), and the explanatory comments in `.github/scripts/resolve-data-channel.sh` + `site/data-channel.json` (registry may now hold R2 URLs; no code change).
- **Commit per slice + push (V)**: ✅ Delivery commits each verified slice (deps+exceptions → upload core → CLI wiring → compare → site test → docs) with descriptive messages; pushes when the operator runs the change, unless they ask to keep it unpublished.

**Result: PASS** (no violations; Complexity Tracking left empty).

## Project Structure

### Documentation (this feature)

```text
specs/020-cloudflare-r2-migration/
├── plan.md              # This file
├── research.md          # Phase 0 — decisions: key scheme, S3 client, dedup, probes, creds
├── data-model.md        # Phase 1 — ContentAddressedObject, UploadManifest, ChannelEntry, ComparisonReport
├── quickstart.md        # Phase 1 — operator runbook + the test list
├── contracts/
│   ├── cli-upload-atlas-package.md     # `ohbmcli upload-atlas-package` command contract
│   ├── cli-compare-data-hosting.md     # `ohbmcli compare-data-hosting` command contract
│   ├── r2-storage-layout.md            # content-addressed key scheme + bucket config (public read, CORS, cache)
│   ├── upload-manifest.schema.json     # JSON Schema for the upload manifest
│   └── comparison-report.schema.json   # JSON Schema for the comparison report
├── checklists/
│   └── requirements.md  # (from /speckit-specify)
└── spec.md
```

### Source Code (repository root)

```text
src/ohbm2026/
├── cli.py                       # MODIFY: register + dispatch `upload-atlas-package`, `compare-data-hosting`
├── exceptions.py                # MODIFY: add Stage20Error subtree (R2 cred/upload/hash/comparison errors)
├── artifacts.py                 # REUSE: _stable_hash / build_state_key for the upload-state-key
├── atlas_package/
│   └── provenance.py            # REUSE: normalise_path() for manifest path sanitisation
└── atlas_hosting/               # NEW package (Stage 20)
    ├── __init__.py
    ├── cli.py                   # build_parser()/main() for BOTH subcommands (mirrors atlas_package/cli.py)
    ├── content_hash.py          # sha256-of-file + object-key derivation (<sha256>/<filename>)
    ├── r2_client.py             # boto3 client factory from .env; head_object existence; upload_file (multipart)
    ├── uploader.py              # discover artifacts → hash → skip-or-upload → manifest + channel snippet
    ├── manifest.py              # UploadManifest dataclass + JSON (de)serialise + schema-shaped dict
    └── compare.py               # Dropbox↔R2 byte-parity / CORS / Range probes → ComparisonReport

tests/
├── test_atlas_hosting_content_hash.py   # NEW: key derivation, stable + collision-distinct
├── test_atlas_hosting_uploader.py       # NEW: dedup skip, non-destructive, discovery error, manifest no-abs-paths (boto3 Stubber)
├── test_atlas_hosting_compare.py        # NEW: parity/CORS/Range verdicts + fail-loud aggregation (requests mocked)
├── test_atlas_hosting_cli.py            # NEW: argparse surface + dispatch + exit codes
└── test_stage20_exceptions.py           # NEW: Stage20Error subtree contract (mirrors test_atlas_exceptions.py)

site/src/tests/unit/
└── loader_r2_passthrough.test.ts        # NEW: non-Dropbox HTTPS URL returns unchanged from normaliseDropboxUrl

pyproject.toml                           # MODIFY: add optional group  r2 = ["boto3>=1.34"]
.gitignore                               # MODIFY: stage-20 manifest/report ignore lines (convention)
README.md                                # MODIFY: R2 publish runbook + env vars + new subcommands
CLAUDE.md                                # MODIFY: data-hosting note (R2 channel alongside Dropbox)
.github/scripts/resolve-data-channel.sh  # MODIFY (comment only): registry may now hold R2 URLs
site/data-channel.json                   # (operator) point a branch at the new R2 channel for validation
```

**Structure Decision**: New self-contained `src/ohbm2026/atlas_hosting/` package, parallel to `atlas_package/`, keeping the publish/validate concern separate from the build concern. Both subcommands live in one `atlas_hosting/cli.py` (mirroring how `atlas_package/cli.py` exposes `build_parser()`/`main()` and is wired into the top-level `cli.py` via `_copy_actions` + a dispatch entry). Reuses `artifacts._stable_hash` (state-keys), `atlas_package.provenance.normalise_path` (path safety), `fetch.graphql_api.get_api_key` (`.env` reads), and the existing channel-registry/`resolve-data-channel.sh`/`data-channel.json` mechanism unchanged.

## Complexity Tracking

> No Constitution Check violations — no entries.
