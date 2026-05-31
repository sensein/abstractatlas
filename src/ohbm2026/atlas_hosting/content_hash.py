"""Content-addressed object keys for Stage 20 R2 publishing.

Spec: ``specs/020-cloudflare-r2-migration/`` — research R-1.

The key for an artifact is derived from the SHA-256 of the EXACT bytes
the browser will fetch, so identical content always maps to the same
key (dedup + immutability) and differing content never collides. The
original filename is kept as the final path segment for readability and
content-type inference; it does not affect correctness because the site
treats the full URL as opaque.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Union

PathLike = Union[str, Path]

# Stream files in 1 MiB chunks so a hundreds-of-MB sidecar
# (neuroscape_vectors.parquet) never loads whole into memory.
_CHUNK_BYTES = 1024 * 1024


def sha256_file(path: PathLike) -> str:
    """Return the lowercase hex SHA-256 of ``path``, streamed in chunks."""

    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def derive_object_key(sha256: str, filename: str, *, prefix: str = "") -> str:
    """Content-addressed key ``[<prefix>/]<sha256>/<filename>``.

    ``prefix`` is an optional bucket namespace (``R2_KEY_PREFIX``);
    leading/trailing slashes are normalised away so the result never
    contains an empty or doubled segment.
    """

    cleaned_prefix = (prefix or "").strip("/")
    segments = [cleaned_prefix] if cleaned_prefix else []
    segments.extend([sha256, filename])
    return "/".join(segments)


def public_url(base_url: str, object_key: str) -> str:
    """Join the public base URL and an object key into one URL.

    Exactly one ``/`` separates the base from the key regardless of how
    either side is punctuated.
    """

    return f"{base_url.rstrip('/')}/{object_key.lstrip('/')}"
