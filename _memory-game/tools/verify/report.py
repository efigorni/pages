"""P9's verdict for each game, from what verify.sh local wrote into <out-dir>.

    python3 -I report.py <out-dir> <game>... [--worker-only]

Per game: the seeded shots at 600x960 and 960x600 (won, no failure, no 404, a clean console), the
audio playthrough (the right name clip on every flip, the match clip after the name, start and win,
no speech fallback), the worker (controls the page, flips online, installability [], an offline
reload plays with every photo) and the state machine. Exits 1 if any game fails.
"""
import json
import sys
from pathlib import Path

OUT = Path(sys.argv[1])
NOISE = ("Service Worker registration blocked by Playwright", "Banner not shown")


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def console_clean(lines):
    return [m for m in lines if not any(n in m for n in NOISE) and not m.startswith(("log:", "info:", "debug:"))]


def drive_checks(r, mode):
    if r is None:
        return {"ran": False}
    a = r["analysis"]
    checks = {"ran": not r.get("failure"), "won": bool(r.get("won")), "no 404": not r["http"],
              "clean console": not console_clean(r["console"]), "no errors": not a["errors"],
              "no speech fallback": not a["speech"], "all fetches 200": not a["fetchBad"]}
    if mode == "shots":
        fan = r.get("fanNames") or []
        checks[f"start-screen name fits ({', '.join(n.get('text') or '?' for n in fan)})"] = len(fan) == 1 and all(
            n.get("inside") for n in fan)
    if mode == "audio":
        marks = [e for e in r["log"] if e["type"] == "mark" and e["label"].split(" ")[0] in ("flip", "hurry", "match")]
        checks.update({
            f"right name clip on every flip ({a['effectiveFlips']}/{len(marks)})": a["effectiveFlips"] == len(marks) and not a["badFlips"],
            f"match clip after the name ({a['matchesWithFollow']} of {a['matches']} let finish)": a["matchesWithFollow"] > 0,
            "start and win clips": a["startClip"] == 1 and a["winClip"] == 1,
        })
    return checks


def sw_checks(r):
    if r is None:
        return {"ran": False}
    on, off = r["online"]["audio"], r["offline"]["audio"]
    imgs = r["offline"]["imgs"]
    return {
        "worker controls the page": bool(r["controlled"]),
        "installability []": r["installability"] == [] and not r["manifestErrors"],
        f"online flips ({on['rightNameClip']}/{on['of']})": on["rightNameClip"] == on["of"] > 0 and not on["errors"] and not on["fetchBad"],
        "offline reload controlled": bool(r["offline"]["state"]["controlled"]),
        f"offline photos ({imgs[1]}/{imgs[0]})": imgs[0] > 0 and imgs[0] == imgs[1],
        f"offline flips ({off['rightNameClip']}/{off['of']})": off["rightNameClip"] == off["of"] > 0 and not off["errors"] and not off["fetchBad"],
        "no 404, clean console": not r["http"] and not console_clean(r["console"]),
    }


worker_only = "--worker-only" in sys.argv
failed = []
for game in [a for a in sys.argv[2:] if not a.startswith("--")]:
    sections = {"worker": sw_checks(load(OUT / f"sw-{game}.json"))}
    if not worker_only:
        sections["shots 600x960"] = drive_checks(load(OUT / game / "tab-portrait-shots/result.json"), "shots")
        sections["shots 960x600"] = drive_checks(load(OUT / game / "tab-landscape-shots/result.json"), "shots")
        sections["audio 600x960"] = drive_checks(load(OUT / game / "tab-portrait-audio/result.json"), "audio")
        path = OUT / f"states-{game}.txt"
        states = path.read_text(encoding="utf-8").strip().splitlines() if path.exists() else []
        sections["state machine"] = {states[-1] if states else "ran": bool(states) and " 0 fail" in states[-1]}
    bad = [f"{s}: {c}" for s, checks in sections.items() for c, ok in checks.items() if not ok]
    for s, checks in sections.items():
        print(f"{game} {s}: {'PASS' if all(checks.values()) else 'FAIL'} ({'; '.join(checks)})")
    print(f"P9 {'worker' if worker_only else 'local'} {game}: {'PASS' if not bad else 'FAIL: ' + ' | '.join(bad)}", flush=True)
    if bad:
        failed.append(game)
sys.exit(1 if failed else 0)
