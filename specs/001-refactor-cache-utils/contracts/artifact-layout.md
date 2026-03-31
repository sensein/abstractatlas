# Contract: Artifact Layout

## Purpose

Define the filesystem contract for fetched inputs, resumable caches,
regenerable outputs, and scratch work touched by this feature.

## Layout Rules

### Fetched Inputs

- GraphQL-fetched abstract source data lives under:

```text
data/inputs/<input-name>__<state-key>.json
```

- Input snapshots remain distinct from caches and outputs.
- Input snapshots are direct-lookup artifacts keyed by source and state.

### Resumable Caches

- Resumable caches live under:

```text
data/cache/<workflow>/<artifact-name>__<state-key>.json
```

- `workflow` is a stable namespace such as `figure_analysis`,
  `claim_analysis`, or `reference_metadata`.
- `state-key` is deterministic and derived from the dependency basis.
- Direct lookup must compute the path from `workflow`, `artifact-name`, and
  `state-key` without scanning sibling directories.
- Timestamp information is recorded in metadata as `generated_at`; optional
  timestamped history, if retained, must not be required for normal lookup.

### Outputs

- Outputs live under separate family roots:

```text
data/outputs/experiments/<artifact-name>__<state-key>/
data/outputs/exported-sites/<artifact-name>__<state-key>/
data/outputs/proposals/<artifact-name>__<state-key>/
```

- Every output artifact belongs to exactly one family: experiments,
  exported-sites, or proposals.
- Output locations must be derivable directly from family, artifact name, and
  state key.
- If a later publish step mirrors an exported site into `export/`, that publish
  step must not replace the local output family contract.

### Scratch And Disposable Work

- Scratch work remains under explicitly disposable locations such as `tmp/`,
  `logs/`, or experiment-specific fresh run directories.
- Scratch outputs must not share naming conventions that imply reusable cache or
  stable output status.

## Git Tracking Rules

- `data/`, `data/inputs/`, `data/cache/`, `data/outputs/`, `export/`, and
  scratch paths remain ignored by git.
- The implementation must include verification that representative paths under
  `data/inputs/`, `data/cache/`, and `data/outputs/` are ignored.

## Backward-Compatibility Rules

- Existing authoritative data remains addressable while in-scope workflows adopt
  the new layout.
- When defaults move to a new input, cache, or output location, runbooks must
  be updated in the same change.
