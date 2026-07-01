# Quickstart: Year-Aware Backdrop Density

Client-side-only feature in `site/`. No Python, no corpus rerun, no
data-package re-publish.

## Prerequisites

Local NeuroScape dev build (per repo memory `local_dev_env`): copy
`site/.env.example` → `site/.env.local` with the `VITE_DATA_PACKAGE_URL_*`
values, then:

```bash
cd site
VITE_SITE_MODE=neuroscape pnpm dev
```

`neuroscape` mode loads the full ~461k corpus (carries `year` + `lod_level`
per point), which is what the sampler operates on.

## Implement (test-first order)

1. **Pure sampler + unit tests (failing first):**
   - Write `site/src/tests/unit/year_density.test.ts` covering the 9 cases in
     `contracts/year-density-sampler.md`.
   - Run red, then add `site/src/lib/atlas/year_density.ts`
     (`calibrate`, `yearQuota`, `yearAwareSample`) to green:

   ```bash
   cd site && pnpm exec vitest run src/tests/unit/year_density.test.ts
   ```

   (Use `vitest run` — never `pnpm test:unit -- --run`, which hangs in watch
   mode. Repo memory `feedback_vitest_run_mode`.)

2. **Wire the seam:** edit `scatterBackdropForMap` (`+page.svelte:840`) per
   `contracts/render-integration.md` — delegate to `yearAwareSample` when a
   year filter is active, keep the `lod_level ≤ cap` path for full span.
   Compute + memoize `densityCalibration` when the corpus is resident.

3. **e2e (failing first):** add
   `site/src/tests/e2e/neuroscape_year_density.spec.ts` — select a
   fixed-width window, record the rendered backdrop dot count at several
   era positions, assert the max/min ratio is within the band (B2), the
   full-span view is unchanged (B1), and `result-count` is unchanged (B4).

## Verify

```bash
cd site
pnpm exec vitest run                 # full unit suite incl. year_density
pnpm exec playwright test src/tests/e2e/neuroscape_year_density.spec.ts
pnpm run check                        # svelte-check 0/0
pnpm run build                        # all three modes still build
```

Manual check (neuroscape `pnpm dev`):
- No year filter → backdrop identical to before (default landing).
- Set a 3-year window, slide it early→recent → density stays legible and
  comparable (no near-empty early / saturated recent swing).
- Clear the filter → returns to the default sample.
- Zoom while windowed → detail dots are all within the window.

## Done-when

- Unit + e2e green; svelte-check clean; all three modes build.
- Full-span, atlas-root, `/ohbm2026/` unchanged.
- No `data/` writes, no parquet/manifest/provenance change.
