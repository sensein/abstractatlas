# Feature Specification: Refactor Shared Utils And Cache Governance

**Feature Branch**: `001-refactor-cache-utils`  
**Created**: 2026-03-28  
**Status**: Draft  
**Input**: User description: "clean up code based on recommendations, create any
shared utils as much as possible. consider what data and cache look like based
on expensive (time/cost/resource) operations look like and routes to
invalidate/regenerate cache"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clean Up Repeated Maintenance Work (Priority: P1)

As a repository maintainer, I want repeated cleanup work to follow shared
repository rules and reusable patterns so that I can improve large workflows
without rediscovering the same conventions in multiple places.

**Why this priority**: The review identified concentrated ownership and repeated
maintenance cost as the highest-priority repo health risk. Establishing shared
behavior first makes later refactors safer and easier to review.

**Independent Test**: Review a refactor slice for one expensive workflow and
confirm that shared behavior is defined once, follows repo-wide rules, and does
not require parallel changes to multiple unrelated areas to stay consistent.

**Acceptance Scenarios**:

1. **Given** a maintainer is updating an in-scope expensive workflow, **When**
   they inspect the repo guidance and feature outputs, **Then** they can locate
   the shared rules for repeated behaviors instead of inferring them from
   duplicated code paths.
2. **Given** a reviewer inspects a cleanup change in scope, **When** they trace
   the affected behavior, **Then** they can see a bounded cleanup objective
   rather than a single change spread across unrelated responsibilities.

---

### User Story 2 - Distinguish Canonical Data From Regenerable Caches (Priority: P1)

As a pipeline operator, I want expensive outputs to be clearly categorized as
canonical data, reusable cache, or disposable scratch so that I can make safe
rerun and cleanup decisions without guessing.

**Why this priority**: The repository already contains costly outputs from
external analysis, enrichment, and downstream processing. Operators need clear
boundaries before they can invalidate or rebuild anything safely.

**Independent Test**: Pick an in-scope expensive workflow and verify that an
operator can determine which outputs are authoritative, which are resumable
caches, and which can be regenerated from upstream artifacts.

**Acceptance Scenarios**:

1. **Given** an operator is preparing to rerun an expensive workflow, **When**
   they inspect the documented artifact set, **Then** they can tell which files
   must be preserved and which can be regenerated.
2. **Given** an operator finds a stale or partial expensive output, **When**
   they consult the feature outputs, **Then** they can identify the correct
   invalidation scope without deleting unrelated canonical artifacts.

---

### User Story 3 - Recover From Stale Or Interrupted Expensive Work (Priority: P2)

As a pipeline operator, I want explicit invalidation and regeneration routes for
expensive work so that I can recover from model changes, input changes, or
interrupted runs without trial-and-error cleanup.

**Why this priority**: Once artifact boundaries are clear, the next value is a
predictable recovery path. This reduces wasted time, cost, and accidental data
loss during reruns.

**Independent Test**: Simulate a stale cache or interrupted run for an
in-scope workflow and verify that the operator can choose a documented
regeneration route that preserves unaffected authoritative outputs.

**Acceptance Scenarios**:

1. **Given** a workflow depends on expensive upstream work, **When** its inputs,
   defaults, or supporting metadata change, **Then** the operator can identify
   whether selective invalidation or full regeneration is required.
2. **Given** an interrupted run left partial progress behind, **When** the
   operator follows the documented recovery route, **Then** they can resume or
   rebuild without manually reconstructing the intended artifact lifecycle.

### Edge Cases

- A cache contains partial progress from an interrupted run and mixes successful
  and failed records.
- A derived output was produced from older defaults while upstream canonical
  inputs remain current.
- Two expensive workflows share upstream inputs but have different regeneration
  costs, so invalidation cannot be treated as all-or-nothing.
- A workflow depends on credentials or environment-local settings, but cache and
  artifact metadata must remain secret-safe.
