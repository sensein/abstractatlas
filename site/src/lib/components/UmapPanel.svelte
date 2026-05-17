<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { selectedCell, lassoSelection, focusedAbstract } from '$lib/stores/selection';
	import { loadCell, type CellShard } from '$lib/shards';
	import type { AbstractRecord } from '$lib/shards';

	export let abstracts: AbstractRecord[] = [];
	/**
	 * Mobile breakpoint — desktop ≥ 1024px gets lasso; smaller viewports get
	 * tap-to-filter-by-community per spec edge case "Mobile lasso".
	 */
	export let mobileBreakpoint = 1024;

	type PlotlyApi = typeof import('plotly.js-basic-dist-min');

	let plotly: PlotlyApi | null = null;
	let plotlyLoading = false;
	let plotlyError: string | null = null;

	let tab: '2d' | '3d' = '2d';
	let chartEl: HTMLDivElement | null = null;
	let cellShard: CellShard | null = null;
	let cellLoading = false;
	let cellError: string | null = null;

	let viewportWidth = typeof window !== 'undefined' ? window.innerWidth : 1280;
	let mobile = viewportWidth < mobileBreakpoint;

	$: cellKey = `${$selectedCell.model}_${$selectedCell.input}`;

	function onResize() {
		viewportWidth = window.innerWidth;
		mobile = viewportWidth < mobileBreakpoint;
		if (plotly && chartEl) {
			plotly.Plots.resize(chartEl);
		}
	}

	onMount(async () => {
		window.addEventListener('resize', onResize);
		await ensurePlotly();
	});

	onDestroy(() => {
		if (typeof window !== 'undefined') {
			window.removeEventListener('resize', onResize);
		}
		if (plotly && chartEl) {
			plotly.purge(chartEl);
		}
	});

	async function ensurePlotly() {
		if (plotly || plotlyLoading) return;
		plotlyLoading = true;
		try {
			plotly = (await import('plotly.js-basic-dist-min')).default as PlotlyApi;
		} catch (err) {
			plotlyError = (err as Error).message;
		} finally {
			plotlyLoading = false;
		}
	}

	$: void (async () => {
		// React to (model, input) changes — fetch the cell shard.
		const key = cellKey;
		cellLoading = true;
		cellError = null;
		const shard = await loadCell(key);
		// Bail out if the user has switched cells while we were fetching.
		if (key === cellKey) {
			cellShard = shard;
			cellLoading = false;
			if (shard === null) cellError = 'cell shard not available';
		}
	})();

	$: void renderChart(plotly, chartEl, cellShard, tab, abstracts, $lassoSelection, mobile);

	function renderChart(
		api: PlotlyApi | null,
		el: HTMLDivElement | null,
		shard: CellShard | null,
		mode: '2d' | '3d',
		records: AbstractRecord[],
		selected: Set<number> | null,
		isMobile: boolean
	) {
		if (!api || !el || !shard) return;

		// Build positional-joined arrays. The cell shard is sorted to match
		// abstracts.json so we can iterate by index.
		const xs: number[] = [];
		const ys: number[] = [];
		const zs: number[] = [];
		const ids: number[] = [];
		const posters: string[] = [];
		const titles: string[] = [];
		const selectedIdx: number[] = [];
		for (let i = 0; i < shard.rows.length; i++) {
			const row = shard.rows[i];
			const rec = records[i];
			if (!rec) continue;
			xs.push(row.umap2d[0]);
			ys.push(row.umap2d[1]);
			zs.push(row.umap3d[2]);
			ids.push(row.abstract_id);
			posters.push(rec.poster_id);
			titles.push(rec.title);
			if (selected !== null && selected.has(row.abstract_id)) selectedIdx.push(i);
		}
		// Color by community_id so clusters are visually distinct.
		const colors = shard.rows.map((r) => r.community_id);

		const baseTrace = {
			mode: 'markers' as const,
			marker: {
				size: mode === '2d' ? 6 : 4,
				color: colors,
				colorscale: 'Viridis',
				opacity: 0.8,
				line: { width: 0 }
			},
			customdata: posters.map((p, i) => [p, titles[i]]) as unknown as number[][],
			hovertemplate:
				'<b>%{customdata[0]}</b><br>%{customdata[1]}<extra>%{text}</extra>',
			text: shard.rows.map((r) => `community ${r.community_id}`),
			unselected: { marker: { opacity: 0.25 } },
			selected: { marker: { opacity: 1 } }
		};

		const data: unknown[] =
			mode === '2d'
				? [{ ...baseTrace, type: 'scattergl', x: xs, y: ys, selectedpoints: selectedIdx.length ? selectedIdx : undefined }]
				: [{ ...baseTrace, type: 'scatter3d', x: xs, y: ys, z: zs }];

		const layout: unknown = {
			margin: { l: 0, r: 0, t: 0, b: 0 },
			showlegend: false,
			hovermode: 'closest',
			dragmode: mode === '2d' && !isMobile ? 'lasso' : mode === '3d' ? 'orbit' : 'pan',
			paper_bgcolor: '#fff',
			plot_bgcolor: '#fafafa',
			...(mode === '2d'
				? { xaxis: { visible: false }, yaxis: { visible: false, scaleanchor: 'x' } }
				: {
						scene: {
							xaxis: { visible: false },
							yaxis: { visible: false },
							zaxis: { visible: false },
							bgcolor: '#fafafa'
						}
					})
		};

		const config = {
			responsive: true,
			displaylogo: false,
			modeBarButtonsToRemove:
				mode === '2d' ? ['select2d', 'autoScale2d'] : ['toImage'],
			scrollZoom: true
		};

		(api as unknown as { react: (...args: unknown[]) => Promise<unknown> })
			.react(el, data, layout, config)
			.then(() => {
				// Attach lasso + click handlers exactly once.
				const node = el as unknown as { on: (event: string, handler: (e: unknown) => void) => void };
				node.on('plotly_selected', (e: unknown) => {
					const ev = e as { points?: Array<{ pointIndex: number }> } | null;
					if (!ev || !ev.points) {
						$lassoSelection = null;
						return;
					}
					const ids: Set<number> = new Set();
					for (const p of ev.points) {
						const aid = shard.rows[p.pointIndex]?.abstract_id;
						if (aid !== undefined) ids.add(aid);
					}
					$lassoSelection = ids.size ? ids : null;
				});
				node.on('plotly_deselect', () => {
					$lassoSelection = null;
				});
				node.on('plotly_click', (e: unknown) => {
					const ev = e as { points?: Array<{ pointIndex: number }> } | null;
					const pt = ev?.points?.[0];
					if (!pt) return;
					const row = shard.rows[pt.pointIndex];
					if (!row) return;
					if (isMobile && mode === '2d') {
						// Mobile lasso replacement: tap → filter to the tapped point's community.
						const commId = row.community_id;
						const ids: Set<number> = new Set();
						for (const r of shard.rows) {
							if (r.community_id === commId) ids.add(r.abstract_id);
						}
						$lassoSelection = ids;
					}
					const rec = records[pt.pointIndex];
					if (rec?.poster_id) $focusedAbstract = rec.poster_id;
				});
			})
			.catch((err: Error) => {
				plotlyError = err.message;
			});
	}
