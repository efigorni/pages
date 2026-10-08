"""Score probe renders: STT round-trip (two ivrit.ai models) + audio metrics.

    tts/.venv-stt/bin/python eval_probe.py OUT.json DIR [DIR ...]

Files are named <voice>__<probe key>.wav; the expected text comes from
probe_set.json. Prints a per-engine/voice summary and writes every row to OUT.json.
"""
from __future__ import annotations

import json
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audio_metrics  # noqa: E402
import hebrew  # noqa: E402
import stt  # noqa: E402


def main(out_json: str, dirs: list[str], second_opinion: bool = True) -> None:
    probes = {p["key"]: p for p in json.load(open(HERE / "probe_set.json", encoding="utf-8"))}
    files = []
    for d in dirs:
        for f in sorted(Path(d).glob("*.wav")):
            voice, key = f.stem.split("__", 1)
            if key in probes:
                files.append((Path(d).name, voice, key, str(f)))
    print(f"[eval] {len(files)} clips; whisper.cpp ivrit turbo...", flush=True)
    res = stt.transcribe([f[3] for f in files])
    fw = [None] * len(files)
    if second_opinion:
        import stt_fw
        print("[eval] faster-whisper ivrit large-v3...", flush=True)
        model = stt_fw.load()
        fw = []
        for i, f in enumerate(files, 1):
            fw.extend(stt_fw.transcribe([f[3]], model))
            if i % 20 == 0:
                print(f"[eval]   fw {i}/{len(files)}", flush=True)
    rows = []
    for (eng, voice, key, path), r, r2 in zip(files, res, fw):
        p = probes[key]
        ok, how = hebrew.compare(p["text"], r["text"], p.get("variants"))
        row = {"engine": eng, "voice": voice, "key": key, "file": path, "expected": p["text"],
               "heard": r["text"], "ok": ok, "how": how, "mean_p": r["mean_p"], "min_p": r["min_p"],
               "sim": round(hebrew.similarity(p["text"], r["text"]), 3)}
        if r2:
            ok2, _ = hebrew.compare(p["text"], r2["text"], p.get("variants"))
            row.update({"heard_fw": r2["text"], "ok_fw": ok2, "mean_p_fw": r2["mean_p"]})
        row.update({k: v for k, v in audio_metrics.measure(path).items() if k != "file"})
        rows.append(row)
    json.dump(rows, open(out_json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    groups = defaultdict(list)
    for r in rows:
        groups[(r["engine"], r["voice"])].append(r)
    print("\nengine/voice                     pass  pass_fw  mean_p  p_fw   lead  f0    f0_st  dur_names")
    for (eng, voice), rs in sorted(groups.items()):
        n = len(rs)
        names = [r for r in rs if r["key"][:2] in ("p1", "p2", "p3", "p4", "p5")]
        print(f"{eng + '/' + voice:32s} {sum(r['ok'] for r in rs)}/{n}   "
              f"{sum(r.get('ok_fw', False) for r in rs)}/{n}    "
              f"{sum(r['mean_p'] for r in rs) / n:.3f}  "
              f"{sum(r.get('mean_p_fw', 0) for r in rs) / n:.3f}  "
              f"{sum(r['lead_ms'] for r in rs) / n:4.0f}  "
              f"{sum(r['f0_med'] for r in rs) / n:4.0f}  "
              f"{sum(r['f0_st'] for r in rs) / n:.2f}   "
              f"{sum(r['duration_ms'] for r in names) / max(1, len(names)):.0f}ms")
    print("\nmisses:")
    for r in rows:
        if not r["ok"] or not r.get("ok_fw", True):
            print(f"  {r['engine']}/{r['voice']}/{r['key']}: want «{r['expected']}» "
                  f"cpp «{r['heard']}» fw «{r.get('heard_fw', '')}»")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:], second_opinion=os.environ.get("NO_FW") != "1")
