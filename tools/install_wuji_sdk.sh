#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck disable=SC1091
source "$root/tools/wuji_sdk.env"

cache_dir=${WUJI_SDK_CACHE_DIR:-$root/downloads/wuji}
deb="$cache_dir/wujihandcpp-${WUJI_SDK_VERSION}-amd64.deb"
mkdir -p "$cache_dir"

die() {
  echo "install_wuji_sdk: $*" >&2
  exit 1
}

verify() {
  [[ -f "$deb" ]] || return 1
  echo "$WUJI_SDK_SHA256  $deb" | sha256sum -c - >/dev/null
}

if ! verify; then
  rm -f "$deb"
  if command -v curl >/dev/null 2>&1; then
    curl --fail --location --retry 3 --output "$deb" "$WUJI_SDK_URL"
  elif command -v wget >/dev/null 2>&1; then
    wget --tries=3 --output-document="$deb" "$WUJI_SDK_URL"
  else
    die "curl or wget is required to download the WUJI SDK"
  fi
fi

verify || die "checksum mismatch for $deb (expected $WUJI_SDK_SHA256)"
echo "WUJI SDK $WUJI_SDK_VERSION: $deb"

case "${1:-install}" in
  path|download)
    echo "Download complete; no system installation requested."
    exit 0
    ;;
  install)
    sudo apt-get update
    sudo apt-get install -y "$deb"
    ;;
  *)
    echo "Usage: $0 [install|download|path]" >&2
    exit 2
    ;;
esac
