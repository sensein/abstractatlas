<script lang="ts">
	import { onMount } from 'svelte';
	import { buildInfoFromEnv, loadManifest, type BuildInfo, type Manifest } from '$lib/shards';
	import BuildInfoFooter from '$lib/components/BuildInfo.svelte';

	let manifest: Manifest | null = null;
	const envBuildInfo: BuildInfo | null = buildInfoFromEnv();
	$: effectiveBuildInfo = manifest?.build_info ?? envBuildInfo;

	onMount(async () => {
		manifest = await loadManifest();
	});
</script>

<svelte:head>
	{#if effectiveBuildInfo}
		<title>OHBM 2026 — under construction · {effectiveBuildInfo.code_revision_short}</title>
	{:else}
		<title>OHBM 2026 — under construction</title>
	{/if}
</svelte:head>

<div class="shell">
	<header>
		<h1>OHBM 2026 — under construction</h1>
		<p class="subtitle">
			Stage 6 UI rewrite · static SvelteKit on GitHub Pages · accepted abstracts only
		</p>
	</header>

	<main>
		<slot />
	</main>

	<BuildInfoFooter buildInfo={effectiveBuildInfo} />
</div>

<style>
	:global(body) {
		margin: 0;
		font-family:
			system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
		color: #222;
		background: #fff;
	}
	.shell {
		min-height: 100vh;
		display: flex;
		flex-direction: column;
	}
	header {
		padding: 2rem 1rem 1rem;
		max-width: 56rem;
		margin: 0 auto;
		width: 100%;
		box-sizing: border-box;
	}
	header h1 {
		margin: 0 0 0.25rem;
		font-size: 1.5rem;
		font-weight: 600;
	}
	.subtitle {
		margin: 0;
		color: #666;
		font-size: 0.9rem;
	}
	main {
		flex: 1;
		padding: 1rem;
		max-width: 56rem;
		margin: 0 auto;
		width: 100%;
		box-sizing: border-box;
	}
</style>
