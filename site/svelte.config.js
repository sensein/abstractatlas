import adapter from '@sveltejs/adapter-static';
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

// Stage 9 (spec 009-conference-subpath FR-101): every OHBM 2026 surface
// lives under `/ohbm2026/`. PR previews override via the env var to
// `/pr-<N>/ohbm2026`; local dev inherits the production default unless
// the caller explicitly sets `BASE_PATH=''` for a no-base smoke test.
//
// Stage 15 (spec 015-neuroscape-context, FR-008 + T048): the same
// SvelteKit project is now built three times by the deploy workflow,
// one per deployment. `VITE_SITE_MODE` selects the bundle's per-
// mode behaviour (Vite substitutes the constant at compile time;
// read at runtime via `$lib/site_mode`); `BASE_PATH` controls the
// `kit.paths.base` setting. Both env vars share the SAME canonical
// name so operators set one variable per mode:
//
//   | VITE_SITE_MODE | BASE_PATH default | publish dir              |
//   |----------------|-------------------|--------------------------|
//   | 'ohbm2026'     | '/ohbm2026'       | site/publish/ohbm2026/   |
//   | 'neuroscape'   | '/neuroscape'     | site/publish/neuroscape/ |
//   | 'atlas-root'   | ''                | site/publish/            |
//
// Operators / CI workflows can override BASE_PATH explicitly (e.g.
// PR previews use `/pr-<N>/<subpath>`). When BASE_PATH is set
// explicitly, it wins over the VITE_SITE_MODE-derived default.
const SITE_MODE = process.env.VITE_SITE_MODE ?? process.env.SITE_MODE ?? 'ohbm2026';

function defaultBasePathForMode(mode) {
	if (mode === 'atlas-root') return '';
	if (mode === 'neuroscape') return '/neuroscape';
	return '/ohbm2026';
}

const basePath = process.env.BASE_PATH ?? defaultBasePathForMode(SITE_MODE);

const config = {
	preprocess: vitePreprocess(),
	kit: {
		adapter: adapter({
			pages: 'build',
			assets: 'build',
			fallback: '404.html',
			precompress: false,
			strict: true
		}),
		paths: {
			base: basePath,
			// Stage 15: SvelteKit's prerender step rewrites absolute
			// hrefs to relative-from-current-page when `relative` is
			// true (the default when `paths.base` is set). That breaks
			// the cross-deployment links in LandingPageHeader — from
			// /pr-37/neuroscape/, an absolute /pr-37/ohbm2026/ gets
			// rewritten to ./ohbm2026/, which the browser resolves to
			// /pr-37/neuroscape/ohbm2026/ (404). Setting `relative:
			// false` keeps the absolute form. Functional impact on
			// ohbm2026 mode is zero — the browser resolves absolute
			// and relative paths identically against the same origin.
			relative: false
		},
		prerender: {
			// Stage 15: cross-deployment links in `LandingPageHeader`
			// (atlas-root → /ohbm2026/ + /neuroscape/, neuroscape →
			// /ohbm2026/ + /, ohbm2026 → no LandingPageHeader) point
			// outside the current build's `paths.base`. The prerender
			// crawler tries to visit them anyway despite `rel="external"`
			// and 404s because they don't start with the configured
			// base. Silently ignore the "does not begin with `base`"
			// error so the build succeeds — the targets exist in
			// SIBLING builds at deploy time.
			handleHttpError: ({ status, message }) => {
				if (
					status === 404 &&
					typeof message === 'string' &&
					message.includes('does not begin with `base`')
				) {
					return;
				}
				throw new Error(message);
			}
		}
	}
};

export default config;
