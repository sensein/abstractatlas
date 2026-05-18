# Feature Specification: Conference subpath rework — OHBM 2026 under `/ohbm2026/`

**Feature Branch**: `009-conference-subpath`
**Created**: 2026-05-18
**Status**: Draft
**Input**: User description: "let's rework the structure so abstract atlas becomes a more generic space for any conference. so the simple change is the location of anything related to ohbm2026 should have a subpath ohbm2026 (so abstract permalinks will be at  <cname>/ohbm2026/abstract/<id>. for now all functionality can stay the same within the path. it would be nice to have permalinks to about at <cname>/ohbm2026/about. till we add another conference we don't need to generalize every bit."

## Overview

Abstract Atlas currently serves OHBM 2026 content at the site root (`abstractatlas.brainkb.org/`, `…/abstract/<id>`, `…/about/`). To leave room for hosting other conferences on the same domain without conflating their URL spaces, every OHBM-2026-specific surface MUST move under a `/ohbm2026/` subpath. The shape becomes:

| Surface | Before | After |
|---|---|---|
| Home (search + browse + UMAP) | `<cname>/` | `<cname>/ohbm2026/` |
| Abstract permalink | `<cname>/abstract/<id>` | `<cname>/ohbm2026/abstract/<id>` |
| About page | `<cname>/about` | `<cname>/ohbm2026/about` |
| PR preview home | `<cname>/pr-<N>/` | `<cname>/pr-<N>/ohbm2026/` |
| PR preview permalink | `<cname>/pr-<N>/abstract/<id>` | `<cname>/pr-<N>/ohbm2026/abstract/<id>` |

The change is **structural only**: every feature behind the new path is exactly what's there today (search, semantic, UMAP, facets, cart, tour, About). No data-model changes, no new conference identifier in the manifest, no second conference. We intentionally do NOT generalize beyond what the path move strictly requires.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - OHBM 2026 visitor reaches the site through the new conference subpath (Priority: P1)

A reviewer or attendee visits `abstractatlas.brainkb.org/ohbm2026/` and sees the same Atlas they used yesterday — search box, model selector, UMAP, facets, cart, tour. Every interaction (typing a query, opening a card, clicking About, adding to the cart) works identically; only the URL shape has changed.

**Why this priority**: This is the change. Without P1 the rework hasn't happened.

**Independent Test**: Deploy the site, navigate to `<cname>/ohbm2026/`, and confirm:
- The home page renders with the search box, result count, UMAP, and facets — same as before the change.
- Typing a query narrows results; clicking a result card opens the detail panel.
- The page title shows the OHBM 2026 branding + the build SHA suffix (FR-022 unchanged).
- The footer build-info still renders the deploy SHA.

**Acceptance Scenarios**:

1. **Given** the site is freshly deployed, **When** a visitor opens `<cname>/ohbm2026/`, **Then** the home page renders with the search box, result count, UMAP, facets, and footer build-info — identical to the pre-rework home.
2. **Given** the visitor is on `<cname>/ohbm2026/`, **When** they click a result card, **Then** the URL becomes `<cname>/ohbm2026/abstract/<poster_id>/` and the detail panel renders.
3. **Given** the visitor is on `<cname>/ohbm2026/`, **When** they click the header "About" link, **Then** the URL becomes `<cname>/ohbm2026/about/` and the About page renders.

---

### User Story 2 - Direct-load of a conference-scoped permalink succeeds (Priority: P1)

A reviewer receives a Slack message with the link `<cname>/ohbm2026/abstract/M-AM-101` and clicks it in a fresh browser tab. The detail panel for poster M-AM-101 renders without an intermediate redirect chain and without losing the deep-link target through the SPA shell's reload handoff.

**Why this priority**: Permalinks are the second-most-common entry path after the home page; if they break, every shared link in the wild breaks.

**Independent Test**: Open an incognito window. Paste the conference-scoped abstract permalink. Confirm the detail panel renders for the expected poster within 3 s; refreshing the page keeps the same URL and panel state.

**Acceptance Scenarios**:

