# Phase 0 Research: Cloudflare R2 Migration & Content-Hashed Data Store

All decisions below are resolved — no open `NEEDS CLARIFICATION`. Scope was
fixed with the operator before the spec (add R2 channel + validate, defer
cutover; build the uploader now; local CLI with `.env` creds). The remaining
questions are technical and have clear best-practice answers.

---

## R-1: Content-addressed object key scheme

**Decision**: Object key = `<sha256hex>/<original-filename>`, where `<sha256hex>`
is the full 64-char lowercase hex SHA-256 of the **exact file bytes** the
browser will fetch (e.g. `a1b2…ef/neuroscape.parquet`). An optional fixed
prefix (`R2_KEY_PREFIX`, default empty) may namespace the bucket.

**Rationale**:
- Content addressing gives immutability + dedup for free: identical bytes → one
  key (FR-007, FR-009); different bytes → different key, so a new version never
  collides with or overwrites an old one (FR-008, FR-013).
- The full sha256 (not the 12-hex `state_key` prefix) makes accidental
  collisions cryptographically impossible across unbounded uploads. The
  `state_key` identifies the *build inputs*; the file hash identifies the
  *served bytes* — they are different and the CAS key must be the latter.
- Keeping the original filename as the final path segment preserves a
  human-recognisable name and the `.parquet` extension (helps R2/CDN content
  typing and ops debugging) without affecting correctness — the site treats the
  full URL as opaque.
- The existing registry channel entry already carries a per-artifact
  `{"url", "sha256"}` pair (see `resolve-data-channel.sh` registry shape), so
  the emitted snippet drops straight in: `sha256` = the key's hash.

**Alternatives considered**:
- `<filename>/<sha256>` (group-by-name): loses nothing functionally but reads
  worse and tempts a "latest" mutable alias. Rejected.
- Pure `<sha256>` (no extension): hurts ops readability and CDN content-type
  inference. Rejected.
- `packages/<state_key>/<filename>` (version-folder): groups siblings but is
  *input*-addressed, not content-addressed — two builds with identical output
  bytes would duplicate, and it invites overwrite if a state_key is reused.
  Rejected in favour of true content addressing; sibling grouping is handled by
  the **channel entry**, not the object layout.

---

## R-2: Public URL formation & bucket configuration

**Decision**: Public URL = `${R2_PUBLIC_BASE_URL}/<key>`. `R2_PUBLIC_BASE_URL`
is the operator-configured public base for the bucket — either R2's managed
`https://pub-<hash>.r2.dev` dev URL or a Cloudflare custom domain. The bucket
must be configured (operator action, documented in `contracts/r2-storage-layout.md`)
for: **public unauthenticated read**, **CORS** allowing the production +
PR-preview origins for `GET` and ranged `GET` (`Access-Control-Allow-Origin`,
`Access-Control-Allow-Headers: Range`, expose `Content-Range`/`Accept-Ranges`/
`ETag`), and a long-lived **immutable cache** header
(`Cache-Control: public, max-age=31536000, immutable`) — safe precisely because
keys are content-addressed.

**Rationale**: The site already fetches a full URL and issues Range requests via
hyparquet's `asyncBufferFromUrl`; R2 supports byte-range GET on public objects.
The site treats the URL opaquely, so the only requirements are public read +
CORS + Range — exactly what Dropbox's `dl.dropboxusercontent.com` provides
today. Immutable caching is a strict win over Dropbox because the URL never
changes content.

**Alternatives considered**: S3 presigned URLs (expiring, unsuitable for a
public static site); Cloudflare Worker proxy (extra moving part, unneeded for
public objects). Rejected.

---

## R-3: S3 client library

**Decision**: `boto3` (with `botocore`), added as a new optional dependency
group `r2 = ["boto3>=1.34"]`. Client built against R2's S3 endpoint
`https://<R2_ACCOUNT_ID>.r2.cloudflarestorage.com`, `region_name="auto"`,
signature v4, credentials from `.env`.

**Rationale**: boto3 is the canonical, well-tested S3 client; R2 is S3-API
compatible. It provides `head_object` (existence check), `upload_file` with a
`TransferConfig` that transparently multiparts large objects (the ~hundreds-of-MB
`neuroscape_vectors.parquet`), and `botocore.stub.Stubber` for hermetic unit
tests with no network. Keeping it optional matches the repo's pattern (`enrich`,
`analysis`, `ui`, … are all opt-in extras) so the base install stays lean.

