import { writable, get } from 'svelte/store';

/**
 * Guided-tour state machine (US6 / shepherd.js wrapper).
 *
 *   idle          → never started in this session
 *   running       → currently walking through tour steps
 *   dismissed     → user closed / completed at least once
 *
 * Two persistent flags in localStorage at `ohbm2026.ui.tour.v1`:
 *   cta_dismissed: true once the first-visit banner has been shown + closed
 *   completed_or_skipped: true once the tour itself was run end-to-end OR
 *                         the user pressed "skip"; controls whether the
 *                         banner is offered on future visits.
 */

const STORAGE_KEY = 'ohbm2026.ui.tour.v1';

export type TourPhase = 'idle' | 'running' | 'dismissed';

export interface TourFlags {
	ctaDismissed: boolean;
	completedOrSkipped: boolean;
}

function isBrowser(): boolean {
	return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
}

function loadFlags(): TourFlags {
	if (!isBrowser()) return { ctaDismissed: false, completedOrSkipped: false };
	try {
		const raw = window.localStorage.getItem(STORAGE_KEY);
		if (!raw) return { ctaDismissed: false, completedOrSkipped: false };
		const parsed = JSON.parse(raw);
		return {
			ctaDismissed: !!parsed?.ctaDismissed,
			completedOrSkipped: !!parsed?.completedOrSkipped
		};
	} catch {
		return { ctaDismissed: false, completedOrSkipped: false };
	}
}

function persist(flags: TourFlags): void {
	if (!isBrowser()) return;
	try {
		window.localStorage.setItem(STORAGE_KEY, JSON.stringify(flags));
	} catch {
		/* private mode / quota — best effort */
	}
}

const _phase = writable<TourPhase>('idle');
const _step = writable<number>(0);
const _flags = writable<TourFlags>(loadFlags());

function start(): void {
	_phase.set('running');
	_step.set(0);
}

function next(): void {
	_step.update((s) => s + 1);
}

function prev(): void {
	_step.update((s) => Math.max(0, s - 1));
}

function complete(): void {
	_phase.set('dismissed');
	_step.set(0);
	const next = { ...get(_flags), completedOrSkipped: true };
	_flags.set(next);
	persist(next);
}

function skip(): void {
	complete();
}

function dismissCta(): void {
	const next = { ...get(_flags), ctaDismissed: true };
	_flags.set(next);
	persist(next);
}

/**
 * Reset everything — primarily for tests. Production callers should use
 * the normal start/skip/complete flow.
 */
function reset(): void {
	_phase.set('idle');
	_step.set(0);
	const blank = { ctaDismissed: false, completedOrSkipped: false };
	_flags.set(blank);
	if (isBrowser()) {
		try {
			window.localStorage.removeItem(STORAGE_KEY);
		} catch {
			/* no-op */
		}
	}
}

// Three separately-subscribable stores so `$tourPhase`, `$tourStep`,
// `$tourFlags` work via Svelte's `$store` auto-subscribe shorthand.
export const tourPhase = { subscribe: _phase.subscribe };
export const tourStep = { subscribe: _step.subscribe };
export const tourFlags = { subscribe: _flags.subscribe };

export const tourStore = {
	start,
	next,
	prev,
	complete,
	skip,
	dismissCta,
	reset,
	phase: tourPhase,
	step: tourStep,
	flags: tourFlags
};

export const TOUR_STORAGE_KEY = STORAGE_KEY;