1. **Given** a fresh browser tab, **When** the visitor opens `<cname>/ohbm2026/abstract/<poster_id>/`, **Then** the detail panel for that poster renders within 3 s.
2. **Given** the detail panel is showing a deep-loaded poster, **When** the visitor refreshes, **Then** the URL and the rendered panel stay the same (no fall-through to the home page).
3. **Given** the visitor opens `<cname>/ohbm2026/abstract/NOT-A-REAL-ID/`, **When** the detail panel attempts to look it up, **Then** an "abstract not found" affordance renders inside the conference shell (NOT a generic GitHub Pages 404).

---

### User Story 3 - Visiting the root domain leads the visitor to OHBM 2026 (Priority: P2)

A first-time visitor types or pastes `abstractatlas.brainkb.org` into the address bar. Because no second conference is hosted yet, they land on the OHBM 2026 site rather than seeing a placeholder, an error, or a generic landing page.

**Why this priority**: Without this, the root URL becomes a dead end for every existing shared link, bookmark, or "abstractatlas.brainkb.org" mention. Critical for continuity, but its UX is decoupled from the subpath move itself.

**Independent Test**: Open an incognito window, visit `<cname>/` (no path), and confirm the visitor reaches the OHBM 2026 home page (`<cname>/ohbm2026/`) — whether by redirect, by being served at both URLs, or by a one-line landing-page link.

**Acceptance Scenarios**:

1. **Given** a fresh browser tab, **When** the visitor opens `<cname>/`, **Then** they reach the OHBM 2026 home within ≤ 1 redirect hop and the address bar shows the canonical `<cname>/ohbm2026/` URL.

---

## Functional Requirements *(mandatory)*

- **FR-101 (Conference subpath as canonical location)**: Every OHBM 2026 surface — home, abstract permalink, About — MUST be served at a URL beginning with `<cname>/ohbm2026/`. The page title, footer build-info, search bar, UMAP, facets, cart, and tour MUST remain functionally identical to their pre-rework behaviour.

- **FR-102 (Abstract permalink shape)**: An abstract's permalink MUST be `<cname>/ohbm2026/abstract/<poster_id>/`. The `<poster_id>` is the program-assigned id (e.g., `M-AM-101`), unchanged from FR-002.

- **FR-103 (About permalink shape)**: The About page MUST be served at `<cname>/ohbm2026/about/`. Internal links to About from the header / tour / build-info footer MUST point at this URL.

- **FR-104 (PR preview shape mirrors production)**: Per-PR preview deploys MUST host the conference site under `<cname>/pr-<N>/ohbm2026/`, with abstract permalinks at `<cname>/pr-<N>/ohbm2026/abstract/<poster_id>/` and About at `<cname>/pr-<N>/ohbm2026/about/`. The Deployments-box surface (FR-021) MUST link to the new shape so reviewers smoke-test the same URL layout the production deploy will use.

- **FR-105 (Root URL behaviour)**: The root path `<cname>/` MUST cause the visitor's browser to land on `<cname>/ohbm2026/` within ≤ 1 perceptual hop. Because gh-pages cannot serve a true HTTP 301, this is implemented as a static redirect island (`<meta http-equiv="refresh">` + JS `location.replace`); the perceptual contract is "the address bar settles on the canonical `<cname>/ohbm2026/` URL on first paint, with no intermediate placeholder page". The same rule applies under PR previews — `<cname>/pr-<N>/` MUST bounce to `<cname>/pr-<N>/ohbm2026/` under the same mechanism.

- **FR-106 (Legacy URLs not preserved)**: Pre-rework URLs at `<cname>/abstract/<poster_id>` and `<cname>/about` are EXPLICITLY NOT preserved. They MAY 404, and we accept the breakage — the pool of links shared in the wild during the brief pre-rework window is bounded, and the cost of a one-time "click and re-find" is acceptable. A future cleanup MAY add a redirect map if demand surfaces; this spec does not require one.

- **FR-107 (Deep-link SPA-redirect under the subpath)**: A direct-load of `<cname>/ohbm2026/abstract/<poster_id>/` (incognito, no prior session) MUST render the detail panel for that poster — not the home page. The same applies under PR previews (`<cname>/pr-<N>/ohbm2026/abstract/<poster_id>/`). This preserves the contract today's `/404.html` SPA-redirect satisfies for the legacy URL space.

