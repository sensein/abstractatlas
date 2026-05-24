<!--
  Stage 15 (spec 015-neuroscape-context, FR-010 + FR-011 + FR-012 + T045 + T056):
  the bare-root cross-conference atlas scatter — and the same panel
  is reused on the /neuroscape/ subsite home (overlayPoints empty).

  Renders two traces:
    1. NeuroScape backdrop  — cluster-coloured, small, dim, dense.
    2. OHBM 2026 overlay    — outlined, larger, distinct foreground
                              (omitted when overlayPoints is empty).

  Props:
    - backdropPoints / overlayPoints / clusters: per-row data.
    - showOverlay: visibility of trace 2 (atlas-overlay toggle).
    - backdropOpacity: per-point alpha on trace 1 (density slider).
    - dimensionality: '3d' (default; scatter3d trace) or '2d' (scattergl).

  Performance: opacity + visibility changes are dispatched via
  `Plotly.restyle` so a slider drag doesn't trigger a full
  recompute of the 461K-point scatter. Only data-shape changes
  (point list / cluster table / dimensionality) call `Plotly.react`.
-->
<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	type PlotlyApi = typeof import('plotly.js-gl3d-dist-min');

	type BackdropPoint = {
		pubmed_id: number;
		cluster_id: number;
		umap_3d: [number, number, number];
		umap_2d?: [number, number];
		title: string;
		year: number;
	};
	type OverlayPoint = {
		submission_id: number;
		poster_id: number;
		umap_3d: [number, number, number];
		umap_2d?: [number, number];
		title: string;
		nearest_cluster_id: number;
	};
	type ClusterRow = {
		cluster_id: number;
		title: string;
		colour_hex: string;
		palette_tier: 'primary' | 'secondary';
	};

	export let backdropPoints: BackdropPoint[] = [];
	export let overlayPoints: OverlayPoint[] = [];
	export let clusters: ClusterRow[] = [];
	export let showOverlay: boolean = true;
	export let backdropOpacity: number = 0.25;
	export let dimensionality: '2d' | '3d' = '3d';

	let plotEl: HTMLDivElement | null = null;
	let plotly: PlotlyApi | null = null;
	let plotError: string | null = null;
	let plotInitialized = false;
	let plotInitializedFor: '2d' | '3d' | null = null;

	$: clusterColour = (() => {
		const map = new Map<number, string>();
		for (const c of clusters) map.set(c.cluster_id, c.colour_hex);
		return map;
	})();

	$: clusterTitle = (() => {
		const map = new Map<number, string>();
		for (const c of clusters) map.set(c.cluster_id, c.title);
		return map;
	})();

	function backdropTrace() {
		const is3d = dimensionality === '3d';
		const x = backdropPoints.map((p) =>
			is3d ? p.umap_3d[0] : (p.umap_2d ?? [0, 0])[0]
		);
		const y = backdropPoints.map((p) =>
			is3d ? p.umap_3d[1] : (p.umap_2d ?? [0, 0])[1]
		);
		const z = is3d ? backdropPoints.map((p) => p.umap_3d[2]) : undefined;
		const colours = backdropPoints.map(
			(p) => clusterColour.get(p.cluster_id) ?? '#9c9c9c'
		);
		const hoverText = backdropPoints.map(
			(p) =>
				`<b>${escape(p.title)}</b><br>${p.year} · ${escape(
					clusterTitle.get(p.cluster_id) ?? `Cluster ${p.cluster_id}`
				)}`
		);
		const base = {
			mode: 'markers' as const,
			x,
			y,
			name: 'NeuroScape backdrop',
			marker: {
				size: is3d ? 2 : 3,
				color: colours,
				opacity: backdropOpacity,
				line: { width: 0 }
			},
			hovertemplate: '%{text}<extra></extra>',
			text: hoverText,
			showlegend: false,
			customdata: backdropPoints.map((p) => ({
				kind: 'neuroscape',
				id: p.pubmed_id
			}))
		};
		return is3d
			? { ...base, type: 'scatter3d' as const, z }
			: { ...base, type: 'scattergl' as const };
	}

	function overlayTrace() {
		const is3d = dimensionality === '3d';
		const x = overlayPoints.map((p) =>
			is3d ? p.umap_3d[0] : (p.umap_2d ?? [0, 0])[0]
		);
		const y = overlayPoints.map((p) =>
			is3d ? p.umap_3d[1] : (p.umap_2d ?? [0, 0])[1]
		);
		const z = is3d ? overlayPoints.map((p) => p.umap_3d[2]) : undefined;
		const colours = overlayPoints.map(
			(p) => clusterColour.get(p.nearest_cluster_id) ?? '#1f77b4'
		);
		const hoverText = overlayPoints.map(
			(p) =>
				`<b>${escape(p.title)}</b><br>OHBM 2026 poster #${p.poster_id} · near ${escape(
					clusterTitle.get(p.nearest_cluster_id) ?? `Cluster ${p.nearest_cluster_id}`
				)}`
		);
		const base = {
			mode: 'markers' as const,
			x,
			y,
			name: 'OHBM 2026 overlay',
			visible: showOverlay,
			marker: {
				size: is3d ? 5 : 6,
				color: colours,
				opacity: 1.0,
				line: { color: '#111111', width: 1.5 }
			},
			hovertemplate: '%{text}<extra></extra>',
			text: hoverText,
			showlegend: false,
			customdata: overlayPoints.map((p) => ({
				kind: 'ohbm2026',
				id: p.poster_id
			}))
		};
		return is3d
			? { ...base, type: 'scatter3d' as const, z }
			: { ...base, type: 'scattergl' as const };
	}

	function escape(s: string): string {
		return s
			.replace(/&/g, '&amp;')
			.replace(/</g, '&lt;')
			.replace(/>/g, '&gt;');
	}

	function layoutFor(d: '2d' | '3d') {
		const base = {
			autosize: true,
			margin: { l: 0, r: 0, t: 0, b: 0 },
			hovermode: 'closest' as const,
			paper_bgcolor: 'rgba(0,0,0,0)',
			showlegend: false
		};
		if (d === '3d') {
			return {
				...base,
				scene: {
					xaxis: { visible: false, showspikes: false },
					yaxis: { visible: false, showspikes: false },
					zaxis: { visible: false, showspikes: false },
					bgcolor: 'rgba(0,0,0,0)'
				}
			};
		}
		return {
			...base,
			xaxis: { visible: false, zeroline: false, showgrid: false },
			yaxis: { visible: false, zeroline: false, showgrid: false, scaleanchor: 'x' },
			plot_bgcolor: 'rgba(0,0,0,0)'
		};
	}

	const plotConfig = {
		responsive: true,
		displaylogo: false,
		modeBarButtonsToRemove: ['toImage', 'sendDataToCloud'] as string[],
		displayModeBar: false
	};

	async function ensurePlotly() {
		if (plotly || plotError) return;
		try {
			plotly = (await import('plotly.js-gl3d-dist-min')).default as PlotlyApi;
		} catch (err) {
			plotError = `failed to load plotly: ${(err as Error)?.message ?? String(err)}`;
		}
	}

	async function renderPlotFull() {
		if (!plotEl || !plotly) return;
		const data = [backdropTrace()];
		if (overlayPoints.length > 0) data.push(overlayTrace());
		const layout = layoutFor(dimensionality);
		const needsFullInit = !plotInitialized || plotInitializedFor !== dimensionality;
		if (needsFullInit) {
			// Switching dimensionality re-initialises (scatter3d ↔
			// scattergl is a trace-type change). Calling newPlot makes
			// the intent explicit + clears any prior scene state.
			await plotly.newPlot(plotEl, data, layout, plotConfig);
			plotInitialized = true;
			plotInitializedFor = dimensionality;
		} else {
			await plotly.react(plotEl, data, layout, plotConfig);
		}
	}

	async function restyleOpacityOnly() {
		if (!plotEl || !plotly || !plotInitialized) return;
		try {
			await plotly.restyle(plotEl, { 'marker.opacity': backdropOpacity }, [0]);
		} catch {
			await renderPlotFull();
		}
	}

	async function restyleOverlayVisibility() {
		if (!plotEl || !plotly || !plotInitialized) return;
		if (overlayPoints.length === 0) return;
		try {
			await plotly.restyle(plotEl, { visible: showOverlay }, [1]);
		} catch {
			await renderPlotFull();
		}
	}

	onMount(async () => {
		await ensurePlotly();
		await renderPlotFull();
	});

	onDestroy(() => {
		if (plotly && plotEl) plotly.purge(plotEl);
	});

	// Reactive split: data + dimensionality changes do a full
	// react/newPlot pass; opacity + visibility changes go through the
	// cheap restyle path so a slider drag is fluid.
	$: if (plotly && plotEl && backdropPoints.length >= 0) {
		// Touch every data dep so Svelte tracks them.
		void backdropPoints;
		void overlayPoints;
		void clusters;
		void dimensionality;
		void renderPlotFull();
	}
	$: if (plotly && plotEl) {
		void backdropOpacity;
		void restyleOpacityOnly();
	}
	$: if (plotly && plotEl) {
		void showOverlay;
		void restyleOverlayVisibility();
	}
