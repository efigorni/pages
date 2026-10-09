#!/usr/bin/env bash
# Renders each game's link-preview image, <game>/og.jpg (og.js: the game's start screen at 1200x630 with
# three starters' faces), with the verify harness's pinned Playwright. Run it after a roster refresh or a
# change to a club's look, LOOK at the images, then commit them.
#
#   _memory-game/tools/og/render_og.sh [<game>...]      (default: every game, `build_page.py list`)
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"  # no git needed: refresh.sh runs it in scratch copies too
# shellcheck source=../verify/playwright.sh
source "$HERE/../verify/playwright.sh"

games=("$@")
if ((${#games[@]} == 0)); then
  while IFS= read -r g; do games+=("$g"); done < <(python3 -I "$REPO/_memory-game/tools/page/build_page.py" list)
fi
setup_playwright
for g in "${games[@]}"; do
  node "$HERE/og.js" "$REPO" "$g"
done
