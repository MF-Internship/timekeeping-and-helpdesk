#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
version="1.26.1"
os_name="$(uname -s)"
architecture="$(uname -m)"
binary_name="oasdiff"

case "$os_name/$architecture" in
  Darwin/*)
    archive="oasdiff_${version}_darwin_all.tar.gz"
    checksum="ac3f56e9b7f3c717355768bc6943b5b54461f43e5c87d1e20027e2209093d2aa"
    ;;
  Linux/x86_64)
    archive="oasdiff_${version}_linux_amd64.tar.gz"
    checksum="ea0007fe536c7915785f754885d2afdb11352d6a14531950edf9d601a2baa674"
    ;;
  Linux/aarch64|Linux/arm64)
    archive="oasdiff_${version}_linux_arm64.tar.gz"
    checksum="423ef13ac4197b1fca948ccd6839dbaa8a666841b59466542f0332a7e95a1d66"
    ;;
  MINGW*/x86_64|MSYS*/x86_64|CYGWIN*/x86_64)
    archive="oasdiff_${version}_windows_amd64.tar.gz"
    checksum="fa662785bce15c9720eccacb693ca6af4f2b98dd51dbda8db6ae009dfae1825a"
    binary_name="oasdiff.exe"
    ;;
  *)
    echo "OASDIFF-PLATFORM: scripts/install_oasdiff.sh" >&2
    exit 1
    ;;
esac

install_dir="${OASDIFF_INSTALL_DIR:-$repo_root/.cache/tools/oasdiff-$version}"
binary="$install_dir/$binary_name"
cached_archive="$install_dir/$archive"

archive_is_verified() {
  local candidate="$1"
  local actual_checksum
  [[ -f "$candidate" ]] || return 1
  if command -v shasum >/dev/null 2>&1; then
    actual_checksum="$(shasum -a 256 "$candidate" | awk '{print $1}')"
  else
    actual_checksum="$(sha256sum "$candidate" | awk '{print $1}')"
  fi
  [[ "$actual_checksum" == "$checksum" ]]
}

binary_matches_archive() {
  [[ -x "$binary" ]] || return 1
  tar -xOf "$cached_archive" "$binary_name" | cmp -s - "$binary"
}

if archive_is_verified "$cached_archive" && binary_matches_archive; then
  printf '%s\n' "$binary"
  exit 0
fi

temporary_dir="$(mktemp -d)"
trap 'rm -rf "$temporary_dir"' EXIT
download="$temporary_dir/$archive"
verified_archive="$cached_archive"
if ! archive_is_verified "$cached_archive"; then
  url="https://github.com/oasdiff/oasdiff/releases/download/v$version/$archive"
  curl --fail --silent --show-error --location "$url" --output "$download"
  if ! archive_is_verified "$download"; then
    echo "OASDIFF-CHECKSUM: scripts/install_oasdiff.sh" >&2
    exit 1
  fi
  verified_archive="$download"
fi

mkdir -p "$install_dir"
tar -xzf "$verified_archive" -C "$temporary_dir" "$binary_name"
install -m 0755 "$temporary_dir/$binary_name" "$binary"
if [[ "$verified_archive" != "$cached_archive" ]]; then
  install -m 0644 "$verified_archive" "$cached_archive"
fi
if ! archive_is_verified "$cached_archive" || ! binary_matches_archive; then
  echo "OASDIFF-CACHE: scripts/install_oasdiff.sh" >&2
  exit 1
fi
printf '%s\n' "$binary"