**Alternatives considered**: `aws-cli`/`rclone` subprocess (harder to unit-test,
adds a non-Python dependency); `s3fs`/`minio` (extra abstraction, no benefit
here). Rejected.

**Credentials (env-var names, values only in `.env`)**:
`R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY`, `R2_BUCKET`,
`R2_PUBLIC_BASE_URL`, optional `R2_KEY_PREFIX`. Read with the existing
`get_api_key(env_path, env_var)` helper (`fetch/graphql_api.py:201`); **no
`python-dotenv` dependency is added** (the repo deliberately doesn't use it).
A missing/blank required var raises `R2CredentialsError` before any network
call.

---

## R-4: Idempotency / dedup / immutability mechanism

**Decision**: Before uploading an artifact, call `head_object(Bucket, Key)` on
its content-addressed key.
- **404 / `NoSuchKey`** → object absent → `upload_file` it; record `action:
  "uploaded"`.
- **200** → object present → **skip** (no PUT); record `action: "skipped"`. As a
  corruption guard, compare the existing object's `ContentLength` to the local
  file size; a mismatch raises `ContentHashMismatchError` (a content-addressed
  key must only ever hold bytes of that hash).
- Never call `delete_object`/overwrite; publishing only ever adds keys (FR-008).

The 404 is detected precisely by catching `botocore.exceptions.ClientError` and
inspecting `err.response["Error"]["Code"]` / HTTP status — **not** a bare
`except` (Constitution VI). Any other `ClientError` (403, network) re-raises as
`R2UploadError` with context (key, bucket, op).

**Rationale**: `head_object` is the runtime discovery of external state
(Constitution VII) — the uploader does not keep or trust a local "already
uploaded" ledger. This makes the upload idempotent (zero bytes on an unchanged
re-run, SC-003) and resumable (an interrupted run skips completed keys).
ETag is **not** used for verification: R2/S3 ETag equals the MD5 only for
single-part uploads and is opaque for multipart, so it cannot be compared to a
sha256; size is the cheap, reliable guard.

**Alternatives considered**: `put_object` with `IfNoneMatch: "*"` (R2 supports
conditional writes, but `head_object` is clearer, lets us size-guard, and avoids
relying on header support); a local manifest ledger as the source of truth
(violates VII — drifts from bucket reality). Rejected.

---

## R-5: Large-file upload

**Decision**: `boto3` `upload_file` with a `TransferConfig(multipart_threshold,
multipart_chunksize)` — multipart kicks in automatically above the threshold so
`neuroscape_vectors.parquet` uploads in parts without loading the whole file in
memory or truncating. The sha256 is computed by streaming the file once
(`hashlib` over fixed-size chunks) *before* the transfer.

**Rationale**: Transparent, memory-bounded, no custom multipart code. Hashing
and uploading both stream the file, so memory stays flat regardless of artifact
size.

---

## R-6: Comparison probes (Dropbox vs R2)

