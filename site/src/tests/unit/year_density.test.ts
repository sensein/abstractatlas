/**
 * Spec 026 — NeuroScape year-aware backdrop density.
 *
 * Unit tests for the pure compressed-proportional sampler
 * (`$lib/atlas/year_density`). See
 * specs/026-neuroscape-year-density/contracts/year-density-sampler.md
 * for the 9 required cases.
 *
 * Model: per year `y` with count `c_y`, render quota_y = min(c_y,
 * round(k·√c_y)) dots, where k = targetBudget / Σ√c_y over the full
 * corpus. Within a year, pick the lowest-`lod_level` points (tiebreak
 * ascending `pubmed_id`) → a shape-preserving spatial cover.
 */
import { describe, expect, it } from 'vitest';
import { calibrate, yearQuota, yearAwareSample, type DensityPoint } from '$lib/atlas/year_density';

/** Build `n` points for a given year with incrementing lod_level + pubmed_id. */
function pts(year: number, n: number, startId = year * 100000): DensityPoint[] {
	return Array.from({ length: n }, (_, i) => ({
		pubmed_id: startId + i,
		year,
		lod_level: i // 0..n-1 → i doubles as the spatial rank here
	}));
}

describe('calibrate() + yearQuota()', () => {
	it('k = targetBudget / Σ√count_y over the corpus', () => {
		// years: 2000→100 pts, 2020→10000 pts. Σ√ = 10 + 100 = 110.
		const corpus = [...pts(2000, 100), ...pts(2020, 10000)];
		const calib = calibrate(corpus, 1100);
		expect(calib.k).toBeCloseTo(10, 6); // 1100 / 110
		expect(calib.targetBudget).toBe(1100);
	});
	it('empty corpus ⇒ k = 0 (no throw)', () => {
		expect(calibrate([], 1000).k).toBe(0);
	});
	it('yearQuota rounds k·√count', () => {
		expect(yearQuota(100, 10)).toBe(100); // 10·10
		expect(yearQuota(10000, 10)).toBe(1000); // 10·100
	});
});

describe('yearAwareSample() — case 1 (√ compression)', () => {
	it('100× the count yields ~10× the dots, not 100×', () => {
		const corpus = [...pts(2000, 100), ...pts(2020, 10000)];
		const calib = calibrate(corpus, 1100); // k = 10
		const out = yearAwareSample(corpus, calib);
		const n2000 = out.filter((p) => p.year === 2000).length;
		const n2020 = out.filter((p) => p.year === 2020).length;
		expect(n2000).toBe(100); // min(100, 10·√100=100)
		expect(n2020).toBe(1000); // min(10000, 10·√10000=1000)
		expect(n2020 / n2000).toBeCloseTo(10, 5); // compressed from 100×
	});
});

describe('yearAwareSample() — case 2 (monotonic)', () => {
	it('year with more articles never gets fewer dots', () => {
		const corpus = [...pts(2001, 400), ...pts(2002, 900), ...pts(2003, 100)];
		const calib = calibrate(corpus, 600); // Σ√ = 20+30+10 = 60 → k=10
		const out = yearAwareSample(corpus, calib);
		const c = (y: number) => out.filter((p) => p.year === y).length;
		expect(c(2002)).toBeGreaterThanOrEqual(c(2001));
		expect(c(2001)).toBeGreaterThanOrEqual(c(2003));
	});
});

describe('yearAwareSample() — case 3 (budget bound)', () => {
	it('over the full corpus Σ quota ≈ targetBudget when no year clamps, and never exceeds Σ count', () => {
		// counts chosen so k ≤ √(min count) → no per-year clamp:
		// Σ√ = 20+50+100 = 170, target 1700 ⇒ k = 10 ≤ 20.
		const corpus = [...pts(2000, 400), ...pts(2010, 2500), ...pts(2020, 10000)];
		const target = 1700;
		const calib = calibrate(corpus, target);
		const out = yearAwareSample(corpus, calib);
		expect(out.length).toBeLessThanOrEqual(corpus.length);
		expect(Math.abs(out.length - target)).toBeLessThanOrEqual(3);
	});
	it('clamping a sparse year reduces the total below budget (never fabricates)', () => {
		// year 2000 has 100 pts but a √-quota of 125 → clamps to 100.
		const corpus = [...pts(2000, 100), ...pts(2010, 2500), ...pts(2020, 10000)];
		const calib = calibrate(corpus, 2000); // k = 12.5
		const out = yearAwareSample(corpus, calib);
		expect(out.filter((p) => p.year === 2000).length).toBe(100); // clamped, all shown
		expect(out.length).toBeLessThan(2000); // shortfall not redistributed (by design)
		expect(out.length).toBeLessThanOrEqual(corpus.length);
	});
});

