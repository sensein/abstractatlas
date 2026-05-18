# Quickstart — Conference subpath rework (local dev)

This recipe verifies the rework in a local Vite preview without touching gh-pages. Five minutes from clean checkout to a green Playwright run.

## Prerequisites

You already have the Stage-6 dev loop working — `pnpm install` has run in `site/`, the data package is at `site/static/data/`, and `pnpm dev` worked before the rework. If not, follow `specs/008-ui-rewrite/quickstart.md` first.

## 1. Dev server at the new base

```bash
cd site
pnpm dev    # http://localhost:5173/ohbm2026/
```

The home page renders at the subpath. Visiting `http://localhost:5173/` should serve the local meta-refresh `index.html` and bounce you to `/ohbm2026/`. The address bar settles on the subpath after the bounce.

Smoke checks at `localhost:5173/ohbm2026/`:

- Type a query → result count updates.
- Click a result card → URL becomes `localhost:5173/ohbm2026/abstract/<poster_id>/`; refresh keeps the panel.
- Click "About" in the header → URL becomes `localhost:5173/ohbm2026/about/`.

## 2. Production build smoke

```bash
cd site
BASE_PATH=/ohbm2026 pnpm build
pnpm preview --port 4173 --host 127.0.0.1
```

Then:

```bash
curl -sI http://127.0.0.1:4173/                | head -5
curl -sI http://127.0.0.1:4173/ohbm2026/       | head -5
curl -sI http://127.0.0.1:4173/ohbm2026/about/ | head -5
```

Expected: `/` returns a 200 with a `<meta http-equiv="refresh">` body; `/ohbm2026/` and `/ohbm2026/about/` both 200 with real content.

## 3. PR-preview-shape build (BASE_PATH override)

```bash
cd site
BASE_PATH=/pr-17/ohbm2026 pnpm build
```

Verify `site/build/index.html` references `/pr-17/ohbm2026/` for its asset URLs. The deploy workflow produces the same shape for actual PR previews; this is just a local sanity check.

## 4. Run the new e2e spec

```bash
cd site
pnpm exec playwright test subpath
```

Five assertions cover SC-101 / SC-103 / SC-106:

1. `/` → URL bar settles on `/ohbm2026/`, ≤ 1 hop.
2. `/ohbm2026/` → home renders.
3. `/ohbm2026/about/` → About renders.
4. `/ohbm2026/abstract/<known-id>/` → detail panel renders that poster.
5. Footer build-info short SHA appears on home, About, and the abstract permalink.

## 5. Re-run the existing user-story specs

```bash
cd site
UI_DATA_AVAILABLE=1 pnpm exec playwright test
```

All eight existing specs (browse, search, facets, cart, tour, a11y, sc-sweep, accepted-only, mobile-check) should still pass with no source changes — `playwright.config.ts`'s widened `baseURL` makes `page.goto('/')` resolve to `/ohbm2026/` automatically. The cart spec gains one new assertion (decoded `mailto:` body contains `/ohbm2026/abstract/`).

## 6. Lighthouse sanity (optional)

Push to a PR branch and watch the `lighthouse-ci` job target `https://abstractatlas.brainkb.org/pr-<N>/ohbm2026/`. Expect the same warn-only assertions to hold as the Stage-6 baseline. No new thresholds are introduced.

## 7. Data-package regression

The data package shouldn't change, but verify:

```bash
.venv/bin/python scripts/eval_typo_recall.py --shards site/static/data
```

Expected: `recall_at_10 ≥ 0.96` (same neighbourhood as the Stage-6 baseline of 0.9685–0.9894). If recall drops, the rework accidentally touched the shards — investigate.

## What success looks like

- `https://abstractatlas.brainkb.org/` bounces to `/ohbm2026/` (visible in DevTools' Network tab as a meta-refresh).
- Every page-title and footer chip shows the deploy's short SHA.
- The data package's `build_info` envelope diffs to zero bytes pre- vs post-rework.
- Open the cart, add an abstract, click "Email my list" — the `mailto:` body contains `https://abstractatlas.brainkb.org/ohbm2026/abstract/<poster_id>`.
- A draft PR's Deployments box surfaces `…/pr-<N>/ohbm2026/` and that URL renders the Atlas at that PR's head SHA.
