#!/usr/bin/env bash
# Validate every shard of a UI data package against the LinkML schema.
#
# Usage:
#   scripts/validate_ui_data.sh [DATA_ROOT]
#
# DATA_ROOT defaults to `site/static/data/` — the locally-built package.
# Exits 0 if every shard validates, 1 otherwise.

set -euo pipefail

ROOT="${1:-site/static/data}"
SCH="specs/008-ui-rewrite/contracts/ui_data.linkml.yaml"
LINKML="${LINKML:-.venv/bin/linkml-validate}"

if [[ ! -d "$ROOT" ]]; then
  echo "no data dir at $ROOT" >&2
  exit 1
fi
if [[ ! -x "$LINKML" ]]; then
  echo "linkml-validate not found at $LINKML — install via 'uv pip install linkml'" >&2
  exit 1
fi

PASS=0
FAIL=0
declare -a FAILED=()

check() {
  local cls="$1" path="$2"
  local out
  if [[ ! -f "$path" ]]; then return; fi
  out=$("$LINKML" --schema "$SCH" --target-class "$cls" "$path" 2>&1 | grep -E "ERROR|No issues" | head -1 || true)
  if [[ "$out" == *"No issues found"* ]]; then
    PASS=$((PASS+1))
  else
    FAIL=$((FAIL+1))
    FAILED+=("$cls / $path: $out")
  fi
}

check Manifest             "$ROOT/manifest.json"
check AbstractsShard       "$ROOT/abstracts.json"
check AuthorsShard         "$ROOT/authors.json"
check EnrichmentShard      "$ROOT/enrichment.json"
check MinilmVectorsSidecar "$ROOT/search/minilm_vectors.build_info.json"
for f in "$ROOT"/cells/*.json; do check CellShard "$f"; done
for f in "$ROOT"/topics/*.json; do check TopicShard "$f"; done
for f in "$ROOT"/neighbors/*.json; do check NeighborsShard "$f"; done

echo "passed: $PASS  failed: $FAIL"
if [[ $FAIL -gt 0 ]]; then
  printf '  FAIL: %s\n' "${FAILED[@]}"
  exit 1
fi
