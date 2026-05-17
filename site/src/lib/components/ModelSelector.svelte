<script lang="ts">
	import { selectedCell } from '$lib/stores/selection';
	import type { Manifest } from '$lib/shards';

	export let manifest: Manifest | null = null;

	const labels: Record<string, string> = {
		neuroscape: 'NeuroScape',
		voyage: 'Voyage',
		minilm: 'MiniLM',
		openai: 'OpenAI',
		pubmedbert: 'PubMedBERT',
		abstract: 'Abstract',
		claims: 'Claims',
		methods: 'Methods'
	};

	function label(key: string): string {
		return labels[key] ?? key;
	}
</script>

<div class="model-selector" data-testid="model-selector">
	<label>
		<span class="caption">Model</span>
		<select bind:value={$selectedCell.model} data-testid="model-selector-model" disabled={!manifest}>
			{#if manifest}
				{#each manifest.models as m (m)}
					<option value={m}>{label(m)}</option>
				{/each}
			{/if}
		</select>
	</label>
	<span class="sep">×</span>
	<label>
		<span class="caption">Input</span>
		<select bind:value={$selectedCell.input} data-testid="model-selector-input" disabled={!manifest}>
			{#if manifest}
				{#each manifest.inputs as i (i)}
					<option value={i}>{label(i)}</option>
				{/each}
			{/if}
		</select>
	</label>
</div>

<style>
	.model-selector {
		display: flex;
		align-items: flex-end;
		gap: 0.4rem;
		font-size: 0.85rem;
	}
	label {
		display: flex;
		flex-direction: column;
		gap: 0.15rem;
	}
	.caption {
		color: #666;
		font-size: 0.7rem;
		text-transform: uppercase;
		letter-spacing: 0.04em;
	}
	select {
		font-size: 0.85rem;
		padding: 0.3rem 0.5rem;
		border: 1px solid #ccc;
		border-radius: 4px;
		background: #fff;
		min-width: 8rem;
	}
	select:focus {
		outline: 2px solid #2c5fa3;
		outline-offset: -1px;
		border-color: #2c5fa3;
	}
	.sep {
		color: #aaa;
		padding-bottom: 0.45rem;
	}
</style>
