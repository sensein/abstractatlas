# Phase 0 Research — Conference subpath rework

This document resolves the four technical unknowns surfaced in the plan's Technical Context. Each finding ends with a **Decision / Rationale / Alternatives** block per the speckit-plan template.

## R1 — How to set the SvelteKit base path

The site is built with `@sveltejs/adapter-static`. SvelteKit exposes the base-path knob as `kit.paths.base` in `svelte.config.js`. Setting it to `/ohbm2026` causes every `<a href>` resolved through `$app/paths`'s `base` import, every `goto()` call, every `<img src>` to a `$lib`-imported asset, and every static-asset reference compiled by Vite to prepend the base automatically. No source-code rewrites beyond the config line are needed for the in-app navigation.

The Stage-6 deploy workflows already plumb a `BASE_PATH` env var through the build so PR previews can sit at `/pr-<N>`:

```js
// svelte.config.js (current)
kit: {
  paths: { base: process.env.BASE_PATH ?? '' }
}
```

Widening this is one line:

```js
// svelte.config.js (after the rework)
kit: {
  paths: { base: process.env.BASE_PATH ?? '/ohbm2026' }
}
```

`deploy-ui.yml` then sets `BASE_PATH=/ohbm2026` (production); `pr-preview.yml` sets `BASE_PATH=/pr-${PR}/ohbm2026` (PR previews); local `pnpm dev` inherits the `/ohbm2026` default. Every existing `$app/paths` use carries the change for free.

- **Decision**: Use `kit.paths.base` with a default of `/ohbm2026` plus a `BASE_PATH` override for PR previews.
- **Rationale**: It's the documented SvelteKit mechanism. No runtime monkey-patching, no Vite plugin, no per-file rewrite. Matches the existing PR-preview override pattern, so the workflow change is incremental.
- **Alternatives considered**:
  - Vite `base` option directly. Rejected — bypasses SvelteKit's router and breaks `$app/paths`.
  - Patching each `<a>` tag manually. Rejected — error-prone, every new component would have to remember.
  - Per-conference build-time templating. Rejected — out of scope ("we don't need to generalize every bit").

## R2 — How to "redirect" `<cname>/` to `<cname>/ohbm2026/` on GitHub Pages

GitHub Pages serves only static files; it cannot issue real `301 Location:` headers. The closest static-site equivalent is an `index.html` at the gh-pages root containing `<meta http-equiv="refresh" content="0; url=/ohbm2026/">` and a `<script>location.replace('/ohbm2026/')</script>`. Both the meta-refresh and the JS replace fire on first paint — perceptually a single hop. Browsers' history stacks treat `location.replace` as not adding a back-button entry, which mirrors the 301 contract.

For misrouted paths (e.g., someone types `<cname>/something-random`), gh-pages serves `<cname>/404.html` by default. We replace that root 404 with the same redirect content so any unknown root-level request lands inside the conference shell instead of leaving the visitor on a generic 404.

The deploy workflow currently uploads the whole `site/build/` output to the gh-pages root. After the rework, the build output sits under `<cname>/ohbm2026/` (because `paths.base = '/ohbm2026'` causes adapter-static to emit `build/ohbm2026/...`). So the gh-pages branch layout becomes:

```text
gh-pages/                      ← branch root (== <cname>/)
├── index.html                 ← root redirect — copied from site/static/conference-root-redirect/
├── 404.html                   ← same redirect content — copied from site/static/conference-root-redirect/
├── CNAME                      ← unchanged
└── ohbm2026/                  ← SvelteKit build output (everything that used to live at root)
    ├── index.html             ← actual home
    ├── about/index.html
    ├── abstract/[id]/index.html
    ├── 404.html               ← SvelteKit's SPA-redirect 404 (Stage-6 mechanism, base-aware)
    ├── _app/                  ← Vite bundle
    └── data/                  ← static data shards (until the runtime fetch supersedes)
```

PR previews mirror this under `<gh-pages>/pr-<N>/`:

```text
gh-pages/pr-17/                ← PR-preview namespace (== <cname>/pr-17/)
├── index.html                 ← redirect to /pr-17/ohbm2026/
├── 404.html                   ← same
└── ohbm2026/                  ← SvelteKit build with BASE_PATH=/pr-17/ohbm2026
    └── …
```

- **Decision**: Ship a tiny static "root-redirect island" in `site/static/conference-root-redirect/` containing `index.html` and `404.html`. The deploy workflow copies it to the gh-pages root (and to `/pr-<N>/` for previews) AFTER the SvelteKit build emits to `<root>/ohbm2026/`. Both files contain `<meta http-equiv="refresh">` + `<script>location.replace('./ohbm2026/' + window.location.search + window.location.hash)</script>`, preserving any query/hash the visitor arrived with.
- **Rationale**: This is the closest static-site equivalent of a 301. It's named honestly as "meta-refresh + JS replace" (not "true 301") in the spec and the deploy workflow comment. Cloudflare-level redirect rules would be a true 301 but require giving the CNAME edge control of brainkb.org — out of scope.
- **Alternatives considered**:
  - Cloudflare Page Rules / Workers. Rejected — needs CDN/DNS-level changes outside this repo.
  - Serve the OHBM 2026 home at both `<cname>/` and `<cname>/ohbm2026/` (Q1 option B). Rejected by the user in /speckit-specify.
  - 404.html → SPA-redirect into `/ohbm2026/` instead of separate root index. Tried mentally; it works but is harder to reason about because the SPA-redirect mechanism is already used at the conference's own `404.html` for deep-link recovery. Keeping them visually separate (root redirect vs. SPA redirect) avoids one-step-think mental overhead.

