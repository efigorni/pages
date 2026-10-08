#!/usr/bin/env bash
# Everything after the scrape, for one game, from the repo root:
#
#   _memory-game/tools/refresh.sh <game> <work>
#
# <work>/data/players.json is the club scraper's output (see <game>/tools/README.md). In order:
#   1. photos      build_images.py --game (mode, fade and sheet colours from <game>/club/club.json);
#                  look at <work>/crops.png
#   2. pins        stops here when a starter or bench player has no pinned IPA in
#                  <game>/tools/tts/pronunciations.json: listen first (tts.sh g2p, ab, listen), pin, rerun
#   3. voice       tts.sh generate --stale (only new or changed clips), check, sync into <game>/audio/
#   4. page        build_page.py data, then assemble --check for every game
# Then test it (_memory-game/tools/verify/verify.sh local) and commit with explicit paths.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
(($# == 2)) || { sed -n '2,14p' "$0"; exit 2; }
game="${1%/}" work="$2"
[[ -f "$work/data/players.json" ]] || { echo "refresh: no $work/data/players.json (run the club's scraper)"; exit 1; }

echo "== photos"
uv run --quiet --with pillow python -I "$here/images/build_images.py" --game "$game" --work "$work"

echo "== pins"
unpinned="$(python3 -I - "$work/data/players.json" "$game/tools/tts/pronunciations.json" <<'PY'
import json, sys
pins = json.load(open(sys.argv[2], encoding="utf-8"))["players"]
print(" ".join(p["id"] for p in json.load(open(sys.argv[1], encoding="utf-8"))["players"]
               if p.get("role") in ("starter", "bench") and not pins.get(p["id"], {}).get("ipa")))
PY
)"
if [[ -n "$unpinned" ]]; then
  echo "refresh: no pinned IPA yet for: $unpinned"
  echo "  see what G2P says:   $here/tts/tts.sh $game $work g2p"
  echo "  compare candidates:  $here/tts/tts.sh $game $work ab --ids <id> --cand <id>:<label>=<ipa>"
  echo "  pin each in $game/tools/tts/pronunciations.json, then run refresh.sh again"
  exit 1
fi

echo "== voice"
"$here/tts/tts.sh" "$game" "$work" generate --stale --takes 8 --second-opinion
"$here/tts/tts.sh" "$game" "$work" check
"$here/tts/tts.sh" "$game" "$work" sync

echo "== page"
python3 -I "$here/page/build_page.py" data "$work/data/players.json" "$game"
python3 -I "$here/page/build_page.py" assemble --check
echo "refresh: $game is ready to test (_memory-game/tools/verify/verify.sh local --out <dir> $game)"
