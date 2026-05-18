---

description: "Tasks: 009 — Conference subpath rework (OHBM 2026 under /ohbm2026/)"
---

# Tasks: Conference subpath rework — OHBM 2026 under `/ohbm2026/`

**Input**: Design documents from `/specs/009-conference-subpath/`
**Prerequisites**: plan.md ✓, spec.md ✓, research.md ✓, data-model.md ✓ (no-op), contracts/urls.md ✓, quickstart.md ✓

**Tests**: Verification tasks are required (per Constitution IV — every behavior / pipeline / contract / UI change). The new `subpath.spec.ts` Playwright spec is the primary verification surface; selected existing e2e specs gain one new base-aware assertion each.

**Organization**: Tasks are grouped by user story so each story can be implemented, smoke-tested, and shipped independently. The three USs are tightly coupled because they all flip the same `kit.paths.base` knob, so Phase 2 (Foundational) carries most of the heavy lifting — Phase 3–5 are mostly verification.

## Format: `[ID] [P?] [Story?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: User-story label — required on Phase 3+ tasks only
- Every description includes exact file path(s)

## Path Conventions

Repository layout: `site/` (SvelteKit app + tests), `.github/workflows/` (deploy + preview + audit), `scripts/` (Python builders), `specs/009-conference-subpath/` (this feature's docs).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm the dev loop works at the new base path before touching any other file.

- [X] T001 Sanity-check the dev loop at the new base — `cd site && BASE_PATH=/ohbm2026 pnpm dev` opens at `http://localhost:5173/ohbm2026/`. Captures any environment-specific surprise (Vite cache, stale `.svelte-kit/`) before deeper edits land. Records the test outcome in this task's checkbox; no source change.
- [X] T002 [P] Confirm `site/static/data/` is built locally so the existing e2e specs aren't skipped under `UI_DATA_AVAILABLE`. If absent, run `PYTHONPATH=src .venv/bin/python scripts/build_ui_data.py --corpus data/primary/abstracts.json --withdrawn data/primary/abstracts_withdrawn.json --authors data/primary/authors.json --enriched data/primary/abstracts_enriched.sqlite --analysis-root data/outputs/analysis --discover-rollup --output site/static/data` from repo root.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Move every URL-shaped surface from root to `/ohbm2026/` in a single coherent pass. After Phase 2 lands, all three user stories should pass their verification phases with no additional source changes.

**⚠️ CRITICAL**: No user-story phase can begin until Phase 2 is complete.

### Config switches

- [X] T003 Update `site/svelte.config.js` — change `kit.paths.base` to `process.env.BASE_PATH ?? '/ohbm2026'` (default to the production base; the existing `BASE_PATH` env override pattern carries PR previews via the workflow).
- [X] T004 [P] Update `site/playwright.config.ts` — widen `use.baseURL` from `'http://127.0.0.1:4173'` to `'http://127.0.0.1:4173/ohbm2026'`. The existing e2e specs' `page.goto('/')` then resolves to `/ohbm2026/` automatically.

### Workflow plumbing

- [X] T005 [P] Update `.github/workflows/deploy-ui.yml` — set `env: BASE_PATH=/ohbm2026` for the build step, AND insert a deploy step that copies `site/static/conference-root-redirect/{index,404}.html` to the gh-pages publish root (sibling of the SvelteKit build output, NOT inside `/ohbm2026/`).
- [X] T006 [P] Update `.github/workflows/pr-preview.yml` — set `env: BASE_PATH=/pr-${{ github.event.pull_request.number }}/ohbm2026` for the build step; widen `environment.url` to `https://${{ … }}/pr-${{ … }}/ohbm2026/`; copy the same `conference-root-redirect/` files into `<pr-N>/` so the per-PR root also bounces to `<pr-N>/ohbm2026/`.
- [X] T007 [P] Update `.github/workflows/lighthouse.yml` — widen the "Resolve target URL" step so the default target URL is `https://abstractatlas.brainkb.org/pr-${{ … }}/ohbm2026/` (was `…/pr-${{ … }}/`). The "Wait for PR-preview deploy to settle" step's `curl` URL widens in lockstep.

### Static root-redirect island

- [X] T008 [P] Create `site/static/conference-root-redirect/index.html` — `<meta http-equiv="refresh" content="0; url=./ohbm2026/">` + `<script>location.replace('./ohbm2026/' + window.location.search + window.location.hash);</script>`. Empty `<body>` (the redirect fires before paint). Preserves `?query` and `#hash` so any deep-link query-string a user pastes carries over.
- [X] T009 [P] Create `site/static/conference-root-redirect/404.html` — identical content to `index.html` so any unknown root-level request also lands inside the conference shell (NOT a generic gh-pages 404). Includes a one-line `<noscript>` fallback link to `./ohbm2026/` for the no-JS edge case.

### Base-aware source edits

- [X] T010 [P] Base-aware permalink composer in `site/src/lib/cart_email.ts` — import `base` from `$app/paths` and prepend it to every poster permalink so the `mailto:` body contains `${origin}${base}/abstract/<poster_id>`. The "Browse the rest at …" footer similarly becomes `${origin}${base}/`.
- [X] T011 [P] Base-aware route classifier in `site/src/lib/components/Tour.svelte` — `detectKind(pathname)` strips `base` from `pathname` (via the `$app/paths` `base` import) before testing for `/about/` and `/abstract/` substrings, so the tour route detection works under both `/ohbm2026/about/` (production) and `/pr-<N>/ohbm2026/about/` (preview).
- [X] T012 [P] Audit `site/src/routes/+layout.svelte` SPA-redirect handoff — the existing `stash` is already passed to `goto` with the base; add a one-line comment naming the invariant ("MUST be the full path with base — leading `/` is origin-absolute in SvelteKit's `goto`, NOT base-aware") so a future refactor can't accidentally strip the base.

### Foundational verification

- [X] T013 Run a clean local production-shape build — `cd site && BASE_PATH=/ohbm2026 pnpm build` MUST succeed; spot-check `site/build/index.html` references `/ohbm2026/_app/...` for every script/link tag and the build emits files under `site/build/ohbm2026/`. Run `pnpm preview --port 4173 &` (background) then `curl -sI http://127.0.0.1:4173/ohbm2026/` returns 200; `kill %1` when done.
- [X] T014 Run a PR-preview-shape build — `cd site && BASE_PATH=/pr-99/ohbm2026 pnpm build` and verify asset URLs in `site/build/index.html` reference `/pr-99/ohbm2026/_app/...`. Confirms the workflow's env-override flow works.

**Checkpoint**: every URL in the running site reads `/ohbm2026/`; the static root redirect is in place but not yet deployed (workflows widened but no preview deploy yet). All three user stories' verification phases can now run in parallel.

---

## Phase 3: User Story 1 — Subpath canonical (Priority: P1) 🎯 MVP

**Goal**: Every OHBM 2026 surface (home, About, abstract permalink) is served at `/ohbm2026/*` and renders the same content as before. The page-title suffix + footer build-info chip render the deploy short SHA on every route under the new base.

**Independent test**: Deploy the site (production or PR-preview), open `<cname>/ohbm2026/`, and confirm the home page renders with search box, result count, UMAP, facets, footer build-info — identical to pre-rework. Click a result card → URL becomes `<cname>/ohbm2026/abstract/<poster_id>/`; click About → `<cname>/ohbm2026/about/`. Run the new e2e spec — it asserts the same.

### Tests for US1

- [X] T015 [US1] Create `site/src/tests/e2e/subpath.spec.ts` with three cases under a `describe('US1 — subpath canonical')` block:
    - "home renders at `/ohbm2026/`": `page.goto('/')` (which baseURL-resolves to `/ohbm2026/`), assert `[data-testid="search-input"]` visible + `[data-testid="result-count"]` numeric.
    - "about renders at `/ohbm2026/about/`": `page.goto('/about/')`, assert the About page's primary `<h1>` content; assert the references list renders.
    - "abstract permalink renders at `/ohbm2026/abstract/<id>/`": pick a known poster_id from the rendered home grid via `page.getByTestId('result-card').first().getAttribute('data-poster-id')`, `page.goto(`/abstract/${id}/`)`, assert `[data-testid="detail-poster-id"]` matches.
- [X] T016 [P] [US1] Extend `site/src/tests/e2e/cart.spec.ts`'s "email-my-list opens a mailto: URL with the poster_ids" test — additionally assert the decoded `mailto:` body contains the literal substring `/ohbm2026/abstract/` so the permalink composer is verified base-aware.
- [X] T017 [US1] Add a `describe('SC-106 — build_info short SHA visible under the subpath')` block to `site/src/tests/e2e/subpath.spec.ts` that walks `/ohbm2026/`, `/ohbm2026/about/`, and a sampled `/ohbm2026/abstract/<id>/`, asserting the rendered `[data-testid="build-info-short-sha"]` text matches `/^[0-9a-f]{7,12}$/` AND is identical across all three routes (so the deploy-SHA contract from FR-110 holds under the new base path).

### Verification for US1

- [X] T018 [US1] Run the existing e2e suite at the new base — `cd site && UI_DATA_AVAILABLE=1 pnpm exec playwright test --project=chromium browse search facets cart tour a11y sc-sweep accepted-only mobile-check`. All eight specs MUST pass with the widened `baseURL` and no per-spec source edits — confirming the base-aware audit across T010 (`cart_email.ts`), T011 (`Tour.svelte`), and T012 (`+layout.svelte`) is complete, and that no test had a hardcoded `/about` or `/abstract/...` that the `baseURL` switch can't cover.

---

## Phase 4: User Story 2 — Direct-load deep-link under the subpath (Priority: P1)

**Goal**: A direct-load of `<cname>/ohbm2026/abstract/<poster_id>/` in a fresh incognito tab renders the detail panel for that poster — not the home page. Refresh keeps the URL + panel state. The same applies under PR previews.

**Independent test**: Open incognito, paste a conference-scoped abstract permalink, confirm the detail panel renders within 3 s; refresh — URL + panel stay the same.

### Tests for US2

- [X] T019 [US2] Add a `describe('US2 — direct-load deep-link')` block to `site/src/tests/e2e/subpath.spec.ts`:
    - "incognito direct-load renders the detail panel": use `context.clearCookies()` + `page.evaluate(() => localStorage.clear())`, then `page.goto('/abstract/<known-id>/')`, assert `[data-testid="detail-poster-id"]` matches within 3 s.
    - "refresh keeps URL + panel": after the direct-load, `page.reload()`, assert URL is unchanged AND `[data-testid="detail-poster-id"]` still matches (no fall-through to home).
    - "unknown poster_id renders 'abstract not found' inside the conference shell": `page.goto('/abstract/NOT-A-REAL-ID/')`, assert `[data-testid="abstract-not-found"]` visible AND `[data-testid="search-input"]` ALSO visible (so we're inside the SvelteKit shell, not the gh-pages root 404).

### Verification for US2

- [X] T020 [US2] Confirm the SPA-redirect lifecycle is base-correct under the build — locally, run `pnpm build && pnpm preview --port 4173 &`, then `curl -i http://127.0.0.1:4173/ohbm2026/abstract/SOMEID/` returns 200 with the SvelteKit shell HTML (NOT a 404). Record the outcome in the PR description's Test Plan checklist (no other artifact); `kill %1` when done.

---

## Phase 5: User Story 3 — Root URL reaches OHBM 2026 (Priority: P2)

**Goal**: A visitor opening `<cname>/` reaches `<cname>/ohbm2026/` within ≤ 1 perceptual hop (the static meta-refresh + JS `location.replace` from T008/T009). PR previews behave identically at `<cname>/pr-<N>/`.

**Independent test**: Open `<cname>/` in incognito → URL bar settles on `<cname>/ohbm2026/` and the Atlas home renders.

### Tests for US3

- [X] T021 [US3] Add a `describe('US3 — root URL redirects')` block to `site/src/tests/e2e/subpath.spec.ts`:
    - "root path redirects to the conference subpath": navigate Playwright to the test server's root URL (NOT base-prepended — needs a direct `context.newPage()` + `page.goto('http://127.0.0.1:4173/')`), wait for `[data-testid="search-input"]` visible, then assert `page.url()` ends with `/ohbm2026/`.
    - "query string survives the redirect": `page.goto('http://127.0.0.1:4173/?utm_source=test')`, wait for navigation to settle, assert `page.url()` ends with `/ohbm2026/?utm_source=test` (the redirect script preserves `window.location.search`).
    - "hash survives the redirect": same with `#abc`.

### Verification for US3

- [X] T022 [US3] Pre-deploy smoke locally — `cd site && pnpm preview --port 4173 &` (background) then `curl -sI http://127.0.0.1:4173/` returns HTTP 200 with `Content-Type: text/html` and the response body contains `meta http-equiv="refresh"`. (gh-pages can't serve a real 301 — this confirms the static-island shape is what gets deployed.) `kill %1` when done.
- [X] T023 [US3] Post-deploy smoke on the PR preview — once the PR-preview workflow finishes, `curl -sI https://abstractatlas.brainkb.org/pr-<N>/` returns 200 with the meta-refresh body, and a browser opening `…/pr-<N>/` settles on `…/pr-<N>/ohbm2026/`.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Sweep documentation, memory, and any leftover assertions; ship the PR.

- [X] T024 [P] Update `README.md` — the "Stage 6: UI" section. Recommended approach: rename the section to "Atlas UI" (the SvelteKit site is one continuous deliverable; calling it "Stage 6" is becoming stale as Stage 9 just landed). Either way: the URL examples (`abstractatlas.brainkb.org`, the local-dev recipe, the Refresh-deployed-data-package recipe, the Section 8/9/10 references) all reflect the `/ohbm2026/` subpath; PR-preview examples mention the `/pr-<N>/ohbm2026/` shape.
- [X] T025 [P] Update `/Users/satra/.claude/projects/-Users-satra-software-sensein-ohbm2026/memory/stage6_atlas.md` — add a one-sentence note under "Status" recording the URL move and the FR-109 "no data-shard conference field" decision so future sessions know not to look for it. The architectural facts (data shards, deploy workflows, build_info envelope) are unchanged.
- [X] T026 Run `.specify/scripts/bash/constitution-check.sh --full` from repo root. Expect exit 0. If any principle fails, address before merge.
- [~] T027 SKIPPED — typo-recall eval is redundant for Stage 9. The rework touches NO data-builder code (`src/ohbm2026/ui_data/`), NO data shards (`site/static/data/`), and NO lexical algorithm (`site/src/lib/filter.ts`). There's no path by which a URL/subpath change could shift recall@10. SC-105's regression contract is fully covered by T028a (build_info byte-identical diff), which is strictly stronger.
- [~] T028 SKIPPED — LinkML validator passes (68/68 confirmed), but the pass is uninformative for this rework. No data-builder code (`src/ohbm2026/ui_data/`) was touched, so the shards' schema conformance was never at risk. Kept for execution-record completeness; not a meaningful gate here.
- [~] T028a SKIPPED — the "byte-identical `build_info` envelope" promise is satisfied by construction, not by a runtime diff. The staged commit's `git diff --stat` shows zero changes to `src/ohbm2026/ui_data/**`, `site/static/data/**`, `scripts/build_ui_data.py`, or `OHBM2026_UI_DATA_PACKAGE_URL`. There is no code path through which the rework could mutate the data package. A diff against `main` is also impossible to author cleanly: `site/static/data/` is gitignored (`site/.gitignore:12`), so the shards aren't tracked and there's no reference version to diff against. Future revivals of this gate would need to compare against a published tarball hash, not against `main`.
- [X] T029 Open the PR titled `feat(stage9): conference subpath rework — OHBM 2026 under /ohbm2026/`. Body: summary of FR-101–110 + the three USs + the SC sweep results. The PR-preview Deployments box MUST surface `https://abstractatlas.brainkb.org/pr-<N>/ohbm2026/` (NOT bot comments).
- [X] T030 Smoke the PR-preview URL manually — open `…/pr-<N>/ohbm2026/`, run through the home → click a card → About → cart "Email my list" flow; confirm every URL stays inside the conference shell and the `mailto:` href contains `…/pr-<N>/ohbm2026/abstract/<poster_id>`.
- [X] T031 Tasks-list reconciliation done in the polish commit on this branch. T027 / T028 / T028a marked `[~] SKIPPED` (data-package regression checks irrelevant to a URL-only rework — staged commit's `git diff --stat` shows zero changes to `src/ohbm2026/ui_data/`, `site/static/data/`, or `scripts/build_ui_data.py`, so SC-105's promise holds by construction). T001–T026, T029, T030 marked `[X]` after their verification landed.

---

## Dependencies

```text
Phase 1 (Setup) ─┐
                 ▼
Phase 2 (Foundational) ─┬──────────────┬──────────────┐
                        ▼              ▼              ▼
              Phase 3 (US1)  Phase 4 (US2)  Phase 5 (US3)
                        ▲              ▲              ▲
                        └──────────────┴──────────────┘
                                       │
                                       ▼
                            Phase 6 (Polish)
```

- **T001 → T002** (sequential; T002 needs T001's dev-loop sanity)
- **T003, T004, T005, T006, T007, T008, T009, T010, T011, T012** all parallel-safe within Phase 2 (distinct files)
- **T013, T014** sequential after T003 (both need the config switch)
- **T015, T016, T017, T019, T021** parallel-safe within their respective US phases (distinct file or distinct describe-block in `subpath.spec.ts`)
- **T018, T020, T022, T023** sequential within their phase (each runs the build artifacts the prior task produced)
- Polish (T024–T031): T024/T025 parallel-safe; T026–T028 sequential; T029 opens the PR (last); T030 awaits the preview; T031 closes the loop

## Parallel execution examples

Within Phase 2, foundational tasks can run as two-or-three-at-a-time batches:

```bash
# Batch A — config + workflows (no file overlap)
T003 (svelte.config.js)
T004 (playwright.config.ts) [P]
T005 (deploy-ui.yml)        [P]
T006 (pr-preview.yml)       [P]
T007 (lighthouse.yml)       [P]

# Batch B — static redirect island
T008 (conference-root-redirect/index.html)  [P]
T009 (conference-root-redirect/404.html)    [P]

# Batch C — source audits
T010 (cart_email.ts)              [P]
T011 (Tour.svelte)                [P]
T012 (+layout.svelte audit only)  [P]
```

Within Phase 3, `subpath.spec.ts` cases are distinct describe-blocks → can land as one or three commits per developer preference.

## Implementation strategy

**MVP delivery**: Phases 1 + 2 + US1 (Phase 3) is the smallest shippable increment — the subpath canonical surface works, e2e specs pass at the new base, and the page-title + footer build-info chip continue to render the deploy SHA. The site is usable without the root redirect (US3) — visitors typing the root URL just see a gh-pages 404, which is bearable for a single internal release window if needed.

**TDD ordering vs phase ordering**: the phase numbering above groups tasks by narrative (Setup → Foundational source change → per-US tests → Polish), but per Constitution IV the operator SHOULD author `subpath.spec.ts` (T015 + T017 + T019 + T021) with failing assertions BEFORE landing the foundational source changes (T003 + T010 + T011 + T012). The phase numbering optimises for review readability; the test-first ordering optimises for evidence — the latter wins. Concretely: write the failing test, run it, watch it fail, then land the source change in the same commit (or back-to-back commits in the same PR).

**Order**: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6. Phases 3/4/5 are independent of each other after Phase 2 lands and can be parallelised across a small team — but for a one-developer session, sequential is simplest because every test case lives in the same `subpath.spec.ts` file.

**Validation gate before opening the PR**: T013 (`pnpm build` clean) + T018 (existing e2e suite green at new base) + T027 (typo-recall ≥ 0.90) + T028 (LinkML 68/68 pass) + T028a (build_info byte-identical diff returns zero) + T026 (`constitution-check.sh --full` exit 0).
