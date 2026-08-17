#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
candidate="$repo_root/contracts/openapi.yaml"
oasdiff_binary="$($repo_root/scripts/install_oasdiff.sh)"
if [[ ! -x "$oasdiff_binary" ]]; then
  echo "COMPAT-TOOL: scripts/check_openapi_compatibility.sh" >&2
  exit 1
fi

run_comparison() {
  local baseline="$1"
  local revision="$2"
  local output
  output="$(mktemp)"
  if "$oasdiff_binary" breaking "$baseline" "$revision" \
    --allow-external-refs=false --fail-on ERR --format text >"$output" 2>&1; then
    rm -f "$output"
    return 0
  fi
  rm -f "$output"
  echo "COMPAT-BREAKING: contracts/openapi.yaml" >&2
  return 1
}

if [[ "${1:-}" == "--baseline" ]]; then
  baseline="${2:?baseline path is required}"
  candidate="${3:?candidate path is required}"
  run_comparison "$baseline" "$candidate"
  exit $?
fi

merge_base_ref="${MERGE_BASE_REF:-origin/main}"
if git -C "$repo_root" rev-parse --verify "$merge_base_ref" >/dev/null 2>&1; then
  merge_base="$(git -C "$repo_root" merge-base HEAD "$merge_base_ref")"
else
  merge_base="$(git -C "$repo_root" rev-list --max-parents=0 HEAD | head -n 1)"
fi

if ! git -C "$repo_root" cat-file -e "$merge_base:contracts/openapi.yaml" 2>/dev/null; then
  echo "COMPAT-FIRST-BASELINE: contracts/openapi.yaml"
  exit 0
fi

temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT
baseline="$temporary_dir/openapi.yaml"
git -C "$repo_root" show "$merge_base:contracts/openapi.yaml" >"$baseline"
run_comparison "$baseline" "$candidate"
