import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
	loadAbstracts,
	loadAuthors,
	loadCell,
	loadManifest,
	resetCachesForTests,
	type AbstractsShard,
	type AuthorsShard,
	type CellShard,
	type Manifest
} from '$lib/shards';

const MANIFEST_FIXTURE: Manifest = {
	schema_version: 'ui.v1',
	build_info: {
		corpus_state_key: 'test12345678',
		code_revision: 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
		code_revision_short: 'a1b2c3d',
		stage4_rollup_state_key: 'test12345678',
		built_at: '2026-05-17T00:00:00+00:00'
	},
	corpus_count: 2,
	default_cell: { model: 'neuroscape', input: 'abstract' },
	models: ['minilm', 'neuroscape'],
	inputs: ['abstract'],
	cells: [],
	facets: [],
	search: {
		lexical_index: 'data/search/lexical_index.json',
		minilm_vectors: 'data/search/minilm_vectors.bin',
		minilm_vectors_build_info_url: 'data/search/minilm_vectors.build_info.json',
		minilm_dim: 384,
		minilm_dtype: 'int8'
	}
};

const ABSTRACTS_FIXTURE: AbstractsShard = {
	schema_version: 'abstracts.v1',
	build_info: MANIFEST_FIXTURE.build_info,
	abstracts: [
		{
			abstract_id: 1001,
			poster_id: 'M-AM-101',
			title: 'Memory fMRI in aging',
			accepted_for: 'Poster',
			sections: {
				introduction: '',
				methods: '',
				results: '',
				conclusion: '',
				references: ''
			},
			topics: {
				primary: 'Lifespan Development',
				primary_subcategory: 'Aging',
				secondary: '',
				secondary_subcategory: ''
			},
			methods_checklist: ['Functional MRI'],
			facets: {},
			author_ids: [0],
			reference_dois: [],
			reference_urls: []
		}
	]
};

const AUTHORS_FIXTURE: AuthorsShard = {
	schema_version: 'authors.v1',
	build_info: MANIFEST_FIXTURE.build_info,
	authors: [
		{
			author_id: 0,
			name: 'Jane Smith',
			affiliations: ['Stanford'],
			abstract_ids: [1001]
		}
	]
};

function mockFetch(map: Record<string, unknown>) {
	return vi.fn(async (input: RequestInfo | URL) => {
		const url = typeof input === 'string' ? input : input.toString();
		const path = url.replace(/^https?:\/\/[^/]+/, '');
		const key = Object.keys(map).find((p) => path.endsWith(p));
		if (!key) {
			return new Response('not found', { status: 404 }) as Response;
		}
		return new Response(JSON.stringify(map[key]), {
			status: 200,
			headers: { 'content-type': 'application/json' }
		}) as Response;
	});
}

describe('shard loaders', () => {
	beforeEach(() => {
		resetCachesForTests();
	});
	afterEach(() => {
		resetCachesForTests();
	});

	it('loadManifest parses the manifest envelope', async () => {
		const fetcher = mockFetch({
			'/data/manifest.json': MANIFEST_FIXTURE
		}) as unknown as typeof fetch;
		const m = await loadManifest(fetcher);
		expect(m).not.toBeNull();
		expect(m?.schema_version).toBe('ui.v1');
		expect(m?.build_info.code_revision_short).toBe('a1b2c3d');
		expect(m?.corpus_count).toBe(2);
	});

	it('loadAbstracts parses the abstracts envelope', async () => {
		const fetcher = mockFetch({
			'/data/abstracts.json': ABSTRACTS_FIXTURE
		}) as unknown as typeof fetch;
		const a = await loadAbstracts(fetcher);
		expect(a).not.toBeNull();
		expect(a?.abstracts).toHaveLength(1);
		expect(a?.abstracts[0].poster_id).toBe('M-AM-101');
		expect(a?.abstracts[0].topics.primary).toBe('Lifespan Development');
	});

	it('loadAuthors parses the authors envelope', async () => {
		const fetcher = mockFetch({
			'/data/authors.json': AUTHORS_FIXTURE
		}) as unknown as typeof fetch;
		const au = await loadAuthors(fetcher);
		expect(au).not.toBeNull();
		expect(au?.authors[0].name).toBe('Jane Smith');
	});

	it('returns null when the shard 404s (graceful degrade for the placeholder)', async () => {
		const fetcher = mockFetch({}) as unknown as typeof fetch;
		expect(await loadAbstracts(fetcher)).toBeNull();
		resetCachesForTests();
		expect(await loadAuthors(fetcher)).toBeNull();
	});

	it('caches between calls (single fetch per shard)', async () => {
		const fetcher = mockFetch({
			'/data/manifest.json': MANIFEST_FIXTURE
		}) as unknown as typeof fetch & ReturnType<typeof vi.fn>;
		await loadManifest(fetcher);
		await loadManifest(fetcher);
		expect((fetcher as unknown as ReturnType<typeof vi.fn>).mock.calls.length).toBe(1);
	});
});

const CELL_FIXTURE: CellShard = {
	schema_version: 'cell.v1',
	build_info: MANIFEST_FIXTURE.build_info,
	cell_key: 'neuroscape_abstract',
	rows: [
		{
			abstract_id: 1001,
			umap2d: [0.1, 0.2],
			umap3d: [0.1, 0.2, 0.3],
			community_id: 7,
			topic_cluster_id: 100,
			neuroscape_cluster_id: 42,
			neuroscape_cluster_distance: 0.5
		}
	]
};

describe('loadCell', () => {
	beforeEach(() => resetCachesForTests());
	afterEach(() => resetCachesForTests());

	it('fetches the per-cell shard at the cell_key path', async () => {
		const fetcher = mockFetch({
			'/data/cells/neuroscape_abstract.json': CELL_FIXTURE
		}) as unknown as typeof fetch;
		const shard = await loadCell('neuroscape_abstract', fetcher);
		expect(shard?.cell_key).toBe('neuroscape_abstract');
		expect(shard?.rows[0].neuroscape_cluster_id).toBe(42);
	});

	it('returns null when the cell shard 404s', async () => {
		const fetcher = mockFetch({}) as unknown as typeof fetch;
		expect(await loadCell('missing_cell', fetcher)).toBeNull();
	});

	it('caches by cell_key (multiple cells share the same module-level Map)', async () => {
		const fetcher = mockFetch({
			'/data/cells/neuroscape_abstract.json': CELL_FIXTURE,
			'/data/cells/voyage_methods.json': { ...CELL_FIXTURE, cell_key: 'voyage_methods' }
		}) as unknown as typeof fetch & ReturnType<typeof vi.fn>;
		await loadCell('neuroscape_abstract', fetcher);
		await loadCell('neuroscape_abstract', fetcher); // cache hit
		await loadCell('voyage_methods', fetcher); // distinct fetch
		const calls = (fetcher as unknown as ReturnType<typeof vi.fn>).mock.calls;
		expect(calls.length).toBe(2);
	});
});
