"""Round-trip STT with a local ivrit.ai Whisper (whisper.cpp + Metal).

Model: ivrit-ai/whisper-large-v3-turbo-ggml from the HF cache, run by the
Homebrew `whisper-cli`. No prompt is passed: prompting with the expected text
would bias the check toward passing.

    python3 stt.py a.wav b.mp3 ...        # prints one JSON object per file

Returns text plus token-probability stats: mean_p (over text tokens) is a usable
proxy for "how clearly Israeli Hebrew this sounds to an Israeli-Hebrew model";
min_p points at the doubtful syllable.
"""
from __future__ import annotations

import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HF = Path(os.environ.get("HF_HUB_CACHE")
          or Path(os.environ.get("HF_HOME") or Path.home() / ".cache/huggingface") / "hub")
MODELS = {
    "turbo": "models--ivrit-ai--whisper-large-v3-turbo-ggml/snapshots/*/ggml-model.bin",
}


def model_path(name: str = "turbo") -> str:
    hits = sorted(glob.glob(str(HF / MODELS[name])))
    if not hits:
        raise SystemExit(
            "ivrit.ai GGML model missing: hf download ivrit-ai/whisper-large-v3-turbo-ggml"
        )
    return hits[-1]


def _to_16k(src: str, dst: str) -> None:
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", src,
         "-af", "apad=pad_dur=0.3", "-ar", "16000", "-ac", "1", dst],
        check=True,
    )


def transcribe(paths: list[str], model: str = "turbo", threads: int = 8) -> list[dict]:
    """Transcribe many clips in one whisper-cli process (model loads once)."""
    if not paths:
        return []
    exe = shutil.which("whisper-cli")
    if not exe:
        raise SystemExit("whisper-cli not found: brew install whisper-cpp")
    tmp = tempfile.mkdtemp(prefix="stt_")
    try:
        wavs = []
        for i, p in enumerate(paths):
            w = os.path.join(tmp, f"{i:05d}.wav")
            _to_16k(p, w)
            wavs.append(w)
        cmd = [exe, "-m", model_path(model), "-l", "he", "-t", str(threads),
               "-np", "-ojf", "-bs", "5", "-bo", "5"] + wavs
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        out = []
        for p, w in zip(paths, wavs):
            with open(w + ".json", encoding="utf-8") as f:
                d = json.load(f)
            text = "".join(s["text"] for s in d.get("transcription", [])).strip()
            probs = [
                t["p"]
                for s in d.get("transcription", [])
                for t in s.get("tokens", [])
                if not t["text"].startswith("[_")
            ]
            out.append({
                "file": p,
                "text": text,
                "mean_p": round(sum(probs) / len(probs), 4) if probs else 0.0,
                "min_p": round(min(probs), 4) if probs else 0.0,
                "tokens": [
                    (t["text"], round(t["p"], 3))
                    for s in d.get("transcription", [])
                    for t in s.get("tokens", [])
                    if not t["text"].startswith("[_")
                ],
            })
        return out
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    for r in transcribe(sys.argv[1:]):
        print(json.dumps(r, ensure_ascii=False), flush=True)
