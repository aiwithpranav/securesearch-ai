#!/usr/bin/env bash
# Downloads the public documentation used by the scale demo (Phase 10). Only the Markdown pages are kept.
# Nothing is stored in this repository: the files go to BIG_DATA_DIR (default: ~/ss-big, a short path on purpose,
# because Windows limits path length).
#
#   bash scripts/big/download.sh            # all three sources
#   bash scripts/big/download.sh kubernetes # only one
#
# Sources and licences (attribution is kept in docs/phases/phase-10-scale-demo/RESULTS.md):
#   kubernetes  github.com/kubernetes/website      content/en/docs        CC BY 4.0
#   docker      github.com/docker/docs             content/manuals        Apache 2.0
#   gitlab      gitlab.com/gitlab-com/content-sites/handbook   content/handbook   CC BY-SA 4.0
# Only the needed folder is fetched (shallow clone, sparse checkout), so it is a few hundred MB, not the whole history.
# It changes nothing outside BIG_DATA_DIR and a temporary folder that is removed at the end.
set -euo pipefail

DEST="${BIG_DATA_DIR:-$HOME/ss-big}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$DEST"

fetch() {  # name url folder-inside-the-repo
  local name="$1" url="$2" folder="$3"
  if [ -d "$DEST/$name" ] && [ -n "$(ls -A "$DEST/$name" 2>/dev/null)" ]; then
    echo "[skip] $name already downloaded in $DEST/$name (delete that folder to download again)"
    return
  fi
  echo "[download] $name from $url ($folder)"
  git clone --depth 1 --filter=blob:none --sparse "$url" "$TMP/$name" > /dev/null 2>&1
  git -C "$TMP/$name" sparse-checkout set "$folder" > /dev/null 2>&1
  mkdir -p "$DEST/$name"
  (cd "$TMP/$name/$folder" && find . -type f -name '*.md' -print0 | xargs -0 -I{} cp --parents "{}" "$DEST/$name/")
  local files size
  files="$(find "$DEST/$name" -type f | wc -l | tr -d ' ')"
  size="$(du -sh "$DEST/$name" | cut -f1)"
  echo "[done] $name: $files Markdown files, $size"
}

want="${1:-all}"
selected() { [ "$want" = all ] || [ "$want" = "$1" ]; }
if selected kubernetes; then fetch kubernetes https://github.com/kubernetes/website content/en/docs; fi
if selected docker; then fetch docker https://github.com/docker/docs content/manuals; fi
if selected gitlab; then fetch gitlab https://gitlab.com/gitlab-com/content-sites/handbook content/handbook; fi

echo
echo "Documents are in: $DEST"
echo "Next: export BIG_DATA_DIR=\"$DEST\"  (on Windows use the form C:/Users/you/ss-big)"
