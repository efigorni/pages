#!/usr/bin/env bash
# One-time, idempotent setup for the memory games' voice clips.
#
#   MACCABI_ROOT=<work> _memory-game/tools/tts/setup.sh           # reuse a working BlueTTS install, else install
#   MACCABI_ROOT=<work> _memory-game/tools/tts/setup.sh --fresh   # install under $MACCABI_TTS_HOME regardless
#   ... setup.sh --all     also the runner-up engine (Phonikud + Piper) for generate.py --engine piper
#
# <work> is the scratch directory outside the repo that holds data/ and tts/.
# An engine home holds:
#   _engines/BlueTTS   pinned clone of github.com/maxmelichov/BlueTTS + its ONNX bundle
#   .venv-blue         BlueTTS + RenikudPlus G2P (Python 3.12)
#   .venv-stt          numpy + faster-whisper (orchestrator, metrics, second-opinion STT)
#   .venv-phonikud     phonikud-tts (Piper), only with --all
# Lookup order (generate.py uses the same): $MACCABI_TTS_ENGINES (e.g. an install another
# project already made), then $MACCABI_TTS_HOME (default $MACCABI_ROOT/tts).
# The first that passes the check is used as is: it is only run (no bytecode, offline
# Hugging Face), never modified. If none passes, a fresh install goes to $MACCABI_TTS_HOME.
# Models live in the Hugging Face cache ($HF_HUB_CACHE, else $HF_HOME/hub, else
# ~/.cache/huggingface/hub). Needs: uv, git, ffmpeg, whisper-cli
# (brew install uv ffmpeg whisper-cpp). No sudo, no global pip.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="${MACCABI_ROOT:?set MACCABI_ROOT to the work directory (outside the repo) that holds data/ and tts/}"
TTS="${MACCABI_TTS_HOME:-$ROOT/tts}"
HF_CACHE="${HF_HUB_CACHE:-${HF_HOME:-$HOME/.cache/huggingface}/hub}"
BLUE_COMMIT=0e38dbf08ed53f85863d1eab092bd9572c53a503   # BlueTTS main, 2026-08-13
FRESH=0
ALL=0
for arg in "$@"; do
  case "$arg" in
    --fresh) FRESH=1 ;;
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

if (( ! FRESH )); then
  for e in ${MACCABI_TTS_ENGINES:-} "$TTS"; do
    [[ -d "$e" ]] || continue
    echo "[setup] checking $e"
    if check "$e" 2>/dev/null; then
      echo "[setup] reusing $e — nothing installed or changed"
      [[ "$e" == "$TTS" ]] || echo "[setup] keep MACCABI_TTS_ENGINES=$e exported for generate.py"
      echo "[setup] next: $e/.venv-stt/bin/python -u $HERE/generate.py --pron <game>/tools/tts/pronunciations.json"
      exit 0
    fi
    echo "[setup]   not usable"
  done
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
echo "[setup] done — next: $TTS/.venv-stt/bin/python -u $HERE/generate.py --pron <game>/tools/tts/pronunciations.json"
