#!/usr/bin/env bash
# The memory games' browser checks (Playwright + Chromium), run from a checkout of the repo.
#
#   verify.sh local   --out <dir> [--tree <dir>] [<game>...]
#       P9 before a commit: assemble --check; seeded start/mid/win screenshots at 600x960 and 960x600;
#       one audio playthrough (the right clip on every flip); a whole quiz at both sizes (every
#       player once, a wrong pick, the clips, question/wrong/reveal/end screenshots); the worker
#       online, offline (memory and quiz) and installable; the state machine. Serves the working
#       tree, or --tree <dir>.
#   verify.sh compare <ref-a> <ref-b> --out <dir> [<game>...]
#       The same seeded screenshots and playthrough on two commits: pixels, DOM, the computed HUD
#       styles and the clip sequence must all match.
#   verify.sh upgrade <old-ref> <new-ref> --out <dir> [<game>...]
#       The GitHub Pages upgrade under /pages/ (sim.js): the old version installed, the new one
#       taking over online, then offline.
#   verify.sh live    --out <dir> [<game>...]
#       After a merge: every deployed precached file, then the worker check on the live site.
#
# <game> defaults to every game (`build_page.py list`); <ref> is a commit, or `.` for the working
# tree. --out must be outside the repo: it gets the screenshots, browser profiles and extracted
# trees. Playwright is pinned and installed once into $MEMORY_GAME_VERIFY_HOME (default
# ~/.cache/memory-game-verify), never into the repo; Chromium comes from Playwright's own cache.
set -euo pipefail

PILLOW_VERSION=12.3.0
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
# shellcheck source=playwright.sh
source "$HERE/playwright.sh"
SERVERS=()
trap 'for p in "${SERVERS[@]+"${SERVERS[@]}"}"; do kill "$p" 2>/dev/null || true; done' EXIT

die() { echo "verify: $*" >&2; exit 2; }
abspath() { python3 -I -c 'import os, sys; print(os.path.abspath(sys.argv[1]))' "$1"; }

cmd="${1:-}"
shift || true
OUT="" TREE="" ARGS=()
while (($#)); do
  case "$1" in
    --out) OUT="$(abspath "$2")"; shift 2 ;;
    --tree) TREE="$(abspath "$2")"; shift 2 ;;
    -h|--help) sed -n '2,23p' "$0"; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
