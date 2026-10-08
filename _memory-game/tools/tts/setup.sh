#!/usr/bin/env bash
# The voice clips' engine install, shared by every game. Without --install it only reports.
#
#   _memory-game/tools/tts/setup.sh              is there a working install? (installs nothing)
#   _memory-game/tools/tts/setup.sh --install    install one into the engine home if there is none (~1 GB)
#   ... --all                                    also the runner-up engine (Phonikud + Piper), for --engine piper
#
# The engine home is $MEMORY_GAME_TTS_ENGINES (or the older $MACCABI_TTS_ENGINES), else
# ${XDG_CACHE_HOME:-~/.cache}/memory-game-tts: it belongs to no club, so every game uses the same one. It holds:
#   _engines/BlueTTS   pinned clone of github.com/maxmelichov/BlueTTS + its ONNX bundle
#   .venv-blue         BlueTTS + RenikudPlus G2P (Python 3.12)
#   .venv-stt          numpy + faster-whisper (orchestrator, metrics, second-opinion STT)
#   .venv-phonikud     phonikud-tts (Piper), only with --all
# A working install is only ever run (no bytecode, offline Hugging Face), never modified. Models
# live in the Hugging Face cache ($HF_HUB_CACHE, else $HF_HOME/hub, else ~/.cache/huggingface/hub).
# Needs: uv, git, ffmpeg, whisper-cli (brew install uv ffmpeg whisper-cpp). No sudo, no global pip.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
TTS="${MEMORY_GAME_TTS_ENGINES:-${MACCABI_TTS_ENGINES:-${XDG_CACHE_HOME:-$HOME/.cache}/memory-game-tts}}"
HF_CACHE="${HF_HUB_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}/hub}"
BLUE_COMMIT=0e38dbf08ed53f85863d1eab092bd9572c53a503   # BlueTTS main, 2026-08-13
INSTALL=0
ALL=0
for arg in "$@"; do
  case "$arg" in
    --install|--fresh) INSTALL=1 ;;
    --all) ALL=1 ;;
    *) echo "unknown option: $arg"; exit 2 ;;
  esac
done

for tool in uv git ffmpeg whisper-cli; do
  command -v "$tool" >/dev/null || { echo "missing $tool — brew install ${tool/whisper-cli/whisper-cpp}"; exit 1; }
done

# check <engine home>: exit 0 when BlueTTS (pinned commit, noa voice), RenikudPlus,
# faster-whisper and both ivrit.ai models all load (and, with --all, Phonikud + Piper),
# without writing anything.
check() {
  local e="$1"
  [[ -x "$e/.venv-blue/bin/python" && -x "$e/.venv-stt/bin/python" ]] || return 1
  [[ -f "$e/_engines/BlueTTS/onnx_models/vector_estimator.onnx" && -f "$e/_engines/BlueTTS/voices/noa.json" ]] || return 1
  [[ "$(git -C "$e/_engines/BlueTTS" rev-parse HEAD 2>/dev/null)" == "$BLUE_COMMIT" ]] || return 1
  PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 PYTHONPATH="$e/_engines/BlueTTS/src" \
    "$e/.venv-blue/bin/python" -c "import blue_onnx; from renikud_onnx import G2P; print('[setup]   G2P שלום ->', G2P().phonemize('שלום'))" || return 1
  PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 \
    "$e/.venv-stt/bin/python" -c "import numpy, faster_whisper; print('[setup]   faster-whisper', faster_whisper.__version__)" || return 1
  ls "$HF_CACHE"/models--ivrit-ai--whisper-large-v3-turbo-ggml/snapshots/*/ggml-model.bin >/dev/null 2>&1 || return 1
  ls -d "$HF_CACHE"/models--ivrit-ai--whisper-large-v3-ct2/snapshots/* >/dev/null 2>&1 || return 1
  if (( ALL )); then
    PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 "$e/.venv-phonikud/bin/python" -c "import phonikud_tts" || return 1
    ls "$HF_CACHE"/models--Phonikud--phonikud-tts-checkpoints/snapshots/*/shaul.onnx >/dev/null 2>&1 || return 1
  fi
}

echo "[setup] checking $TTS"
if [[ -d "$TTS" ]] && check "$TTS" 2>/dev/null; then
  echo "[setup] $TTS works — nothing installed or changed"
  echo "[setup] next: $HERE/tts.sh <game> <work> generate"
  exit 0
fi
if (( ! INSTALL )); then
  echo "[setup] no working install in $TTS. Install one there (about 1 GB: BlueTTS, two venvs, the models) with:"
  echo "        $0 --install"
  exit 1
fi

echo "[setup] fresh install under $TTS"
mkdir -p "$TTS/_engines"
echo "[setup] BlueTTS @ ${BLUE_COMMIT:0:8}"
if [[ ! -d "$TTS/_engines/BlueTTS/.git" ]]; then
  git clone https://github.com/maxmelichov/BlueTTS.git "$TTS/_engines/BlueTTS"
fi
git -C "$TTS/_engines/BlueTTS" fetch --quiet origin "$BLUE_COMMIT" 2>/dev/null || true
git -C "$TTS/_engines/BlueTTS" checkout --quiet "$BLUE_COMMIT"
(cd "$TTS/_engines/BlueTTS" && UV_PROJECT_ENVIRONMENT="$TTS/.venv-blue" uv sync --frozen)
if [[ ! -f "$TTS/_engines/BlueTTS/onnx_models/vector_estimator.onnx" ]]; then
  (cd "$TTS/_engines/BlueTTS" && UV_PROJECT_ENVIRONMENT="$TTS/.venv-blue" \
    uv run hf download notmax123/BlueTTS2.5-onnx --repo-type model --local-dir ./onnx_models)
fi
# RenikudPlus G2P weights (~310 MB) download on first use; warm them now.
PYTHONPATH="$TTS/_engines/BlueTTS/src" "$TTS/.venv-blue/bin/python" -c "from renikud_onnx import G2P; print(G2P().phonemize('שלום'))"

echo "[setup] STT + tooling venv"
[[ -x "$TTS/.venv-stt/bin/python" ]] || uv venv "$TTS/.venv-stt" --python 3.12
uv pip install --python "$TTS/.venv-stt/bin/python" faster-whisper numpy
"$TTS/.venv-stt/bin/hf" download ivrit-ai/whisper-large-v3-turbo-ggml ggml-model.bin >/dev/null
"$TTS/.venv-stt/bin/hf" download ivrit-ai/whisper-large-v3-ct2 >/dev/null

if (( ALL )); then
  echo "[setup] runner-up: Phonikud + Piper"
  [[ -x "$TTS/.venv-phonikud/bin/python" ]] || uv venv "$TTS/.venv-phonikud" --python 3.12
  uv pip install --python "$TTS/.venv-phonikud/bin/python" phonikud-tts "huggingface-hub[cli]"
  "$TTS/.venv-phonikud/bin/hf" download Phonikud/phonikud-onnx phonikud-1.0.int8.onnx >/dev/null
  "$TTS/.venv-phonikud/bin/hf" download Phonikud/phonikud-tts-checkpoints \
    model.onnx shaul.onnx michael.onnx model.config.json >/dev/null
fi
check "$TTS" || { echo "[setup] the fresh install does not pass the check"; exit 1; }
echo "[setup] done — next: $HERE/tts.sh <game> <work> generate"
