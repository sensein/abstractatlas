// Dynamic route — served via the adapter-static SPA fallback (404.html), not
// prerendered. The list of poster_ids is read from the data package at
// runtime, so prerendering would either need to crawl the data package at
// build time (out of scope for the first US1 PR) or enumerate ~3,244 routes.
export const prerender = false;
export const ssr = false;
