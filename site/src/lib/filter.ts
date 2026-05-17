import type { AbstractRecord, AuthorRecord } from '$lib/shards';

/** Lower-case + accent-fold for case/diacritic-insensitive substring search. */
export function normalize(value: string): string {
	return value
		.normalize('NFD')
		.replace(/\p{Diacritic}/gu, '')
		.toLowerCase();
}

interface SearchHaystack {
	abstract_id: number;
	haystack: string;
}

const haystackCache = new WeakMap<AbstractRecord[], SearchHaystack[]>();

export function buildHaystacks(
	abstracts: AbstractRecord[],
	authorsById: Map<number, AuthorRecord>
): SearchHaystack[] {
	const cached = haystackCache.get(abstracts);
	if (cached) return cached;
	const out: SearchHaystack[] = abstracts.map((a) => {
		const authorNames = a.author_ids
			.map((id) => authorsById.get(id)?.name ?? '')
			.filter(Boolean)
			.join(' ');
		const facetBlob = Object.values(a.facets)
			.map((v) => (Array.isArray(v) ? v.join(' ') : (v as string)))
			.join(' ');
		const haystack = normalize(
			[
				a.title,
				a.poster_id,
				a.topics.primary,
				a.topics.primary_subcategory,
				a.topics.secondary,
				a.topics.secondary_subcategory,
				a.methods_checklist.join(' '),
				authorNames,
				facetBlob
			].join('\n')
		);
		return { abstract_id: a.abstract_id, haystack };
	});
	haystackCache.set(abstracts, out);
	return out;
}

/** Substring search across title/poster_id/topics/methods/authors/facets. */
export function searchAbstracts(
	abstracts: AbstractRecord[],
	authorsById: Map<number, AuthorRecord>,
	query: string
): Set<number> | null {
	const q = normalize(query).trim();
	if (!q) return null;
	const haystacks = buildHaystacks(abstracts, authorsById);
	const out = new Set<number>();
	for (const { abstract_id, haystack } of haystacks) {
		if (haystack.includes(q)) out.add(abstract_id);
	}
	return out;
}
