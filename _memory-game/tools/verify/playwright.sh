# Sourced by verify.sh and tools/og/render_og.sh: Playwright pinned, installed once into
# $MEMORY_GAME_VERIFY_HOME (default ~/.cache/memory-game-verify), never into the repo; Chromium comes from
# Playwright's own cache. setup_playwright installs it when the pinned version is missing and exports
# NODE_PATH for the node scripts.
PLAYWRIGHT_VERSION=1.64.0

setup_playwright() {
  local home="${MEMORY_GAME_VERIFY_HOME:-${XDG_CACHE_HOME:-$HOME/.cache}/memory-game-verify}" have=""
  if [[ -f "$home/node_modules/playwright/package.json" ]]; then
    have="$(node -p "require(process.argv[1]).version" "$home/node_modules/playwright/package.json")"
  fi
  if [[ "$have" != "$PLAYWRIGHT_VERSION" ]]; then
    echo "verify: installing playwright@$PLAYWRIGHT_VERSION into $home"
    mkdir -p "$home"
    npm install --prefix "$home" --no-audit --no-fund --loglevel=error "playwright@$PLAYWRIGHT_VERSION"
  fi
  "$home/node_modules/.bin/playwright" install chromium >/dev/null
  export NODE_PATH="$home/node_modules"
}
