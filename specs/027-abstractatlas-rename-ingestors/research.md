# Phase 0 Research: Abstract Atlas Rename + Pluggable LinkML Ingestors

The three highest-impact unknowns were resolved with the requester before
planning (build scope, rename reach, CLI name). The remaining decisions are
recorded here.

## R1 — Rename mechanics: move + import-rewrite, verified as a mechanical slice

**Decision**: Rename by (a) `git mv src/ohbm2026 src/abstractatlas`, (b) a
mechanical rewrite of `ohbm2026` → `abstractatlas` across imports and string
references, (c) `pyproject.toml` package name + entry points, (d) docs +
tests + CI `PYTHONPATH`/`-m` invocations. Land it as ONE slice and prove it
with SC-001 (identical artifacts on a fixture run) + SC-002 (full suite
green) before any ingestor work.

**Rationale**: The rename is broad (~86 files) but mechanical; isolating it
keeps the diff reviewable and lets a regression be attributed to the rename,
not the architecture. `git mv` preserves history.

**Alternatives considered**:
- *Rename incrementally alongside the ingestor work* — rejected: entangles a
  mechanical rename with a design change, making regressions ambiguous.
- *Keep `ohbm2026` as the package, only rename the CLI* — rejected: the ask
  is to re-frame the whole component; a half-rename leaves the confusing
  single-instance name in every import.

## R2 — Data-name preservation vs. package rename (the intentional divergence)

**Decision**: Preserve every on-disk path, state-key/cache/checkpoint key,
and published data-package name — including the historical `ohbm2026.parquet`
— verbatim. The package is `abstractatlas`; the *OHBM source's* data keeps
its `ohbm2026` name because that is the name of that source's data, not the
component. Document this divergence prominently (README + rename-map).

**Rationale**: The requester chose "preserve data" → no regeneration, no
site re-publish, byte-identical (FR-004, SC-003). Data names are a source
identity, not the component identity, so the divergence is correct, not
debt. Renaming published names would force a data rebuild + site loader/URL
registry changes — explicitly out of scope.

**Alternatives considered**: rename data names too (the "Full rename"
option) — rejected by the requester for continuity.

## R3 — Legacy name policy (`ohbmcli`, `import ohbm2026`)

**Decision (updated per requester): HARD CUTOVER — no deprecation shims.**
`aacli` / `abstractatlas` are the sole names. The `ohbmcli` entry point and
any `ohbm2026` import path are removed; using them fails loudly with the
standard not-found error (`command not found: ohbmcli` /
`ModuleNotFoundError: No module named 'ohbm2026'`). The venv is reinstalled
(`uv pip uninstall ohbm2026 && uv pip install -e .`) so a previously
pip-installed `ohbm2026` dist doesn't mask the cutover.

**Rationale**: The requester opted for a clean break — no shim to maintain
or later remove. A bare not-found error is loud and unambiguous (satisfies
FR-003/SC-007's "never silent/partial"), and there is no external
consumer that needs a grace period.

**Alternatives considered**: a labeled deprecation shim (`ohbmcli` warns +
delegates; `ohbm2026` meta-path redirect) — implemented first, then
**removed** at the requester's direction in favour of the hard cutover.

## R4 — Ingestor contract: wrap, don't rewrite

**Decision**: `abstractatlas/ingest/base.py` defines an `Ingestor` ABC:
`name`, `source_type` (enum: `conference` | `literature_index`),
`pull()` (acquire raw records from the origin), `normalize(raw)` → records
conforming to the ingest schema, and `ingest()` orchestrating pull →
normalize → validate. The OHBM ingestor wraps the existing
`fetch/stage.py` + `assets.normalize_abstract`; the NeuroScape ingestor
wraps the existing NeuroScape record normalization used by `atlas_package`.
Neither rewrites logic — they adapt existing code behind the contract.

**Rationale**: Wrapping guarantees byte-identical outputs (SC-003) and zero
downstream change (SC-004/FR-009). The contract is the seam future sources
implement; the two ports are the worked examples (SC-006).

**Alternatives considered**: rewrite both ingestion paths into a unified
new pipeline — rejected: high risk of output drift, violates the
data-preservation constraint, and is far larger than the foundation scope.

## R5 — Registry: runtime discovery, not a hardcoded list

**Decision**: `registry.py` maintains a name→`Ingestor` mapping populated by
registration (decorator/entry-point style), queried at runtime by the CLI +
orchestration. An unknown ingestor name raises a precise error listing the
registered names. No hardcoded source allow-list anywhere downstream.

**Rationale**: Constitution VII / FR-010 — onboarding a new source must not
require editing a central list or downstream stages; mismatches surface
loudly.

## R6 — Standardized ingest schema in LinkML

**Decision**: `contracts/ingest-schema.linkml.yaml` defines an
`IngestedDocument` core class (identity, title, authors, abstract/summary
text, `source` provenance block) plus source-type extension classes/mixins:
`ConferenceDocument` (program/session/poster identifiers) and
`LiteratureDocument` (DOI, venue, index id, year). Each ingestor validates
its emitted records against the schema (via the `linkml`
validator, mirroring `scripts/validate_ui_data.sh`). The core is designed to
**capture the existing OHBM normalized shape** so the ported output
validates unchanged — the schema documents/validates, it does not reshape.

**Rationale**: LinkML is already the project's schema language for UI/export
contracts, so the tooling + reviewer familiarity exist. A core+extensions
model expresses conference/literature asymmetry cleanly (edge case) while
giving downstream one contract (FR-007/FR-008, US3).

**Alternatives considered**:
- *Pydantic-only models* — rejected: LinkML is the established contract
  language here and gives machine-readable schema + validation for free.
- *One flat schema with every field optional* — rejected: lets a conference
  record masquerade as literature (edge case); source-typed extensions
  prevent that.

## R7 — Entry-point sprawl (`ohbm-*` scripts)

**Decision**: The canonical `ohbmcli` → `aacli`. The ~14 legacy `ohbm-*`
per-stage scripts (mostly superseded by `aacli` subcommands) are renamed to
`aa-*` **only if still used**; unused/legacy ones are dropped (their
functions remain importable). The rename-map enumerates each with its
disposition.

**Rationale**: Keeps the canonical surface clean without silently removing a
script someone depends on; the rename-map is the auditable record.
