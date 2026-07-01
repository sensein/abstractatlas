<!--
  Spec 025 — NeuroScape atlas year range slider.

  Dual-handle range slider that replaces the two `From`/`To` number boxes
  in the NeuroScape "Years" facet. Two `role="slider"` thumbs set the
  start/end endpoints (US1); the draggable band between them shifts the
  whole window, width preserved (US2). Built from a plain track + buttons
  + Pointer Events (mouse + touch on one path) — no slider dependency.

  All window math lives in the pure `$lib/filter/year_range` helper; this
  component only maps pointer/keyboard input to calls there and renders.
  The parent owns the filter state (minYear/maxYear) and is the single
  source of truth; we derive the window from it via `fromFilter` and emit
  `change` with `toFilter` (full span ⇒ {min_year:null,max_year:null}).
-->
<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import {
		fromFilter,
		toFilter,
		setStart,
		setEnd,
		moveWindow,
		type YearWindow,
		type YearFilter
	} from '$lib/filter/year_range';

	export let minYear: number | null;
	export let maxYear: number | null;
	export let bounds: { lo: number; hi: number };

	const dispatch = createEventDispatcher<{ change: YearFilter }>();

	// Derived window — recomputed whenever the parent's filter changes.
	// During a drag the parent echoes the same filter back, so this
	// re-derivation round-trips to the same window (see year_range tests).
	$: win = fromFilter({ min_year: minYear, max_year: maxYear }, bounds);

	// Degenerate / pre-load corpus (lo === hi, or {0,0} before the backdrop
	// arrives): render a single fixed position and disable interaction.
	$: span = bounds.hi - bounds.lo;
	$: disabled = span <= 0;
	$: startPct = disabled ? 0 : ((win.start - bounds.lo) / span) * 100;
	$: endPct = disabled ? 100 : ((win.end - bounds.lo) / span) * 100;

	let trackEl: HTMLDivElement;
	let dragging: 'start' | 'end' | 'band' | null = null;
	let bandStartX = 0;
	let bandStartWin: YearWindow = { start: 0, end: 0 };

	function commit(next: YearWindow) {
		win = next; // immediate local feedback
		dispatch('change', toFilter(next, bounds));
	}

	function yearFromClientX(clientX: number): number {
		if (!trackEl) return bounds.lo;
		const rect = trackEl.getBoundingClientRect();
		if (rect.width <= 0) return bounds.lo;
		const frac = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
		return Math.round(bounds.lo + frac * span);
	}

	function onThumbDown(which: 'start' | 'end', e: PointerEvent) {
		if (disabled) return;
		e.preventDefault();
		dragging = which;
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
	}

	function onBandDown(e: PointerEvent) {
		if (disabled) return;
		e.preventDefault();
		dragging = 'band';
		bandStartX = e.clientX;
		bandStartWin = win;
		(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
	}

	function onPointerMove(e: PointerEvent) {
		if (!dragging || disabled) return;
		if (dragging === 'start') {
			commit(setStart(win, yearFromClientX(e.clientX), bounds));
		} else if (dragging === 'end') {
			commit(setEnd(win, yearFromClientX(e.clientX), bounds));
		} else {
			if (!trackEl) return;
			const rect = trackEl.getBoundingClientRect();
			const deltaYears =
				rect.width <= 0 ? 0 : Math.round(((e.clientX - bandStartX) / rect.width) * span);
			commit(moveWindow(bandStartWin, deltaYears, bounds));
		}
	}

	// Also cleared on pointercancel (e.g. a touch interrupted by a scroll).
	function onPointerUp() {
		dragging = null;
	}

	function onThumbKey(which: 'start' | 'end', e: KeyboardEvent) {
		if (disabled) return;
		const cur = which === 'start' ? win.start : win.end;
		let target = cur;
		switch (e.key) {
			case 'ArrowLeft':
			case 'ArrowDown':
				target = cur - 1;
				break;
			case 'ArrowRight':
			case 'ArrowUp':
				target = cur + 1;
				break;
			case 'Home':
				target = bounds.lo;
				break;
			case 'End':
				target = bounds.hi;
				break;
			default:
				return;
		}
		e.preventDefault();
		commit(which === 'start' ? setStart(win, target, bounds) : setEnd(win, target, bounds));
	}
</script>

<div class="year-slider" data-testid="neuroscape-year-slider" class:disabled>
	<div class="track" bind:this={trackEl}>
		<!-- Selected window fill — draggable to move the whole window. -->
		<button
			type="button"
			class="band"
			data-testid="neuroscape-year-band"
			style="left:{startPct}%; width:{Math.max(0, endPct - startPct)}%"
			aria-label="Move selected year range"
			tabindex="-1"
			{disabled}
			on:pointerdown={onBandDown}
			on:pointermove={onPointerMove}
			on:pointerup={onPointerUp}
			on:pointercancel={onPointerUp}
		></button>

		<button
			type="button"
			class="thumb"
			data-testid="neuroscape-year-handle-start"
			style="left:{startPct}%"
			role="slider"
			aria-label="Start year"
			aria-valuemin={bounds.lo}
			aria-valuemax={bounds.hi}
			aria-valuenow={win.start}
			aria-disabled={disabled}
			{disabled}
			on:pointerdown={(e) => onThumbDown('start', e)}
			on:pointermove={onPointerMove}
			on:pointerup={onPointerUp}
			on:pointercancel={onPointerUp}
			on:keydown={(e) => onThumbKey('start', e)}
		></button>

		<button
			type="button"
			class="thumb"
			data-testid="neuroscape-year-handle-end"
			style="left:{endPct}%"
			role="slider"
			aria-label="End year"
			aria-valuemin={bounds.lo}
			aria-valuemax={bounds.hi}
			aria-valuenow={win.end}
			aria-disabled={disabled}
			{disabled}
			on:pointerdown={(e) => onThumbDown('end', e)}
			on:pointermove={onPointerMove}
			on:pointerup={onPointerUp}
			on:pointercancel={onPointerUp}
			on:keydown={(e) => onThumbKey('end', e)}
		></button>
	</div>

	<div class="readout" data-testid="neuroscape-year-readout">
		<span>{win.start}</span><span class="dash">–</span><span>{win.end}</span>
	</div>
</div>

<style>
	.year-slider {
		display: flex;
		flex-direction: column;
		gap: 0.4rem;
		padding: 0.5rem 0.6rem 0.35rem 1.1rem;
	}
	.track {
		position: relative;
		height: 1.4rem;
		margin: 0 0.5rem;
	}
	/* Rail */
	.track::before {
		content: '';
		position: absolute;
		top: 50%;
		left: -0.5rem;
		right: -0.5rem;
		height: 3px;
		transform: translateY(-50%);
		background: var(--border);
		border-radius: 2px;
	}
	.band {
		all: unset;
		position: absolute;
		top: 50%;
		height: 3px;
		transform: translateY(-50%);
		background: var(--accent);
		border-radius: 2px;
		cursor: grab;
		touch-action: none;
	}
	.band:active {
		cursor: grabbing;
	}
	.thumb {
		all: unset;
		position: absolute;
		top: 50%;
		width: 0.85rem;
		height: 0.85rem;
		transform: translate(-50%, -50%);
		box-sizing: border-box;
		background: var(--bg-elevated);
		border: 2px solid var(--accent);
		border-radius: 50%;
		cursor: pointer;
		touch-action: none;
	}
	.thumb:focus-visible {
		outline: 2px solid var(--accent);
		outline-offset: 2px;
	}
	.year-slider.disabled .thumb,
	.year-slider.disabled .band {
		cursor: default;
		opacity: 0.5;
	}
	.readout {
		display: flex;
		justify-content: center;
		gap: 0.25rem;
		font-size: 0.78rem;
		color: var(--text-faint);
		font-variant-numeric: tabular-nums;
	}
	.readout .dash {
		color: var(--text-muted);
	}
</style>