</script>

<section class="umap-panel" data-testid="umap-panel">
	<header class="umap-header">
		<div class="tabs" role="tablist">
			<button
				role="tab"
				aria-selected={tab === '2d'}
				class:active={tab === '2d'}
				on:click={() => (tab = '2d')}
				data-testid="umap-tab-2d"
			>
				2D map{mobile ? '' : ' (lasso)'}
			</button>
			<button
				role="tab"
				aria-selected={tab === '3d'}
				class:active={tab === '3d'}
				on:click={() => (tab = '3d')}
				data-testid="umap-tab-3d"
			>
				3D map
			</button>
		</div>
		{#if $lassoSelection}
			<button
				type="button"
				class="clear-lasso"
				on:click={() => ($lassoSelection = null)}
				data-testid="umap-clear-lasso"
			>
				Clear selection ({$lassoSelection.size})
			</button>
		{/if}
	</header>

	<div class="chart-wrap" class:loading={plotlyLoading || cellLoading} data-testid="umap-chart-wrap">
		{#if plotlyError || cellError}
			<p class="error">
				Map unavailable: {plotlyError || cellError}
			</p>
		{:else if !plotly || cellLoading}
			<p class="status">Loading map…</p>
		{/if}
		<div bind:this={chartEl} class="chart" data-testid="umap-chart"></div>
	</div>

	{#if mobile && tab === '2d'}
		<p class="mobile-hint">Tap a point to filter by its community.</p>
	{/if}
</section>

<style>
	.umap-panel {
		display: flex;
		flex-direction: column;
		gap: 0.5rem;
		min-width: 0;
	}
	.umap-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		gap: 0.5rem;
		flex-wrap: wrap;
	}
	.tabs {
		display: flex;
		gap: 0.25rem;
	}
	.tabs button {
		all: unset;
		cursor: pointer;
		padding: 0.3rem 0.7rem;
		font-size: 0.85rem;
		border: 1px solid #d0d0d0;
		border-radius: 4px;
		background: #fff;
		color: #444;
	}
	.tabs button.active {
		background: #2c5fa3;
		color: #fff;
		border-color: #2c5fa3;
	}
	.clear-lasso {
		all: unset;
		cursor: pointer;
		padding: 0.25rem 0.6rem;
		border-radius: 4px;
		font-size: 0.8rem;
		background: #fff8e1;
		color: #a26000;
		border: 1px solid #f0d27a;
	}
	.clear-lasso:hover {
		background: #fff0c0;
	}
	.chart-wrap {
		position: relative;
		min-height: 300px;
		height: clamp(300px, 50vh, 540px);
		border: 1px solid #eaeaea;
		border-radius: 6px;
		background: #fafafa;
	}
	.chart {
		width: 100%;
		height: 100%;
	}
	.status,
	.error {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		color: #888;
		font-style: italic;
		margin: 0;
		pointer-events: none;
	}
	.error {
		color: #b00;
	}
	.mobile-hint {
		margin: 0;
		font-size: 0.75rem;
		color: #888;
	}
</style>
