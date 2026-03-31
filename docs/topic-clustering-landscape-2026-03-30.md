# Topic Clustering Landscape

Date: 2026-03-30

## Goal

Summarize recent approaches that are relevant to this repo's next experiment
ladder for clustering OHBM abstracts into explainable topic groups, including
overlapping or multi-membership structures where appropriate.

This note is intentionally practical. It focuses on methods that could inform
near-term experiments in this repository rather than trying to be a complete
survey of topic modeling.

## Scope Of The Scan

Primary emphasis:

- recent ACL/NAACL/EMNLP and arXiv work on topic modeling, document clustering,
  and interpretability
- methods that support one or more of:
  - strong semantic grouping from embeddings
  - overlapping or multi-topic assignments
  - cluster/topic rationales that humans can understand
  - evaluation protocols that go beyond silhouette or coherence

BioRxiv note:

- I searched bioRxiv for recent directly comparable work on topic clustering of
  scientific abstracts, but did not find a clearly on-point 2024-2025 method
  paper that was as relevant as the ACL/arXiv literature below.
- The most directly useful recent methods for this problem appear to be coming
  from NLP venues rather than bioRxiv.

## Main Takeaways

1. The center of gravity has shifted away from pure bag-of-words topic models.
   Recent strong approaches combine document embeddings, graph structure,
   clustering, and LLM-assisted labeling or alignment.
2. Overlapping structure is becoming more important. Recent work increasingly
   treats multi-topic membership as a first-class capability rather than a
   failure mode.
3. Evaluation is moving beyond topic coherence. Recent papers emphasize human
   usefulness, reproducibility, and labelability.
4. For scientific abstracts, embedding quality is still one of the biggest
   levers. Better document representations can matter as much as, or more than,
   swapping one clustering algorithm for another.

## Papers Most Relevant To This Repo

### 1. Multi-topic assignments are now an explicit design target

