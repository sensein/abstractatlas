// Prerender every route at build time so the page title (and the build_info
// footer) are baked into the static HTML — that lets reviewers verify the
// committish via `view-source` or curl, not only after JS hydration.
export const prerender = true;
export const trailingSlash = 'always';
