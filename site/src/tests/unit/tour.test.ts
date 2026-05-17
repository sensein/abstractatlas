import { afterEach, describe, expect, it } from 'vitest';
import { get } from 'svelte/store';
import { tourStore, TOUR_STORAGE_KEY } from '$lib/stores/tour';

describe('tourStore', () => {
	afterEach(() => {
		tourStore.reset();
		window.localStorage.removeItem(TOUR_STORAGE_KEY);
	});

	it('starts in the idle phase with step 0', () => {
		expect(get(tourStore.phase)).toBe('idle');
		expect(get(tourStore.step)).toBe(0);
	});

	it('start() sets phase to running and step to 0', () => {
		tourStore.start();
		expect(get(tourStore.phase)).toBe('running');
		expect(get(tourStore.step)).toBe(0);
	});

	it('next() advances the step counter', () => {
		tourStore.start();
		tourStore.next();
		tourStore.next();
		expect(get(tourStore.step)).toBe(2);
	});

	it('prev() decrements but clamps at 0', () => {
		tourStore.start();
		tourStore.next();
		tourStore.prev();
		tourStore.prev();
		expect(get(tourStore.step)).toBe(0);
	});

	it('complete() flips to dismissed + marks completedOrSkipped', () => {
		tourStore.start();
		tourStore.next();
		tourStore.complete();
		expect(get(tourStore.phase)).toBe('dismissed');
		expect(get(tourStore.step)).toBe(0);
		expect(get(tourStore.flags).completedOrSkipped).toBe(true);
	});

	it('skip() is equivalent to complete()', () => {
		tourStore.start();
		tourStore.skip();
		expect(get(tourStore.phase)).toBe('dismissed');
		expect(get(tourStore.flags).completedOrSkipped).toBe(true);
	});

	it('dismissCta() sets ctaDismissed without changing phase', () => {
		tourStore.dismissCta();
		expect(get(tourStore.flags).ctaDismissed).toBe(true);
		expect(get(tourStore.phase)).toBe('idle');
	});

	it('persists flags across reload', () => {
		tourStore.dismissCta();
		tourStore.complete();
		const raw = window.localStorage.getItem(TOUR_STORAGE_KEY);
		expect(raw).not.toBeNull();
		const parsed = JSON.parse(raw!);
		expect(parsed.ctaDismissed).toBe(true);
		expect(parsed.completedOrSkipped).toBe(true);
	});
});
