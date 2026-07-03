# Repository Review 2026-03-28

## Scope

This review combines a software-engineering and technical-management pass over
the repository after adding the vision and governance documentation.

Inspection inputs:

- current repository structure
- commit history and memory summary
- plan documents and experiment READMEs
- module and script size distribution
- full `unittest` suite execution

## Overall Assessment

The project is healthy, productive, and unusually well tested for a research
workflow repository. Its main debt is not correctness drift. Its main debt is
concentration: a lot of capability and project knowledge lives in a small number
of very large modules and in a broad script surface that requires local context
to navigate confidently.

## Strengths To Preserve

- the canonical pipeline is resumable and centered on `aacli`
- experiment immutability is explicit and documented
- test coverage is broad across pipeline, UI export, poster layout, and
  experiment tooling
- the repository retains evidence of decisions rather than only final outputs
- the project already writes many machine-readable artifacts that support audit
  and comparison

## Findings

### P1: Domain logic is concentrated in very large modules

Current hotspots:

- `src/abstractatlas/neuroscape.py`
  - about `2951` lines, `106` functions
- `src/abstractatlas/poster_sequencing.py`
  - about `2371` lines, `59` functions
- `src/abstractatlas/openalex.py`
  - about `2279` lines, `76` functions
- `src/abstractatlas/poster_layout.py`
  - about `2191` lines, `60` functions
- `src/abstractatlas/enrichment.py`
  - about `1437` lines, `59` functions

Why this matters:

- ownership boundaries are hard to see
- reviews are harder because unrelated concerns share files
- test targeting is good, but change isolation is weaker than it should be
- future agents will spend more time rediscovering structure instead of editing
  confidently

Recommended next step:

- split these files by responsibility rather than by line count alone
- start with `neuroscape.py` and `openalex.py`, where the boundaries are
  already visible

Suggested slices:

- `neuroscape.py`
  - embeddings
  - clustering
  - projections
  - published stage-2 application
  - manifest writing
- `openalex.py`
  - reference parsing and splitting
  - external API clients
  - resolution and cache orchestration

### P1: Organizer and experiment workflows are discoverable only through tribal knowledge

The `scripts/` directory now contains a large set of entrypoints, including
review builders, proposal generators, experiment runners, layout plots, and
verification utilities. The code is useful, but the mental map is expensive.

Why this matters:

- new contributors can pick the wrong entrypoint
- “current default” versus “historical experiment” is not always obvious
- operational risk rises when scripts look similar but serve different stages

Mitigation landed in this pass:

- added documentation and experiment indexes to make the workflow surface easier
  to navigate

Recommended next step:

- introduce a `scripts/README.md` or eventually promote the most stable
  organizer flows into explicit `aacli` or package-level namespaces

### P2: Canonical versus exploratory outputs still need stronger machine-readable boundaries

The repo conceptually separates canonical corpus artifacts from experiment and
layout outputs, but that distinction is still partly conventional rather than
explicitly machine-readable.

Why this matters:

- future automation may treat every artifact in `data/` as equally authoritative
- promotion from experiment to default remains a social process rather than a
  declared one

Recommended next step:

- add a checked-in manifest for the current canonical artifact set and active
  organizer comparison set
- when a default changes, update the manifest and the README together

### P2: Plotting and review tooling still depends on environment details

The test run succeeded, but plotting-related tests emitted a Matplotlib cache
warning because the default user cache directory was not writable in the current
execution context.

Why this matters:

- it is a small but recurring source of avoidable friction for automation
- it is exactly the kind of issue that makes reproduction feel less robust than
  it really is

Recommended next step:

- standardize `MPLCONFIGDIR` to a local writable path in developer docs, test
  setup, or plotting entrypoints

### P3: Planning discipline is strong, but backlog discipline is still document-centric

The repository has many good plan documents, but not yet one living roadmap that
tracks which plans are active, superseded, or completed.

Why this matters:

- readers must infer status from scattered checklists and commit history
- management-style prioritization is harder than it should be

Recommended next step:

- add a single roadmap or project-board-facing index that links plans to status,
  owning area, and next action

## Low-Risk Improvements Landed In This Review Pass

- added a repo-level vision and reproducibility guide
- strengthened the constitution with additional commitments around raw-data
  traceability, resumability, documentation, and auditability
- added a documentation index
- added an experiment index

These changes do not solve the structural refactor backlog, but they reduce the
cost of navigating and reproducing the project today.

## Recommended Refactor Order

1. split `neuroscape.py`
2. split `openalex.py`
3. move poster-layout and poster-sequencing logic into a dedicated package
   subtree with clearer ownership boundaries
4. add a canonical-artifacts manifest
5. standardize local plotting cache configuration

## Verification Snapshot

- full test suite run: `221` tests
- result: `OK`
- no code regressions observed during this review pass
