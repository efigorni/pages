"""A/B pronunciation candidates: render each one in both contexts, round-trip through STT.

    <engines>/.venv-stt/bin/python -u _memory-game/tools/tts/ab_ipa.py SPEC.json [--seeds 6] [--run NAME] [--fw]

SPEC.json:
    {"cases": [{"id": "player-id", "speak": "טקסט", "number": 7,
                "stt_text": "טקסט",                  # optional: intended sound's spelling
                "variants": ["accepted spelling", ...],
                "speed": 0.88,                       # optional
                "cands": {"A": "ipa ...", "B": "he:עברית מנוקדת"}}]}

A candidate is IPA used verbatim, or "he:<text>" run through RenikudPlus G2P.
Each candidate is rendered as the name clip (", <cand>.") and the match clip
(", מספר <N>, <cand>!") with seeds 1..N, exactly like generate.py, and every take
is transcribed. Prints pass counts and what was heard; writes tts/probe/ab/<run>/results.json.
--fw adds the second model (ivrit large-v3 on faster-whisper, slower) for every take.
"""
from __future__ import annotations

import argparse
import collections
import json
import time
from pathlib import Path

import generate as g  # sets the read-only environment for the engine install first
import hebrew


def cand_part(c: str, end: str) -> dict:
    return {"text": c[3:] + end} if c.startswith("he:") else {"ipa": c + end}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--run")
    ap.add_argument("--fw", action="store_true")
    ap.add_argument("--voice", default="noa")
    args = ap.parse_args()
    spec = json.load(open(args.spec, encoding="utf-8"))
    run = args.run or time.strftime("ab-%Y%m%d-%H%M%S")
    work = g.TTS / "probe/ab" / run
    (work / "raw").mkdir(parents=True, exist_ok=True)

    items = []
    for c in spec["cases"]:
        words = hebrew.number_words_fem(c["number"]) if c.get("number") is not None else None
        for label, cand in c["cands"].items():
            base = {"id": f"{c['id']}~{label}", "case": c["id"], "cand": label, "cand_input": cand,
                    "speed": c.get("speed")}
            var = c.get("variants", [])
            expect = c.get("stt_text", c["speak"])
            items.append({**base, "kind": "name", "text": expect, "variants": var,
                          "job": {"parts": [{"ipa": g.LEAD_IN}, cand_part(cand, ".")]}})
            lead = [{"text": f"מספר {words},"}] if words else []
            items.append({**base, "kind": "match", "text": hebrew.match_text(c.get("number"), expect),
                          "variants": [hebrew.match_text(c.get("number"), v) for v in var],
                          "job": {"parts": [{"ipa": g.LEAD_IN}] + lead + [cand_part(cand, "!")]}})
    g.render("blue", args.voice, items, args.seeds, 0.88, work)
    paths = {(it["id"], it["kind"], s): str(work / "raw" / f"{it['kind']}__{it['id']}__s{s}.wav")
             for it in items for s in range(1, args.seeds + 1)}
    res = g.transcribe(list(paths.values()), "ab")
    fw = {}
    if args.fw:
        import stt_fw
        model = stt_fw.load()
        for i, p in enumerate(paths.values(), 1):
            fw[p] = stt_fw.transcribe([p], model)[0]
            if i % 20 == 0 or i == len(paths):
                g.log(f"    fw {i}/{len(paths)}")

    out = []
    for it in items:
        rows = []
        for s in range(1, args.seeds + 1):
            p = paths[(it["id"], it["kind"], s)]
            r = res[p]
            ok, _ = hebrew.compare(it["text"], r["text"], it["variants"])
            row = {"seed": s, "heard": r["text"], "ok": ok, "mean_p": r["mean_p"], "min_p": r["min_p"]}
            if p in fw:
                row.update(heard_fw=fw[p]["text"],
                           ok_fw=hebrew.compare(it["text"], fw[p]["text"], it["variants"])[0])
            rows.append(row)
        ph = json.load(open(str(work / "raw" / f"{it['kind']}__{it['id']}__s1.json"), encoding="utf-8"))
        out.append({"case": it["case"], "cand": it["cand"], "kind": it["kind"], "input": it["cand_input"],
                    "phonemes": ph["phonemes_used"], "takes": rows})
    json.dump(out, open(work / "results.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    g.log(f"\n[ab] {run}: pass = STT heard the intended words (of {args.seeds} seeds)")
    for o in out:
        t = o["takes"]
        n_ok = sum(x["ok"] for x in t)
        fwp = f" fw {sum(x.get('ok_fw', False) for x in t)}/{len(t)}" if args.fw else ""
        heard = collections.Counter(x["heard"].strip(" .!,") for x in t).most_common(3)
        g.log(f"  {o['case']:22s} {o['cand']:3s} {o['kind']:5s} {n_ok}/{len(t)}{fwp} "
              f"p={sum(x['mean_p'] for x in t) / len(t):.2f}  {o['phonemes']}")
        g.log("        heard: " + " | ".join(f"«{h}»×{n}" for h, n in heard))


if __name__ == "__main__":
    main()
