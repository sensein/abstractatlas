<script lang="ts">
	import { onMount } from 'svelte';
	import { buildInfoFromEnv, loadManifest, type BuildInfo, type Manifest } from '$lib/shards';

	let manifest: Manifest | null = null;
	let manifestLoaded = false;
	const envBuildInfo: BuildInfo | null = buildInfoFromEnv();

	onMount(async () => {
		manifest = await loadManifest();
		manifestLoaded = true;
	});
</script>

<section class="placeholder">
	<h2 data-testid="page-title">Stage 6 — under construction</h2>

	{#if manifest}
		<p class="committish-callout">
			Built from
			<code data-testid="placeholder-short-sha">{manifest.build_info.code_revision_short}</code>
			against corpus
			<code>{manifest.build_info.corpus_state_key}</code>
			and Stage 4 rollup
			<code>{manifest.build_info.stage4_rollup_state_key}</code>.
		</p>
		<p>
			This page renders the data-package <code>manifest.json</code> only — the real US1 home
			page lands in a subsequent PR. The build pipeline + per-PR preview deploys are wired so
			reviewers can verify each PR by clicking <em>"View deployment"</em> in the PR's Deployments
			box (top-of-PR) and confirming the short SHA above matches the latest pushed commit.
		</p>
		<dl class="stats">
			<dt>Accepted abstracts</dt>
			<dd>{manifest.corpus_count}</dd>
			<dt>Models</dt>
			<dd>{manifest.models.join(', ')}</dd>
			<dt>Inputs</dt>
			<dd>{manifest.inputs.join(', ')}</dd>
			<dt>Cells</dt>
			<dd>{manifest.cells.length} <span class="muted">({manifest.models.length} × {manifest.inputs.length})</span></dd>
			<dt>Facet catalog</dt>
			<dd>{manifest.facets.length} facets</dd>
		</dl>
	{:else if envBuildInfo && manifestLoaded}
		<p class="committish-callout">
			Built from
			<code data-testid="placeholder-short-sha">{envBuildInfo.code_revision_short}</code>
			{#if envBuildInfo.built_at}
				at <time datetime={envBuildInfo.built_at}>{envBuildInfo.built_at}</time>
			{/if}.
		</p>
		<p>
			This preview is a <strong>workflow-only</strong> deploy — the Stage 1–4 inputs haven't
			been materialized in CI yet, so the data package is empty. The short SHA above comes
			from the deploy workflow's git revision (<code>VITE_BUILD_SHA</code>) and matches the
			commit at the head of this PR — that's the signal reviewers need to confirm the
			Deployments-box URL points at the latest pushed commit.
		</p>
		<p>
			Full data-package rendering (3,244 abstracts, 15 cells, 33 topic shards) lights up
			once <code>scripts/fetch_ui_inputs.sh</code> is wired to an artifact store.
		</p>
	{:else if manifestLoaded}
		<p class="error">
			No <code>manifest.json</code> found and no build-time SHA was injected. Set
			<code>VITE_BUILD_SHA</code> + <code>VITE_BUILD_SHA_SHORT</code> in your build env to
			surface the committish on the page.
		</p>
	{:else}
		<p>Loading…</p>
		<noscript>
			<p class="error">JavaScript is required to render the build provenance.</p>
		</noscript>
	{/if}
</section>

<style>
	.placeholder {
		padding: 1rem 0 2rem;
	}
	.placeholder h2 {
		margin: 0 0 0.75rem;
	}
	.committish-callout {
		background: #fffbe6;
		border: 1px solid #f0e2a4;
		padding: 0.75rem 1rem;
		border-radius: 4px;
		font-size: 0.95rem;
	}
	.stats {
		margin: 1.5rem 0 0;
		display: grid;
		grid-template-columns: max-content 1fr;
		gap: 0.25rem 1rem;
		font-size: 0.9rem;
	}
	.stats dt {
		color: #666;
		font-weight: 500;
	}
	.stats dd {
		margin: 0;
	}
	.muted {
		color: #999;
	}
	.error {
		color: #b00;
	}
	code {
		background: #f4f4f4;
		padding: 0 0.25rem;
		border-radius: 3px;
		font-size: 0.95em;
	}
</style>
