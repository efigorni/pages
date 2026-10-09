#!/usr/bin/env bash
# Render a game's PWA icons from its two SVGs (icon-any.svg, icon-maskable.svg).
#
# usage: render_icons.sh --game <game>          its tools/page/icons/*.svg into its icons/
#        render_icons.sh <svg-dir> <out-dir>
#   CHROME=<chrome binary>  overrides the macOS default below.
#
# Headless Chrome won't render a window narrower than ~500 px, so both icons are
# rendered at 512 and the small sizes are downscaled with Pillow.
set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
if [[ "${1:-}" == "--game" ]]; then
  set -- "${2:?usage: render_icons.sh --game <game>}/tools/page/icons" "$2/icons"
fi
svgs="$(cd "${1:?usage: render_icons.sh --game <game> | <svg-dir> <out-dir>}" && pwd)"
out="${2:?usage: render_icons.sh --game <game> | <svg-dir> <out-dir>}"
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
# Lossless (the same pixels in fewer bytes): every install precaches them.
uv run --quiet --with pyoxipng==9.1.1 python -I -c \
  'import oxipng, sys; [oxipng.optimize(f, level=6, deflate=oxipng.Deflaters.zopfli(15)) for f in sys.argv[1:]]' "$out"/*.png
echo "icons written to $out"
