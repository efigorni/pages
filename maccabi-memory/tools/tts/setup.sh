#!/usr/bin/env bash
# One-time, idempotent setup for the Maccabi memory-game voice clips.
#
#   tools/tts/setup.sh            # winner engine (BlueTTS) + STT check tools
#   tools/tts/setup.sh --all      # also the runner-up (Phonikud + Piper) for comparison samples
#
# Everything lands under $MACCABI_TTS_HOME (default $MACCABI_WORK/tts, where
# $MACCABI_WORK defaults to the current directory):
#   _engines/BlueTTS   pinned clone of github.com/maxmelichov/BlueTTS + its ONNX bundle
#   .venv-blue         BlueTTS + RenikudPlus G2P (Python 3.12)
#   .venv-stt          numpy + faster-whisper (orchestrator, metrics, second-opinion STT)
#   .venv-phonikud     phonikud-tts (Piper) — only with --all
# Models go to the normal Hugging Face cache. Needs: uv, git, ffmpeg, whisper-cli
# (brew install uv ffmpeg whisper-cpp). No sudo, no global pip.
set -euo pipefail

TTS="${MACCABI_TTS_HOME:-${MACCABI_WORK:-$PWD}/tts}"
BLUE_COMMIT=0e38dbf08ed53f85863d1eab092bd9572c53a503   # BlueTTS main, 2026-08-13
ALL=0; [[ "${1:-}" == "--all" ]] && ALL=1

for tool in uv git ffmpeg whisper-cli; do
  command -v "$tool" >/dev/null || { echo "missing $tool — brew install ${tool/whisper-cli/whisper-cpp}"; exit 1; }
done
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
"$TTS/.venv-blue/bin/python" -c "from renikud_onnx import G2P; print(G2P().phonemize('שלום'))"

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
echo "[setup] done — next: $TTS/.venv-stt/bin/python $(dirname "$0")/generate.py --work $(dirname "$TTS")"
