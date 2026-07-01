<!--
  Stage 15 UX-unification — neuroscape facet sidebar.

  Same OHBM-FacetSidebar visual pattern as AtlasRootFacets:
    - `<aside class="facets">` with "Filters" header + Clear button
    - Collapsible `<section class="facet">` per group

  Facets:
    - Clusters: 175-option multi-select, same as atlas-root.
    - Years: a range filter (min / max bounded by the corpus' min/max
      year). Spec 025 — a dual-handle <YearRangeSlider>: drag each handle
      to set an endpoint, drag the band between them to move the whole
      window. Replaces the former two `From`/`To` number inputs; the
      `update` event payload is unchanged.
-->
<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { normalize } from '$lib/filter';
	import YearRangeSlider from '$lib/components/YearRangeSlider.svelte';

	type Cluster = {
		cluster_id: number;
		title: string;
		colour_hex: string;
	};

	export let clustersById: Map<number, Cluster> = new Map();
	export let clusterCounts: Map<number, number> = new Map();
	export let selectedClusterIds: Set<number>;
	export let minYear: number | null;
	export let maxYear: number | null;
	export let yearBounds: { lo: number; hi: number };

	const dispatch = createEventDispatcher<{
		update: {
			cluster_ids: Set<number>;
			min_year: number | null;
			max_year: number | null;
		};
	}>();

	let clustersOpen = true;
	let yearsOpen = true;
	let clusterSearch = '';

	$: clusterPickList = (() => {
		const list = [...clustersById.values()];
		list.sort((a, b) => {
			const ca = clusterCounts.get(a.cluster_id) ?? 0;
			const cb = clusterCounts.get(b.cluster_id) ?? 0;
			if (ca !== cb) return cb - ca;
			return a.title.localeCompare(b.title);
		});
		if (!clusterSearch.trim()) return list;
		const needle = normalize(clusterSearch);
		return list.filter((c) => normalize(c.title).includes(needle));
	})();

	$: activeCount =
		selectedClusterIds.size +
		(minYear !== null && minYear > yearBounds.lo ? 1 : 0) +
		(maxYear !== null && maxYear < yearBounds.hi ? 1 : 0);

	function notify(next: {
		cluster_ids: Set<number>;
		min_year: number | null;
		max_year: number | null;
	}) {
		dispatch('update', next);
	}

	function toggleCluster(id: number) {
		const next = new Set(selectedClusterIds);
		if (next.has(id)) next.delete(id);
		else next.add(id);
		notify({ cluster_ids: next, min_year: minYear, max_year: maxYear });
	}

	function clearAll() {
		notify({ cluster_ids: new Set(), min_year: null, max_year: null });
	}

	function onYears(detail: { min_year: number | null; max_year: number | null }) {
		notify({
			cluster_ids: selectedClusterIds,
			min_year: detail.min_year,
			max_year: detail.max_year
		});
	}
</script>

