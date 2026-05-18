# URL Contract — Conference subpath rework

The only interface this feature exposes is the URL space. The contract below is what the deployed site MUST serve after the rework lands; each row corresponds to one FR / SC and one e2e assertion in `site/src/tests/e2e/subpath.spec.ts`.

## Production URLs

| URL | Status | What renders | FR / SC | e2e assertion |
|---|---|---|---|---|
| `https://abstractatlas.brainkb.org/` | 200 (HTML w/ meta-refresh + JS replace) | Empty body; redirects to `/ohbm2026/` | FR-105 / SC-103 | Open root → URL bar settles on `/ohbm2026/`; ≤ 1 hop |
| `https://abstractatlas.brainkb.org/ohbm2026/` | 200 OK | Atlas home (search + UMAP + facets + cart) | FR-101 / SC-101 | `data-testid="search-input"` visible; `data-testid="result-count"` is numeric |
| `https://abstractatlas.brainkb.org/ohbm2026/about/` | 200 OK | About page | FR-103 / SC-101 | `<h1>` text contains "About"; references list renders |
| `https://abstractatlas.brainkb.org/ohbm2026/abstract/<poster_id>/` | 200 OK | Detail panel for the named poster | FR-102 / FR-107 / SC-102 | Direct-load in incognito → `data-testid="detail-poster-id"` matches |
| `https://abstractatlas.brainkb.org/abstract/<anything>` | 200 (meta-refresh body served as `/404.html`) → bounces to `/ohbm2026/` | The `/abstract/<id>` path component is LOST in the bounce — the visitor lands on the home page, not on the equivalent poster. Acceptable per FR-106's "we accept the breakage". | FR-106 | No assertion needed (out-of-scope, see Q2) |
| `https://abstractatlas.brainkb.org/about` | 200 (same `/404.html`) → bounces to `/ohbm2026/` | Same — lands on home, not About. Acceptable per FR-106. | FR-106 | None |

## PR preview URLs

| URL | Status | What renders | FR / SC |
|---|---|---|---|
| `https://abstractatlas.brainkb.org/pr-<N>/` | 200 (meta-refresh + JS replace) | Empty body; redirects to `/pr-<N>/ohbm2026/` | FR-105 |
| `https://abstractatlas.brainkb.org/pr-<N>/ohbm2026/` | 200 OK | Atlas home, built with `BASE_PATH=/pr-<N>/ohbm2026` | FR-104 / SC-104 |
| `https://abstractatlas.brainkb.org/pr-<N>/ohbm2026/about/` | 200 OK | About page | FR-104 |
| `https://abstractatlas.brainkb.org/pr-<N>/ohbm2026/abstract/<poster_id>/` | 200 OK | Detail panel | FR-104 |
| `https://abstractatlas.brainkb.org/pr-<N>/abstract/<id>` | 404 | Accepted breakage | (none — PR previews never had cite-able legacy links) |

## Build-info SHA visibility

On every 200 OK URL above, both surfaces MUST render the deploy's short SHA:

1. The `<title>` element contains the short SHA suffix (e.g., `OHBM 2026 Atlas (beta) · 1a2b3c4`).
2. The footer `data-testid="build-info-short-sha"` renders the matching short SHA.

This is FR-110 / SC-106 — a base-URL widening of the existing SC-011.

## Composed permalinks (out-of-band)

| Producer | Pre-rework shape | Post-rework shape |
|---|---|---|
| Cart "email my list" `mailto:` body | `<origin>/abstract/<poster_id>` | `<origin>/ohbm2026/abstract/<poster_id>` |
| Cart "email my list" footer | `Browse the rest at <origin>` | `Browse the rest at <origin>/ohbm2026/` |
| Footer feedback issue `body` field | `page` line uses `$page.url.href` | unchanged — `$page.url.href` carries the base automatically |

T071's cart e2e spec gains one new assertion (the decoded `mailto:` `body` parameter contains `/ohbm2026/abstract/`). T062 search spec is unaffected.

## Status of the URL contract

| Status | Why |
|---|---|
| 200 OK | The conference subpath, every page under it, every base-aware permalink, and the redirect HTML at the root |
| 200 (meta-refresh) → bounce | Every unknown root-level path (including legacy `<cname>/abstract/<id>` and `<cname>/about`) hits the static redirect `/404.html` and bounces to `<cname>/ohbm2026/`. The original path component is lost; this is acceptable per FR-106. |
| ≤ 1 redirect hop | `<cname>/` and `<cname>/pr-<N>/` (meta-refresh + JS `location.replace`; perceptually one hop) |

The site MUST NOT introduce any 3xx HTTP status (gh-pages can't serve real redirects), 5xx anywhere, or 401/403 (the site is public).
