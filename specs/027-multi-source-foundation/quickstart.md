# Quickstart: Multi-Source Ingest Foundation

## Run the tests (offline, stdlib only)

```bash
PYTHONPATH=src .venv/bin/python -m unittest tests.test_sources_base tests.test_sources_biorxiv -v
```

23 tests, no optional heavy dependencies, no network.

## Normalize a bioRxiv record (offline)

```python
from ohbm2026.sources.biorxiv import BiorxivSource

raw = {
    "doi": "10.1101/2024.01.15.575000",
    "title": "Cortical dynamics under a test paradigm",
    "authors": "Doe, Jane; Smith, John A.",
    "date": "2024-01-15",
    "category": "neuroscience",
    "abstract": "We show that ...",
    "server": "biorxiv",
    "license": "cc_by",
}

src = BiorxivSource()                 # default network fetcher (unused for normalize)
rec = src.normalize(raw)
print(rec.record_uid)                 # biorxiv:10.1101/2024.01.15.575000
print(rec.year, rec.venue)            # 2024 bioRxiv
print(rec.sections["abstract"])       # We show that ...
print(rec.authors[0].family)          # Doe
print(rec.provenance.raw_digest[:12]) # deterministic sha256 prefix
```

## Stream records over an injected fetcher (offline)

```python
def fake_page(server, interval, cursor):
    return {"messages": [{"count": 1, "total": 1, "cursor": cursor}],
            "collection": [raw]}

src = BiorxivSource(fetch_page=fake_page)
for rec in src.records({"interval": "2024-01-01/2024-01-31"}):
    print(rec.record_uid, rec.title)
```

## Live fetch (real bioRxiv API — needs outbound network)

```python
src = BiorxivSource(server="biorxiv")
recs = list(src.records({"interval": "2024-01-01/2024-01-02"}))
print(len(recs), "records")
```

The public bioRxiv details API needs no credentials; the default fetcher
issues an anonymous GET through the environment's proxy.

## Write your own source

Implement three members on a `BaseAbstractSource` subclass:

```python
from ohbm2026.sources.base import (
    AbstractRecord, BaseAbstractSource, SourceDescriptor,
    SourceProvenance, digest_raw,
)

class MySource(BaseAbstractSource):
    @property
    def descriptor(self):
        return SourceDescriptor(name="mysrc", kind="conference", title="My Conf")

    def fetch_raw(self, query):
        yield from my_paginated_fetch(query)      # your I/O; injectable for tests

    def normalize(self, raw):
        return AbstractRecord(
            source="mysrc",
            native_id=str(raw["id"]),
            title=raw["title"],
            provenance=SourceProvenance(
                source="mysrc", descriptor=self.descriptor,
                fetched_at=None, raw_digest=digest_raw(raw),
            ),
        )
```

`records()` is inherited. See `contracts/abstract-source.md` for the guarantees
your `normalize` must uphold (loud failure, discovered structure, provenance).
