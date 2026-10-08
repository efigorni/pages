"""Torch engines for the bake-off — run with tts/.venv-chatterbox/bin/python.

    render_torch.py chatterbox jobs.json   # Chatterbox Multilingual, built-in voice
    render_torch.py mms jobs.json          # facebook/mms-tts-heb (VITS)

jobs.json: {"out_dir": str, "jobs": [{key, text, seed?, exaggeration?, cfg_weight?,
            temperature?}]}. Chatterbox gets pre-vocalized text (it only adds
nikud itself when the optional dicta_onnx is installed); MMS takes bare letters.
"""
from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf
import torch


def run_chatterbox(spec: dict, out: Path) -> None:
    from chatterbox.mtl_tts import ChatterboxMultilingualTTS
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    t0 = time.time()
    model = ChatterboxMultilingualTTS.from_pretrained(device=dev)
    print(f"[chatterbox] loaded on {dev} in {time.time() - t0:.1f}s", flush=True)
    for i, j in enumerate(spec["jobs"], 1):
        torch.manual_seed(int(j.get("seed", 0)))
        t1 = time.time()
        wav = model.generate(
            j["text"], language_id="he",
            exaggeration=float(j.get("exaggeration", 0.5)),
            cfg_weight=float(j.get("cfg_weight", 0.5)),
            temperature=float(j.get("temperature", 0.8)),
        )
        x = wav.squeeze(0).cpu().numpy().astype(np.float32)
        x = x * (0.95 / max(1e-6, float(np.abs(x).max())))
        sf.write(out / f"{j['key']}.wav", x, model.sr, subtype="PCM_16")
        json.dump({**j, "engine": "chatterbox-mtl", "sr": model.sr},
                  open(out / f"{j['key']}.json", "w", encoding="utf-8"), ensure_ascii=False)
        print(f"[chatterbox] {i}/{len(spec['jobs'])} {j['key']} {len(x) / model.sr:.2f}s "
              f"({time.time() - t1:.1f}s)", flush=True)


def run_mms(spec: dict, out: Path) -> None:
    from transformers import AutoTokenizer, VitsModel
    tok = AutoTokenizer.from_pretrained("facebook/mms-tts-heb")
    model = VitsModel.from_pretrained("facebook/mms-tts-heb")
    sr = model.config.sampling_rate
    for i, j in enumerate(spec["jobs"], 1):
        torch.manual_seed(int(j.get("seed", 0)))
        text = re.sub(r"[^א-ת' -]", " ", j["text"])
        with torch.no_grad():
            x = model(**tok(text, return_tensors="pt")).waveform[0].numpy().astype(np.float32)
        x = x * (0.95 / max(1e-6, float(np.abs(x).max())))
        sf.write(out / f"{j['key']}.wav", x, sr, subtype="PCM_16")
        json.dump({**j, "engine": "mms-tts-heb", "sr": sr, "text_used": text},
                  open(out / f"{j['key']}.json", "w", encoding="utf-8"), ensure_ascii=False)
        print(f"[mms] {i}/{len(spec['jobs'])} {j['key']} {len(x) / sr:.2f}s", flush=True)


if __name__ == "__main__":
    engine, spec_path = sys.argv[1], sys.argv[2]
    spec = json.load(open(spec_path, encoding="utf-8"))
    out = Path(spec["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    {"chatterbox": run_chatterbox, "mms": run_mms}[engine](spec, out)
