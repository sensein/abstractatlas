/**
 * Spec 026 — NeuroScape year-aware backdrop density.
 *
 * When a year filter is active on `/neuroscape/`, the scatter backdrop's
 * base sample is chosen so each year contributes dots ∝ √(that year's
 * count in the filtered set) — a *compressed-proportional* density that
 * tempers the steep 1999→2023 publication-volume growth without
 * flattening it, so sliding a fixed-width year window shows a comparable,
 * legible density at every position instead of the order-of-magnitude
 * swing a raw spatial sample produces.
 *
 * Within each year, the chosen dots are the ones with the smallest
 * `lod_level` (the existing quadtree blue-noise rank — coarsest first),
 * tie-broken by ascending `pubmed_id`. That yields a shape-preserving
 * spatial cover *of that year* for free, with no new precomputed data —
 * so the whole feature is client-side and the published data stays
 * byte-identical.
 *
 * All functions are pure, side-effect-free, and total (never throw).
 * Contract: specs/026-neuroscape-year-density/contracts/year-density-sampler.md
 */

export interface DensityPoint {
	pubmed_id: number;
	year: number;
	lod_level?: number;
}

export interface DensityCalibration {
	/** ≈ size of today's full-span base sample (points with lod_level ≤ cap). */
	targetBudget: number;
	/** Dots per √article: targetBudget / Σ_all √(count_y). */
	k: number;
}

/** Per-year article counts from a point list. Points without a finite
 *  `year` are ignored so a NaN/undefined key can never enter the map and
 *  break the deterministic year sort downstream. */
function countsByYear(points: readonly DensityPoint[]): Map<number, number> {
	const counts = new Map<number, number>();
	for (const p of points) {
		if (!Number.isFinite(p.year)) continue;
		counts.set(p.year, (counts.get(p.year) ?? 0) + 1);
	}
	return counts;
}

/**
 * Calibrate the dots-per-√article constant once from the full corpus so
 * the notional full-corpus total equals `targetBudget`. Empty corpus ⇒
 * `k = 0` (sampler then returns nothing, which the caller never hits
 * because the feature is off with no data).
 */
export function calibrate(
	fullCorpus: readonly DensityPoint[],
	targetBudget: number
): DensityCalibration {
	let sumSqrt = 0;
	for (const c of countsByYear(fullCorpus).values()) sumSqrt += Math.sqrt(c);
	return { targetBudget, k: sumSqrt > 0 ? targetBudget / sumSqrt : 0 };
}

/** Dots to render for a year with `countY` articles: round(k·√countY), ≥ 0. */
export function yearQuota(countY: number, k: number): number {
	if (countY <= 0 || k <= 0) return 0;
	return Math.round(k * Math.sqrt(countY));
}

/**
 * Compressed-proportional, shape-preserving sample of `points` (already
 * year+cluster filtered to the active window). Each year contributes
 * `min(count_y, round(k·√count_y))` dots — its lowest-`lod_level` points
 * (tiebreak ascending `pubmed_id`). Order of the returned array is
 * unspecified (the caller renders it as a set) but deterministic.
 */
export function yearAwareSample(
	points: readonly DensityPoint[],
	calib: DensityCalibration
): DensityPoint[] {
	if (points.length === 0 || calib.k <= 0) return [];

	// Bucket by year, skipping points without a finite year so the year
	// keys stay strictly numeric (a NaN/undefined key would make the
	// ascending-year sort below non-deterministic).
	const byYear = new Map<number, DensityPoint[]>();
	for (const p of points) {
		if (!Number.isFinite(p.year)) continue;
		const bucket = byYear.get(p.year);
		if (bucket) bucket.push(p);
		else byYear.set(p.year, [p]);
	}

	const out: DensityPoint[] = [];
	// Iterate years in ascending order so the result is deterministic
	// regardless of input order.
	for (const year of [...byYear.keys()].sort((a, b) => a - b)) {
		const bucket = byYear.get(year)!;
		const quota = Math.min(bucket.length, yearQuota(bucket.length, calib.k));
		if (quota >= bucket.length) {
			// Sparse year: keep all of it (no fabrication/duplication).
			out.push(...bucket);
			continue;
		}
		// Lowest lod_level first (coarsest = most spatially representative),
		// tiebreak ascending pubmed_id. Missing lod_level sorts as +∞ so
		// legacy builds fall back to a deterministic pubmed_id order.
		const ranked = [...bucket].sort((a, b) => {
			// `?? +Inf` handles null/undefined; `Number.isFinite` additionally
			// treats NaN (and ±Inf) as the rest tier, so the comparator can
			// never return NaN → the sort stays deterministic. Legacy builds
			// (no lod_level) fall through to the pubmed_id tiebreak.
			const la = Number.isFinite(a.lod_level) ? (a.lod_level as number) : Number.POSITIVE_INFINITY;
			const lb = Number.isFinite(b.lod_level) ? (b.lod_level as number) : Number.POSITIVE_INFINITY;
			if (la !== lb) return la - lb;
			return a.pubmed_id - b.pubmed_id;
		});
		for (let i = 0; i < quota; i++) out.push(ranked[i]);
	}
	return out;
}