- Local scratch outputs exist beside recorded artifacts and must not be mistaken
  for canonical or reusable cache state.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define the in-scope cleanup target as the set of
  repeated maintenance behaviors associated with expensive or long-running
  workflows identified by the current repository review and operator runbooks.
- **FR-002**: The system MUST describe a shared repository-level contract for
  repeated behaviors that are currently rediscovered across in-scope cleanup
  targets.
- **FR-003**: The system MUST identify the in-scope artifact classes for
  expensive workflows, including authoritative outputs, resumable caches, and
  disposable scratch artifacts.
- **FR-004**: The system MUST state the upstream dependency basis for each
  in-scope expensive artifact class so an operator can tell what it depends on
  before deleting or regenerating it.
- **FR-005**: The system MUST define the invalidation triggers for each in-scope
  cache or regenerable artifact class, including input changes, default changes,
  interrupted progress, and stale metadata.
- **FR-006**: The system MUST define the approved regeneration route for each
  in-scope cache or regenerable artifact class, including whether selective
  resume, selective rebuild, or full rebuild is expected.
- **FR-007**: The system MUST preserve the distinction between canonical
  repository outputs and exploratory or scratch outputs during cleanup and cache
  lifecycle decisions.
- **FR-008**: The system MUST provide operator-facing guidance that lets a
  reviewer or maintainer understand the cleanup boundary and cache lifecycle
  without consulting commit history or tribal knowledge.
- **FR-009**: The system MUST require verification for each cleanup slice that
  demonstrates unchanged intended behavior while confirming the new artifact and
  cache rules remain accurate.
- **FR-010**: The system MUST ensure that cache descriptions, invalidation
  guidance, and regeneration routes never require checked-in credentials or
  expose secret values.

### Key Entities *(include if feature involves data)*

- **Cleanup Slice**: A bounded maintenance target within an expensive workflow
  that can be reviewed and verified independently.
- **Artifact Class**: A named category that distinguishes canonical outputs,
  resumable caches, and disposable scratch products.
- **Dependency Basis**: The upstream inputs, defaults, or metadata conditions
  that determine whether an artifact remains valid.
- **Invalidation Trigger**: A defined reason an artifact or cache must be
  resumed, rebuilt, or left untouched.
- **Regeneration Route**: The approved operator path for selectively resuming or
  rebuilding an invalidated artifact class.

### Constitution Alignment *(mandatory)*

- **CA-001**: All verification and regeneration work described by this feature
  MUST use the repository-approved isolated Python environment defined by the
  constitution.
- **CA-002**: Each cleanup slice in scope MUST identify the verification to add
  or update before implementation begins.
- **CA-003**: Any change to canonical defaults, artifact locations, or
  regeneration routes MUST update the relevant runbook and planning documents in
  the same change.
- **CA-004**: Cache metadata and documentation MUST refer only to secret
  boundaries or environment variable names, never credential values.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Operators can classify 100% of the expensive artifact classes in
  scope as canonical, resumable cache, or disposable scratch using checked-in
  project outputs alone.
- **SC-002**: For every in-scope expensive workflow, an operator can identify
  the correct invalidation and regeneration route in under 5 minutes without
  consulting commit history.
- **SC-003**: Reviewers can evaluate each in-scope cleanup slice independently,
  with each slice having an explicit verification method and a clearly bounded
  purpose.
- **SC-004**: Recovery from a stale or interrupted in-scope workflow can be
  completed without deleting unaffected canonical outputs in all documented
  rerun scenarios.

## Assumptions

- The initial scope will focus on the expensive and long-running workflows
  highlighted by the current repository review rather than attempting a whole-
  repo reorganization in one pass.
- Existing authoritative artifacts remain the source of truth unless the feature
  explicitly reclassifies them in checked-in documentation or metadata.
- Selective invalidation is preferable to full rebuilds when upstream evidence
  allows unaffected outputs to remain valid.
- The feature may introduce shared repository rules or reusable maintenance
  patterns, but it is not expected to change end-user-facing scientific results
  by itself.
