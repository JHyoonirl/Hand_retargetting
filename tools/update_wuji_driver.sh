#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
target="$root/packages/wuji_hand"
repo="https://github.com/wuji-technology/wujihandros2.git"
tag="${WUJI_DRIVER_TAG:-v1.1.0}"

if [[ ! -e "$target" ]]; then
  git clone --depth 1 --branch "$tag" --recurse-submodules "$repo" "$target"
elif [[ -d "$target/.git" ]]; then
  git -C "$target" fetch --depth 1 origin "refs/tags/$tag:refs/tags/$tag"
  git -C "$target" checkout --detach "$tag"
  git -C "$target" submodule update --init --recursive
else
  echo "Refusing to replace non-Git directory: $target" >&2
  exit 2
fi

echo "WUJI driver checkout: $(git -C "$target" rev-parse --short HEAD) ($tag)"
git -C "$target" submodule status
