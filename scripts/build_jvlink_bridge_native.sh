#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
src="$repo_root/tools/jvlink-bridge/bridge_native.c"
out_dir="$repo_root/tools/jvlink-bridge/bin/native"
out="$out_dir/JVLinkBridge.exe"

mkdir -p "$out_dir"

i686-w64-mingw32-gcc \
  -std=c99 \
  -O2 \
  -Wall \
  -Wextra \
  -o "$out" \
  "$src" \
  -lole32 \
  -loleaut32 \
  -luuid

echo "Built $out"