- **FR-108 (Asset paths follow the subpath)**: Every static asset the page loads (CSS, JS bundles, ONNX models, the data-package tarball, favicons, OG images) MUST be reachable from under the conference subpath without leaving the conference shell. References to absolute root paths in HTML, CSS, or JS MUST be relative to the conference base.

- **FR-109 (No data-model conference identifier)**: This rework MUST NOT introduce a `conference` or `conference_id` field in the JSON shards' `build_info` envelope, the manifest, or the search/relations shards. Per the user's "we don't need to generalize every bit" guidance, generalization beyond URL paths is explicitly deferred until a second conference exists.

- **FR-110 (Build-info SHA visibility at the new path)**: The page-title suffix AND the footer build-info chip MUST continue to render the deploy's short SHA on every route under `/ohbm2026/` (home, About, abstract permalink). SC-011 continues to apply; the assertion path widens to include the new URLs.

## Assumptions

- The conference identifier `ohbm2026` is treated as a magic string at the URL/build-config layer, not as a data-model concept. A future second conference would need a small generalization pass at that time (out of scope here).
- The CNAME on gh-pages (`abstractatlas.brainkb.org`) is unchanged.
- The data-package URL (the Dropbox tarball pinned by `vars.OHBM2026_UI_DATA_PACKAGE_URL`) is unchanged — it's an external resource, not in the on-domain URL space.
- The Lighthouse-CI workflow's `target_url` lookup widens to include `/pr-<N>/ohbm2026/` so the audit still runs the right surface (mechanical change; no spec impact).

## Out of Scope

- Introducing a multi-conference landing page at `<cname>/`.
- Adding a `conference` field to any data-shard envelope.
- Generalizing the SvelteKit site to be conference-agnostic at the code level (it stays OHBM-specific behind the path).
- Migrating any cite-able permalinks in print/email materials (those are content tasks owned by the conference organizers).
- Per-conference theming, branding, or content overrides.

## Success Criteria *(mandatory)*

- **SC-101 (Subpath canonical)**: 100% of OHBM 2026 surfaces (home, About, abstract permalink) are reachable at a URL beginning with `<cname>/ohbm2026/` and render the same content as the corresponding pre-rework URL.

- **SC-102 (Direct-load works under the subpath)**: A fresh incognito direct-load of `<cname>/ohbm2026/abstract/<poster_id>/` renders the detail panel within 3 s on a desktop network (SC-001 budget unchanged).

- **SC-103 (Root URL reaches OHBM 2026)**: A visitor opening `<cname>/` reaches the OHBM 2026 home within ≤ 1 perceptual hop (a static meta-refresh + JS `location.replace`; not a true HTTP 301 because gh-pages cannot serve one), and the address bar settles on `<cname>/ohbm2026/` before the first contentful paint of the home page.

- **SC-104 (PR-preview parity)**: The PR preview for a Stage-9 PR exposes the conference site at `<cname>/pr-<N>/ohbm2026/`, with abstract permalinks at `<cname>/pr-<N>/ohbm2026/abstract/<poster_id>/`, and the Deployments-box link points to that URL.

- **SC-105 (No data-shard drift)**: The data package's `build_info` envelope is byte-identical before and after the rework — no `conference` field, no schema bump. (LinkML validator: 68/68 shards still pass.)

- **SC-106 (Build SHA visible under the subpath)**: SC-011 holds: the page-title suffix and footer build-info chip render the deploy's short SHA on every route under `/ohbm2026/` (home, About, abstract permalink), checked by a Playwright assertion.

## Key Entities

This feature does not introduce new data-model entities. The only entity is implicit:

- **Conference subpath**: the magic string `ohbm2026` that nests every OHBM-2026 URL under a common namespace. Lives in the build configuration, not in any data shard.

## Dependencies

- Stage 6 (PRs #9–#18) is the prerequisite — this rework is a re-shape of what landed there.
- The deploy + PR-preview workflows (`.github/workflows/deploy-ui.yml`, `pr-preview.yml`, `pr-preview-cleanup.yml`, `lighthouse.yml`) need their `BASE_PATH` / target URLs widened to include the subpath (mechanical, no spec impact).
