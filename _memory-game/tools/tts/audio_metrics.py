"""Objective audio measurements for the TTS clips (numpy + ffmpeg).

    tts/.venv-stt/bin/python audio_metrics.py clip.wav ...

lead_ms / trail_ms : silence before the first / after the last speech frame
                     (10 ms RMS frames, threshold 40 dB under the loudest frame,
                     floored at -55 dBFS)
lufs / tp_db       : integrated loudness and true peak (ffmpeg ebur128)
f0_med / f0_st     : median pitch (Hz) and pitch spread in semitones — a
                     monotone read has a small spread
"""
from __future__ import annotations

import json
import re
import subprocess
import sys

import numpy as np


def load_mono(path: str, sr: int = 24000) -> np.ndarray:
    raw = subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", path,
         "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
        check=True, capture_output=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def frame_db(x: np.ndarray, sr: int, win_ms: float = 10.0) -> np.ndarray:
    n = max(1, int(sr * win_ms / 1000))
    frames = len(x) // n
    if frames == 0:
        return np.array([-120.0])
    f = x[: frames * n].reshape(frames, n)
    rms = np.sqrt(np.mean(f * f, axis=1) + 1e-12)
    return 20 * np.log10(rms + 1e-12)


def speech_bounds(x: np.ndarray, sr: int, rel_db: float = 40.0, floor_db: float = -55.0,
                  win_ms: float = 10.0) -> tuple[int, int]:
    """Sample indices [start, end) of the speech region."""
    db = frame_db(x, sr, win_ms)
    thr = max(floor_db, float(db.max()) - rel_db)
    idx = np.nonzero(db > thr)[0]
    n = max(1, int(sr * win_ms / 1000))
    if idx.size == 0:
        return 0, len(x)
    return int(idx[0] * n), int(min(len(x), (idx[-1] + 1) * n))


def loudness(path: str) -> tuple[float, float]:
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", path,
         "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True,
    )
    tail = r.stderr[r.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", tail)
    p = re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", tail)
    lufs = float(i.group(1)) if i and i.group(1) != "-inf" else float("-inf")
    tp = float(p.group(1)) if p and p.group(1) != "-inf" else float("-inf")
    return lufs, tp


def f0_track(x: np.ndarray, sr: int, fmin: float = 70.0, fmax: float = 400.0) -> np.ndarray:
    """Autocorrelation pitch per 40 ms frame (hop 10 ms); voiced frames only."""
    win, hop = int(0.04 * sr), int(0.01 * sr)
    lo, hi = int(sr / fmax), int(sr / fmin)
    db = frame_db(x, sr, 40.0)
    gate = db.max() - 30 if db.size else -60
    out = []
    for start in range(0, len(x) - win, hop):
        f = x[start:start + win]
        f = f - f.mean()
        e = float(np.dot(f, f))
        if e <= 1e-8 or 10 * np.log10(e / win + 1e-12) < gate:
            continue
        ac = np.correlate(f, f, mode="full")[win - 1:]
        ac = ac / (ac[0] + 1e-12)
        seg = ac[lo:hi]
        if seg.size == 0:
            continue
        k = int(np.argmax(seg))
        if seg[k] < 0.5:
            continue
        out.append(sr / (lo + k))
    return np.array(out)


def measure(path: str) -> dict:
    sr = 24000
    x = load_mono(path, sr)
    s, e = speech_bounds(x, sr)
    f0 = f0_track(x[s:e], sr)
    lufs, tp = loudness(path)
    st = float(np.std(12 * np.log2(f0 / np.median(f0)))) if f0.size > 5 else 0.0
    return {
        "file": path,
        "duration_ms": round(1000 * len(x) / sr),
        "speech_ms": round(1000 * (e - s) / sr),
        "lead_ms": round(1000 * s / sr),
        "trail_ms": round(1000 * (len(x) - e) / sr),
        "lufs": round(lufs, 1),
        "tp_db": round(tp, 1),
        "f0_med": round(float(np.median(f0)), 1) if f0.size else 0.0,
        "f0_st": round(st, 2),
    }


if __name__ == "__main__":
    for p in sys.argv[1:]:
        print(json.dumps(measure(p)), flush=True)
