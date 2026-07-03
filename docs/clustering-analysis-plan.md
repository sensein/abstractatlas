# Clustering Analysis Plan

## Goal

Build a label-independent clustering benchmark over local embedding bundles to identify:

- which clustering methods work best on a given embedding space
- which cluster counts produce the strongest separation and cohesion

The analysis should rank candidate runs using unsupervised metrics rather than any external labels.

## Scope

Initial scope:

- input: any local embedding bundle under `data/embeddings/*`
- methods:
  - `kmeans`
  - `agglomerative-ward`
  - `agglomerative-average`
  - `gaussian-mixture`
  - `birch`
- cluster-count sweep:
  - configurable `k_min..k_max`
- dimensionality reduction:
  - optional PCA preprocessing for speed/stability
- metrics:
  - silhouette score
  - Calinski-Harabasz score
  - Davies-Bouldin score
  - intercluster / intracluster distance ratio
  - cluster-size balance summary
- outputs:
  - ranked JSON results
  - per-run metrics table
  - best-run assignments and cluster summaries

Out of scope for the first pass:

- supervised evaluation against topic labels
- HDBSCAN/UMAP-assisted clustering unless already installed and stable
- automatic paper-quality figure generation

## Ranking Strategy

Each candidate run should produce:

- `cluster_count`
- `silhouette_score`
- `calinski_harabasz_score`
- `davies_bouldin_score`
- `intercluster_distance_ratio`
- `mean_intercluster_distance`
- `mean_intracluster_distance`
- `largest_cluster_fraction`
- `smallest_cluster_size`

Primary ranking:

- prefer higher silhouette
- prefer lower Davies-Bouldin
- prefer higher Calinski-Harabasz
- prefer higher intercluster/intracluster ratio
- penalize extreme cluster imbalance

Implementation approach:

- compute all metrics for all valid runs
- normalize metric columns across the sweep
- combine them into a composite score with imbalance penalty
- keep the raw metrics so ranking can be audited later

## Validation Checks

Code-level checks:

- reject runs that collapse to fewer than 2 clusters
- reject runs where one cluster contains almost all points
- ensure assignment count matches embedding row count
- ensure cluster summaries can be written for the best run

Test coverage:

- metric computation for a small synthetic dataset
- method runner returns assignments of expected size
- ranking prefers a clearly better-separated synthetic solution
- CLI writes benchmark results and best-run outputs

Runtime checks on real data:

- benchmark completes on at least one real embedding bundle
- best run yields more than one nontrivial cluster
- output JSON includes enough metadata to reproduce the run

## Deliverables

- new CLI command for clustering benchmark
- output directory per analyzed embedding bundle
- JSON summary of all candidate runs
- best-run cluster assignments
- best-run cluster summaries

## Status

- [x] Added `aacli cluster-benchmark`
- [x] Implemented method sweep across `kmeans`, `agglomerative-ward`, `agglomerative-average`, `gaussian-mixture`, and `birch`
- [x] Added label-independent ranking using silhouette, Davies-Bouldin, Calinski-Harabasz, inter/intracluster distance ratio, and cluster-balance terms
- [x] Added test coverage for method execution, metric computation, ranking, CLI wiring, and output writing
- [x] Ran the benchmark on real embedding bundles

## First-Pass Findings

Real-data runs completed on:

- `data/embeddings/voyage_stage2_published`
- `data/embeddings/minilm_stage1`

Current best runs:

- `voyage_stage2_published`
  - best method: `kmeans`
  - best `k`: `25`
  - silhouette: `0.1028`
  - Davies-Bouldin: `2.2867`
  - inter/intracluster ratio: `1.2782`
- `minilm_stage1`
  - best method: `kmeans`
  - best `k`: `30`
  - silhouette: `0.0664`
  - Davies-Bouldin: `2.6519`
  - inter/intracluster ratio: `1.0939`

Interpretation:

- the published Voyage stage-2 space separates clusters better than the default MiniLM stage-1 space on this benchmark
- the best-scoring solutions are at relatively high `k`, which suggests the corpus supports fine-grained partitions more readily than a small number of broad communities
