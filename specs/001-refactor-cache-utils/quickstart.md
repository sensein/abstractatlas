# Quickstart: Refactor Shared Utils And Cache Governance

## Purpose

Validate the first implementation slice for shared artifact utilities, input
layout, cache layout, output layout, and direct lookup behavior.

## Setup

```bash
UV_CACHE_DIR=.uv-cache uv venv --python 3.11 .venv
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
```

## Focused Verification

1. Run the shared artifact utility and affected workflow tests:

```bash
PYTHONPATH=src .venv/bin/python -m unittest \
  tests.test_artifacts \
  tests.test_enrichment \
  tests.test_openalex \
  tests.test_neuroscape \
  tests.test_ui -v
```

2. Confirm git ignores representative local artifact paths:

```bash
git check-ignore \
  data/inputs/abstracts_graphql__state-key.json \
  data/cache/figure_analysis/sample__state-key.json \
  data/outputs/exported-sites/site_bundle__state-key/manifest.json
```

3. Exercise one cache-producing workflow and verify the resulting path is
   derived directly from workflow plus state key rather than discovered by
   scanning directories.

4. Exercise one output-producing workflow and verify the result lands in the
   correct output family (`experiments`, `exported-sites`, or `proposals`).

5. Simulate a stale dependency basis for one in-scope workflow and verify the
   implementation chooses the documented regeneration route without deleting
   unaffected inputs.

## Expected Outcomes

- Shared path/metadata helpers are reused instead of duplicated.
- GraphQL-fetched abstract inputs resolve under `data/inputs/`.
- In-scope caches resolve under `data/cache/`.
- In-scope outputs resolve under the correct `data/outputs/` family.
- Local artifacts remain untracked by git.
