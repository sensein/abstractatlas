"""bioRxiv / medRxiv source — the concrete proof of the Arc A abstraction.

Implements :class:`~ohbm2026.sources.base.AbstractSource` against the
public bioRxiv "details" API
(``https://api.biorxiv.org/details/<server>/<interval>/<cursor>``),
which returns a ``collection`` of records plus a ``messages`` block
carrying ``count`` / ``total`` / ``cursor`` for pagination.

Chosen deliberately as a *different family* from OHBM's Oxford Abstracts
GraphQL: a DOI-keyed preprint feed paginated by date interval, with a
single ``abstract`` blob rather than named sections. If the canonical
record + Protocol can express both bioRxiv and OHBM without either
leaking into the other, the abstraction holds.

Network access is fully injectable via ``fetch_page`` so the test suite
runs offline (Principle I). Field presence is discovered from each
payload and any mismatch raises
:class:`~ohbm2026.sources.base.SourceNormalizationError` — never a
silent skip (Principle VII).
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any, Callable, Iterable, Mapping

from ohbm2026.sources.base import (
    AbstractAuthor,
    AbstractRecord,
    BaseAbstractSource,
    SourceDescriptor,
    SourceNormalizationError,
    SourceProvenance,
    digest_raw,
)

_API_BASE = "https://api.biorxiv.org"
_SERVER_VENUE = {"biorxiv": "bioRxiv", "medrxiv": "medRxiv"}

# fetch_page(server, interval, cursor) -> parsed JSON mapping
FetchPage = Callable[[str, str, int], Mapping[str, Any]]


def _default_fetch_page(server: str, interval: str, cursor: int) -> Mapping[str, Any]:
    """Real network fetch of one bioRxiv details page.

    Kept tiny and dependency-free (stdlib ``urllib``); the outbound
    request honours the environment's proxy configuration automatically.
    """
    url = f"{_API_BASE}/details/{server}/{interval}/{cursor}"
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310 (trusted host)
        payload = json.loads(response.read().decode("utf-8"))
    if not isinstance(payload, Mapping):
        raise SourceNormalizationError(f"bioRxiv page for {interval!r} was not a JSON object")
    return payload


def _parse_authors(raw_authors: object) -> tuple[AbstractAuthor, ...]:
    """Parse bioRxiv's ``"Last, First; Last, First"`` author string."""
    if not isinstance(raw_authors, str) or not raw_authors.strip():
        return ()
    authors: list[AbstractAuthor] = []
    for order, chunk in enumerate(part.strip() for part in raw_authors.split(";")):
        if not chunk:
            continue
        family: str | None = None
        given: str | None = None
        if "," in chunk:
            fam, _, giv = chunk.partition(",")
            family = fam.strip() or None
            given = giv.strip() or None
        authors.append(AbstractAuthor(name=chunk, family=family, given=given, order=order))
    return tuple(authors)


def _parse_year(raw_date: object) -> int | None:
    if isinstance(raw_date, str) and len(raw_date) >= 4 and raw_date[:4].isdigit():
        return int(raw_date[:4])
    return None


def _require_str(raw: Mapping[str, Any], key: str) -> str:
    value = raw.get(key)
    if not isinstance(value, str) or not value.strip():
        raise SourceNormalizationError(
            f"bioRxiv record missing required non-empty field {key!r} "
            f"(doi={raw.get('doi')!r})"
        )
    return value.strip()


class BiorxivSource(BaseAbstractSource):
    """A bioRxiv/medRxiv preprint source.

    Parameters
    ----------
    fetch_page:
        Injected page fetcher; defaults to a real ``urllib`` call.
        Tests pass a fake to stay offline.
    server:
        ``"biorxiv"`` (default) or ``"medrxiv"``.
    fetched_at:
        Optional ISO timestamp stamped into provenance. Passed in
        (never ``datetime.now()`` inline) so a build can make normalized
        output deterministic.
    """

    def __init__(
        self,
        fetch_page: FetchPage | None = None,
        *,
        server: str = "biorxiv",
        fetched_at: str | None = None,
    ) -> None:
        if server not in _SERVER_VENUE:
            raise SourceNormalizationError(
                f"unknown bioRxiv server {server!r}; expected one of {sorted(_SERVER_VENUE)}"
            )
        self._fetch_page: FetchPage = fetch_page or _default_fetch_page
        self._server = server
        self._fetched_at = fetched_at

    @property
    def descriptor(self) -> SourceDescriptor:
        return SourceDescriptor(
            name=self._server,
            kind="preprint",
            title=_SERVER_VENUE[self._server],
            homepage=f"https://www.{self._server}.org",
            api_base=_API_BASE,
        )

    def fetch_raw(self, query: Any) -> Iterable[Mapping[str, Any]]:
        """Yield raw records for a query ``{"interval": "<from>/<to>"}``.

        Cursor pagination is discovered from the response ``messages``
        block (Principle VII) rather than assuming a page size.
        """
        interval = self._resolve_interval(query)
        cursor = 0
        seen = 0
        while True:
            page = self._fetch_page(self._server, interval, cursor)
            collection = page.get("collection")
            if not isinstance(collection, list):
                raise SourceNormalizationError(
                    f"bioRxiv page for interval {interval!r} at cursor {cursor} "
                    "had no 'collection' list"
                )
            for item in collection:
                if isinstance(item, Mapping):
                    yield item
            seen += len(collection)
            total = self._page_total(page)
            if total is None or seen >= total or not collection:
                break
            cursor = seen

    def normalize(self, raw: Mapping[str, Any]) -> AbstractRecord:
        doi = _require_str(raw, "doi")
        title = _require_str(raw, "title")
        abstract = raw.get("abstract")
        abstract = abstract.strip() if isinstance(abstract, str) and abstract.strip() else None
        sections = {"abstract": abstract} if abstract else {}
        extra = {
            "category": raw.get("category"),
            "version": raw.get("version"),
            "license": raw.get("license"),
            "server": raw.get("server") or self._server,
            "published_doi": raw.get("published"),
            "author_corresponding": raw.get("author_corresponding"),
            "author_corresponding_institution": raw.get("author_corresponding_institution"),
            "date": raw.get("date"),
        }
        extra = {k: v for k, v in extra.items() if v not in (None, "", "NA")}
        return AbstractRecord(
            source=self._server,
            native_id=doi,
            title=title,
            display_id=doi,
            abstract=abstract,
            sections=sections,
            authors=_parse_authors(raw.get("authors")),
            venue=_SERVER_VENUE[self._server],
            year=_parse_year(raw.get("date")),
            url=f"https://doi.org/{doi}",
            extra=extra,
            provenance=SourceProvenance(
                source=self._server,
                descriptor=self.descriptor,
                fetched_at=self._fetched_at,
                raw_digest=digest_raw(raw),
                query=None,
            ),
        )

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _resolve_interval(query: Any) -> str:
        if isinstance(query, str):
            interval = query
        elif isinstance(query, Mapping):
            interval = query.get("interval")  # type: ignore[assignment]
        else:
            interval = None
        if not isinstance(interval, str) or "/" not in interval:
            raise SourceNormalizationError(
                "bioRxiv query requires an 'interval' of the form 'YYYY-MM-DD/YYYY-MM-DD' "
                f"(got {query!r})"
            )
        return interval

    @staticmethod
    def _page_total(page: Mapping[str, Any]) -> int | None:
        messages = page.get("messages")
        if isinstance(messages, list) and messages and isinstance(messages[0], Mapping):
            total = messages[0].get("total")
            if isinstance(total, (int, str)) and str(total).isdigit():
                return int(total)
        return None