## R3 — Locations where `/` paths are hardcoded outside SvelteKit's base awareness

`$app/paths`'s `base` import covers everything routed through SvelteKit. But there are a handful of code-paths that compose URLs by hand:

| Location | What it composes | Action |
|---|---|---|
| `site/src/lib/cart_email.ts` | Per-item permalink in the mailto: body: `${origin}/abstract/${posterId}` | Replace with `${origin}${base}/abstract/${posterId}`; `base` imported from `$app/paths`. T071 cart e2e spec already asserts the poster_id is in the decoded `mailto:` body; the spec needs a new assertion that the permalink contains `/ohbm2026/`. |
| `site/src/routes/+layout.svelte` | SPA-redirect handoff — sessionStorage stash + `?spa=` query → `goto(stash)` | The Stage-6 implementation already keeps the FULL path (with base) on `goto()`. Re-validate: any base-relative trimming would silently route outside the SPA. Add a comment naming the invariant explicitly. |
| `site/src/lib/components/Tour.svelte` | `detectKind(pathname)` matches `/about/` and `/abstract/` substrings | Make the matcher base-tolerant: strip `base` off `pathname` before classifying. Otherwise `detectKind('/ohbm2026/about/')` would return 'home' and trigger the wrong tour variant. |
| Build provenance / feedback issue body | `here = $page.url.href` | Already dynamic; no change. |
| `<a href={`${base}/about/`}>` in the header | Already base-aware via `$app/paths` `base` import | Verify; no change expected. |

- **Decision**: Audit the four call-sites above; only `cart_email.ts` and `Tour.svelte` need real edits. The other two are already base-aware.
- **Rationale**: A direct grep for hardcoded `'/abstract'` and `'/about'` strings outside `$app/paths` usage is a cheap, deterministic completeness check during implementation.
- **Alternatives considered**: Wrapping every URL composer in a helper. Rejected — over-engineering for two call-sites; would constrain future code without measurable benefit.

## R4 — Playwright + workflow plumbing under the new base

`playwright.config.ts` currently sets `baseURL: 'http://127.0.0.1:4173'`. After the rework, every spec that calls `page.goto('/')` would land at the meta-refresh root and (under JSDOM-or-Playwright) follow the redirect, costing one extra page-load per test. Easier: widen `baseURL` to `'http://127.0.0.1:4173/ohbm2026'`. The seven existing specs' `goto('/')` calls then resolve to `/ohbm2026/` directly — no per-spec edits needed except for those that hard-coded `/about/`, `/abstract/...`, or other base-relative strings (none, after the audit confirms it).

Workflow plumbing:

- `deploy-ui.yml`:
  - Set `BASE_PATH=/ohbm2026` for the Vite build.
  - After the `pnpm build` step, copy `site/static/conference-root-redirect/{index,404}.html` to the gh-pages publish root (alongside the SvelteKit build dir).
- `pr-preview.yml`:
  - Set `BASE_PATH=/pr-${{ github.event.pull_request.number }}/ohbm2026`.
  - Copy `conference-root-redirect/` to `<gh-pages>/pr-<N>/`.
  - The `environment.url` field widens to `…/pr-<N>/ohbm2026/`.
- `lighthouse.yml`:
  - `steps.target.outputs.url` widens to `…/pr-<N>/ohbm2026/`.
- `pr-preview-cleanup.yml`:
  - Already removes the whole `pr-<N>/` directory on PR close; no change needed.

- **Decision**: Widen `baseURL` in `playwright.config.ts`; widen `BASE_PATH` + the copy step in two workflows; widen `target_url` in `lighthouse.yml`.
- **Rationale**: All four edits are one-liners; the test plumbing change is what unlocks the existing specs to keep working without modification.
- **Alternatives considered**: Force every test to spell out `/ohbm2026/` in its `goto()`. Rejected — couples the test to the conference id and makes future relocations (out of scope here) require a sweep.

## R5 — Things that explicitly do NOT change

For the post-rework reviewer's sanity:

- **Data shards** (`site/static/data/*` and the runtime Dropbox tarball) — `build_info` envelope is byte-identical, no `conference` field added (FR-109 + SC-105). The LinkML schema doesn't change.
- **GraphQL ingest / Stage 1–4 pipeline** — entirely upstream of the URL space.
- **Page title content** — still "OHBM 2026 Atlas (beta) · <short-sha>". Per-conference titling is a future concern.
- **CNAME** — `abstractatlas.brainkb.org`. Unchanged.
- **Data-package URL** — `OHBM2026_UI_DATA_PACKAGE_URL` (Dropbox) and `OHBM2026_UI_DATA_PACKAGE_SHA256`. Unchanged.
- **Tour content** — the steps and their selectors don't change; only `detectKind`'s base-tolerance does.
- **Lighthouse thresholds** — unchanged.
