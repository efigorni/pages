#!/usr/bin/env bash
# The memory games' browser checks (Playwright + Chromium), run from a checkout of the repo.
#
#   verify.sh sanity  [--from <ref>] [--tree <dir>] [<game>...]
#       The PR gate: every game at once, in parallel, headless, at 600x960 touch, in about a minute.
#       assemble --check (the builder's lints) and the format of every shipped clip; per game, no
#       console error and no 404; the worker controls the page, three flips and matches say their
#       clips, installability []; an offline reload keeps what she learned, shows the pictures, plays
#       cached clips, asks a quiz question and opens the next new flash card; the quiz's first
#       question with a wrong and a right pick and their clips; the state machine (the new-first
#       deal, the learned-only quiz, flash cards); a quick upgrade from <ref> (default origin/main),
#       online then offline, for the games there. Serves the working tree, or --tree <dir>.
#   verify.sh live    [<game>...]        (or: sanity --live)
#       After a merge: every deployed precached file, then sanity's browser checks on the live site.
#   verify.sh full    [--from <ref>] [<game>...]
#       Only for a deliberate engine-wide behaviour refactor, or on request: local, then compare and
#       upgrade from <ref> (default origin/main) for the games there.
#   verify.sh local   [--tree <dir>] [<game>...]
#       P9: assemble --check; seeded start/mid/win screenshots at 600x960 and 960x600; one audio
#       playthrough (the right clip on every flip); a whole quiz at both sizes (every player once, a
#       wrong pick, the clips, question/wrong/reveal/end screenshots); the worker online, offline
#       (memory and quiz) and installable; the state machine. Serves the working tree, or --tree <dir>.
#   verify.sh compare <ref-a> <ref-b> [<game>...]
#       The same seeded screenshots, playthrough and quiz on two commits: pixels, DOM, the computed HUD
#       styles, the clip sequences and the quiz's questions must all match.
#   verify.sh upgrade <old-ref> <new-ref> [<game>...]
#       The GitHub Pages upgrade under /pages/ (sim.js): the old version installed, the new one
#       taking over online, then offline.
#
# <game> defaults to every game (`build_page.py list`); <ref> is a commit, or `.` for the working
# tree. --out <dir> (default: one folder per checkout under $TMPDIR) must be outside the repo: it gets
# the screenshots, browser profiles and extracted trees. MEMORY_GAME_VERIFY_PORTS ("8801-8804" or
# "8801 8802") pins the test servers' ports for concurrent runs on one machine; sanity takes one more
# than the games it upgrades. Playwright is pinned and installed once into $MEMORY_GAME_VERIFY_HOME
# (default ~/.cache/memory-game-verify), never into the repo; Chromium comes from Playwright's own cache.
set -euo pipefail

PILLOW_VERSION=12.3.0
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(git -C "$HERE" rev-parse --show-toplevel)"
# shellcheck source=playwright.sh
source "$HERE/playwright.sh"
SERVERS=()
trap 'for p in "${SERVERS[@]+"${SERVERS[@]}"}"; do kill "$p" 2>/dev/null || true; done' EXIT

die() { echo "verify: $*" >&2; exit 2; }
usage() { sed -n '2,/^set -euo/p' "$0" | sed '$d'; }
abspath() { python3 -I -c 'import os, sys; print(os.path.abspath(sys.argv[1]))' "$1"; }

cmd="${1:-}"
shift || true
OUT="" TREE="" FROM="origin/main" LIVE=0 ARGS=()
while (($#)); do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --tree) TREE="$(abspath "$2")"; shift 2 ;;
    --from) FROM="$2"; shift 2 ;;
    --live) LIVE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) ARGS+=("$1"); shift ;;
  esac
