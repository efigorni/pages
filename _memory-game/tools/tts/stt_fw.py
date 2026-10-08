"""Second-opinion STT: ivrit.ai Whisper large-v3 (full, non-turbo) on faster-whisper.

Runs on CPU (CTranslate2 has no Metal backend), so it is slower than stt.py; it
is used to cross-check, not as the primary gate.

    tts/.venv-stt/bin/python stt_fw.py a.wav b.mp3 ...
"""
from __future__ import annotations

import glob
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from faster_whisper import WhisperModel

HF = Path(os.environ.get("HF_HUB_CACHE")
          or Path(os.environ.get("HF_HOME") or Path.home() / ".cache/huggingface") / "hub")


def _decode16k(path: str) -> np.ndarray:
    # faster-whisper's own PyAV decoder breaks on newer PyAV (`metadata_errors`).
    raw = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path,
         "-af", "apad=pad_dur=0.3", "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def load(name: str = "large-v3") -> WhisperModel:
    repo = {
        "large-v3": "models--ivrit-ai--whisper-large-v3-ct2",
        "turbo": "models--ivrit-ai--whisper-large-v3-turbo-ct2",
    }[name]
    snap = sorted(glob.glob(str(HF / repo / "snapshots/*")))
    if not snap:
        raise SystemExit(f"missing {repo} in the HF cache")
    return WhisperModel(snap[-1], device="cpu", compute_type="int8", cpu_threads=8)


def transcribe(paths: list[str], model: WhisperModel | None = None) -> list[dict]:
    model = model or load()
    out = []
    for p in paths:
        segs, _ = model.transcribe(
            _decode16k(p), language="he", beam_size=5, word_timestamps=True,
            condition_on_previous_text=False, vad_filter=False,
        )
        segs = list(segs)
        words = [w for s in segs for w in (s.words or [])]
        probs = [w.probability for w in words]
        out.append({
            "file": p,
            "text": "".join(s.text for s in segs).strip(),
            "mean_p": round(sum(probs) / len(probs), 4) if probs else 0.0,
            "min_p": round(min(probs), 4) if probs else 0.0,
            "avg_logprob": round(sum(s.avg_logprob for s in segs) / len(segs), 4) if segs else -math.inf,
        })
    return out


if __name__ == "__main__":
    m = load()
    for r in transcribe(sys.argv[1:], m):
        print(json.dumps(r, ensure_ascii=False), flush=True)