**Decision**: `compare-data-hosting` takes the two channel entries (or resolves
them from the registry JSON + channel keys) and, per logical artifact, probes
both URLs with `requests`:
- **Byte-parity**: stream-download each URL, sha256 it, and compare the two
  hashes (and, when available, against the registry's recorded `sha256`). A
  `--trust-recorded-sha256` flag skips the download and compares the recorded
  hashes / R2 key instead, for a fast check.
- **Range support**: send `Range: bytes=0-<n>`; expect `206 Partial Content` +
  a correct `Content-Range`; a `200` (range ignored) is a **fail**.
- **CORS**: send a `GET` (and an `OPTIONS` preflight) carrying an `Origin`
  header equal to the production site origin; assert the response echoes an
  acceptable `Access-Control-Allow-Origin` (origin or `*`). (The server *sending*
  the header is what the browser needs; `requests` checks the header presence,
  which is the correct server-side signal.)
- **Latency** (informational): wall-time of a small ranged GET, recorded but not
  a pass/fail gate.

Each probe yields a typed verdict; any failure (mismatch, `200`-not-`206`,
missing/again wrong ACAO, unreachable) sets that artifact non-passing and the
overall report `overall_pass=false` (FR-015). A probe that cannot complete is
recorded as an explicit failed verdict — never omitted (no silent gaps).

**Rationale**: These are exactly the three capabilities the live site depends on
(byte-identity so permalinks/cached previews stay valid; Range so per-table
reads stay cheap; CORS so the cross-origin fetch succeeds). `requests` is
already available via the `ui` extra. The report is the auditable evidence the
deferred cutover decision needs (US3).

**Alternatives considered**: a headless-browser CORS check (heavier; `[review]`
playwright exists but is overkill for a header assertion); HEAD-only parity
(can't prove byte-identity). Rejected; HEAD is used only for reachability/size
hints.

---

## R-7: Output locations & provenance

**Decision**:
- **Upload manifest** → `data/provenance/atlas_upload_provenance__<upload_state_key>.json`,
  mirroring `atlas_package`'s `_write_provenance` convention. `upload_state_key`
  = `_stable_hash({bucket, key_prefix, sorted artifact (logical_name, sha256)
  pairs})` so the manifest name is deterministic per published set.
- **Comparison report** → `data/outputs/data-hosting-comparison__<ts>.json`
  (timestamp passed in, since `Date.now()` is unavailable in some contexts; for
  the CLI we stamp `uploaded_utc`/`generated_utc` from `datetime.now(UTC)` at
  runtime).
- Both live under the gitignored `data/` root (`.gitignore:7`). A stage-specific
  ignore line is added for convention/clarity before first write.
- Manifest paths run through the reused `atlas_package.provenance.normalise_path`,
  which rejects absolute and `~` paths (Constitution VIII / CA-008).

**Rationale**: Matches the existing provenance pattern and artifact layout
contract; keeps every generated byte out of git; gives the published bundle the
machine-readable provenance CA-008 requires.

---

## R-8: Wiring into the registry (no site/CI code change)

**Decision**: The uploader **emits** a channel entry — a JSON object mapping
`ohbm2026`/`neuroscape`/`atlas`/`neuroscape_vectors` → `{"url", "sha256"}` —
to stdout and into the manifest. The operator merges it under a new key in the
`OHBM2026_UI_DATA_PACKAGE_URLS` GitHub Actions variable (e.g. via
`gh variable set`) and sets `site/data-channel.json`'s `key` on the validation
branch. The CLI does **not** mutate GitHub state and needs no GitHub token.

**Rationale**: Preserves the existing resolver contract exactly (FR-004,
FR-011); keeps the GitHub-variable edit an explicit, reviewable operator action
(the registry is operator-managed); avoids putting GH credentials in the upload
path (CA-004). `resolve-data-channel.sh` and the site loader are unchanged
because R2 URLs flow through them unmodified (FR-005).

**Verified**: `normaliseDropboxUrl()` (`site/src/lib/data_package/loader.ts:64`)
only rewrites `https://www.dropbox.com/…` and strips `dl=0`; a non-Dropbox HTTPS
URL is returned byte-for-byte. The new vitest test pins this so a future edit
can't silently start mangling R2 URLs.

---

## R-9: Exceptions

**Decision**: New `Stage20Error(OhbmStageError)` subtree in `exceptions.py`,
matching the `Stage15Error` style (keyword-only context attributes, exported in
`__all__`):
- `R2CredentialsError(Stage20Error)` — missing/blank env var (`var` attr).
- `R2UploadError(Stage20Error)` — any S3 op failure (`key`, `bucket`, `op`,
  `reason`).
- `ContentHashMismatchError(Stage20Error)` — existing object size/hash disagrees
  with the content-addressed key (`key`, `expected`, `actual`).
- `ArtifactDiscoveryError(Stage20Error)` — required artifact missing / unexpected
  file in the package dir (`path`, `missing`/`unexpected`).
- `HostingComparisonError(Stage20Error)` — a probe could not be performed
  (distinct from a *failed verdict*, which is recorded, not raised) (`url`,
  `probe`, `reason`).

**Rationale**: Constitution VI demands precise, typed, contextful errors;
mirroring the established subtree keeps the hierarchy consistent and keeps
`test_stage20_exceptions.py` a straight analogue of `test_atlas_exceptions.py`.