case "$cmd" in local|compare|upgrade|live) ;; *) sed -n '2,23p' "$0"; exit 2 ;; esac
[[ -n "$OUT" ]] || die "--out <dir> is required"
case "$OUT/" in "$REPO"/*) die "--out must be outside the repo ($REPO)" ;; esac
mkdir -p "$OUT"

# tree_of <ref>: a directory holding that commit's files (the working tree for ".").
tree_of() {
  if [[ "$1" == "." ]]; then echo "$REPO"; return; fi
  local sha dir
  sha="$(git -C "$REPO" rev-parse --verify --quiet --short=12 "$1^{commit}")" || die "unknown commit $1"
  dir="$OUT/trees/$sha"
  if [[ ! -d "$dir" ]]; then
    rm -rf "$dir.part" && mkdir -p "$dir.part"
    git -C "$REPO" archive "$sha" | tar -x -C "$dir.part"
    mv "$dir.part" "$dir"
  fi
  echo "$dir"
}

label_of() { if [[ "$1" == "." ]]; then echo worktree; else git -C "$REPO" rev-parse --short=12 "$1^{commit}"; fi; }

free_port() { python3 -I -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])'; }

# serve <dir>: serve.py on a free port; sets PORT.
serve() {
  PORT="$(free_port)"
  python3 -I "$HERE/serve.py" "$PORT" "$1" >"$OUT/serve-$PORT.log" 2>&1 &
  SERVERS+=("$!")
  for _ in $(seq 50); do
    curl -fsS -o /dev/null "http://127.0.0.1:$PORT/" 2>/dev/null && return 0
    sleep 0.1
  done
  die "serve.py did not start on $PORT"
}

# drive <out-dir> <base-url> <games>: the seeded screenshots at both tablet sizes, then the audio game.
drive() {
  node "$HERE/drive.js" "$1" "$2" --games "$3" --vps tab-portrait,tab-landscape --modes shots --reduced off
  node "$HERE/drive.js" "$1" "$2" --games "$3" --vps tab-portrait --modes audio
}

GAMES=()
pick_games() {
  local root="$1"
  shift
  if (($#)); then GAMES=("$@"); else
    GAMES=()
    while IFS= read -r g; do GAMES+=("$g"); done < <(python3 -I "$root/_memory-game/tools/page/build_page.py" list)
  fi
  ((${#GAMES[@]})) || die "no games"
}

csv() { local IFS=,; echo "$*"; }

case "$cmd" in
  local)
    root="${TREE:-$REPO}"
    pick_games "$root" "${ARGS[@]+"${ARGS[@]}"}"
    setup_playwright
    dir="$OUT/local"
    rm -rf "$dir" && mkdir -p "$dir"
    status=0
    python3 -I "$root/_memory-game/tools/page/build_page.py" assemble --check | tee "$dir/assemble-check.txt" || status=1
    serve "$root"
    base="http://127.0.0.1:$PORT/"
    drive "$dir" "$base" "$(csv "${GAMES[@]}")"
    node "$HERE/drive.js" "$dir" "$base" --games "$(csv "${GAMES[@]}")" --vps tab-portrait,tab-landscape --modes quiz
    pids=()
    for g in "${GAMES[@]}"; do
      node "$HERE/sw_check.js" "$base" "$g" "$dir" >"$dir/sw-$g.txt" 2>&1 &
      pids+=("$!")
      node "$HERE/states/scenarios.js" "$root/$g/index.html" >"$dir/states-$g.txt" 2>&1 || true
    done
    for p in "${pids[@]}"; do wait "$p" || true; done
    python3 -I "$HERE/report.py" "$dir" "${GAMES[@]}" || status=1
    echo "verify local: $([[ $status == 0 ]] && echo PASS || echo FAIL) (assemble --check: $(grep -c 'up to date' "$dir/assemble-check.txt") up to date; outputs in $dir)"
    exit "$status"
    ;;
  compare)
    ((${#ARGS[@]} >= 2)) || die "compare needs two refs"
    ref_a="${ARGS[0]}" ref_b="${ARGS[1]}"
    tree_a="$(tree_of "$ref_a")"
    tree_b="$(tree_of "$ref_b")"
    pick_games "$tree_b" "${ARGS[@]:2}"
    setup_playwright
    a="$OUT/compare/$(label_of "$ref_a")" b="$OUT/compare/$(label_of "$ref_b")"
    rm -rf "$a" "$b" "$OUT/compare/diffs"
    serve "$tree_a"
    drive "$a" "http://127.0.0.1:$PORT/" "$(csv "${GAMES[@]}")"
    serve "$tree_b"
    drive "$b" "http://127.0.0.1:$PORT/" "$(csv "${GAMES[@]}")"
    uv run --quiet --with "pillow==$PILLOW_VERSION" python -I "$HERE/compare.py" "$a" "$b" --diffs "$OUT/compare/diffs" \
      | tee "$OUT/compare/compare.txt"
    ;;
  upgrade)
    ((${#ARGS[@]} >= 2)) || die "upgrade needs two refs"
    tree_old="$(tree_of "${ARGS[0]}")"
    tree_new="$(tree_of "${ARGS[1]}")"
    pick_games "$tree_new" "${ARGS[@]:2}"
    setup_playwright
    rm -rf "$OUT/upgrade"
    node "$HERE/sim.js" "$OUT/upgrade" "$tree_old" "$tree_new" "$(free_port)" "${GAMES[@]}"
    ;;
  live)
    pick_games "$REPO" "${ARGS[@]+"${ARGS[@]}"}"
    setup_playwright
    LIVE_BASE="$(python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import build_page; print(build_page.SITE)' \
      "$REPO/_memory-game/tools/page")"
    mkdir -p "$OUT/live"
    status=0
    all=()
    while IFS= read -r g; do all+=("$g"); done < <(python3 -I "$REPO/_memory-game/tools/page/build_page.py" list)
    for g in "${GAMES[@]}"; do
      others=()
      for o in "${all[@]}"; do [[ "$o" == "$g" ]] || others+=("$o"); done
      python3 -I "$HERE/live_files.py" "$REPO" "$g" "${others[@]+"${others[@]}"}" || status=1
      version="$(sed -n "s/^const VERSION = '\(.*\)';$/\1/p" "$REPO/$g/sw.js")"
      node "$HERE/sw_check.js" "$LIVE_BASE" "$g" "$OUT/live" "$version" >"$OUT/live/sw-$g.txt" 2>&1 || status=1
      python3 -I "$HERE/report.py" "$OUT/live" "$g" --worker-only || status=1
    done
    exit "$status"
    ;;
esac
