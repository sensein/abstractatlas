# Phase 1 Data Model — Conference subpath rework

**No data-model changes.** The data package's `build_info` envelope, the per-shard schemas, the LinkML contract, and the `OHBM2026_UI_DATA_PACKAGE_*` repo variables remain byte-identical pre- and post-rework. SC-105 makes this an explicit verification gate.

This is intentional per the spec's "we don't need to generalize every bit" guidance (FR-109). A future feature that hosts a second conference will introduce a `conference` or `conference_id` field at the manifest level — at that point a new spec will own that data-model change. This rework does not.

## Entities

The only entity introduced is implicit, at the build-config layer, not the data layer:

### Conference subpath

| Field | Type | Source | Notes |
|---|---|---|---|
| `paths.base` | string | `svelte.config.js` (or `BASE_PATH` env override) | `/ohbm2026` for production; `/pr-<N>/ohbm2026` for PR previews |

It has no representation in any JSON shard.

## Validation rules

| Rule | Where enforced | Failure mode |
|---|---|---|
| LinkML schema unchanged | `scripts/validate_ui_data.sh` | If any shard's envelope changes, validation fails before deploy. SC-105 gate. |
| `build_info` envelope byte-identical | manual `diff` in the validation task | Diffing the production shards pre- and post-rework MUST yield zero bytes of change in `build_info`. |

## State transitions

None — there is no state.
