<script lang="ts">
	import { activeFilters } from '$lib/stores/selection';
	import {
		FACET_KEYS_ORDERED,
		FACET_LABELS,
		clearAllFilters,
		toggleFilter,
		type FacetCounts,
		type FacetKey
	} from '$lib/facets';

	export let counts: FacetCounts;
	export let collapsedByDefault: FacetKey[] = [
		'keywords',
		'processing_packages',
		'brain_regions',
		'brain_networks',
		'recording_technology',
		'accepted_for'
	];

	let expanded: Record<string, boolean> = {};
	$: for (const key of FACET_KEYS_ORDERED) {
		if (!(key in expanded)) expanded[key] = !collapsedByDefault.includes(key);
	}

	function toggle(key: FacetKey, option: string) {
		$activeFilters = toggleFilter($activeFilters, key, option);
	}

	function clear() {
		$activeFilters = clearAllFilters();
	}

	function isActive(key: FacetKey, option: string): boolean {
		return $activeFilters.get(key)?.has(option) ?? false;
	}

	$: activeCount = [...$activeFilters.values()].reduce((sum, s) => sum + s.size, 0);
</script>

<aside class="facets" data-testid="facet-sidebar">
	<header>
		<h2>Filters</h2>
		{#if activeCount > 0}
			<button type="button" class="clear" on:click={clear} data-testid="facets-clear">
				Clear ({activeCount})
			</button>
		{/if}
	</header>

	{#each FACET_KEYS_ORDERED as key (key)}
		{@const options = counts.get(key) ?? []}
		{@const isOpen = expanded[key]}
		{#if options.length}
			<section class="facet" data-testid={`facet-${key}`}>
				<button
					type="button"
					class="facet-header"
					on:click={() => (expanded[key] = !isOpen)}
					aria-expanded={isOpen}
				>
					<span class="caret">{isOpen ? '▾' : '▸'}</span>
					<span class="facet-label">{FACET_LABELS[key]}</span>
					<span class="facet-count">{options.length}</span>
				</button>
				{#if isOpen}
					<ul class="options">
						{#each options.slice(0, 30) as opt (opt.value)}
							<li>
								<label
									class="opt"
									class:active={isActive(key, opt.value)}
									data-testid={`facet-option-${key}`}
								>
									<input
										type="checkbox"
										checked={isActive(key, opt.value)}
										on:change={() => toggle(key, opt.value)}
									/>
									<span class="opt-label">{opt.value}</span>
									<span class="opt-count">{opt.count}</span>
								</label>
							</li>
						{/each}
						{#if options.length > 30}
							<li class="more-hint">+ {options.length - 30} more</li>
						{/if}
					</ul>
				{/if}
			</section>
		{/if}
	{/each}
</aside>

<style>
	.facets {
		min-width: 0;
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
	}
	.options {
		list-style: none;
		padding: 0 0 0.25rem 1.1rem;
		margin: 0;
		display: flex;
		flex-direction: column;
		gap: 0.1rem;
	}
	.opt {
		display: flex;
		align-items: center;
		gap: 0.4rem;
		padding: 0.15rem 0.35rem;
		border-radius: 3px;
		cursor: pointer;
		font-size: 0.8rem;
	}
	.opt:hover {
		background: var(--bg-sunken);
	}
	.opt.active {
		background: var(--accent-soft-bg);
		color: var(--accent-soft-text);
	}
	.opt input[type='checkbox'] {
		margin: 0;
	}
	.opt-label {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}
	.opt-count {
		font-size: 0.72rem;
		color: var(--text-faint);
		font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
	}
	.more-hint {
		color: var(--text-faint);
		font-size: 0.72rem;
		padding-left: 0.4rem;
		font-style: italic;
	}
</style>
