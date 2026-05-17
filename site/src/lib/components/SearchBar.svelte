<script lang="ts">
	import { searchQuery } from '$lib/stores/selection';

	let value = '';
	$: $searchQuery = value;

	function onClear() {
		value = '';
	}
</script>

<div class="searchbar" role="search">
	<label for="search-input" class="visually-hidden">Search abstracts</label>
	<input
		id="search-input"
		type="search"
		bind:value
		placeholder="Search by keyword, author, topic, or poster id…"
		autocomplete="off"
		spellcheck="false"
		data-testid="search-input"
	/>
	{#if value}
		<button type="button" on:click={onClear} aria-label="Clear search" data-testid="search-clear">
			×
		</button>
	{/if}
</div>

<style>
	.searchbar {
		position: relative;
		display: flex;
		align-items: center;
		width: 100%;
	}
	input[type='search'] {
		width: 100%;
		padding: 0.6rem 2.5rem 0.6rem 0.8rem;
		font-size: 1rem;
		border: 1px solid #ccc;
		border-radius: 6px;
		box-sizing: border-box;
		background: #fff;
		color: #222;
	}
	input[type='search']:focus {
		outline: 2px solid #2c5fa3;
		outline-offset: 0;
		border-color: #2c5fa3;
	}
	button {
		position: absolute;
		right: 0.4rem;
		top: 50%;
		transform: translateY(-50%);
		background: transparent;
		border: 0;
		font-size: 1.4rem;
		line-height: 1;
		cursor: pointer;
		color: #888;
		padding: 0.2rem 0.4rem;
	}
	button:hover {
		color: #222;
	}
	.visually-hidden {
		position: absolute;
		width: 1px;
		height: 1px;
		padding: 0;
		margin: -1px;
		overflow: hidden;
		clip: rect(0, 0, 0, 0);
		white-space: nowrap;
		border: 0;
	}
</style>
