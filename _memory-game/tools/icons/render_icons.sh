#!/usr/bin/env bash
# Render a game's PWA icons from its two SVGs (icon-any.svg, icon-maskable.svg).
#
# usage: render_icons.sh <svg-dir> <out-dir>
#   e.g. render_icons.sh maccabi-memory/tools/page/icons maccabi-memory/icons
#   CHROME=<chrome binary>  overrides the macOS default below.
#
# Headless Chrome won't render a window narrower than ~500 px, so both icons are
# rendered at 512 and the small sizes are downscaled with Pillow.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
svgs="$(cd "${1:?usage: render_icons.sh <svg-dir> <out-dir>}" && pwd)"
out="${2:?usage: render_icons.sh <svg-dir> <out-dir>}"
chrome="${CHROME:-/Applications/Google Chrome.app/Contents/MacOS/Google Chrome}"
profile="$(mktemp -d)"
trap 'rm -rf "$profile"' EXIT
mkdir -p "$out"

shot() {
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --user-data-dir="$profile" \
    --default-background-color=00000000 --window-size=512,512 \
    --screenshot="$2" "file://$svgs/$1" >/dev/null 2>&1
}

shot icon-any.svg "$out/icon-512.png"
shot icon-maskable.svg "$out/icon-maskable-512.png"
uv run --with pillow python -I "$here/resize_icon.py" "$out/icon-512.png" 192 "$out/icon-192.png"
uv run --with pillow python -I "$here/resize_icon.py" "$out/icon-maskable-512.png" 192 "$out/icon-maskable-192.png"
uv run --with pillow python -I "$here/resize_icon.py" "$out/icon-maskable-512.png" 180 "$out/apple-touch-icon.png"
echo "icons written to $out"
