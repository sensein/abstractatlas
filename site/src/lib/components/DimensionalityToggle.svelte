<!--
  Stage 15 (spec 015-neuroscape-context, FR-012 + T056-prep):
  the 2D ↔ 3D control on the atlas landing page.

  Two-segment button so the active mode is visible at a glance
  (vs a checkbox/toggle where the user has to read the label to
  know which mode is on).
-->
<script lang="ts">
	import { dimensionality } from '$lib/stores/dimensionality';

	$: current = $dimensionality;

	function set(d: '2d' | '3d') {
		$dimensionality = d;
	}
</script>

<div
	class="dim-toggle"
	role="radiogroup"
	aria-label="Scatter dimensionality"
	data-testid="dimensionality-toggle"
	data-state={current}
>
	<button
		type="button"
		role="radio"
		aria-checked={current === '3d'}
		class:active={current === '3d'}
		on:click={() => set('3d')}
		data-testid="dim-3d"
	>3D</button>
	<button
		type="button"
		role="radio"
		aria-checked={current === '2d'}
		class:active={current === '2d'}
		on:click={() => set('2d')}
		data-testid="dim-2d"
	>2D</button>
</div>

<style>
	.dim-toggle {
		display: inline-flex;
		border: 1px solid var(--border);
		border-radius: 4px;
		overflow: hidden;
		font-size: 0.9rem;
	}
	.dim-toggle button {
		all: unset;
		cursor: pointer;
		padding: 0.35rem 0.7rem;
		min-width: 2.5em;
		text-align: center;
		font-variant-numeric: tabular-nums;
		color: var(--text-muted);
	}
	.dim-toggle button:hover {
		background: var(--bg-subtle);
	}
	.dim-toggle button.active {
		background: var(--accent);
		color: var(--accent-text);
	}
</style>
