# Contract: render integration (`+page.svelte`)

The single wiring point. `UmapPanel` is unchanged.

## Seam: `scatterBackdropForMap` (`+page.svelte:840`)

Today:
```ts
$: scatterBackdropForMap = (() => {
	if (SITE_MODE !== 'neuroscape' || neuroscapeLodCap === null) return scatterBackdrop;
	const cap = neuroscapeLodCap;
	return scatterBackdrop.filter((p) => {
		const lv = (p as { lod_level?: number }).lod_level;
		return lv === undefined || lv <= cap;
	});
})();
```

New:
```ts
$: scatterBackdropForMap = (() => {
	if (SITE_MODE !== 'neuroscape' || neuroscapeLodCap === null) return scatterBackdrop;
	const yearActive = filterMinYear !== null || filterMaxYear !== null;
	if (yearActive && densityCalibration !== null) {
		return yearAwareSample(scatterBackdrop, densityCalibration);   // NEW — FR-001/002/003
	}
	const cap = neuroscapeLodCap;                                       // UNCHANGED full-span path — FR-004
	return scatterBackdrop.filter((p) => {
		const lv = (p as { lod_level?: number }).lod_level;
		return lv === undefined || lv <= cap;
	});
})();
```

## Calibration wiring

- `densityCalibration` computed once when the corpus + `neuroscapeLodCap`
  are resident: `targetBudget = count(atlasBackdrop where lod_level ≤ cap)`,
  then `calibrate(atlasBackdrop, targetBudget)`. Memoized; recomputed only
  if the corpus reloads. `null` until ready (⇒ full-span path, feature off).

## Behavioural contract (verified by e2e)

| ID | Behaviour |
|----|-----------|
| B1 | Full span (no year filter): `scatterBackdropForMap` byte-identical to today (FR-004/SC-003). |
| B2 | Fixed-width window slid across eras: visible backdrop dot count stays within a bounded band (≤~2×), vs today's 10×+ swing (SC-001). |
| B3 | Higher-volume years in a window still show more dots than lower-volume years (SC-002). |
| B4 | Result-list count for a window is unchanged vs today (FR-006/SC-004). |
| B5 | Clearing the year filter restores the full-span sample exactly (FR-005). |
| B6 | Zoom/pan with a year window active shows detail only within the window (FR-008 — already holds via `backdropFull` filtering). |

## Untouched (regression guards)

- `scatterBackdrop`, `listFacetFiltered`, facet counts, `backdropFull`,
  overlay, atlas-root branch, `/ohbm2026/` — no change.
- `UmapPanel` props/behaviour — no change (renders whatever it's given).

## Test data attributes

Reuse existing scatter/result testids; the e2e reads the rendered 2D
backdrop point count (e.g. via the plotly trace point array or an exposed
count) and the `result-count` for the invariance check.
