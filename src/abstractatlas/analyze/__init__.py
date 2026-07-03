"""Stage 4 analysis & annotation package.

The flat `analyze.py` module was split into per-concern submodules:

- `analyze.errors` — typed `AnalysisError` hierarchy (re-exported from
  `abstractatlas.exceptions`).
- `analyze.provenance` — Stage 4 path-safe provenance writers.
- `analyze.storage` — I/O helpers, bundle readers/writers, text-shaping
  utilities, and `write_analysis_bundle` for Stage 4's per-kind output.
- `analyze.clusters` — legacy cluster benchmark + semantic analysis +
  Stage-2 community detection surface (the sklearn-based pipeline that
  the cluster_benchmark and semantic_analysis CLIs use).
- `analyze.projections` — legacy UMAP + t-SNE projection / HTML viz
  surface, including the projection-comparison CLI.
- `analyze.communities` — Stage 4 FAISS + Leiden + CPM community
  detection (US4).
- `analyze.centroids` — Stage 4 NeuroScape centroid cluster assignment
  (US3).
- `analyze.topics` — Stage 4 spaCy + c-TF-IDF + optional LLM topic
  pipeline (US5 generated-cluster labels).
- `analyze.topic_clusters` — Stage 4 BERTopic-style UMAP + HDBSCAN
  topic-model clustering (US5).
- `analyze.umap` — Stage 4 UMAP fit + `project_into_umap` (US2).
- `analyze.rollup` — Canonical UI rollup writer (annotations.parquet
  + sqlite).
- `analyze.stage` — Stage 4 orchestrator (`aacli analyze-matrix`).

**No package-level re-exports.** Per spec clarification Session
2026-05-15 Q2, every caller imports from the explicit submodule that
owns the symbol — `from abstractatlas.analyze.storage import …`,
`from abstractatlas.analyze.clusters import …`, etc. The `runners` import
below is a side-effect-only import that registers per-kind runners
with `analyze.stage.KIND_RUNNERS`; nothing else lives at the package
top level.
"""

from __future__ import annotations

# Warm-up imports to break a pre-existing
# `exceptions ↔ fetch.graphql_api ↔ fetch.stage ↔ exceptions` cycle.
# When the first entry into the `analyze` package comes from a
# submodule that imports from `abstractatlas.exceptions` (e.g. test code
# that does `from abstractatlas.analyze.centroids import ...`), exceptions
# would otherwise be loaded partially. Loading fetch + exceptions
# here first warms the chain so downstream submodule imports see a
# fully-initialized exceptions module.
from abstractatlas import fetch as _fetch_warmup  # noqa: F401
from abstractatlas import exceptions as _exceptions_warmup  # noqa: F401

# Side-effect import: registers projections / communities /
# neuroscape_clusters / topic_clusters runners with
# `analyze.stage.KIND_RUNNERS`. Without this, the orchestrator's
# dispatch can't find any runners.
from abstractatlas.analyze import runners  # noqa: F401
