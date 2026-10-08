#!/usr/bin/env python3
"""Embed the roster into maccabi-haifa-memory/index.html and refresh the service worker.

- Writes `const DATA = {...};` into the page's <script id="data"> block: the starters
  and bench from players.json plus the list of audio clips that exist under audio/, so
  the page never requests a clip that isn't there. Per player:
    name_he   the name exactly as the club site displays it (shown on the card)
    first_he  the small line and last_he the big line: the site card's own split
              (`card_name_lines` from the scrape), else the same rule applied here
    speak_he  what the voice says: the text inside a trailing "(...)", else name_he
- Rewrites VERSION and ASSETS at the top of sw.js: every file the game needs offline,
  and a content hash so a changed asset installs a fresh cache.

usage:
  python3 -I build_page.py <players.json> <maccabi-haifa-memory dir>
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_memory-game/tools/tts"))
from hebrew import speak_text, split_display_name  # noqa: E402

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PRECACHE_DIRS = ("fonts", "img", "audio", "icons")
PRECACHE_SUFFIXES = {".woff2", ".webp", ".png", ".mp3"}
UI_CLIPS = ("start", "win")
CACHE_PREFIX = "maccabi-haifa-memory-"


def clean(text):
    return " ".join(str(text or "").split())


def entry(p, page):
    pid = p["id"]
    if not ID_RE.match(pid):
        sys.exit(f"unsafe player id: {pid!r}")
    number = int(p["number"])
    if not 0 <= number <= 99:
        sys.exit(f"{pid}: shirt number out of range: {number}")
    name = clean(p["name_he"])
    lines = p.get("card_name_lines")
    if isinstance(lines, list) and len(lines) == 2:
        first, last = clean(lines[0]), clean(lines[1])
    elif p.get("last_he"):
        first, last = clean(p.get("first_he")), clean(p["last_he"])
    else:
        first, last = split_display_name(name)
    speak = clean(p.get("speak_he")) or speak_text(name)
    for label, text in (("name_he", name), ("first_he", first), ("last_he", last), ("speak_he", speak)):
        if any(ch in text for ch in "<>&\"`"):
            sys.exit(f"{pid}: unexpected characters in {label}: {text!r}")
    if not name or not last or not speak:
        sys.exit(f"{pid}: empty name field")
    if clean(f"{first} {last}") != name:
        sys.exit(f"{pid}: first/last {first!r} + {last!r} do not reproduce name_he {name!r}")
    if speak != speak_text(name):
        print(f"note: {pid}: speak_he {speak!r} differs from the parentheses rule ({speak_text(name)!r})", flush=True)
    img = f"img/{pid}.webp"
    if not (page / img).is_file():
        sys.exit(f"{pid}: missing {img} (run tools/images first)")
    return {"id": pid, "name_he": name, "first_he": first, "last_he": last, "speak_he": speak,
            "number": number, "role": p["role"], "img": img}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("players_json", type=Path)
    ap.add_argument("page_dir", type=Path)
    args = ap.parse_args()

    page = args.page_dir.resolve()
    data = json.loads(args.players_json.read_text(encoding="utf-8"))
    starters = [entry(p, page) for p in data["players"] if p.get("role") == "starter"]
    bench = [entry(p, page) for p in data["players"] if p.get("role") == "bench"]
    if len(starters) != 11:
        sys.exit(f"expected 11 starters, found {len(starters)}")
    if len(bench) < 4:
        sys.exit(f"need at least 4 bench players, found {len(bench)}")

    ids = [p["id"] for p in starters + bench]
    audio = {
        "ui": [k for k in UI_CLIPS if (page / "audio" / "ui" / f"{k}.mp3").is_file()],
        "name": [i for i in ids if (page / "audio" / "name" / f"{i}.mp3").is_file()],
        "match": [i for i in ids if (page / "audio" / "match" / f"{i}.mp3").is_file()],
    }
    payload = {"season": data.get("season"), "starters": starters, "bench": bench, "audio": audio}
    js = "const DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"

    index = page / "index.html"
    html = index.read_text(encoding="utf-8")
    html, n = re.subn(r'(<script id="data">\n).*?(\n</script>)', lambda m: m.group(1) + js + m.group(2),
                      html, count=1, flags=re.S)
    if n != 1:
        sys.exit('index.html has no <script id="data"> block')
    index.write_text(html, encoding="utf-8")

    files = sorted(
        f for d in PRECACHE_DIRS if (page / d).is_dir()
        for f in (page / d).rglob("*") if f.is_file() and f.suffix in PRECACHE_SUFFIXES
    )
    rel = [f.relative_to(page).as_posix() for f in files]
    digest = hashlib.sha256()
    for path in [index, page / "manifest.webmanifest", *files]:
        digest.update(path.relative_to(page).as_posix().encode())
        digest.update(path.read_bytes())
    version = f"{CACHE_PREFIX}{digest.hexdigest()[:12]}"
    assets = ["./", "index.html", "manifest.webmanifest", *rel]

    sw = page / "sw.js"
    src = sw.read_text(encoding="utf-8")
    src, a = re.subn(r"^const VERSION = .*;$", f"const VERSION = '{version}';", src, count=1, flags=re.M)
    src, b = re.subn(r"^const ASSETS = .*?;$", "const ASSETS = " + json.dumps(assets, indent=2).replace('"', "'") + ";",
                     src, count=1, flags=re.M | re.S)
    if a != 1 or b != 1:
        sys.exit("sw.js is missing its VERSION / ASSETS lines")
    sw.write_text(src, encoding="utf-8")

    total = sum(f.stat().st_size for f in files) + index.stat().st_size
    print(f"starters={len(starters)} bench={len(bench)} audio ui={len(audio['ui'])} "
          f"name={len(audio['name'])} match={len(audio['match'])}", flush=True)
    print(f"precache: {len(assets)} entries, {total / 1024:.0f} KB, version {version}", flush=True)


if __name__ == "__main__":
    main()
