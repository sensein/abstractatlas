<!--
  Reusable cart toggle icon. Same Lucide-style outlined-cart that OHBM
  2026's ResultList uses, kind-aware so atlas-root and neuroscape
  can pass the right `kind` for the typed cart store.

  Mirrors the original ResultList markup byte-for-byte except for the
  kind-tagged add/remove calls — keeps the visual language identical
  across the three sibling subsites so a visitor recognises the
  "in your list" / "not in list" pip immediately.
-->
<script lang="ts">
	import { cartStore } from '$lib/stores/cart';
	import type { CartKind } from '$lib/stores/cart';

	export let kind: CartKind = 'ohbm2026';
	export let id: number;
	export let inCart: boolean = false;
	export let disabled: boolean = false;
	export let testidPrefix: string = 'card-cart';

	function add() {
		cartStore.addItem(kind, id);
	}
	function remove() {
		cartStore.removeItem(kind, id);
	}
</script>

{#if inCart}
	<button
		type="button"
		class="cart-icon in-cart"
		on:click={remove}
		aria-label="Remove from your list"
		aria-pressed="true"
		title="In your list — click to remove"
		data-testid={`${testidPrefix}-remove`}
	>
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="currentColor"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<circle cx="9" cy="21" r="1.2" />
			<circle cx="18" cy="21" r="1.2" />
			<path
				fill="currentColor"
				stroke="currentColor"
				d="M2 3h2.5L5.5 7H21l-2 9H7L5.5 7 4.5 3H2zM7 9l1 5h11l1-5z"
			/>
		</svg>
		<span class="check-pip" aria-hidden="true">✓</span>
	</button>
{:else}
	<button
		type="button"
		class="cart-icon"
		on:click={add}
		{disabled}
		aria-label="Add to your list"
		aria-pressed="false"
		title="Add to your list"
		data-testid={`${testidPrefix}-add`}
	>
		<svg
			width="20"
			height="20"
			viewBox="0 0 24 24"
			fill="none"
			stroke="currentColor"
			stroke-width="2"
			stroke-linecap="round"
			stroke-linejoin="round"
			aria-hidden="true"
		>
			<circle cx="9" cy="21" r="1.2" />
			<circle cx="18" cy="21" r="1.2" />
			<path d="M2 3h2.5L5.5 7H21l-2 9H7L5.5 7" />
		</svg>
	</button>
{/if}

<style>
	.cart-icon {
		all: unset;
		cursor: pointer;
		position: relative;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		width: 2.1rem;
		height: 2.1rem;
		border-radius: 4px;
		color: var(--text-faint);
	}
	.cart-icon:hover {
		background: var(--accent-soft-bg);
		color: var(--accent);
	}
	.cart-icon.in-cart {
		color: var(--accent);
	}
	.cart-icon.in-cart:hover {
		color: var(--warning-text, var(--accent));
	}
	.cart-icon .check-pip {
		position: absolute;
		bottom: -2px;
		right: -2px;
		background: var(--success);
		color: var(--bg-elevated);
		border-radius: 999px;
		width: 0.9rem;
		height: 0.9rem;
		display: inline-flex;
		align-items: center;
		justify-content: center;
		font-size: 0.65rem;
		font-weight: 700;
		line-height: 1;
		border: 1.5px solid var(--bg-elevated);
	}
	.cart-icon:disabled {
		opacity: 0.4;
		cursor: not-allowed;
	}
</style>
