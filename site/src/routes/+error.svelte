<script lang="ts">
	// Stage 24 (specs/024-fix-ios-safari-load) — route error boundary.
	//
	// Before this existed, any uncaught error during route load / hydration
	// (a thrown await in a `load`/`onMount`, a failed dynamic import, an iOS
	// WebKit tab-pressure abort) rendered as a BLANK PAGE with no message —
	// the exact "site does not load" symptom on iPhone Safari. This boundary
	// guarantees a visible, human-readable failure instead (Constitution VI:
	// fail loudly), satisfying spec FR-004 / User Story 2.
	import { page } from '$app/stores';
	import { base } from '$app/paths';

	$: status = $page.status;
	$: message = $page.error?.message?.trim() || 'Something went wrong while loading the atlas.';

	function reload() {
		if (typeof location !== 'undefined') location.reload();
	}
</script>

<section class="error-boundary" data-testid="route-error" role="alert">
	<h1>The atlas couldn’t load{status ? ` (${status})` : ''}</h1>
	<p class="error-message">{message}</p>
	<p class="error-help">
		This can happen on older devices or flaky connections. Try reloading, and if
		it keeps failing on a phone, opening the atlas on a laptop usually works.
	</p>
	<div class="error-actions">
		<button type="button" class="error-retry" on:click={reload}>Reload</button>
		<a class="error-home" href={`${base}/`}>Back to start</a>
	</div>
</section>

<style>
	.error-boundary {
		max-width: 36rem;
		margin: 4rem auto;
		padding: 0 1.25rem;
		text-align: center;
	}
	.error-boundary h1 {
		font-size: 1.4rem;
		margin-bottom: 0.75rem;
	}
	.error-message {
		font-weight: 600;
		margin-bottom: 0.5rem;
	}
	.error-help {
		opacity: 0.8;
		margin-bottom: 1.25rem;
	}
	.error-actions {
		display: flex;
		gap: 0.75rem;
		justify-content: center;
		flex-wrap: wrap;
	}
	.error-retry,
	.error-home {
		padding: 0.5rem 1rem;
		border-radius: 0.4rem;
		border: 1px solid currentColor;
		background: transparent;
		color: inherit;
		font: inherit;
		cursor: pointer;
		text-decoration: none;
	}
</style>