- [Semantic Component Analysis: Introducing Multi-Topic Distributions to Clustering-Based Topic Modeling](https://aclanthology.org/2025.findings-emnlp.964/)
  (Eichin et al., Findings of EMNLP 2025)
  - Proposes a decomposition step on top of clustering-based topic modeling so
    a sample can receive multiple topics rather than exactly one.
  - Reported result: competitive coherence/diversity against BERTopic while
    uncovering at least twice as many topics with near-zero noise on their
    datasets.
  - Why it matters here: this is one of the clearest recent arguments for a
    repo experiment that does not force every abstract into exactly one topic.
  - Repo implication: add an experiment family that starts from our strongest
    embedding spaces and estimates per-abstract topic mixtures or top-2 topic
    memberships, then checks whether bridge abstracts become more interpretable.

### 2. LLMs look strongest when used to help structure the topic space, not only
as a post-hoc labeler

- [LLM-Guided Semantic-Aware Clustering for Topic Modeling](https://aclanthology.org/2025.acl-long.902/)
  (Liu et al., ACL 2025)
  - LiSA uses LLM-generated candidate topic words and descriptions, clusters
    both documents and topic words, and aligns the two semantic spaces.
  - The paper reports better topic alignment than prior GPT-4-based topic
    methods and competitive topic quality against neural topic models.
  - Why it matters here: this suggests a middle path between pure unsupervised
    clustering and full LLM-generated topic systems.
  - Repo implication: after baseline clustering, generate candidate labels or
    topic phrases for each abstract or cluster, then align cluster structure and
    label structure instead of treating naming as an afterthought.

### 3. Prompt-based topic discovery makes explainability much better, but it is
not necessarily the right first clustering engine

- [TopicGPT: A Prompt-based Topic Modeling Framework](https://aclanthology.org/2024.naacl-long.164/)
  (Pham et al., NAACL 2024)
  - Uses an LLM to produce human-readable topic labels and descriptions and
    supports user control and hierarchical exploration.
  - Reported result: stronger alignment with human categorizations than LDA,
    SeededLDA, and BERTopic on their evaluation datasets.
  - Why it matters here: it reinforces that natural-language topic rationales
    can be a first-class output, not just a bag of keywords.
  - Repo implication: even if we keep clustering based on local embeddings or
    graph methods, we should add TopicGPT-like rationale generation for the top
    representative abstracts in each cluster/community.

### 4. Graph structure remains highly relevant for topic discovery

- [GINopic: Topic Modeling with Graph Isomorphism Network](https://aclanthology.org/2024.naacl-long.342/)
  (Adhya and Sanyal, NAACL 2024; arXiv:2404.02115)
  - Combines contextual representations with graph structure over word
    relationships and reports gains over earlier topic models.
  - Why it matters here: this supports keeping graph-based structure in scope
    rather than limiting the repo to centroid-style partitions.
  - Repo implication: our kNN graph plus community-detection track is still a
    good direction. The main opportunity is to improve the graph inputs and
    reporting, not abandon graph methods.

### 5. Scientific-document embeddings are a separate optimization problem and a
worthwhile lever

- [SciRepEval: A Multi-Format Benchmark for Scientific Document Representations](https://openreview.net/forum?id=ft0c1K3492)
  (Singh et al., EMNLP 2023)
- [SPECTER2 model card](https://huggingface.co/allenai/specter2)
  and [Ai2 overview](https://allenai.org/blog/specter2-adapting-scientific-document-embeddings-to-multiple-fields-and-task-formats-c95686c06567)
  (updated 2023-11-27)
  - SPECTER2 introduces task-format-aware scientific embeddings for titles and
    abstracts, trained over multiple scientific tasks.
  - Why it matters here: our corpus is not generic short text; it is a
    scientific-abstract corpus, so scientific-document embeddings may close
    real gaps that general embeddings leave behind.
  - Repo implication: add a scientific-embedding comparison lane, likely with
    SPECTER2 or a similar scientific abstract encoder, before declaring the
    current embedding family optimal.

### 6. Embedding advances remain a state-of-the-art lever

- [Improving Text Embeddings with Large Language Models](https://arxiv.org/abs/2401.00368)
  (Wang et al., arXiv 2024; updated 2024-05-31)
  - Shows that synthetic-data-assisted LLM training can produce much stronger
    text embeddings with a comparatively simple pipeline.
  - Why it matters here: if clustering quality plateaus, the next best move may
    be better embeddings rather than ever more elaborate downstream clustering.
  - Repo implication: keep the experiment ladder modular so new embedding
    bundles can be dropped into the same benchmark and community-detection
    pipeline.

### 7. Evaluation is shifting toward human-useful cluster quality

- [Improving the TENOR of Labeling: Re-evaluating Topic Models for Content Analysis](https://aclanthology.org/2024.eacl-long.51/)
  (Li et al., EACL 2024)
  - Shows that commonly used automated metrics do not capture the full
    practical value of topic models in human tasks.
- [Reliability of Topic Modeling](https://aclanthology.org/2025.naacl-long.134/)
  (Schroeder and Wood-Doughty, NAACL 2025)
  - Argues for stronger attention to reproducibility and reliability in topic
    modeling workflows.
- [ProxAnn: Use-Oriented Evaluations of Topic Models and Document Clustering](https://aclanthology.org/2025.acl-long.772/)
  (Hoyle et al., ACL 2025)
  - Introduces a scalable evaluation protocol where annotators, or an LLM proxy,
    infer a category from a cluster/topic and then apply that category to held
    out documents.
  - Why it matters here: this is very close to our organizer-facing use case.
  - Repo implication: our experiments should not stop at silhouette, modularity,
    or coherence. We should add a use-oriented labelability check for each
    cluster system and a stability check across seeds or resampled corpora.

### 8. Clustering-specific variants still matter, especially for short or noisy
text

- [Topic Modeling for Short Texts via Optimal Transport-Based Clustering](https://aclanthology.org/2025.findings-acl.398/)
  (Vu et al., Findings of ACL 2025)
  - Uses optimal transport-based clustering to improve short-text topic
    modeling.
  - Why it matters here: abstracts are longer than tweets, but individual claim
    units and title-introduction-conclusion snippets are still relatively short.
  - Repo implication: this is more relevant to the claim-only track than to the
    full-abstract clustering track, and may be worth testing later if claim
    clustering remains noisy.

## What Looks Most Actionable For This Repo

### Keep

- embedding-first clustering and community detection
- graph-based structure discovery
- explainable topic rationales generated from representative abstracts
- evaluation against organizer-facing utility rather than only generic metrics

### Add

- an explicit overlapping or multi-membership experiment lane
- a stability and reliability lane across random seeds and modest corpus
  perturbations
- a use-oriented labelability evaluation inspired by ProxAnn
- a scientific-embedding comparison lane such as SPECTER2

### Deprioritize For Now

- replacing the whole pipeline with a fully LLM-native topic model
- word-graph neural topic models that require a large new modeling stack before
  we have exhausted simpler embedding-plus-graph baselines
- methods that are optimized for extremely short texts before we have clear
  evidence that the full-abstract track is the real bottleneck

## Recommended Experiment Ladder Changes

### Experiment A: Reliability-first hard clustering refresh

- rerun the partition benchmark on the strongest current embedding families
- add seed sweeps and resampled-corpus stability summaries
- select not just the best score, but the most reproducible score band

### Experiment B: Overlapping topic assignments

- extend the current NOCD/community workflow
- compare hard communities, overlapping communities, and top-2 assignment
  variants
- measure bridge-abstract rate, multi-membership rate, coverage, and the
  readability of resulting cluster rationales

### Experiment C: Rationale-aware cluster labeling

- generate labels and brief rationales from:
  - representative abstracts
  - top discriminative terms
  - nearest-neighbor exemplars
- optionally add LLM-guided phrase candidates and compare them with purely
  extractive cluster labels

### Experiment D: Use-oriented evaluation

- for each candidate clustering, ask whether a human or LLM proxy can infer a
  cluster rationale and accurately place held-out abstracts into that rationale
- use this as an organizer-facing interpretability metric alongside geometry

### Experiment E: Scientific-embedding comparison

- test whether a scientific-document encoder such as SPECTER2 improves
  structure, explainability, or cluster stability relative to the current
  embedding families

## Concrete Implications For The Current Codebase

- The repo should keep NOCD and related community analyses in scope because the
  literature still supports overlapping structure as a serious option.
- The next implementation pass should add better cluster-summary artifacts:
  rationale, representative abstracts, bridge examples, and confidence notes.
- The experiment record format should explicitly capture:
  - motivation
  - plan
  - tasks
  - debugging notes
  - result summary
  - evaluation metrics for both geometry and human usefulness
- If we add a new embedding family, the experiment harness should treat it as a
  swappable input bundle rather than a special case.

## Bottom Line

The recent literature does not point to one universally dominant replacement
for the repo's current approach. Instead, it points to a stronger combined
strategy:

- use the best available document embeddings
- compare hard and overlapping structure
- generate explicit human-readable rationales for each cluster
- judge candidate taxonomies with reliability and use-oriented evaluation, not
  only unsupervised geometry

That is a good fit for the experiment ladder already emerging in this repo.
The main gap is not lack of ideas; it is turning those ideas into a disciplined
set of repeatable experiments and reports.

## Sources

- [Semantic Component Analysis: Introducing Multi-Topic Distributions to Clustering-Based Topic Modeling](https://aclanthology.org/2025.findings-emnlp.964/)
- [LLM-Guided Semantic-Aware Clustering for Topic Modeling](https://aclanthology.org/2025.acl-long.902/)
- [TopicGPT: A Prompt-based Topic Modeling Framework](https://aclanthology.org/2024.naacl-long.164/)
- [GINopic: Topic Modeling with Graph Isomorphism Network](https://aclanthology.org/2024.naacl-long.342/)
- [SciRepEval: A Multi-Format Benchmark for Scientific Document Representations](https://openreview.net/forum?id=ft0c1K3492)
- [SPECTER2 model card](https://huggingface.co/allenai/specter2)
- [SPECTER2: Adapting scientific document embeddings to multiple fields and task formats](https://allenai.org/blog/specter2-adapting-scientific-document-embeddings-to-multiple-fields-and-task-formats-c95686c06567)
- [Improving Text Embeddings with Large Language Models](https://arxiv.org/abs/2401.00368)
- [Improving the TENOR of Labeling: Re-evaluating Topic Models for Content Analysis](https://aclanthology.org/2024.eacl-long.51/)
- [Reliability of Topic Modeling](https://aclanthology.org/2025.naacl-long.134/)
- [ProxAnn: Use-Oriented Evaluations of Topic Models and Document Clustering](https://aclanthology.org/2025.acl-long.772/)
- [Topic Modeling for Short Texts via Optimal Transport-Based Clustering](https://aclanthology.org/2025.findings-acl.398/)
