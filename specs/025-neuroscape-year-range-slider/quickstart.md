# Quickstart: NeuroScape Atlas Year Range Slider

Client-side-only feature in `site/`. No Python, no corpus rerun, no
data-package re-publish.

## Prerequisites

- Local site dev env per the repo memory `local_dev_env`: copy
  `site/.env.example` → `site/.env.local` with the
  `VITE_DATA_PACKAGE_URL_*` values, then run the NeuroScape build:

```bash
cd site
VITE_SITE_MODE=neuroscape pnpm dev
```

The `neuroscape` mode loads the full ~461k-article backdrop, which is what
populates `yearBounds` and the Years facet.

## Implement (test-first order)

1. **Pure helper + unit tests (failing first):**
   - Write `site/src/tests/unit/year_range.test.ts` covering the 9 cases in
     `contracts/year-range-helper.md`.
   - Run them red, then add `site/src/lib/filter/year_range.ts` to green:

   ```bash
   cd site && pnpm exec vitest run src/tests/unit/year_range.test.ts
   ```

   (Use `vitest run` — never `pnpm test:unit -- --run`, which drops into
   watch mode and hangs. See repo memory `feedback_vitest_run_mode`.)

2. **Component:** add `site/src/lib/components/YearRangeSlider.svelte`
   per `contracts/slider-ui.md` (two `role="slider"` handles, draggable
   band, pointer + keyboard, the listed `data-testid`s).

3. **Wire into the facet:** in `NeuroscapeFacets.svelte`, replace the
   `.year-row` two-input block with `<YearRangeSlider minYear maxYear
   bounds={yearBounds} on:change={...}>` and re-emit the existing
   `update` payload. Leave `activeCount` / `clearAll` as-is.

4. **e2e (failing first):** add
   `site/src/tests/e2e/neuroscape_year_slider.spec.ts` exercising U1–U6
   from the UI contract against the NeuroScape build.

## Verify

```bash
cd site
pnpm exec vitest run                 # full unit suite incl. year_range + facets
pnpm exec playwright test src/tests/e2e/neuroscape_year_slider.spec.ts
pnpm run build                        # all three modes still build
```

Manual check (neuroscape `pnpm dev`):
- Open "Filters" → "Years": two handles at the corpus bounds, no active badge.
- Drag each handle → list/scatter narrow, readout tracks.
- Drag the band → window slides, width preserved, stops at the bounds.
- Tab to a handle, arrow-key it; confirm touch works in mobile emulation.
- "Clear" returns to full span and drops the year filter.

## Done-when

- All unit + e2e tests green; all three site modes build.
- atlas-root and `/ohbm2026/` unaffected (no year facet there).
- No `data/` writes, no parquet/manifest/provenance change.