done
case "$cmd" in sanity|live|full|local|compare|upgrade) ;; *) usage; exit 2 ;; esac
if [[ "$cmd" == live ]]; then cmd=sanity LIVE=1; fi
OUT="$(abspath "${OUT:-${TMPDIR:-/tmp}/memory-game-verify-$(printf '%s' "$REPO" | cksum | cut -d' ' -f1)}")"
case "$OUT/" in "$REPO"/*) die "--out must be outside the repo ($REPO)" ;; esac
mkdir -p "$OUT"

PORTS=()
if [[ "${MEMORY_GAME_VERIFY_PORTS:-}" =~ ^([0-9]+)-([0-9]+)$ ]]; then
  for ((p = BASH_REMATCH[1]; p <= BASH_REMATCH[2]; p++)); do PORTS+=("$p"); done
elif [[ -n "${MEMORY_GAME_VERIFY_PORTS:-}" ]]; then
  read -ra PORTS <<<"${MEMORY_GAME_VERIFY_PORTS//,/ }"
fi
NEXT_PORT=0

# take_port: sets PORT to the next pinned port, or to a free one.
take_port() {
  if ((${#PORTS[@]})); then
    ((NEXT_PORT < ${#PORTS[@]})) || die "MEMORY_GAME_VERIFY_PORTS has ${#PORTS[@]} ports, too few for this run"
    PORT="${PORTS[NEXT_PORT]}"
    NEXT_PORT=$((NEXT_PORT + 1))
  else
    PORT="$(python3 -I -c 'import socket; s = socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1])')"
  fi
}

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

# serve <dir>: serve.py on the next port; sets PORT.
serve() {
  take_port
  if curl -s -o /dev/null "http://127.0.0.1:$PORT/" 2>/dev/null; then die "port $PORT is already in use"; fi
  python3 -I "$HERE/serve.py" "$PORT" "$1" >"$OUT/serve-$PORT.log" 2>&1 &
  SERVERS+=("$!")
  for _ in $(seq 50); do
    kill -0 "$!" 2>/dev/null || die "serve.py could not listen on $PORT (see $OUT/serve-$PORT.log)"
    curl -fsS -o /dev/null "http://127.0.0.1:$PORT/" 2>/dev/null && return 0
    sleep 0.1
  done
  die "serve.py did not start on $PORT"
}

# drive <out-dir> <base-url> <games>: the seeded screenshots at both tablet sizes, the audio game, then
# the quiz at both sizes.
drive() {
  node "$HERE/drive.js" "$1" "$2" --games "$3" --vps tab-portrait,tab-landscape --modes shots --reduced off
  node "$HERE/drive.js" "$1" "$2" --games "$3" --vps tab-portrait --modes audio
  node "$HERE/drive.js" "$1" "$2" --games "$3" --vps tab-portrait,tab-landscape --modes quiz
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

# on_ref <tree>: sets UPGRADED to the GAMES that exist in that tree (the ones an upgrade can start from).
on_ref() {
  UPGRADED=()
  for g in "${GAMES[@]}"; do if [[ -f "$1/$g/sw.js" ]]; then UPGRADED+=("$g"); fi; done
}

csv() { local IFS=,; echo "$*"; }

# job <name> <command...>: a background job logging to $dir/<name>.txt. finish waits for every job,
# saying when each ends, and fails the run on a job that exits non-zero.
NAMES=() PIDS=()
job() { local name="$1"; shift; "$@" >"$dir/$name.txt" 2>&1 & NAMES+=("$name"); PIDS+=("$!"); }
finish() {
  local left=${#PIDS[@]} i rc seen=()
  while ((left)); do
    for i in "${!PIDS[@]}"; do
      if [[ -n "${seen[$i]:-}" ]] || kill -0 "${PIDS[$i]}" 2>/dev/null; then continue; fi
      seen[i]=1 left=$((left - 1)) rc=0
      wait "${PIDS[$i]}" || rc=$?
      if ((rc == 0)); then say "${NAMES[$i]} finished"; else
        status=1
        say "${NAMES[$i]} FAILED (exit $rc), the end of $dir/${NAMES[$i]}.txt:"
        tail -n 8 "$dir/${NAMES[$i]}.txt" | cut -c1-240 | sed 's/^/    /'
      fi
    done
    if ((left)); then sleep 1; fi
  done
  NAMES=() PIDS=()
}

case "$cmd" in
  sanity)
    t0=$SECONDS
    say() { printf 'sanity %4ss: %s\n' "$((SECONDS - t0))" "$*"; }
    root="${TREE:-$REPO}"
    pick_games "$root" "${ARGS[@]+"${ARGS[@]}"}"
    dir="$OUT/$(if ((LIVE)); then echo live; else echo sanity; fi)"
    rm -rf "$dir" && mkdir -p "$dir"
    status=0 UPGRADED=()
    say "$(if ((LIVE)); then echo "the live site"; else echo "$root"; fi): ${GAMES[*]}"
    if ((!LIVE)); then
      if python3 -I "$root/_memory-game/tools/page/build_page.py" assemble --check >"$dir/assemble-check.txt" 2>&1; then
        say "assemble --check PASS ($(grep -c 'up to date' "$dir/assemble-check.txt") up to date)"
      else
        status=1
        say "assemble --check FAIL:"
        { grep -v ': up to date' "$dir/assemble-check.txt" || true; } | sed 's/^/    /'
      fi
      if python3 -I "$root/_memory-game/tools/tts/clips.py" format "${GAMES[@]/#/$root/}" >"$dir/clips.txt" 2>&1; then
        say "clip format PASS ($(sed -n 's/^\[format\] \(.* clips in .*\): OK$/\1/p' "$dir/clips.txt"))"
      else
        status=1
        say "clip format FAIL:"
        sed 's/^/    /' "$dir/clips.txt"
      fi
    fi
    setup_playwright
    if ((LIVE)); then
      base="$(python3 -I -c 'import sys; sys.path.insert(0, sys.argv[1]); import build_page; print(build_page.SITE)' \
        "$REPO/_memory-game/tools/page")"
      all=()
      while IFS= read -r g; do all+=("$g"); done < <(python3 -I "$REPO/_memory-game/tools/page/build_page.py" list)
      for g in "${GAMES[@]}"; do
        others=()
        for o in "${all[@]}"; do if [[ "$o" != "$g" ]]; then others+=("$o"); fi; done
        job "files-$g" python3 -I "$HERE/live_files.py" "$REPO" "$g" "${others[@]+"${others[@]}"}"
      done
      say "waiting for the deploy, then fetching every precached file"
      finish
      for g in "${GAMES[@]}"; do sed -n "s/^\($g: VERSION .*\)/    \1/p" "$dir/files-$g.txt"; done
    else
      serve "$root"
      base="http://127.0.0.1:$PORT/"
      old="$(tree_of "$FROM")"
      on_ref "$old"
      for g in "${UPGRADED[@]+"${UPGRADED[@]}"}"; do
        take_port
        job "upgrade-$g" node "$HERE/sim.js" "$dir/upgrade/$g" "$old" "$root" "$PORT" --quick "$g"
      done
      for g in "${GAMES[@]}"; do job "states-$g" node "$HERE/states/scenarios.js" "$root/$g/index.html"; done
    fi
    job quiz node "$HERE/drive.js" "$dir" "$base" --games "$(csv "${GAMES[@]}")" --vps tab-portrait --modes quiz --questions 1
    for g in "${GAMES[@]}"; do
      want=""
      if ((LIVE)); then want="$(sed -n "s/^const VERSION = '\(.*\)';$/\1/p" "$REPO/$g/sw.js")"; fi
      job "worker-$g" node "$HERE/sw_check.js" "$base" "$g" "$dir" ${want:+"$want"}
    done
    say "running: the worker per game, the quiz$(((LIVE)) || echo ", the state machine")${UPGRADED[0]:+, the upgrade from $FROM per game on it}"
    finish
    rep=(--sanity)
    if ((${#UPGRADED[@]})); then rep+=(--upgraded "$(csv "${UPGRADED[@]}")" --from "$FROM"); fi
    python3 -I "$HERE/report.py" "$dir" "${GAMES[@]}" "${rep[@]}" >"$dir/report.txt" 2>&1 || status=1
    if grep -q '^sanity ' "$dir/report.txt"; then grep '^sanity ' "$dir/report.txt"; else sed 's/^/    /' "$dir/report.txt"; fi
    echo "verify $(if ((LIVE)); then echo live; else echo sanity; fi): $(if ((status)); then echo FAIL; else echo PASS; fi)" \
      "in $((SECONDS - t0)) s (${#GAMES[@]} games; the report and outputs in $dir)"
    exit "$status"
    ;;
  full)
    pick_games "$REPO" "${ARGS[@]+"${ARGS[@]}"}"
    on_ref "$(tree_of "$FROM")"
    status=0
    "$HERE/verify.sh" local --out "$OUT" "${GAMES[@]}" || status=1
    if ((${#UPGRADED[@]})); then
      "$HERE/verify.sh" compare "$FROM" . --out "$OUT" "${UPGRADED[@]}" || status=1
      "$HERE/verify.sh" upgrade "$FROM" . --out "$OUT" "${UPGRADED[@]}" || status=1
    fi
    echo "verify full: $(if ((status)); then echo FAIL; else echo PASS; fi) (outputs in $OUT)"
    exit "$status"
    ;;
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
    take_port
    node "$HERE/sim.js" "$OUT/upgrade" "$tree_old" "$tree_new" "$PORT" "${GAMES[@]}"
    ;;
esac