describe('yearAwareSample() — case 4 (within-year blue-noise)', () => {
	it('selects the lowest lod_level points of a year (not a raw prefix / random)', () => {
		// year 2010: 5 points with lod_level 4,2,0,3,1 (shuffled), pubmed 10..14
		const yr: DensityPoint[] = [
			{ pubmed_id: 10, year: 2010, lod_level: 4 },
			{ pubmed_id: 11, year: 2010, lod_level: 2 },
			{ pubmed_id: 12, year: 2010, lod_level: 0 },
			{ pubmed_id: 13, year: 2010, lod_level: 3 },
			{ pubmed_id: 14, year: 2010, lod_level: 1 }
		];
		const calib = calibrate(yr, 3); // Σ√5≈2.236 → k≈1.342; quota=round(1.342·√5)=3
		const out = yearAwareSample(yr, calib).filter((p) => p.year === 2010);
		expect(out.length).toBe(3);
		// lowest three lod_levels are 0,1,2 → pubmed 12,14,11
		expect(out.map((p) => p.lod_level).sort((a, b) => a! - b!)).toEqual([0, 1, 2]);
	});
	it('ties on lod_level break by ascending pubmed_id', () => {
		const yr: DensityPoint[] = [
			{ pubmed_id: 30, year: 2011, lod_level: 0 },
			{ pubmed_id: 20, year: 2011, lod_level: 0 },
			{ pubmed_id: 25, year: 2011, lod_level: 0 }
		];
		const calib = { targetBudget: 2, k: 2 / Math.sqrt(3) }; // quota=round(k√3)=2
		const out = yearAwareSample(yr, calib).filter((p) => p.year === 2011);
		expect(out.length).toBe(2);
		expect(out.map((p) => p.pubmed_id).sort((a, b) => a - b)).toEqual([20, 25]);
	});
});

describe('yearAwareSample() — case 5 (sparse year: all shown)', () => {
	it('never fabricates/duplicates when quota ≥ count', () => {
		const corpus = [...pts(2000, 4), ...pts(2020, 10000)];
		const calib = calibrate(corpus, 5000);
		const out = yearAwareSample(corpus, calib);
		expect(out.filter((p) => p.year === 2000).length).toBe(4); // all 4
		// no duplicate ids
		const ids = out.map((p) => p.pubmed_id);
		expect(new Set(ids).size).toBe(ids.length);
	});
});

describe('yearAwareSample() — case 6 (single-year window)', () => {
	it('returns a bounded cover of the one year', () => {
		const corpus = pts(2015, 1000);
		const calib = calibrate(corpus, 100); // k = 100/√1000 ≈ 3.162 → quota=round(3.162·√1000)=100
		const out = yearAwareSample(corpus, calib);
		expect(out.length).toBe(100);
		expect(out.every((p) => p.year === 2015)).toBe(true);
	});
});

describe('yearAwareSample() — case 7 (empty input)', () => {
	it('returns [] without throwing', () => {
		expect(yearAwareSample([], { targetBudget: 1000, k: 5 })).toEqual([]);
	});
});

describe('yearAwareSample() — case 8 (legacy: no lod_level)', () => {
	it('deterministic, reproducible selection when lod_level is absent', () => {
		const yr: DensityPoint[] = Array.from({ length: 10 }, (_, i) => ({
			pubmed_id: 100 + i,
			year: 2012
		}));
		const calib = { targetBudget: 4, k: 4 / Math.sqrt(10) }; // quota=round(k√10)=4
		const a = yearAwareSample(yr, calib);
		const b = yearAwareSample(yr, calib);
		expect(a.length).toBe(4);
		expect(a.map((p) => p.pubmed_id)).toEqual(b.map((p) => p.pubmed_id)); // reproducible
	});
});

describe('yearAwareSample() — case 9 (determinism)', () => {
	it('same input ⇒ same output (stable ordering)', () => {
		const corpus = [...pts(2000, 300), ...pts(2010, 1200), ...pts(2020, 9000)];
		const calib = calibrate(corpus, 1500);
		const a = yearAwareSample(corpus, calib).map((p) => p.pubmed_id);
		const b = yearAwareSample(corpus, calib).map((p) => p.pubmed_id);
		expect(a).toEqual(b);
	});
});
