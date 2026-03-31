# Phase 0 Research: Refactor Shared Utils And Cache Governance

## Decision 1: Make `data/inputs/`, `data/cache/`, and `data/outputs/` explicit siblings

- **Decision**: If `data/` remains the parent artifact directory, store
  GraphQL-fetched abstract inputs under `data/inputs/`, resumable caches under
  `data/cache/`, and regenerable outputs under `data/outputs/`.
- **Rationale**: The clarified spec now requires fetched source inputs to be
  distinct from caches and outputs. Sibling directories under `data/` make the
  lifecycle legible without changing the repo’s existing choice to keep local
  artifacts out of git.
- **Alternatives considered**:
  - Keep GraphQL-fetched inputs beside caches or outputs
    - Rejected because it weakens the operator’s ability to reason about source
      versus derivative data.
  - Keep all artifacts flat under `data/`
    - Rejected because it preserves the ambiguity this feature is meant to fix.

## Decision 2: Treat output families explicitly as experiments, exported sites, and proposals

- **Decision**: Model outputs as separate families under `data/outputs/`,
  specifically `experiments/`, `exported-sites/`, and `proposals/`.
- **Rationale**: The clarified spec says outputs must be modeled explicitly as
  experiments, exported sites, and proposals. These families have different
  retention and regeneration rules even when they share upstream inputs.
- **Alternatives considered**:
  - Treat all derived artifacts as one generic output family
    - Rejected because invalidation and operator expectations differ across the
      three output types.
  - Keep exported sites only under `export/`
    - Rejected because the feature needs one coherent local output taxonomy
      before any final publication/export step happens.

## Decision 3: Use deterministic state-keyed paths for direct lookup

- **Decision**: Resolve caches and outputs by a deterministic state key derived
  from workflow inputs, model/default choices, and other invalidation-relevant
  options. Paths take forms such as
  `data/cache/<workflow>/<artifact>__<state-key>.json` and
  `data/outputs/<family>/<artifact>__<state-key>/`, with `generated_at` stored
  in metadata.
- **Rationale**: The user wants cache names to reflect timestamp or state and to
  be looked up directly. A deterministic state key enables direct lookup without
  scanning directories, while metadata retains precise timing information.
- **Alternatives considered**:
  - Timestamp-only filenames
    - Rejected because they are easy to archive but poor for direct lookup.
  - Directory scans to find the newest artifact
    - Rejected because they hide invalidation logic and add operator ambiguity.

## Decision 4: Centralize artifact path and metadata logic in a shared utility layer

- **Decision**: Introduce a shared artifact-governance module responsible for
  path templates, state-key generation, metadata normalization, direct lookup,
  and git-safe directory rules.
- **Rationale**: The review found concentrated logic in large modules, and the
  repo currently duplicates JSON/path helpers across multiple files. A shared
  utility layer is the smallest refactor that improves consistency without
  forcing a whole-repo split.
- **Alternatives considered**:
  - Keep per-module helper functions in `enrichment.py`, `openalex.py`,
    `neuroscape.py`, and `ui.py`
    - Rejected because the same cache and output rules would continue to drift.
  - Perform a full multi-module decomposition first
    - Rejected because it is higher risk and broader than this feature’s scope.

## Decision 5: Invalidate artifacts by dependency basis, not manual deletion habits

- **Decision**: Define invalidation around explicit dependency-basis fields:
  source inputs, model/backend, relevant options, schema/version, artifact
  family, and status. Regeneration routes will choose resume, selective rebuild,
  or full rebuild from that metadata instead of relying on ad hoc file deletion.
- **Rationale**: The expensive workflows already record partial progress and
  backend/model information in several places. Formalizing the dependency basis
  makes stale-cache decisions auditable and predictable.
- **Alternatives considered**:
  - Require operators to delete caches manually whenever uncertain
    - Rejected because it wastes time and increases the risk of deleting valid
      inputs or outputs.
  - Trust only `updated_at` timestamps for invalidation
    - Rejected because timestamps alone do not explain why an artifact is stale.

## Decision 6: Treat git hygiene as part of the contract

- **Decision**: Keep `data/`, `data/inputs/`, `data/cache/`, `data/outputs/`,
  `export/`, and scratch output paths ignored by git, and add verification that
  new artifact locations do not become tracked accidentally.
- **Rationale**: The user explicitly requires that data/cache/outputs are not
  committed. The repo already ignores `data/` and `export/`, so the design
  should preserve that guarantee while making the substructure clearer.
- **Alternatives considered**:
  - Track selected local artifacts in git
    - Rejected because it conflicts with the user requirement and the repo’s
      reproducibility model.
  - Rely on contributor discipline without ignore-path verification
    - Rejected because this feature is supposed to reduce operational guesswork.

## Decision 7: Limit the first migration slice to the highest-cost workflows

- **Decision**: Apply the shared artifact-governance layer first to GraphQL
  input capture, figure analysis, claim extraction, reference metadata,
  embedding-manifest/output helpers, exported-site generation, and proposal-
  adjacent output writers.
- **Rationale**: Those workflows already expose resumable caches, output
  manifests, or expensive downstream products, and they match the review’s
  recommendation to start with the biggest workflow files where boundaries are
  visible.
- **Alternatives considered**:
  - Migrate every script and experiment path in one pass
    - Rejected because it is too broad for one safe cleanup slice.
  - Start with only one workflow
    - Rejected because the shared utility layer needs a few different consumers
      to prove the contract is generic enough.
