#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEPS="$ROOT/third_party"
mkdir -p "$DEPS" "$ROOT/build"
fetch_pinned() {
  local repo="$1" sha="$2" folder="$3"
  if [ -d "$folder/.git" ]; then
    git -C "$folder" fetch --depth 1 origin "$sha"
  else
    git init -q "$folder"
    git -C "$folder" remote add origin "https://github.com/$repo.git"
    git -C "$folder" fetch --depth 1 origin "$sha"
  fi
  git -C "$folder" checkout --detach -q "$sha"
  test "$(git -C "$folder" rev-parse HEAD)" = "$sha"
}
fetch_pinned "LSPosed/LSPlant" "06bd3412d639d6b0d76fe6c7388066fe44e8963d" "$DEPS/lsplant"
git -C "$DEPS/lsplant" submodule update --init --recursive --depth 1 lsplant/src/main/jni/external/dex_builder
fetch_pinned "LSPosed/Dobby" "c1da0315d7a2069bde2ab432e45d4ab6df91237a" "$DEPS/dobby"
fetch_pinned "hexhacking/xDL" "1e0b6254165a2ddcbd32f77a371700c69155acf8" "$DEPS/xdl"
{
  echo "LSPlant=06bd3412d639d6b0d76fe6c7388066fe44e8963d"
  echo "Dobby=c1da0315d7a2069bde2ab432e45d4ab6df91237a"
  echo "xDL=1e0b6254165a2ddcbd32f77a371700c69155acf8"
  printf "DexBuilder="; git -C "$DEPS/lsplant/lsplant/src/main/jni/external/dex_builder" rev-parse HEAD
} > "$ROOT/build/dependency-versions.txt"
cat "$ROOT/build/dependency-versions.txt"
