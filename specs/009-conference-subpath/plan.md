# Implementation Plan: Conference subpath rework — OHBM 2026 under `/ohbm2026/`

**Branch**: `009-conference-subpath` | **Date**: 2026-05-18 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-conference-subpath/spec.md`

## Summary

Move every OHBM-2026 surface (home, About, abstract permalink) under a `/ohbm2026/` URL subpath without changing any feature behaviour. The site stays the same Stage-6 SvelteKit app; only the base path moves. Root `<cname>/` redirects to `<cname>/ohbm2026/`; legacy URLs (`<cname>/abstract/*`, `<cname>/about`) are intentionally NOT preserved; PR previews mirror production at `<cname>/pr-<N>/ohbm2026/`.

Primary mechanism: SvelteKit's `kit.paths.base` config. The deploy + PR-preview workflows widen their `BASE_PATH` from `/pr-<N>` to `/pr-<N>/ohbm2026` (and production builds with `BASE_PATH=/ohbm2026`). A small static root index + 404 at `<cname>/` issues a `<meta http-equiv="refresh">` + JS redirect to `<cname>/ohbm2026/`. The cart-email permalinks, the SPA-redirect `?spa=` handoff, and the Playwright spec base-URLs all need a base-aware sweep.

No data-shard changes — `build_info` is byte-identical, no `conference` field, no schema bump (FR-109 + SC-105).

## Technical Context

**Language/Version**: TypeScript 5 / Svelte 5 / Vite 6 for the site. Python 3.14 for the data-package builder (no behaviour change — only the link-check + a quickstart path get touched).
**Primary Dependencies**: SvelteKit 2 + `@sveltejs/adapter-static`. The base-path move is configured through `kit.paths.base` — a documented, supported mechanism (no Vite hacks, no runtime monkey-patching).
**Storage**: None. The site loads its static-JSON shards from `site/static/data/` (unchanged) and the runtime data tarball from the Dropbox URL pinned by `vars.OHBM2026_UI_DATA_PACKAGE_URL` (unchanged).
**Testing**: Vitest for unit tests, `@playwright/test` for e2e (the seven existing e2e specs plus a new `subpath.spec.ts` for SC-101 / SC-103 / SC-106), `pnpm build` for compile-time validation, `scripts/eval_typo_recall.py` for SC-010 regression (data-only — unaffected by this rework).
**Target Platform**: GitHub Pages (gh-pages branch), served at `abstractatlas.brainkb.org` (CNAME) for production and `…/pr-<N>/…` for PR previews. No CDN with edge-redirect rules — gh-pages serves static files only, so the root redirect MUST be a static `<meta http-equiv="refresh">` + JS `location.replace`. That is the closest static-site equivalent of a 301 (≤ 1 hop perceptually, but not a true HTTP 301).
**Project Type**: Static site (the SvelteKit app is built once and uploaded; no server runtime).
**Performance Goals**: Identical to Stage 6 — SC-001 (FCP ≤ 3 s), SC-002 (search latency ≤ 500 ms warm), SC-003 (cell switch ≤ 1.5 s), SC-004 (mobile 360 × 640 no overflow), SC-006 (data-package ≤ 50 MB gzipped). The subpath rework MUST NOT regress any of these.
**Constraints**: No hardcoded `/abstract/`, `/about`, or root-relative URLs may remain in `site/src/` after the rework — every internal reference uses SvelteKit's `$app/paths` `base` so the same source tree works at both `/ohbm2026/` (production) and `/pr-<N>/ohbm2026/` (preview). The cart-email permalinks (currently composed in `cart_email.ts`) must use `window.location.origin + base + '/abstract/<id>'`.
**Scale/Scope**: ~3,244 abstracts (unchanged); one SvelteKit app; eight existing Playwright specs to update; one new e2e spec; two workflow yamls to widen (`pr-preview.yml`, `lighthouse.yml`); one root-redirect file pair (`<cname>/index.html`, `<cname>/404.html`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Reproducible Venv Execution** — PASS. The only Python touch is `scripts/eval_typo_recall.py` (re-run for SC-010 regression), already invoked via `.venv/bin/python`. No new Python entry-points.
- **II. Immutable Evidence And Canonical Data** — PASS. No data writes; no canonical-corpus rewrite; no new artifact roots. The data package is byte-identical (SC-105).
- **III. Resumable, Auditable Pipelines** — N/A. No pipeline changes.
- **IV. Plan-First, Test-Driven Delivery** — PASS. This plan precedes the change; the new `subpath.spec.ts` Playwright test is named first and will fail until the base-path migration lands. Two existing specs (`browse.spec.ts`, `sc-sweep.spec.ts`) get base-URL updates; their pre-rework forms are expected to fail post-rework until the base-aware sweep is complete.
- **V. Secret-Safe, Reviewable Delivery** — PASS. No new secrets; no changes to `OHBM2026_UI_DATA_PACKAGE_URL` / `_SHA256` / `GITHUB_TOKEN`. Commits land in small slices (workflow widen → site base-path config → cart-email + SPA-redirect → root-redirect static files → tests).
- **VI. Fail Loudly, No Shortcuts** — PASS. The root-redirect is a static `<meta http-equiv="refresh">` + JS `location.replace`, which is the honest static-site equivalent of a 301 and is named as such in the spec and research — not a silent fallback. No `--no-verify`. No bare excepts. Pre-rework legacy URLs WILL 404 (FR-106), which is the conscious choice the user accepted in Q2 — not a silent regression.
- **VII. Discover External State, Don't Hardcode It** — PASS. SvelteKit's `kit.paths.base` is discovered at build time from the `BASE_PATH` environment variable already set by the deploy workflows. Asset paths are derived from `$app/paths`'s `base` import; no hardcoded `/ohbm2026/` strings outside the build-config files.
- **VIII. Provenance For Organizer-Facing Outputs** — PASS. `build_info` envelope is unchanged (SC-105). The deploy SHA continues to surface in the page-title suffix + footer chip (FR-110); the assertion path widens to include the `/ohbm2026/` URLs (SC-106).

**Verdict: GATE PASSES. No Complexity Tracking entries needed.**

## Project Structure

### Documentation (this feature)

```text
specs/009-conference-subpath/
├── plan.md              # This file
├── research.md          # Phase 0 — base-path mechanism, gh-pages root-redirect, BASE_PATH override
├── data-model.md        # Phase 1 — N/A but stub captures "no data-model change"
├── quickstart.md        # Phase 1 — local-dev recipe at the new base path
├── contracts/
│   └── urls.md          # Phase 1 — canonical URL shapes the site must serve
├── checklists/
│   └── requirements.md  # Spec quality gate (from /speckit-specify)
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
site/
├── svelte.config.js                       # base path moves to '/ohbm2026' (override via BASE_PATH at build time)
├── playwright.config.ts                   # baseURL gains `/ohbm2026/` so existing specs' `page.goto('/')` keeps working
├── src/
│   ├── routes/
│   │   ├── +layout.svelte                 # all `<a href>` already use `$app/paths` `base` — audit; cart-email permalink composer needs `base`
│   │   ├── +page.svelte                   # home — `goto()` calls inspected; FacetSidebar / DetailPanel `<a>`s likewise
│   │   ├── about/+page.svelte             # No URL changes; About already uses base-relative anchors
│   │   └── abstract/[id]/+page.svelte     # Permalink route; no source change — only base-path config moves it under /ohbm2026/
│   ├── lib/
│   │   ├── cart_email.ts                  # permalink composer — must include `base` in every poster link
│   │   ├── components/SearchBar.svelte    # no URL touches
│   │   └── …                              # the rest is base-agnostic
│   └── tests/
│       └── e2e/
│           ├── subpath.spec.ts            # NEW — SC-101/SC-103/SC-106 (root redirects, subpath canonical, SHA visible)
│           ├── browse.spec.ts             # update: `goto('/ohbm2026/')` or rely on widened baseURL
│           ├── search.spec.ts             # same
│           ├── facets.spec.ts             # same
│           ├── cart.spec.ts               # same + assert cart-email href includes /ohbm2026/abstract/
│           ├── tour.spec.ts               # same
│           ├── a11y.spec.ts               # audited routes gain /ohbm2026/ prefix
│           ├── sc-sweep.spec.ts           # SC-002/003/004/005/011 — base URL widens
│           ├── accepted-only.spec.ts      # base-agnostic; verifies still passes
│           └── mobile-check.spec.ts       # base URL widens
└── static/
    ├── 404.html                           # SPA-redirect — base-aware (stash full path with base, goto with base)
    └── conference-root-redirect/           # NEW small static dir copied to <cname>/ root at deploy time
        ├── index.html                     # meta-refresh + JS redirect to /ohbm2026/
        └── 404.html                       # same — any unknown path under <cname>/ falls back to /ohbm2026/

.github/workflows/
├── deploy-ui.yml                          # widen BASE_PATH=/ohbm2026; deploy the conference-root-redirect to <gh-pages>/
├── pr-preview.yml                         # widen BASE_PATH=/pr-${PR}/ohbm2026
└── lighthouse.yml                         # widen target_url to include /ohbm2026/

specs/008-ui-rewrite/
└── contracts/references.yaml              # READ-ONLY (no spec edits) — external-URL list unaffected
```

**Structure Decision**: The SvelteKit app stays exactly where it is (`site/`). The change is entirely build-time configuration (`svelte.config.js` `paths.base`) plus a small static "root redirect" island at the gh-pages root. No new top-level directories; nothing new is gitignored.

## Complexity Tracking

No violations. The plan adds one new e2e spec (`subpath.spec.ts`), one tiny static-island directory (`site/static/conference-root-redirect/`), and a base-path config switch — no new modules, no new abstractions.
