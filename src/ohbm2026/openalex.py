from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
from datetime import datetime, timezone
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse
from urllib.request import Request

from ohbm2026.enrichment import html_to_markdown
from ohbm2026.graphql_api import load_dotenv, urlopen_with_retries

OPENALEX_API = "https://api.openalex.org/works"
OPENALEX_API_ENV = "OPENALEX_API"
DOI_PATTERN = re.compile(r"(?:https?://(?:dx\.)?doi\.org/|doi:\s*)?(10\.\d{4,9}/[-._;()/:A-Z0-9]+)", re.I)
PMID_PATTERN = re.compile(r"\bPMID\s*:?\s*(\d+)\b", re.I)


class OpenAlexError(RuntimeError):
    """Raised when OpenAlex reference enrichment cannot continue."""


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def normalize_reference_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def extract_reference_entries(raw_value: str | None) -> list[str]:
    markdown = html_to_markdown(raw_value or "")
    if not markdown.strip():
        return []

    lines = [line.strip() for line in markdown.splitlines() if line.strip()]
    entries: list[str] = []
    current: list[str] = []
    for line in lines:
        if re.match(r"^(\d+\.\s+|-+\s+)", line):
            if current:
                entries.append(normalize_reference_text(" ".join(current)))
            current = [re.sub(r"^(\d+\.\s+|-+\s+)", "", line)]
        else:
            current.append(line)

    if current:
        entries.append(normalize_reference_text(" ".join(current)))
    if not entries and markdown.strip():
        entries.append(normalize_reference_text(markdown))
    return [entry for entry in entries if entry]


def normalize_doi(doi: str | None) -> str | None:
    if not doi:
        return None
    cleaned = doi.strip()
    cleaned = re.sub(r"^(?:https?://(?:dx\.)?doi\.org/|doi:\s*)", "", cleaned, flags=re.I)
    cleaned = cleaned.split()[0]
    cleaned = re.split(r"(?i)\.pmid:?", cleaned)[0]
    cleaned = cleaned.rstrip(").,; ]}")
    return cleaned.lower() or None


def extract_dois(reference_text: str) -> list[str]:
    dois = [normalize_doi(match) for match in DOI_PATTERN.findall(reference_text)]
    seen: set[str] = set()
    result: list[str] = []
    for doi in dois:
        if doi and doi not in seen:
            seen.add(doi)
            result.append(doi)
    return result


def extract_pmid(reference_text: str) -> str | None:
    match = PMID_PATTERN.search(reference_text)
    return match.group(1) if match else None


def guess_reference_title(reference_text: str) -> str:
    text = DOI_PATTERN.sub("", reference_text)
    text = PMID_PATTERN.sub("", text)
    segments = [segment.strip(" .") for segment in re.split(r"\.\s+", text) if segment.strip(" .")]
    if len(segments) >= 2 and len(segments[1].split()) >= 3:
        return segments[1]
    if segments:
        return segments[0]
    return normalize_reference_text(reference_text)


def build_reference_key(reference_text: str, doi: str | None = None, pmid: str | None = None) -> str:
    if doi:
        return f"doi:{doi}"
    if pmid:
        return f"pmid:{pmid}"
    digest = hashlib.sha1(normalize_reference_text(reference_text).lower().encode("utf-8")).hexdigest()
    return f"text:{digest}"


def title_similarity(left: str, right: str) -> float:
    normalized_left = re.sub(r"[^a-z0-9]+", " ", left.lower()).strip()
    normalized_right = re.sub(r"[^a-z0-9]+", " ", right.lower()).strip()
    if not normalized_left or not normalized_right:
        return 0.0
    return SequenceMatcher(a=normalized_left, b=normalized_right).ratio()


@lru_cache(maxsize=1)
def get_openalex_api_key(env_path: str = ".env") -> str | None:
    env_values = load_dotenv(Path(env_path))
    api_key = os.environ.get(OPENALEX_API_ENV) or env_values.get(OPENALEX_API_ENV)
    return api_key or None


