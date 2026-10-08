"""Phonikud + Piper (ONNX) renderer — run with tts/.venv-phonikud/bin/python.

    render_piper.py jobs.json

jobs.json: {"out_dir": str, "jobs": [{key, text?, nikud?, phonemes?, voice,
            length_scale?, noise_scale?, noise_w?}]}

voice is one of the Phonikud checkpoints: model | shaul | michael.
Text goes text → Phonikud diacritics → phonikud.phonemize → Piper; `nikud` or
`phonemes` short-circuit the earlier stages for hand-fixed pronunciations.
"""
from __future__ import annotations

import glob
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
from phonikud_tts import Phonikud, Piper, phonemize

HF = Path(os.environ.get("HF_HUB_CACHE")
          or Path(os.environ.get("HF_HOME") or Path.home() / ".cache/huggingface") / "hub")


def _snap(repo: str, fname: str) -> str:
    hits = sorted(glob.glob(str(HF / f"models--{repo.replace('/', '--')}/snapshots/*/{fname}")))
    if not hits:
        raise SystemExit(f"missing {repo}/{fname}: hf download {repo} {fname}")
    return hits[-1]


def main(spec_path: str) -> None:
    spec = json.load(open(spec_path, encoding="utf-8"))
    out = Path(spec["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    nikud = Phonikud(_snap("Phonikud/phonikud-onnx", "phonikud-1.0.int8.onnx"))
    cfg = _snap("Phonikud/phonikud-tts-checkpoints", "model.config.json")
    voices: dict[str, Piper] = {}
    jobs = spec["jobs"]
    print(f"[piper] loaded in {time.time() - t0:.1f}s, {len(jobs)} jobs", flush=True)
    for i, j in enumerate(jobs, 1):
        v = j.get("voice", "shaul")
        if v not in voices:
            voices[v] = Piper(_snap("Phonikud/phonikud-tts-checkpoints", f"{v}.onnx"), cfg)
        diac = j.get("nikud") or (None if j.get("phonemes") else nikud.add_diacritics(j["text"]))
        ph = j.get("phonemes") or phonemize(diac)
        t1 = time.time()
        wav, sr = voices[v].create(
            ph, is_phonemes=True,
            length_scale=float(j.get("length_scale", 1.15)),
            noise_scale=float(j.get("noise_scale", 0.667)),
            noise_w=float(j.get("noise_w", 0.8)),
        )
        wav = np.asarray(wav, dtype=np.float32).reshape(-1)
        peak = float(np.max(np.abs(wav))) or 1.0
        wav = wav * (0.95 / peak)
        sf.write(out / f"{j['key']}.wav", wav, sr, subtype="PCM_16")
        meta = {**j, "engine": "phonikud+piper", "nikud_used": diac, "phonemes_used": ph,
                "sr": sr, "render_s": round(time.time() - t1, 2)}
        json.dump(meta, open(out / f"{j['key']}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"[piper] {i}/{len(jobs)} {j['key']} {len(wav) / sr:.2f}s {diac} | {ph}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
