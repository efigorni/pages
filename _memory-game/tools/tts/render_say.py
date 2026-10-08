"""macOS `say` renderer (Carmit, he_IL) — stdlib only, any python3.

    render_say.py jobs.json

jobs.json: {"out_dir": str, "jobs": [{key, text, voice?="Carmit", rate?}]}
Baseline only: `say` takes plain text, so there is no pronunciation control.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def main(spec_path: str) -> None:
    spec = json.load(open(spec_path, encoding="utf-8"))
    out = Path(spec["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    jobs = spec["jobs"]
    for i, j in enumerate(jobs, 1):
        with tempfile.TemporaryDirectory() as td:
            aiff = os.path.join(td, "x.aiff")
            cmd = ["say", "-v", j.get("voice") or "Carmit", "-o", aiff]
            if j.get("rate"):
                cmd += ["-r", str(j["rate"])]
            subprocess.run(cmd + [j["text"]], check=True)
            subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", aiff,
                            str(out / f"{j['key']}.wav")], check=True)
        json.dump({**j, "engine": "macos-say", "phonemes_used": j["text"]},
                  open(out / f"{j['key']}.json", "w", encoding="utf-8"), ensure_ascii=False)
        print(f"[say] {i}/{len(jobs)} {j['key']}", flush=True)


if __name__ == "__main__":
    main(sys.argv[1])
