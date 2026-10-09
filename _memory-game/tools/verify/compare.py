"""Compare two drive.js output trees: every screenshot pixel by pixel, the DOM snapshots, the
computed HUD styles, the flyer geometry and the audio event sequences.

    uv run --with pillow==12.3.0 python -I compare.py <dir-a> <dir-b> [--dom] [--diffs <dir>]

Prints one line per screenshot (identical, or how many pixels differ, the largest channel delta and
the bounding box) and one per run; a quiz run also compares what it asked and the clips it heard. With
--diffs, writes an amplified difference image for each non-identical pair. Exits 1 if anything differs or
is missing, and 2 if it can't see a one-level difference (its canary).
"""
import difflib
import json
import sys
from pathlib import Path

from PIL import Image, ImageChops

A, B = Path(sys.argv[1]), Path(sys.argv[2])
show_dom = "--dom" in sys.argv
diff_dir = Path(sys.argv[sys.argv.index("--diffs") + 1]) if "--diffs" in sys.argv else None


def pixel_diff(ia, ib):
    """The difference image and its bbox, or None when the two are identical. RGB: Pillow's getbbox() on an
    RGBA difference looks at alpha only, so opaque shots would always match."""
    d = ImageChops.difference(ia.convert("RGB"), ib.convert("RGB"))
    bbox = d.getbbox()
    return (d, bbox) if bbox else None


# A compare that can't fail proves nothing: one level of one channel must read as a difference.
if pixel_diff(Image.new("RGB", (2, 2), (9, 9, 9)), Image.new("RGB", (2, 2), (9, 10, 9))) is None:
    print("compare.py is blind: a one-level difference reads as identical")
    sys.exit(2)

n_same = n_diff = n_runs_diff = 0
for pa in sorted(A.rglob("*.png")):
    rel = pa.relative_to(A)
    pb = B / rel
    if not pb.exists():
        print(f"MISSING  {rel}")
        n_diff += 1
        continue
    ia, ib = Image.open(pa), Image.open(pb)
    if ia.size != ib.size:
        print(f"SIZE     {rel}: {ia.size} vs {ib.size}")
        n_diff += 1
        continue
    found = pixel_diff(ia, ib)
    if not found:
        n_same += 1
        print(f"same     {rel}")
        continue
    d, bbox = found
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
    # A quiz flight leaves while the right card's lift is still running, so its start box is the clock's too.
    if x.get("mode") != "quiz" and strip(fa) != strip(fb):
        notes.append(f"flyers differ ({len(fa)} vs {len(fb)})")
    keys = ("starts", "stops", "speech", "html", "fetchBad", "errors", "startClip", "winClip", "effectiveFlips",
            "matchesWithFollow", "matches", "fullscreen", "wake") if x.get("mode") == "audio" else (
        "speech", "fetchBad", "errors", "fullscreen")
    notes += [f"audio.{k}" for k in keys if x["analysis"].get(k) != y["analysis"].get(k)]
    if x.get("mode") == "quiz":  # what was asked and heard; how soon each reveal moved on is the clock's
        def asked(r):
            return [{**{k: q.get(k) for k in ("id", "cards", "text")},
                     "wrong": {k: v for k, v in (q.get("wrong") or {}).items() if k != "saidMs"}} for q in r.get("questions") or []]
        notes += [k for k, a, b in (("quiz.questions", asked(x), asked(y)),
                                    ("quiz.clips", (x.get("quiz") or {}).get("sequence"), (y.get("quiz") or {}).get("sequence")))
                  if a != b]
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
