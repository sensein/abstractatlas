import{a as f,f as b,s as D,e as K}from"../chunks/CfsBuQlH.js";import{s as t}from"../chunks/DJqCkxES.js";import{be as q,a8 as Y,$ as Z,U as s,aS as a,b4 as e,ae as k,aF as $,aX as ee,ab as x,aH as c}from"../chunks/grBROpRT.js";import{i as N}from"../chunks/BAdNfywN.js";import{e as se}from"../chunks/C--ridr8.js";import{h as ae}from"../chunks/DaX5jQg-.js";import{d as te}from"../chunks/ecAqeHQc.js";var le=b(`<aside class="tldr svelte-cwls5q"><span class="tldr-label svelte-cwls5q">TL;DR</span> <ul class="svelte-cwls5q"><li class="svelte-cwls5q">GraphQL → JSON. <code class="svelte-cwls5q">graphql_api.py</code> + <code class="svelte-cwls5q">fetch_stage.py</code> paginate the Oxford Abstracts API; tiered HARD / SOFT / INFORMATIONAL
									schema diff (<code class="svelte-cwls5q">schema_diff.py</code>) blocks the build if the
									upstream contract drifts.</li> <li class="svelte-cwls5q">Resumable: per-state-key checkpoints under <code class="svelte-cwls5q">data/cache/fetch_abstracts/</code>; figure assets are
									reuse-aware via <code class="svelte-cwls5q">asset_stem</code> hashing.</li> <li class="svelte-cwls5q">Outputs: <code class="svelte-cwls5q">data/primary/abstracts.json</code> (accepted) + <code class="svelte-cwls5q">abstracts_withdrawn.json</code> (excluded from the site). <em>poster_id</em> is the canonical user-facing key (FR-002).</li></ul></aside> <p>We pull the accepted-abstract corpus from the <a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">Oxford Abstracts GraphQL API</a>, paginating through every accepted submission. Each record carries
							its program-assigned <em>poster id</em>, authors + affiliations,
							submitter-typed abstract sections (introduction / methods / results /
							conclusion), and the answers to the submission-form "extra questions"
							that drive our facets (methods, study type, population, etc.). Withdrawn
							submissions never reach this site — they're filtered out at this stage.</p>`,1),re=b(`<aside class="tldr svelte-cwls5q"><span class="tldr-label svelte-cwls5q">TL;DR</span> <ul class="svelte-cwls5q"><li class="svelte-cwls5q"><strong>Claims</strong>: agentic OpenAI Responses API call with three
									function tools (verify_source_quote, lookup_eco_code, dedupe_check),
									Pydantic-validated structured output annotated with <a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">ECO v1</a> evidence codes.</li> <li class="svelte-cwls5q"><strong>Figures</strong>: per-abstract grouped vision call on local
									JPEG-q85@1024 px compression, plus a four-field Pillow quality
									probe (laplacian_variance, mean_brightness, compression_ratio,
									native_max_dim).</li> <li class="svelte-cwls5q">Storage: SQLite + zlib-JSON
									(<code class="svelte-cwls5q">data/primary/abstracts_enriched.sqlite</code>); per-component
									caches keyed by <code class="svelte-cwls5q">sha256(input || model_id || vocabulary_version)</code>;
									flex-tier retry pattern (1 flex + 1 standard) so timeouts don't burn
									the whole batch.</li> <li class="svelte-cwls5q">References: LLM-assisted splitting of the citations block, lexically
									verified against the source text, then DOI → PMID → OpenAlex title
									search → Semantic Scholar fallback. The LLM only helps SPLIT — the
									canonical metadata is the lookup result, which is why references
									don't carry the <span class="ai-pill-demo svelte-cwls5q">✨ AI</span> pill.</li></ul></aside> <p>Each abstract is passed to an LLM (currently <code class="svelte-cwls5q">gpt-5.4-mini</code>) twice:
							once to extract structured <em>claims</em> with the <a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">Evidence and Conclusion Ontology</a> annotating each piece of evidence, and once per figure to produce a
							written <em>interpretation</em>. Both outputs are cached by content hash so
							re-runs only pay for changed records. References are split out of the
							submitter's text via the same LLM, then resolved to canonical DOIs via <a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">OpenAlex</a>.</p> <p>These two surfaces — figure interpretations and claims — are the only
							pieces of the site that are LLM-written. They're always tagged <span class="ai-pill-demo svelte-cwls5q">✨ AI</span> with the model identifier in the
							tooltip so readers can decide how much to trust them. Verbatim
							submitter content (abstract sections, topic dropdowns, methods
							checklists, authors) carries no such pill — that text is theirs.</p>`,1),ce=b(`<aside class="tldr svelte-cwls5q"><span class="tldr-label svelte-cwls5q">TL;DR</span> <ul class="svelte-cwls5q"><li class="svelte-cwls5q">Per-component bundles: every abstract embedded separately for <code class="svelte-cwls5q">title</code>, <code class="svelte-cwls5q">introduction</code>, <code class="svelte-cwls5q">methods</code>, <code class="svelte-cwls5q">results</code>, <code class="svelte-cwls5q">conclusion</code>, and <code class="svelte-cwls5q">claims</code> —
									recipes (e.g. <code class="svelte-cwls5q">title + intro + methods + results + conclusion</code>)
									are composed downstream via <code class="svelte-cwls5q">neuroscape.compose_recipe(...)</code>.</li> <li class="svelte-cwls5q">Token-level chunking + L2 normalization; per-abstract cache keyed
									by <code class="svelte-cwls5q">sha256(text || model_id || model_version)</code>. State-key
									suffix on the bundle dir lets multiple historical versions coexist.</li> <li class="svelte-cwls5q">Models: <a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">MiniLM-L6</a>,
									PubMedBERT, OpenAI <code class="svelte-cwls5q">text-embedding-3-small</code>, Voyage AI,
									and project-specific NeuroScape (Stage-2 transform applied to a
									public base; see the <a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">Aperture Neuro paper</a>).</li> <li class="svelte-cwls5q">Wire format for the SPA: MiniLM full-corpus matrix is int8-quantised
									to <code class="svelte-cwls5q">[N, 384]</code> with a global scale, cosine-recovery MAE ≤
									0.005, then transferred zero-copy into a Web Worker.</li></ul></aside> <p>We compute sentence-level embeddings for every abstract using five
							different encoder families: a public general-purpose model
							(<a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">MiniLM-L6</a>), a domain-specific biomedical model (PubMedBERT), two commercial APIs
							(OpenAI, Voyage), and our project-specific NeuroScape model
							(<a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">Aperture Neuro paper</a>, <a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">code</a>). Embeddings are computed per section (title / introduction /
							methods / results / conclusion / claims) and composed into bundles at
							read time, so the UI can show the same corpus through different "lenses".</p>`,1),oe=b(`<aside class="tldr svelte-cwls5q"><span class="tldr-label svelte-cwls5q">TL;DR</span> <ul class="svelte-cwls5q"><li class="svelte-cwls5q">15 (model × input) cells. Per cell: nearest-neighbour graph
									(FAISS-backed cosine kNN, k=15) → Leiden community detection
									(<a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">Traag 2019</a>) → 2D + 3D UMAP layouts
									(<a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">McInnes 2018</a>, <code class="svelte-cwls5q">n_neighbors=15, min_dist=0.1</code>) → HDBSCAN topic
									clusters (<a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">McInnes 2017</a>, <code class="svelte-cwls5q">min_cluster_size=15, cluster_selection_epsilon=0.05</code>).</li> <li class="svelte-cwls5q">Topic labelling: hybrid spaCy keyword extraction + c-TF-IDF, with
									an LLM grouping pass to produce human-friendly cluster titles +
									descriptions + focus blurbs — these carry the <span class="ai-pill-demo svelte-cwls5q">✨ AI</span> pill on the cluster facet.</li> <li class="svelte-cwls5q">Output: a single Stage-4 rollup
									(<code class="svelte-cwls5q">analysis/annotations__&lt;state-key&gt;.sqlite + .parquet</code>)
									whose rows feed the per-cell shards consumed by the site.
									Joblib-parallel orchestrator across cells.</li> <li class="svelte-cwls5q">Pre-computed neighbour lists: for each abstract per cell, the
									nearest-10 + farthest-10 by cosine distance are baked in via <code class="svelte-cwls5q">scripts/compute_neighbors.py</code>; the detail panel
									aggregates across cells to surface "most consistently similar".</li></ul></aside> <p>For each (model, input) combination we build a UMAP layout
							(<a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">McInnes 2018</a>) in 2D and 3D, run Leiden community detection
							(<a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">Traag 2019</a>) on the nearest-neighbour graph to find topic clusters, and HDBSCAN
							(<a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">McInnes 2017</a>) for a density-based view. An LLM names each community by reading a
							representative sample of titles from inside it; those names are what
							you see in the "Cluster (current map)" facet and in the UMAP hover
							tooltips.</p> <p>The same per-(model, input) bundle drives the "Most similar" and "Most
							different" lists in the detail panel — we precompute the 10 nearest +
							10 farthest abstracts per record per cell. The detail panel then
							aggregates across all 15 cells so the similar-list reflects every
							"lens" rather than just the currently-selected one.</p>`,1),ie=b(`<aside class="tldr svelte-cwls5q"><span class="tldr-label svelte-cwls5q">TL;DR</span> <ul class="svelte-cwls5q"><li class="svelte-cwls5q">Static SvelteKit + Vite, <code class="svelte-cwls5q">@sveltejs/adapter-static</code> → GitHub
									Pages. Per-PR previews under <code class="svelte-cwls5q">/pr-N/</code> with their own <code class="svelte-cwls5q">BASE_PATH</code>; production at the apex via CNAME. Deploys
									use <code class="svelte-cwls5q">peaceiris/actions-gh-pages@v3</code>.</li> <li class="svelte-cwls5q">Data delivery: a single gzipped tarball fetched on first paint from
									a stable Dropbox CDN URL, decoded in-browser with native <code class="svelte-cwls5q">DecompressionStream('gzip')</code> + a hand-rolled ~50-line tar
									parser into a <code class="svelte-cwls5q">Map&lt;path, JsonValue|Uint8Array&gt;</code>. No
									server, no per-query backend round-trip.</li> <li class="svelte-cwls5q">Lexical search: in-memory inverted index over title + topics +
									methods + author names + facet values + section bodies; Damerau-
									Levenshtein with length-adaptive thresholds (&lt;4 chars exact,
									4–6 → ≤1, ≥7 → ≤2). Exact-match abstracts ranked first.</li> <li class="svelte-cwls5q">Semantic search: <a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">MiniLM-L6</a> ONNX in a Web Worker via <code class="svelte-cwls5q">@xenova/transformers</code>; cosine
									similarity against the int8 quantised corpus matrix, dequantised
									per-row and clamped to [-1, 1]. Results merged with lexical via
									rank fusion (exactness first, semantic score secondary).</li> <li class="svelte-cwls5q">Permalink direct-load: gh-pages root <code class="svelte-cwls5q">404.html</code> is a
									hand-written SPA-redirect that stashes the original path in <code class="svelte-cwls5q">?spa=…</code> (and <code class="svelte-cwls5q">sessionStorage</code> as fallback) and
									replaces location with the SPA shell root for the detected base
									path. The layout's <code class="svelte-cwls5q">onMount</code> pops the stash and <code class="svelte-cwls5q">goto</code>s to the deep link before paint.</li> <li class="svelte-cwls5q">Schema: every JSON shard validates against the LinkML schema at <code class="svelte-cwls5q">specs/008-ui-rewrite/contracts/ui_data.linkml.yaml</code> —
									another generator emitting conforming data can be loaded by the
									site without code changes.</li></ul></aside> <p>This site is a static SvelteKit app deployed to GitHub Pages. The data
							package is a single gzipped tarball fetched from a stable CDN URL at
							page load — no server, no database, no per-query backend round-trip.
							Lexical typo-tolerant search runs in the main thread; semantic search
							runs in a Web Worker using <a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">MiniLM-L6</a> ONNX through transformers.js, against an int8-quantised vector matrix
							also shipped in the tarball.</p> <p class="muted svelte-cwls5q">Source: <a target="_blank" rel="noopener noreferrer" class="svelte-cwls5q">github.com/sensein/ohbm2026</a>. Build provenance is in the footer of every page.</p>`,1),ne=b('<div class="stage-body svelte-cwls5q"><!></div>'),de=b('<section class="stage svelte-cwls5q"><button type="button" class="stage-header svelte-cwls5q"><span class="caret svelte-cwls5q"> </span> <span class="stage-label svelte-cwls5q"> </span></button> <!></section>'),pe=b(`<div class="about-page svelte-cwls5q"><nav class="back svelte-cwls5q"><a class="svelte-cwls5q">← back to atlas</a></nav> <header class="svelte-cwls5q"><h1 class="svelte-cwls5q">About the OHBM 2026 Atlas</h1> <p class="lead svelte-cwls5q">A search-and-browse interface for every accepted OHBM 2026 abstract. Each abstract
			is the submitter's own text; everything else on the site — clusters, related-abstract
			suggestions, figure interpretations, claim extractions — is computed from those
			abstracts by an automated pipeline. The pipeline is open-source and reproducible.</p></header> <section class="overview svelte-cwls5q"><p class="svelte-cwls5q">Reading 3,000+ abstracts to find the ones you care about isn't realistic for most
			people. This atlas tries to make that browsable: a free-text + faceted search, a
			2D + 3D map of the corpus coloured by topic cluster, AI-extracted highlights of each
			abstract's claims and figures, and a lightweight saved-list export.</p> <p class="svelte-cwls5q">The pipeline runs in five stages, listed below. Click each one to see how it works.
			Surfaces that were authored or interpreted by an LLM (figure interpretations,
			extracted claims, LLM-grouped topic-cluster titles) carry an <span class="ai-pill-demo svelte-cwls5q">✨ AI</span> pill in the detail panel so the
			provenance is always visible.</p></section> <!></div>`);function ge(R){let _=$({});function E(w){ee(_,{...k(_),[w]:!k(_)[w]})}const l={oxford:{url:"https://app.oxfordabstracts.com/"},umap:{url:"https://arxiv.org/abs/1802.03426"},leiden:{url:"https://www.nature.com/articles/s41598-019-41695-z"},hdbscan:{url:"https://joss.theoj.org/papers/10.21105/joss.00205"},minilm:{url:"https://arxiv.org/abs/2002.10957"},eco:{url:"https://evidenceontology.org/"},openalex:{url:"https://openalex.org/"},neuroscape_repo:{url:"https://github.com/sensein/neuroscape"},neuroscape_paper:{url:"https://apertureneuro.org/article/124574-neuroscape-a-domain-specific-embedding-for-neuroscience-abstracts"},repo:{url:"https://github.com/sensein/ohbm2026"}};var M=pe();ae("cwls5q",w=>{Y(()=>{Z.title="About · OHBM 2026 Atlas"})});var S=s(M),C=s(S);a(S);var j=e(S,6);se(j,0,()=>[{key:"fetch",label:"Stage 1 — Fetch & normalise (Oxford Abstracts → JSON)"},{key:"enrich",label:"Stage 2 — AI enrichment (figures + claims + references)"},{key:"embed",label:"Stage 3 — Embeddings (5 models × per-section)"},{key:"analyse",label:"Stage 4 — Communities + clusters + UMAP"},{key:"ui",label:"Stage 6 — This site"}],w=>w.key,(w,d)=>{var L=de(),y=s(L),T=s(y),B=s(T,!0);a(T);var O=e(T,2),F=s(O,!0);a(O),a(y);var H=e(y,2);{var W=I=>{var P=ne(),U=s(P);{var z=o=>{var i=le(),r=e(x(i),2),n=e(s(r));c(3),a(r),q(()=>t(n,"href",l.oxford.url)),f(o,i)},J=o=>{var i=re(),r=x(i),n=e(s(r),2),p=s(n),v=e(s(p),2);c(),a(p),c(6),a(n),a(r);var h=e(r,2),m=e(s(h),5),u=e(m,4);c(),a(h),c(2),q(()=>{t(v,"href",l.eco.url),t(m,"href",l.eco.url),t(u,"href",l.openalex.url)}),f(o,i)},G=o=>{var i=ce(),r=x(i),n=e(s(r),2),p=e(s(n),4),v=e(s(p)),h=e(v,4);c(),a(p),c(2),a(n),a(r);var m=e(r,2),u=e(s(m)),g=e(u,2),A=e(g,2);c(),a(m),q(()=>{t(v,"href",l.minilm.url),t(h,"href",l.neuroscape_paper.url),t(u,"href",l.minilm.url),t(g,"href",l.neuroscape_paper.url),t(A,"href",l.neuroscape_repo.url)}),f(o,i)},V=o=>{var i=oe(),r=x(i),n=e(s(r),2),p=s(n),v=e(s(p)),h=e(v,2),m=e(h,4);c(3),a(p),c(6),a(n),a(r);var u=e(r,2),g=e(s(u)),A=e(g,2),X=e(A,2);c(),a(u),c(2),q(()=>{t(v,"href",l.leiden.url),t(h,"href",l.umap.url),t(m,"href",l.hdbscan.url),t(g,"href",l.umap.url),t(A,"href",l.leiden.url),t(X,"href",l.hdbscan.url)}),f(o,i)},Q=o=>{var i=ie(),r=x(i),n=e(s(r),2),p=e(s(n),6),v=e(s(p));c(3),a(p),c(4),a(n),a(r);var h=e(r,2),m=e(s(h));c(),a(h);var u=e(h,2),g=e(s(u));c(),a(u),q(()=>{t(v,"href",l.minilm.url),t(m,"href",l.minilm.url),t(g,"href",l.repo.url)}),f(o,i)};N(U,o=>{d.key==="fetch"?o(z):d.key==="enrich"?o(J,1):d.key==="embed"?o(G,2):d.key==="analyse"?o(V,3):d.key==="ui"&&o(Q,4)})}a(P),f(I,P)};N(H,I=>{k(_)[d.key]&&I(W)})}a(L),q(()=>{t(L,"data-testid",`about-stage-${d.key}`),t(y,"aria-expanded",!!k(_)[d.key]),D(B,k(_)[d.key]?"▾":"▸"),D(F,d.label)}),K("click",y,()=>E(d.key)),f(w,L)}),a(M),q(()=>t(C,"href",`${te}/`)),f(R,M)}export{ge as component};
