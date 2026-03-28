# OHBM 2026 Pipeline Constitution

## Core Principles

### I. Reproducible Venv Execution
All Python actions in this repository MUST run through the repository-local
`.venv/bin/python` interpreter or a `uv` command explicitly targeting that
interpreter. System Python MUST NOT be used for tests, scripts, CLI entrypoints,
dependency installation, or one-off validation commands. New docs, plans, and
automation MUST show `.venv`-scoped Python commands only.

Rationale: the pipeline depends on reproducible local execution, and host-level
Python drift is an avoidable source of breakage.

### II. Immutable Evidence And Canonical Data
Recorded experiment outputs are append-only. New runs MUST write to fresh
directories and MUST NOT overwrite prior recorded results. `data/abstracts.json`
is the canonical normalized raw corpus; cleanup, normalization, or corrective
transformations MUST be captured in explicit derivative artifacts instead of
silently rewriting the raw record. Canonical derived datasets SHOULD prefer
append-or-rebuild workflows over ad hoc in-place mutation.

Rationale: the project serves as both evidence base and delivery pipeline, so
operators need to distinguish raw inputs, derived artifacts, and experiments.

### III. Resumable, Auditable Pipelines
Long-running API, LLM, enrichment, or batch jobs MUST checkpoint incrementally
and remain resumable without recomputing completed records. New pipeline steps
MUST emit deterministic local outputs with enough metadata to explain their
inputs, model choices, and defaults. `ohbmcli` remains the canonical interface
for the main corpus pipeline; script-only workflows are acceptable for
experiments and organizer tooling only when they write auditable outputs and
are documented close to the workflow.

Rationale: resumability keeps expensive work practical, and auditability keeps
current defaults explainable to future operators.

### IV. Plan-First, Test-Driven Delivery
Behavior-changing work MUST begin with the closest relevant plan, spec, or
design note being created or updated before implementation. Tests or other
explicit verification steps MUST be identified first and MUST fail, or be shown
to be missing, before code changes land for behavior, contract, pipeline, or UI
changes. When canonical defaults, interfaces, inputs, or outputs change, the
code and the docs users rely on MUST be updated in the same change.

Rationale: this repository is large enough that unplanned local edits create
hidden regressions and documentation debt quickly.

### V. Secret-Safe, Reviewable Delivery
API keys, access tokens, and similar credentials MUST remain in `.env`, local
environment variables, or secret stores and MUST NOT be committed, echoed into
logs, pasted into docs, or embedded in generated artifacts. Reviews and
automation MUST assume redaction by default. Once a requested change is locally
verified, it MUST be committed with a descriptive message and pushed to the
configured remote unless the requester explicitly asks not to publish it.

Rationale: the repo handles live external services and collaborative work, so
credential hygiene and auditable delivery are both mandatory.

## Operational Constraints

- Use `uv` to create and manage the repository-local virtual environment before
  any Python work.
- Preserve machine-readable provenance for organizer-facing outputs; summaries,
  HTML pages, or screenshots are not sufficient by themselves.
- Keep experiment and proposal outputs auditable, with README files or nearby
  docs that state purpose, inputs, outputs, and repeat commands.
- Treat `memory/` as working context rather than canon, and keep local-only
  notes untracked unless someone explicitly requests otherwise.

## Delivery Workflow

1. Start from the nearest plan, spec, or experiment doc and update it if the
   requested change affects behavior, defaults, or intended workflow.
2. Refresh or create `.venv` with `uv`, then run Python commands only through
   `.venv/bin/python` or `uv` targeting that interpreter.
3. Add or update verification first for code, pipeline, contract, or UI
   changes, then implement the smallest auditable slice.
4. Update README, plan docs, and experiment docs in the same change whenever
   the code changes canonical defaults, paths, commands, or review surfaces.
5. Before finishing, verify no secrets were exposed, confirm outputs remain
   auditable and non-destructive, then commit and push the change.

## Governance

This constitution supersedes conflicting local habits and outdated docs. Amend
it by updating this file together with any affected templates and operator
documentation in the same reviewable change.

Versioning policy:

- MAJOR: removes or materially redefines a core principle or governance rule
- MINOR: adds a new principle or materially expands required workflow
- PATCH: clarifies wording without changing operative requirements

Compliance review expectations:

- Every implementation plan MUST pass the constitution check before work begins
  and again after design is updated.
- Every task list MUST reflect required verification, documentation sync, and
  secret-safe execution where relevant.
- Every merge-ready or handoff-ready change MUST confirm venv-only Python
  execution, auditable outputs, docs sync for changed defaults, and secret
  hygiene.

**Version**: 1.0.0 | **Ratified**: 2026-03-26 | **Last Amended**: 2026-03-28