def add_query_parameter(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query[key] = value
    return urlunparse(parsed._replace(query=urlencode(query)))


def openalex_request(url: str) -> dict[str, Any]:
    api_key = get_openalex_api_key()
    if api_key:
        url = add_query_parameter(url, "api_key", api_key)
    request = Request(url, headers={"User-Agent": "ohbm2026-reference-enrichment/0.1"})
    try:
        with urlopen_with_retries(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise OpenAlexError(f"OpenAlex request failed with HTTP {exc.code}: {body}") from exc
    except (URLError, OSError, TimeoutError, ValueError) as exc:
        raise OpenAlexError(f"OpenAlex request failed: {exc}") from exc


def fetch_openalex_work_by_doi(doi: str) -> dict[str, Any] | None:
    url = f"{OPENALEX_API}?filter=doi:{quote(doi, safe='')}&per-page=1"
    parsed = openalex_request(url)
    results = parsed.get("results", [])
    return results[0] if results else None


def fetch_openalex_work_by_pmid(pmid: str) -> dict[str, Any] | None:
    url = f"{OPENALEX_API}?filter=pmid:{quote(pmid, safe='')}&per-page=1"
    parsed = openalex_request(url)
    results = parsed.get("results", [])
    return results[0] if results else None


def search_openalex_work_by_title(title: str, min_similarity: float = 0.75) -> dict[str, Any] | None:
    if not title.strip():
        return None
    url = f"{OPENALEX_API}?search={quote(title)}&per-page=5"
    parsed = openalex_request(url)
    best_match: dict[str, Any] | None = None
    best_score = 0.0
    for result in parsed.get("results", []):
        score = title_similarity(title, result.get("display_name") or "")
        if score > best_score:
            best_score = score
            best_match = result
    if best_match and best_score >= min_similarity:
        return best_match
    return None


def normalize_openalex_work(work: dict[str, Any]) -> dict[str, Any]:
    pmid_value = ((work.get("ids") or {}).get("pmid") or "").strip()
    pmid_match = re.search(r"(\d+)", pmid_value)
    return {
        "openalex_id": work.get("id"),
        "doi": normalize_doi((work.get("doi") or "").strip()) if work.get("doi") else None,
        "pmid": pmid_match.group(1) if pmid_match else None,
        "display_name": work.get("display_name"),
        "publication_year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "journal": (((work.get("primary_location") or {}).get("source") or {}).get("display_name")),
        "type": work.get("type"),
        "type_crossref": work.get("type_crossref"),
        "is_review": str(work.get("type") or "").lower() == "review"
        or str(work.get("type_crossref") or "").lower() == "review-article",
        "cited_by_count": work.get("cited_by_count"),
        "referenced_works": work.get("referenced_works") or [],
        "referenced_works_count": work.get("referenced_works_count"),
    }


def build_reference_record(reference_text: str) -> dict[str, Any]:
    doi = next(iter(extract_dois(reference_text)), None)
    pmid = extract_pmid(reference_text)
    title_guess = guess_reference_title(reference_text)
    return {
        "reference_key": build_reference_key(reference_text, doi=doi, pmid=pmid),
        "raw_text": normalize_reference_text(reference_text),
        "doi": doi,
        "pmid": pmid,
        "title_guess": title_guess,
    }


def load_existing_reference_cache(output_path: Path) -> dict[str, dict[str, Any]]:
    if not output_path.exists():
        return {}
    try:
        database = load_json(output_path)
    except json.JSONDecodeError:
        return {}
    return {
        reference["reference_key"]: reference
        for reference in database.get("references", [])
        if isinstance(reference.get("reference_key"), str)
    }


def normalize_cached_reference(reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "reference_key": reference["reference_key"],
        "raw_text": reference.get("raw_text") or "",
        "doi": reference.get("doi"),
        "pmid": reference.get("pmid"),
        "title_guess": reference.get("title_guess"),
        "matched": bool(reference.get("matched")),
        "match_method": reference.get("match_method") or "pending",
        "openalex": reference.get("openalex"),
        "source_count": 0,
        "raw_text_examples": [],
        "doi_lookup_completed": bool(reference.get("doi_lookup_completed")),
        "pmid_lookup_completed": bool(reference.get("pmid_lookup_completed")),
        "title_lookup_completed": bool(reference.get("title_lookup_completed")),
    }


def chunked_values(values: list[str], chunk_size: int) -> list[list[str]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    return [values[index : index + chunk_size] for index in range(0, len(values), chunk_size)]


def fetch_openalex_works_by_field(field_name: str, values: list[str]) -> dict[str, dict[str, Any]]:
    if not values:
        return {}
    filter_value = f"{field_name}:" + "|".join(quote(value, safe="") for value in values)
    try:
        parsed = openalex_request(f"{OPENALEX_API}?filter={filter_value}&per-page={len(values)}")
    except OpenAlexError as exc:
        if "HTTP 400" not in str(exc):
            raise
        if len(values) == 1:
            return {}
        midpoint = max(1, len(values) // 2)
        left = fetch_openalex_works_by_field(field_name, values[:midpoint])
        right = fetch_openalex_works_by_field(field_name, values[midpoint:])
        return {**left, **right}
    results = parsed.get("results", [])
    mapping: dict[str, dict[str, Any]] = {}
    for result in results:
        if field_name == "doi":
            key = normalize_doi(result.get("doi"))
        elif field_name == "pmid":
            pmid_value = ((result.get("ids") or {}).get("pmid") or "").strip()
            pmid_match = re.search(r"(\d+)", pmid_value)
            key = pmid_match.group(1) if pmid_match else None
        else:
            raise ValueError(f"Unsupported field_name: {field_name}")
        if key:
            mapping[key] = result
    return mapping


def collect_reference_cache(
    abstracts_database: dict[str, Any], output_path: Path
) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    reference_cache = {
        key: normalize_cached_reference(value)
        for key, value in load_existing_reference_cache(output_path).items()
    }
    abstract_reference_records: list[dict[str, Any]] = []

    for abstract in abstracts_database.get("abstracts", []):
        raw_reference_value = ""
        for response in abstract.get("responses", []):
            if response.get("question_name") == "References/Citations":
                raw_reference_value = response.get("value") or ""
                break

        references: list[dict[str, Any]] = []
        for reference_text in extract_reference_entries(raw_reference_value):
            reference = build_reference_record(reference_text)
            cached = reference_cache.get(reference["reference_key"])
            if cached is None:
                cached = {
                    **reference,
                    "matched": False,
                    "match_method": "pending",
                    "openalex": None,
                    "source_count": 0,
                    "raw_text_examples": [],
                    "doi_lookup_completed": False,
                    "pmid_lookup_completed": False,
                    "title_lookup_completed": False,
                }
                reference_cache[reference["reference_key"]] = cached
            else:
                if not cached.get("doi") and reference.get("doi"):
                    cached["doi"] = reference["doi"]
                if not cached.get("pmid") and reference.get("pmid"):
                    cached["pmid"] = reference["pmid"]
                if not cached.get("title_guess") and reference.get("title_guess"):
                    cached["title_guess"] = reference["title_guess"]
                cached.setdefault("matched", False)
                cached.setdefault("match_method", "pending")
                cached.setdefault("openalex", None)
                cached.setdefault("source_count", 0)
                cached.setdefault("raw_text_examples", [])
                cached.setdefault("doi_lookup_completed", False)
                cached.setdefault("pmid_lookup_completed", False)
                cached.setdefault("title_lookup_completed", False)

            cached["source_count"] = int(cached.get("source_count", 0)) + 1
            raw_text_examples = list(cached.get("raw_text_examples", []))
            if reference["raw_text"] not in raw_text_examples and len(raw_text_examples) < 3:
                raw_text_examples.append(reference["raw_text"])
            cached["raw_text_examples"] = raw_text_examples
            references.append(reference)

        abstract_reference_records.append({"id": abstract["id"], "references": references})

    return abstract_reference_records, reference_cache


def build_reference_metadata_payload(
    abstract_reference_records: list[dict[str, Any]],
    reference_cache: dict[str, dict[str, Any]],
    *,
    use_title_search: bool,
    request_counts: dict[str, int] | None = None,
    status: str = "completed",
    phase: str = "completed",
) -> dict[str, Any]:
    abstracts_out: list[dict[str, Any]] = []
    for abstract in abstract_reference_records:
        abstract_references: list[dict[str, Any]] = []
        for reference in abstract["references"]:
            resolved = reference_cache[reference["reference_key"]]
            abstract_references.append(
                {
                    "reference_key": resolved["reference_key"],
                    "raw_text": reference["raw_text"],
                    "doi": reference.get("doi"),
                    "pmid": reference.get("pmid"),
                    "title_guess": reference.get("title_guess"),
                    "matched": bool(resolved.get("matched")),
                    "match_method": resolved.get("match_method"),
                    "openalex_id": ((resolved.get("openalex") or {}).get("openalex_id")),
                }
            )
        abstracts_out.append({"id": abstract["id"], "references": abstract_references})

    references = sorted(reference_cache.values(), key=lambda item: item["reference_key"])
    matched_count = sum(1 for reference in references if reference.get("matched"))
    doi_completed = sum(1 for reference in references if reference.get("doi_lookup_completed"))
    pmid_completed = sum(1 for reference in references if reference.get("pmid_lookup_completed"))
    title_completed = sum(1 for reference in references if reference.get("title_lookup_completed"))
    return {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "phase": phase,
        "abstract_count": len(abstracts_out),
        "unique_reference_count": len(references),
        "matched_reference_count": matched_count,
        "unmatched_reference_count": len(references) - matched_count,
        "use_title_search": use_title_search,
        "request_counts": request_counts or {"doi_requests": 0, "pmid_requests": 0, "title_requests": 0},
        "progress": {
            "doi_lookup_completed_count": doi_completed,
            "pmid_lookup_completed_count": pmid_completed,
            "title_lookup_completed_count": title_completed,
        },
        "abstracts": abstracts_out,
        "references": references,
    }


def write_reference_metadata_snapshot(
    output_path: Path,
    abstract_reference_records: list[dict[str, Any]],
    reference_cache: dict[str, dict[str, Any]],
    *,
    use_title_search: bool,
    request_counts: dict[str, int],
    status: str,
    phase: str,
) -> None:
    write_json(
        output_path,
        build_reference_metadata_payload(
            abstract_reference_records,
            reference_cache,
            use_title_search=use_title_search,
            request_counts=request_counts,
            status=status,
            phase=phase,
        ),
    )


def resolve_reference_cache_exact_matches(
    abstract_reference_records: list[dict[str, Any]],
    reference_cache: dict[str, dict[str, Any]],
    *,
    output_path: Path,
    use_title_search: bool,
    exact_batch_size: int = 50,
    request_counts: dict[str, int] | None = None,
    checkpoint_every_batches: int = 5,
) -> dict[str, int]:
    stats = dict(request_counts or {"doi_requests": 0, "pmid_requests": 0, "title_requests": 0})

    for reference in reference_cache.values():
        if not reference.get("doi"):
            reference["doi_lookup_completed"] = True
        if not reference.get("pmid"):
            reference["pmid_lookup_completed"] = True
        if reference.get("matched") and reference.get("match_method") == "doi":
            reference["doi_lookup_completed"] = True
            reference["pmid_lookup_completed"] = True
        if reference.get("matched") and reference.get("match_method") == "pmid":
            reference["pmid_lookup_completed"] = True
        if reference.get("doi_lookup_completed") and reference.get("pmid_lookup_completed") and not reference.get("matched"):
            reference["match_method"] = "unmatched"

    doi_pending = sorted(
        {
            str(reference["doi"])
            for reference in reference_cache.values()
            if reference.get("doi")
            and not reference.get("doi_lookup_completed")
        }
    )
    doi_batches = chunked_values(doi_pending, exact_batch_size)
    for batch_index, doi_batch in enumerate(doi_batches, start=1):
        matched_by_doi = fetch_openalex_works_by_field("doi", doi_batch)
        stats["doi_requests"] += 1
        for reference in reference_cache.values():
            doi = reference.get("doi")
            if not doi or doi not in doi_batch or reference.get("doi_lookup_completed"):
                continue
            reference["doi_lookup_completed"] = True
            work = matched_by_doi.get(str(doi))
            if work is not None:
                reference["matched"] = True
                reference["match_method"] = "doi"
                reference["openalex"] = normalize_openalex_work(work)
                reference["pmid_lookup_completed"] = True
            elif reference.get("pmid_lookup_completed"):
                reference["match_method"] = "unmatched"
        if batch_index % checkpoint_every_batches == 0:
            write_reference_metadata_snapshot(
                output_path,
                abstract_reference_records,
                reference_cache,
                use_title_search=use_title_search,
                request_counts=stats,
                status="running",
                phase="exact",
            )
            print(
                json.dumps(
                    {
                        "phase": "exact",
                        "doi_requests": stats["doi_requests"],
                        "pmid_requests": stats["pmid_requests"],
                        "completed_batches": batch_index,
                        "total_batches": len(doi_batches),
                    }
                )
            )

    pmid_pending = sorted(
        {
            str(reference["pmid"])
            for reference in reference_cache.values()
            if reference.get("pmid")
            and not reference.get("pmid_lookup_completed")
        }
    )
    pmid_batches = chunked_values(pmid_pending, exact_batch_size)
    for batch_index, pmid_batch in enumerate(pmid_batches, start=1):
        matched_by_pmid = fetch_openalex_works_by_field("pmid", pmid_batch)
        stats["pmid_requests"] += 1
        for reference in reference_cache.values():
            pmid = reference.get("pmid")
            if not pmid or pmid not in pmid_batch or reference.get("pmid_lookup_completed"):
                continue
            reference["pmid_lookup_completed"] = True
            work = matched_by_pmid.get(str(pmid))
            if work is not None:
                reference["matched"] = True
                reference["match_method"] = "pmid"
                reference["openalex"] = normalize_openalex_work(work)
            elif reference.get("doi_lookup_completed"):
                reference["match_method"] = "unmatched"
        if batch_index % checkpoint_every_batches == 0:
            write_reference_metadata_snapshot(
                output_path,
                abstract_reference_records,
                reference_cache,
                use_title_search=use_title_search,
                request_counts=stats,
                status="running",
                phase="exact",
            )
            print(
                json.dumps(
                    {
                        "phase": "exact",
                        "doi_requests": stats["doi_requests"],
                        "pmid_requests": stats["pmid_requests"],
                        "completed_batches": batch_index,
                        "total_batches": len(pmid_batches),
                    }
                )
            )

    for reference in reference_cache.values():
        if reference.get("doi_lookup_completed") and reference.get("pmid_lookup_completed") and not reference.get("matched"):
            reference["match_method"] = "unmatched"

    return stats


def resolve_reference_cache_title_matches(
    abstract_reference_records: list[dict[str, Any]],
    reference_cache: dict[str, dict[str, Any]],
    *,
    output_path: Path,
    use_title_search: bool,
    title_similarity_threshold: float = 0.75,
    delay_seconds: float = 0.0,
    request_counts: dict[str, int] | None = None,
) -> dict[str, int]:
    stats = dict(request_counts or {"doi_requests": 0, "pmid_requests": 0, "title_requests": 0, "title_errors": 0})
    for reference in reference_cache.values():
        if reference.get("title_lookup_completed"):
            continue
        if reference.get("matched") or not reference.get("title_guess"):
            reference["title_lookup_completed"] = True
            continue
        stats["title_requests"] += 1
        try:
            work = search_openalex_work_by_title(
                str(reference["title_guess"]),
                min_similarity=title_similarity_threshold,
            )
        except OpenAlexError as exc:
            stats["title_errors"] = int(stats.get("title_errors", 0)) + 1
            reference["last_error"] = str(exc)
            if delay_seconds:
                time.sleep(delay_seconds)
            if stats["title_requests"] % 50 == 0 or stats["title_errors"] % 10 == 0:
                write_reference_metadata_snapshot(
                    output_path,
                    abstract_reference_records,
                    reference_cache,
                    use_title_search=use_title_search,
                    request_counts=stats,
                    status="running",
                    phase="title",
                )
                print(
                    json.dumps(
                        {
                            "phase": "title",
                            "title_requests": stats["title_requests"],
                            "title_errors": stats["title_errors"],
                        }
                    )
                )
            continue
        if work is not None:
            reference["matched"] = True
            reference["match_method"] = "title"
            reference["openalex"] = normalize_openalex_work(work)
            reference.pop("last_error", None)
        elif reference.get("match_method") == "pending":
            reference["match_method"] = "unmatched"
        reference["title_lookup_completed"] = True
        if delay_seconds:
            time.sleep(delay_seconds)
        if stats["title_requests"] % 50 == 0:
            write_reference_metadata_snapshot(
                output_path,
                abstract_reference_records,
                reference_cache,
                use_title_search=use_title_search,
                request_counts=stats,
                status="running",
                phase="title",
            )
            print(
                json.dumps(
                    {
                        "phase": "title",
                        "title_requests": stats["title_requests"],
                        "title_errors": stats.get("title_errors", 0),
                    }
                )
            )
    return stats


def build_reference_metadata_database(
    abstracts_database: dict[str, Any],
    *,
    output_path: Path,
    use_title_search: bool = False,
    title_similarity_threshold: float = 0.75,
    delay_seconds: float = 0.05,
    exact_batch_size: int = 50,
    checkpoint_every_batches: int = 5,
) -> dict[str, Any]:
    abstract_reference_records, reference_cache = collect_reference_cache(abstracts_database, output_path)
    request_counts = {"doi_requests": 0, "pmid_requests": 0, "title_requests": 0}
    write_reference_metadata_snapshot(
        output_path,
        abstract_reference_records,
        reference_cache,
        use_title_search=use_title_search,
        request_counts=request_counts,
        status="running",
        phase="collect",
    )
    request_counts = resolve_reference_cache_exact_matches(
        abstract_reference_records,
        reference_cache,
        output_path=output_path,
        use_title_search=use_title_search,
        exact_batch_size=exact_batch_size,
        request_counts=request_counts,
        checkpoint_every_batches=checkpoint_every_batches,
    )
    if use_title_search:
        request_counts.setdefault("title_errors", 0)
        request_counts = resolve_reference_cache_title_matches(
            abstract_reference_records,
            reference_cache,
            output_path=output_path,
            use_title_search=use_title_search,
            title_similarity_threshold=title_similarity_threshold,
            delay_seconds=delay_seconds,
            request_counts=request_counts,
        )

    return build_reference_metadata_payload(
        abstract_reference_records,
        reference_cache,
        use_title_search=use_title_search,
        request_counts=request_counts,
        status="completed",
        phase="completed",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve abstract references against OpenAlex and persist citation metadata")
    parser.add_argument("--input", default="data/abstracts.json")
    parser.add_argument("--output", default="data/reference_metadata.json")
    parser.add_argument("--exact-batch-size", type=int, default=50)
    parser.add_argument("--checkpoint-every-batches", type=int, default=5)
    parser.add_argument("--use-title-search", action="store_true")
    parser.add_argument("--title-similarity-threshold", type=float, default=0.75)
    parser.add_argument("--delay-seconds", type=float, default=0.05)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    database = load_json(Path(args.input))
    output_path = Path(args.output)
    result = build_reference_metadata_database(
        database,
        output_path=output_path,
        use_title_search=args.use_title_search,
        title_similarity_threshold=args.title_similarity_threshold,
        delay_seconds=args.delay_seconds,
        exact_batch_size=args.exact_batch_size,
        checkpoint_every_batches=args.checkpoint_every_batches,
    )
    write_json(output_path, result)
    print(
        json.dumps(
            {
                "input": args.input,
                "output": args.output,
                "abstract_count": result["abstract_count"],
                "unique_reference_count": result["unique_reference_count"],
                "matched_reference_count": result["matched_reference_count"],
                "unmatched_reference_count": result["unmatched_reference_count"],
                "use_title_search": args.use_title_search,
                "request_counts": result["request_counts"],
            },
            indent=2,
        )
    )
    return 0
