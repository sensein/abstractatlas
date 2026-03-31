# Contract: Cache Metadata And Invalidation

## Purpose

Define the metadata required for direct lookup, invalidation, and regeneration
of fetched inputs, expensive workflow caches, and derived output families.

## Required Metadata

Each in-scope input, cache, or output record must expose, either in the file
payload or an adjacent metadata structure, the following fields:

- `artifact_name`
- `artifact_class`
- `workflow`
- `state_key`
- `generated_at`
- `status`
- `input_sources`
- `input_digest`
- `options_digest`
- `backend` when applicable
- `model` when applicable
- `output_family` when applicable
- `schema_version`
- `env_boundary` using env-var names only

## State-Key Rules

- `state_key` must be deterministic for the same dependency basis.
- `state_key` must change when invalidation-relevant inputs, model choices,
  options, output-family-relevant defaults, or schema versions change.
- `state_key` must be sufficient for direct lookup without a directory search.

## Invalidation Triggers

An artifact becomes stale when any of the following change:

- fetched input content relevant to the artifact
- model or backend selection
- invalidation-relevant workflow options
- output family defaults or publication assumptions
- schema or metadata version
- error/interruption status that prevents trusted reuse

## Regeneration Actions

- `resume`: continue writing the same state key after partial progress
- `selective_rebuild`: create a new state key for the affected artifact class or
  output family while preserving unaffected inputs
- `full_rebuild`: regenerate all downstream artifacts whose dependency basis no
  longer matches

## Secret-Safety Rules

- Metadata may record env-var names such as `OPENAI_API_KEY` or `VOYAGE_API`.
- Metadata must never record token values, copied secret strings, or request
  payloads that reveal credentials.
