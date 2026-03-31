# Data Model: Refactor Shared Utils And Cache Governance

## Entities

### Input Snapshot

- **Purpose**: Stores GraphQL-fetched abstract source data under `data/inputs/`
  so source inputs remain distinct from caches and outputs.
- **Fields**:
  - `source_name`: stable input identifier
  - `path`: deterministic path under `data/inputs/`
  - `generated_at`: UTC timestamp
  - `input_digest`: fingerprint of fetched source content
  - `status`: `ready`, `stale`, or `superseded`
  - `source_metadata`: upstream fetch context without secrets
- **Relationships**:
  - one Input Snapshot can feed many Artifact Records
- **Validation rules**:
  - input snapshots must never be stored under cache or output directories
  - input snapshots must not contain credential values

### Artifact Class

- **Purpose**: Names the role an artifact plays in the repository lifecycle.
- **Fields**:
  - `name`: stable identifier such as `input`, `cache`, `output`, or `scratch`
  - `git_tracked`: whether the class is ever eligible for git tracking
  - `base_root`: filesystem root such as `data/inputs/`, `data/cache/`,
    `data/outputs/`, `export/`, or `tmp/`
  - `retention_rule`: preservation expectation
  - `resume_capable`: whether partial progress can be resumed
- **Relationships**:
  - one Artifact Class applies to many Artifact Records
- **Validation rules**:
  - `input` artifacts must remain distinct from caches and outputs
  - `cache`, `output`, and `scratch` classes must remain untracked in git for
    this feature

### Output Family

- **Purpose**: Differentiates output retention and regeneration rules.
- **Fields**:
  - `name`: `experiments`, `exported-sites`, or `proposals`
  - `path_root`: family directory under `data/outputs/`
  - `retention_rule`: lifecycle expectation for that family
  - `publication_step`: whether an additional publish/export step exists
- **Relationships**:
  - one Output Family applies to many Artifact Records of class `output`
- **Validation rules**:
  - every output artifact in scope belongs to exactly one family
  - families must remain distinguishable in path and metadata

### Artifact Record

- **Purpose**: Describes a concrete file or directory produced or consumed by an
  expensive workflow.
- **Fields**:
  - `workflow`: workflow namespace such as `graphql_fetch`,
    `figure_analysis`, `claim_analysis`, `reference_metadata`, `embeddings`,
    `exported_site`, or `proposal_generation`
  - `artifact_name`: stable artifact identifier
  - `artifact_class`: owning Artifact Class
  - `output_family`: Output Family when `artifact_class = output`
  - `path`: direct filesystem location
  - `state_key`: deterministic identifier for direct lookup
  - `generated_at`: UTC timestamp recorded in metadata
  - `status`: `missing`, `running`, `ready`, `stale`, `error`, or `superseded`
  - `producer`: command or module that produced the record
  - `schema_version`: artifact metadata version
- **Relationships**:
  - each Artifact Record belongs to one Artifact Class
  - each output Artifact Record belongs to one Output Family
  - each Artifact Record may depend on one Dependency Basis
- **Validation rules**:
  - `path` must be derivable from class/family/workflow plus `state_key`
  - `generated_at` is required for caches and outputs
  - `status` must reflect whether the artifact can be resumed or regenerated

### Dependency Basis

- **Purpose**: Captures the conditions that determine whether an artifact is
  still valid.
- **Fields**:
  - `input_sources`: upstream files or artifact references
  - `input_digest`: normalized fingerprint of the relevant upstream state
  - `backend`: provider/backend choice if applicable
  - `model`: model identifier if applicable
  - `options_digest`: fingerprint of invalidation-relevant options
  - `env_boundary`: env-var names or secret boundary references only
  - `supersedes`: prior state key if this record replaces another
- **Relationships**:
  - one Dependency Basis can be referenced by many Artifact Records
- **Validation rules**:
  - secret values must never appear in `env_boundary`
  - dependency fields must be sufficient to explain invalidation decisions

### Regeneration Policy

- **Purpose**: Defines how to recover when an artifact record becomes stale or
  incomplete.
- **Fields**:
  - `workflow`: owning workflow namespace
  - `artifact_name`: target artifact
  - `artifact_class`: affected class
  - `output_family`: affected family when relevant
  - `trigger`: reason for invalidation
  - `action`: `resume`, `selective_rebuild`, or `full_rebuild`
  - `preserve_classes`: artifact classes that must remain untouched
  - `notes`: operator-facing recovery guidance
- **Relationships**:
  - one Regeneration Policy can apply to many Artifact Records of the same type
- **Validation rules**:
  - policies must preserve unaffected inputs
  - every cache or output family in scope requires at least one recovery route

### Cleanup Slice

- **Purpose**: Tracks a bounded implementation/refactor target for this feature.
- **Fields**:
  - `name`: slice identifier
  - `workflows`: in-scope workflows touched by the slice
  - `shared_rules`: reusable behavior extracted by the slice
  - `verification`: tests or checks required before merge
  - `docs_to_update`: operator docs affected by the slice
- **Relationships**:
  - one Cleanup Slice can affect many Artifact Records and Regeneration Policies
- **Validation rules**:
  - each slice must be independently reviewable and verifiable
  - each slice must document whether defaults or paths changed

## State Transitions

### Input Lifecycle

1. `ready` -> `stale`
   - The fetched GraphQL snapshot no longer matches the desired source state.
2. `stale` -> `superseded`
   - A newer snapshot replaces it.

### Cache and Output Lifecycle

1. `missing` -> `running`
   - A workflow starts producing a cache or output.
2. `running` -> `ready`
   - Enough metadata and artifact content exist for direct reuse.
3. `running` -> `error`
   - Execution failed but metadata remains for diagnosis or selective resume.
4. `ready` -> `stale`
   - Dependency Basis no longer matches the current input, model, options, or
     schema state.
5. `stale` -> `running`
   - A regeneration route is selected.
6. `ready` -> `superseded`
   - A newer state key replaces the artifact while preserving history or audit
     metadata.

### Cleanup Slice Lifecycle

1. `defined`
   - Scope and verification are documented.
2. `implemented`
   - Shared rules and path handling are updated in code.
3. `verified`
   - Tests and path/ignore checks pass.
4. `documented`
   - README and operator docs are updated to reflect the new lifecycle.
