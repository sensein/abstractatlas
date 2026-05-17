import { base } from '$app/paths';

export interface BuildInfo {
	corpus_state_key: string;
	code_revision: string;
	code_revision_short: string;
	stage4_rollup_state_key: string;
	built_at: string;
}

/**
 * Build-time fallback when the data-package builder hasn't run (e.g. the
 * placeholder deploy where Stage 1–4 inputs aren't materialized in CI). The
 * Vite env vars `VITE_BUILD_SHA` / `VITE_BUILD_SHA_SHORT` / `VITE_BUILD_AT`
 * are populated by the deploy workflow before `pnpm build`. Local dev (no
 * env vars set) returns null so the UI doesn't display stale data.
 */
export function buildInfoFromEnv(): BuildInfo | null {
	const sha = import.meta.env.VITE_BUILD_SHA;
	const short = import.meta.env.VITE_BUILD_SHA_SHORT;
	const at = import.meta.env.VITE_BUILD_AT;
	if (!sha || !short) return null;
	return {
		corpus_state_key: 'placeholder',
		code_revision: sha,
		code_revision_short: short,
		stage4_rollup_state_key: 'placeholder',
		built_at: at || ''
	};
}

export interface Manifest {
	schema_version: string;
	build_info: BuildInfo;
	corpus_count: number;
	default_cell: { model: string; input: string };
	models: string[];
	inputs: string[];
	cells: Array<{
		cell_key: string;
		model: string;
		input: string;
		shard_url: string;
		topic_shards: Record<string, string>;
	}>;
	facets: Array<{ key: string; label: string; options: string[] }>;
	search: {
		lexical_index: string;
		minilm_vectors: string;
		minilm_vectors_build_info_url: string;
		minilm_dim: number;
		minilm_dtype: string;
	};
}

export interface AbstractRecord {
	abstract_id: number;
	poster_id: string;
	title: string;
	accepted_for: string;
	sections: {
		introduction: string;
		methods: string;
		results: string;
		conclusion: string;
		references: string;
	};
	topics: {
		primary: string;
		primary_subcategory: string;
		secondary: string;
		secondary_subcategory: string;
	};
	methods_checklist: string[];
	facets: Record<string, string | string[]>;
	author_ids: number[];
	reference_dois: string[];
	reference_urls: string[];
	reference_titles?: string[];
}

export interface AuthorRecord {
	author_id: number;
	name: string;
	affiliations: string[];
	abstract_ids: number[];
}

export interface AbstractsShard {
	schema_version: string;
	build_info: BuildInfo;
	abstracts: AbstractRecord[];
}

export interface AuthorsShard {
	schema_version: string;
	build_info: BuildInfo;
	authors: AuthorRecord[];
}

let manifestCache: Promise<Manifest | null> | null = null;
let abstractsCache: Promise<AbstractsShard | null> | null = null;
let authorsCache: Promise<AuthorsShard | null> | null = null;

async function fetchJson<T>(url: string, fetcher: typeof fetch): Promise<T | null> {
	try {
		const response = await fetcher(url);
		if (!response.ok) return null;
		return (await response.json()) as T;
	} catch {
		return null;
	}
}

export function loadManifest(fetcher: typeof fetch = fetch): Promise<Manifest | null> {
	if (manifestCache === null) {
		manifestCache = fetchJson<Manifest>(`${base}/data/manifest.json`, fetcher);
	}
	return manifestCache;
}

export function loadAbstracts(fetcher: typeof fetch = fetch): Promise<AbstractsShard | null> {
	if (abstractsCache === null) {
		abstractsCache = fetchJson<AbstractsShard>(`${base}/data/abstracts.json`, fetcher);
	}
	return abstractsCache;
}

export function loadAuthors(fetcher: typeof fetch = fetch): Promise<AuthorsShard | null> {
	if (authorsCache === null) {
		authorsCache = fetchJson<AuthorsShard>(`${base}/data/authors.json`, fetcher);
	}
	return authorsCache;
}

export function resetCachesForTests(): void {
	manifestCache = null;
	abstractsCache = null;
	authorsCache = null;
}