<aside class="facets" data-testid="neuroscape-facet-sidebar">
	<header>
		<h2>Filters</h2>
		{#if activeCount > 0}
			<button
				type="button"
				class="clear"
				on:click={clearAll}
				data-testid="neuroscape-facets-clear"
			>
				Clear ({activeCount})
			</button>
		{/if}
	</header>

	<section class="facet" data-testid="neuroscape-facet-years">
		<button
			type="button"
			class="facet-header"
			on:click={() => (yearsOpen = !yearsOpen)}
			aria-expanded={yearsOpen}
		>
			<span class="caret">{yearsOpen ? '▾' : '▸'}</span>
			<span class="facet-label">Years</span>
			<span class="facet-count">{yearBounds.lo}–{yearBounds.hi}</span>
		</button>
		{#if yearsOpen}
			<YearRangeSlider
				{minYear}
				{maxYear}
				bounds={yearBounds}
				on:change={(e) => onYears(e.detail)}
			/>
		{/if}
	</section>

	<section class="facet" data-testid="neuroscape-facet-clusters">
		<button
			type="button"
			class="facet-header"
			on:click={() => (clustersOpen = !clustersOpen)}
			aria-expanded={clustersOpen}
		>
			<span class="caret">{clustersOpen ? '▾' : '▸'}</span>
			<span class="facet-label">Clusters</span>
			<span class="facet-count">{clustersById.size}</span>
			{#if selectedClusterIds.size > 0}
				<span class="facet-active" data-testid="neuroscape-cluster-selected-count"
					>· {selectedClusterIds.size} selected</span
				>
			{/if}
		</button>
		{#if clustersOpen}
			<input
				type="search"
				class="cluster-search"
				placeholder="Filter clusters…"
				bind:value={clusterSearch}
				data-testid="neuroscape-cluster-search"
			/>
			<ul class="options scroll" data-testid="neuroscape-cluster-list">
				{#each clusterPickList as c (c.cluster_id)}
					{@const count = clusterCounts.get(c.cluster_id) ?? 0}
					<li>
						<label class="opt" class:active={selectedClusterIds.has(c.cluster_id)}>
							<input
								type="checkbox"
								checked={selectedClusterIds.has(c.cluster_id)}
								on:change={() => toggleCluster(c.cluster_id)}
								data-testid={`neuroscape-cluster-cb-${c.cluster_id}`}
							/>
							<span
								class="cluster-swatch"
								style="background:{c.colour_hex}"
								aria-hidden="true"
							></span>
							<span class="opt-label" title={c.title}>{c.title}</span>
							<span class="opt-count">{count.toLocaleString()}</span>
						</label>
					</li>
				{/each}
			</ul>
		{/if}
	</section>
</aside>

<style>
	/* Visual alignment with OHBM 2026's FacetSidebar — see
	   AtlasRootFacets.svelte for the rationale. */
	.facets {
		min-width: 0;
		box-sizing: border-box;
		max-width: 100%;
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		font-size: 0.85rem;
		color: var(--text);
	}
	header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.5rem;
		padding-bottom: 0.5rem;
		border-bottom: 1px solid var(--border);
	}
	h2 {
		margin: 0;
		font-size: 0.95rem;
		font-weight: 600;
	}
	.clear {
		all: unset;
		cursor: pointer;
		font-size: 0.75rem;
		color: var(--accent);
		padding: 0.2rem 0.5rem;
		border-radius: 3px;
		border: 1px solid var(--border);
	}
	.clear:hover {
		background: var(--bg-sunken);
	}
	.facet {
		display: flex;
		flex-direction: column;
	}
	.facet-header {
		all: unset;
		cursor: pointer;
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.35rem 0;
		font-weight: 500;
		color: var(--text);
	}
	.facet-header:hover {
		color: var(--accent);
	}
	.caret {
		font-size: 0.65rem;
		color: var(--text-muted);
		width: 0.7rem;
	}
	.facet-label {
		flex: 1;
		font-size: 0.85rem;
	}
	.facet-count {
		font-size: 0.7rem;
		color: var(--text-faint);
		font-variant-numeric: tabular-nums;
	}
	.facet-active {
		color: var(--accent-soft-text, var(--accent));
		font-size: 0.7rem;
	}
	.cluster-search {
		padding: 0.3rem 0.5rem;
		margin: 0 0 0.25rem 1.1rem;
		border: 1px solid var(--border);
		border-radius: 3px;
		background: var(--bg);
		color: var(--text);
		font-size: 0.82rem;
	}
	.options {
		list-style: none;
		padding: 0 0 0.25rem 1.1rem;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}
	.options.scroll {
		max-height: 14rem;
		overflow-y: auto;
		padding-right: 0.4rem;
	}
	.opt {
		display: flex;
		align-items: flex-start;
		gap: 0.4rem;
		padding: 0.15rem 0.35rem;
		border-radius: 3px;
		cursor: pointer;
		font-size: 0.8rem;
	}
	.opt input[type='checkbox'] {
		margin: 0;
		margin-top: 0.18rem;
	}
	.opt:hover {
		background: var(--bg-sunken);
	}
	.opt.active {
		background: var(--accent-soft-bg);
		color: var(--accent-soft-text);
	}
	.cluster-swatch {
		display: inline-block;
		width: 0.65rem;
		height: 0.65rem;
		margin-top: 0.32rem;
		flex-shrink: 0;
		border-radius: 2px;
		border: 1px solid var(--border);
	}
	.opt-label {
		flex: 1;
		min-width: 0;
		line-height: 1.25;
		word-break: break-word;
	}
	.opt-count {
		flex-shrink: 0;
		font-size: 0.72rem;
		color: var(--text-faint);
		font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
	}
</style>
