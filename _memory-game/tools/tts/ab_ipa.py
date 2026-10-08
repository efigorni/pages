"""A/B pronunciation candidates: render each one in both contexts, round-trip through STT.

    _memory-game/tools/tts/tts.sh <game> <work> ab --ids ID,ID [--cand ID:LABEL=IPA ...] [--seeds 6] [--fw]
    <engines>/.venv-stt/bin/python -u _memory-game/tools/tts/ab_ipa.py --work <work> SPEC.json [--seeds 6] [--run NAME] [--fw]

With --ids the cases come from players.json and the club's pronunciations.json: each id's current pin
(or "he:<speak_he>" when it has none) as candidate "pin", plus every --cand for it.
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


def spec_from_pins(players_path: str, pron_path: str, ids: list[str], cands: list[str]) -> dict:
    roster = {p["id"]: p for p in json.load(open(players_path, encoding="utf-8"))["players"]}
    pins = json.load(open(pron_path, encoding="utf-8"))["players"]
    cases = []
    for pid in ids:
        if pid not in roster:
            raise SystemExit(f"{pid} is not in {players_path}")
        p, e = roster[pid], pins.get(pid, {})
        say = g.speak_he(p)
        case = {"id": pid, "speak": say, "number": p.get("number"), "variants": e.get("stt_variants", []),
                "cands": {"pin": e.get("ipa") or f"he:{say}"}}
        case.update({k: e[k] for k in ("stt_text", "speed") if k in e})
        for c in cands:
            cid, _, rest = c.partition(":")
            label, _, ipa = rest.partition("=")
            if cid == pid:
                case["cands"][label] = ipa
        cases.append(case)
    return {"cases": cases}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("spec", nargs="?")
    ap.add_argument("--game")
    ap.add_argument("--work")
    ap.add_argument("--tts-home")
    ap.add_argument("--engines")
    ap.add_argument("--ids", help="ID,ID: cases from the roster and the club's pins")
    ap.add_argument("--cand", action="append", default=[], help="ID:LABEL=IPA (or he:<text>), with --ids")
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--run")
    ap.add_argument("--fw", action="store_true")
    ap.add_argument("--voice", default="noa")
    args = ap.parse_args()
    g.configure(args.work, args.tts_home, args.engines)
    if args.ids:
        if not args.game:
            ap.error("--ids needs --game")
        spec = spec_from_pins(str(g.ROOT / "data/players.json"),
                              str(g.config.game_dir(args.game) / "tools/tts/pronunciations.json"),
                              args.ids.split(","), args.cand)
    elif args.spec:
        spec = json.load(open(args.spec, encoding="utf-8"))
    else:
        ap.error("pass SPEC.json or --ids")
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