</script>

<div
	class="atlas-umap-panel"
	data-testid="atlas-umap-panel"
	data-dimensionality={dimensionality}
>
	{#if plotError}
		<div class="error-banner" role="alert" data-testid="atlas-umap-error">
			{plotError}
		</div>
	{:else}
		<div
			class="plot-host"
			bind:this={plotEl}
			data-testid="atlas-umap-plot"
		></div>
		<div class="counts" data-testid="atlas-umap-counts" aria-live="polite">
			<span>{backdropPoints.length.toLocaleString()} backdrop pts</span>
			{#if showOverlay && overlayPoints.length > 0}
				<span>·</span>
				<span>{overlayPoints.length.toLocaleString()} OHBM 2026 pts</span>
			{/if}
		</div>
	{/if}
</div>

<style>
	.atlas-umap-panel {
		flex: 1;
		display: flex;
		flex-direction: column;
		min-height: 0;
		position: relative;
	}

	.plot-host {
		flex: 1;
		min-height: 50vh;
	}

	.counts {
		position: absolute;
		bottom: 0.5rem;
		right: 0.75rem;
		display: flex;
		gap: 0.4rem;
		font-size: 0.85rem;
		color: var(--color-text-muted, #666);
		background: var(--color-surface, rgba(255, 255, 255, 0.75));
		padding: 0.15rem 0.5rem;
		border-radius: 4px;
		font-variant-numeric: tabular-nums;
		pointer-events: none;
	}

	.error-banner {
		padding: 1rem;
		border: 1px solid var(--color-error, #c00);
		border-radius: 4px;
		background: var(--color-error-bg, rgba(192, 0, 0, 0.08));
		color: var(--color-error, #c00);
	}
</style>
