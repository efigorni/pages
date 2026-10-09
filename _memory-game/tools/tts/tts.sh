#!/usr/bin/env bash
# A game's voice clips with the shared engine install, from the repo root:
#
#   tts.sh <game> <work> generate [--stale] [generate.py options]   render into <work>/tts/out
#   tts.sh <game> <work> check                                      every roster clip there, passing, in spec
#   tts.sh <game> <work> sync                                       check, then copy the clips into <game>/audio/
#   tts.sh <game> <work> ab --ids ID,ID [--cand ID:LABEL=IPA ...] [--seeds 6] [--fw]
#   tts.sh <game> <work> listen [--alt ID=LABEL:IPA ...]            <work>/tts/listen.html, to judge by ear
#   tts.sh <game> <work> g2p [TEXT [target_speaker]]                G2P next to the pin for every roster name
#
# <work> holds data/players.json (the scrape) and tts/ (takes, QA, out/). The engine install is found
# as config.py says (default ~/.cache/memory-game-tts; `setup.sh --install` makes it). A roster refresh:
# generate --stale, listen for every new or changed name, check, sync.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
(($# >= 3)) || { sed -n '2,14p' "$0"; exit 2; }
game="$1" work="$2" cmd="$3"
shift 3
paths="$(python3 -I -B - "$HERE" "$game" "$work" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import config
work = config.work_dir(sys.argv[3])
print(config.engines_home(None, config.tts_home(work)))
print(config.game_dir(sys.argv[2]))
print(work)
PY
)"
{ read -r engines; read -r game; read -r work; } <<<"$paths"
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 MEMORY_GAME_TTS_ENGINES="$engines"
stt="$engines/.venv-stt/bin/python"
blue="$engines/.venv-blue/bin/python"
case "$cmd" in
  generate) exec "$stt" -u "$HERE/generate.py" --game "$game" --work "$work" "$@" ;;
  check|sync) exec "$stt" -u "$HERE/clips.py" "$cmd" --game "$game" --work "$work" "$@" ;;
  ab) exec "$stt" -u "$HERE/ab_ipa.py" --game "$game" --work "$work" "$@" ;;
  listen) exec "$stt" -u "$HERE/make_listen.py" --game "$game" --work "$work" "$@" ;;
  g2p)
    if (($#)); then exec "$blue" "$HERE/render_blue.py" --g2p "$@"; fi
    exec "$blue" "$HERE/render_blue.py" --g2p-roster "$work/data/players.json" "$game/tools/tts/pronunciations.json" ;;
  *) echo "tts.sh: unknown command $cmd" >&2; exit 2 ;;
esac
