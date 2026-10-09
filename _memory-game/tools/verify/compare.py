"""Compare two drive.js output trees: every screenshot pixel by pixel, the DOM snapshots, the
computed HUD styles, the flyer geometry and the audio event sequences.

    uv run --with pillow==12.3.0 python -I compare.py <dir-a> <dir-b> [--dom] [--diffs <dir>]

Prints one line per screenshot (identical, or how many pixels differ, the largest channel delta and
the bounding box) and one per run. With --diffs, writes an amplified difference image for each
non-identical pair. Exits 1 if anything differs or is missing.
"""
import difflib
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

A, B = Path(sys.argv[1]), Path(sys.argv[2])
show_dom = "--dom" in sys.argv
diff_dir = Path(sys.argv[sys.argv.index("--diffs") + 1]) if "--diffs" in sys.argv else None

n_same = n_diff = n_runs_diff = 0
for pa in sorted(A.rglob("*.png")):
    rel = pa.relative_to(A)
    pb = B / rel
    if not pb.exists():
        print(f"MISSING  {rel}")
        n_diff += 1
        continue
    ia, ib = Image.open(pa).convert("RGBA"), Image.open(pb).convert("RGBA")
    if ia.size != ib.size:
        print(f"SIZE     {rel}: {ia.size} vs {ib.size}")
        n_diff += 1
        continue
    d = ImageChops.difference(ia, ib)
    bbox = d.getbbox()
    if not bbox:
        n_same += 1
        print(f"same     {rel}")
        continue
    n_diff += 1
    px = sum(1 for p in d.getdata() if any(p))
    mx = max(max(p) for p in d.getdata())
    print(f"DIFF     {rel}: {px} px, max delta {mx}, bbox {bbox}")
    if diff_dir:
        out = diff_dir / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        Image.eval(d.convert("RGB"), lambda v: min(255, v * 8)).save(out)
print(f"screenshots: {n_same} identical, {n_diff} different")


def styles_diff(x, y, where):
    if x == y:
        return []
    out = []
    for part in sorted(set(x or {}) | set(y or {})):
        a, b = (x or {}).get(part), (y or {}).get(part)
        if a != b:
            out.append(f"{where}.{part}: {json.dumps(a, ensure_ascii=False)} vs {json.dumps(b, ensure_ascii=False)}")
    return out


for ra in sorted(A.rglob("result.json")):
    rel = ra.relative_to(A)
    rb = B / rel
    if not rb.exists():
        print(f"MISSING  {rel}")
        n_runs_diff += 1
        continue
    x, y = json.loads(ra.read_text()), json.loads(rb.read_text())
    notes = []
    for k in ("domStart", "domMid", "domWin"):
        if k in x and x.get(k) != y.get(k):
            notes += [f"{k}.{part}" for part in x[k] if x[k][part] != (y.get(k) or {}).get(part)]
    for k in ("stylesStart", "stylesMid"):
        if k in x or k in y:
            notes += styles_diff(x.get(k), y.get(k), k)
    if x.get("deck") != y.get("deck"):
        notes.append("deck")
    if x.get("fanNames") != y.get("fanNames"):
        notes.append(f"fanNames {x.get('fanNames')} vs {y.get('fanNames')}")
    if x.get("flight") != y.get("flight"):
        notes.append(f"flight {x.get('flight')} vs {y.get('flight')}")
    strip = lambda f: [{k: v for k, v in e.items() if k != "t"} for e in f]  # noqa: E731
    fa, fb = x["analysis"]["flyers"], y["analysis"]["flyers"]
    if strip(fa) != strip(fb):
        notes.append(f"flyers differ ({len(fa)} vs {len(fb)})")
    keys = ("starts", "stops", "speech", "html", "fetchBad", "errors", "startClip", "winClip", "effectiveFlips",
            "matchesWithFollow", "matches", "fullscreen", "wake") if x.get("mode") == "audio" else (
        "speech", "fetchBad", "errors", "fullscreen")
    notes += [f"audio.{k}" for k in keys if x["analysis"].get(k) != y["analysis"].get(k)]
    if x.get("installedCss") != y.get("installedCss"):
        notes.append(f"installedCss {x.get('installedCss')} vs {y.get('installedCss')}")
    if x.get("focus") != y.get("focus"):
        notes.append("focus")
    for side, r in (("A", x), ("B", y)):
        if r.get("http") or r.get("failure") or r["analysis"].get("errors"):
            notes.append(f"{side} problems: http={r.get('http')} failure={r.get('failure')} errors={r['analysis'].get('errors')}")
    n_runs_diff += bool(notes)
    print(f"{'same    ' if not notes else 'NOTES   '} {rel.parent}: {'; '.join(notes) if notes else 'DOM, styles, deck, flight, audio identical'}")
    if show_dom and notes:
        for k in ("domStart", "domMid", "domWin"):
            if k in x and x.get(k) != y.get(k):
                for part in ("board", "fan"):
                    if x[k][part] != y[k][part]:
                        sa = x[k][part].replace("><", ">\n<").splitlines()
                        sb = y[k][part].replace("><", ">\n<").splitlines()
                        diff = list(difflib.unified_diff(sa, sb, lineterm="", n=0))
                        print(f"   {k}.{part}: {len(diff)} diff lines; first:", "\n      ".join(diff[:8]))
print(f"runs: {n_runs_diff} with differences")
sys.exit(1 if n_diff or n_runs_diff else 0)
