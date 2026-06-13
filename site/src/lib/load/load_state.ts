/**
 * Stage 24 (specs/024-fix-ios-safari-load) — bootstrap load-state helpers.
 *
 * The atlas presented its iPhone-Safari load failure as a permanent blank
 * screen / "Loading…" spinner because `+page.svelte` only flipped `loaded`
 * true AFTER its awaits, with no `+error.svelte` and no failure branch: any
 * thrown await left the render stuck on the spinner forever, with no message.
 *
 * These pure helpers model the critical-load outcome so the bootstrap can
 * ALWAYS escape the spinner — into a `ready` view on success or a visible,
 * human-readable error on failure (constitution Principle VI: fail loudly).
 * Non-critical work (e.g. warming the semantic-search worker) is intentionally
 * NOT routed through here, so its failure degrades a feature without blanking
 * the page.
 */

export type CriticalLoadOutcome = { ready: true } | { ready: false; reason: string };

/** Map any thrown value to a non-empty, human-readable failure reason. */
export function describeLoadError(err: unknown): string {
	if (err instanceof Error && err.message.trim()) return err.message.trim();
	if (typeof err === 'string' && err.trim()) return err.trim();
	return 'The atlas data could not be loaded.';
}

/**
 * Run the critical bootstrap load and settle to a terminal outcome. A resolved
 * `load()` yields `{ ready: true }`; any rejection yields
 * `{ ready: false, reason }` with a non-empty reason. This never rejects, so
 * the caller's render can always leave the loading state.
 */
export async function settleCriticalLoad(load: () => Promise<void>): Promise<CriticalLoadOutcome> {
	try {
		await load();
		return { ready: true };
	} catch (err) {
		return { ready: false, reason: describeLoadError(err) };
	}
}
