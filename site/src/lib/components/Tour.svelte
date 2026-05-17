<script lang="ts">
	import { onDestroy } from 'svelte';
	import { tourStore, tourPhase } from '$lib/stores/tour';

	/**
	 * Shepherd.js wrapper for the US6 guided tour.
	 *
	 * Steps:
	 *   1. Search bar           — `[data-testid="search-input"]`
	 *   2. Model selector       — `[data-testid="model-selector"]`
	 *   3. UMAP toggle          — `[data-testid="toggle-map"]`
	 *   4. Lasso hint           — desktop only (skipped < 1024 px)
	 *   5. Facets               — `[data-testid="facet-sidebar"]`
	 *                              (falls back to the mobile toggle on small viewports)
	 *   6. Cart                 — `[data-testid="toggle-cart"]`
	 *
	 * On mobile the tour attaches its tooltip below the highlighted target
	 * instead of beside it. Phase transitions go through `tourStore` so the
	 * "start" / "skip" actions can also be triggered from external places
	 * (the header button + the first-visit CTA banner).
	 */

	let shepherdInstance: { start: () => void; cancel: () => void; complete: () => void } | null =
		null;

	$: void launchOrTearDown($tourPhase);

	async function launchOrTearDown(p: 'idle' | 'running' | 'dismissed') {
		if (p === 'running') {
			await launch();
		} else if (shepherdInstance) {
			shepherdInstance.cancel();
			shepherdInstance = null;
		}
	}

	async function launch() {
		if (shepherdInstance) return;
		// Lazy-load shepherd.js — it's ~30 KB gz + brings its own CSS, no
		// reason to pay the cost until the user actually starts the tour.
		const { default: Shepherd } = await import('shepherd.js');
		await import('shepherd.js/dist/css/shepherd.css');

		const isMobile = typeof window !== 'undefined' && window.innerWidth < 1024;
		const tour = new Shepherd.Tour({
			useModalOverlay: true,
			defaultStepOptions: {
				cancelIcon: { enabled: true },
				classes: 'ohbm-shepherd',
				scrollTo: { behavior: 'smooth', block: 'center' }
			}
		});

		const goNext = (): void => {
			tourStore.next();
			tour.next();
		};
		const goBack = (): void => {
			tourStore.prev();
			tour.back();
		};
		const skip = (): void => {
			tourStore.skip();
			tour.cancel();
		};
		const finish = (): void => {
			tourStore.complete();
			tour.complete();
		};

		const place = (preferred: 'bottom' | 'right' | 'top'): 'bottom' | 'right' | 'top' =>
			isMobile ? 'bottom' : preferred;

		const baseButtons = (
			isFirst: boolean,
			isLast: boolean
		): Array<{ text: string; classes?: string; action: () => void }> => {
			const buttons: Array<{ text: string; classes?: string; action: () => void }> = [
				{ text: 'Skip', classes: 'shepherd-button-secondary', action: skip }
			];
			if (!isFirst) buttons.push({ text: 'Back', classes: 'shepherd-button-secondary', action: goBack });
			if (isLast) buttons.push({ text: 'Done', action: finish });
			else buttons.push({ text: 'Next', action: goNext });
			return buttons;
		};

		tour.addStep({
			id: 'search',
			title: 'Search',
			text: 'Type any keyword, author, or topic — typos are tolerated. Semantic search runs in the background; toggle it off if you only want literal matches.',
			attachTo: { element: '[data-testid="search-input"]', on: place('bottom') },
			buttons: baseButtons(true, false)
		});

		tour.addStep({
			id: 'model',
			title: 'Pick a lens',
			text: 'Switch the model + input pair to view the corpus through a different embedding. Each lens gives the UMAP its own colouring, clusters, and similar-abstract lists.',
			attachTo: { element: '[data-testid="model-selector"]', on: place('bottom') },
			buttons: baseButtons(false, false)
		});

		tour.addStep({
			id: 'map',
			title: 'The map',
			text: "Every dot is one accepted abstract, coloured + shaped by its cluster. Click a dot to focus that abstract; on desktop, lasso a region to filter the result list. Tap the rotation control on the 3D side to pause it.",
			attachTo: { element: '[data-testid="toggle-map"]', on: place('bottom') },
			buttons: baseButtons(false, false)
		});

		if (!isMobile) {
			tour.addStep({
				id: 'lasso',
				title: 'Lasso on 2D',
				text: 'On the 2D map, drag with the lasso tool (top-right of the chart toolbar) to select a region. The result list, facets, and 3D map all narrow to that selection in real time.',
				attachTo: { element: '[data-testid="umap-chart-2d"]', on: 'right' },
				buttons: baseButtons(false, false)
			});
		}

		tour.addStep({
			id: 'facets',
			title: 'Refine',
			text: 'Filter by cluster, topic, methods, population, and a dozen more facets. Each filter narrows the list AND dims the map; combine them freely.',
			attachTo: {
				element: isMobile ? '[data-testid="toggle-facets"]' : '[data-testid="facet-sidebar"]',
				on: place(isMobile ? 'bottom' : 'right')
			},
			buttons: baseButtons(false, false)
		});

		tour.addStep({
			id: 'cart',
			title: 'Save a list',
			text: 'Tap the cart icon on any card to save an abstract for later. The 🛒 button opens your saved list; from there you can email it to yourself or copy it to the clipboard.',
			attachTo: { element: '[data-testid="toggle-cart"]', on: place('bottom') },
			buttons: baseButtons(false, true)
		});

		tour.on('cancel', () => {
			tourStore.skip();
		});
		tour.on('complete', () => {
			tourStore.complete();
		});

		shepherdInstance = tour;
		tour.start();
	}

	onDestroy(() => {
		if (shepherdInstance) {
			shepherdInstance.cancel();
			shepherdInstance = null;
		}
	});
</script>

<style global>
	.ohbm-shepherd {
		--shepherd-primary: var(--accent, #2c5fa3);
	}
	.shepherd-element {
		border-radius: 6px;
		max-width: min(28rem, 90vw);
	}
	.shepherd-text {
		font-size: 0.92rem;
		line-height: 1.55;
	}
	.shepherd-button {
		background: var(--accent);
		color: var(--accent-text, white);
		padding: 0.4rem 0.9rem;
		font-size: 0.85rem;
		border-radius: 4px;
		margin-right: 0.4rem;
	}
	.shepherd-button-secondary {
		background: var(--bg-elevated);
		color: var(--text);
		border: 1px solid var(--border);
	}
</style>
