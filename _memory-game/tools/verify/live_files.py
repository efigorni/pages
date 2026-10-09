"""After a merge: poll until GitHub Pages serves the game's new sw.js, then fetch every precached file.

    python3 -I live_files.py <repo> <game> [<other-game> ...]

Prints the served VERSION, how many precached files return 200 and match the repo's bytes, each
other game's status, and which games the root index mentions (it must mention none). Exits 1 if a
file is missing or different, another game is down, or the root index links a game.
"""
import hashlib
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(sys.argv[1])
GAME = sys.argv[2]
OTHERS = sys.argv[3:]
sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "page"))
from build_page import SITE as LIVE  # noqa: E402


def get(url):
    req = urllib.request.Request(f"{url}{'&' if '?' in url else '?'}nocache={time.time()}", headers={"Cache-Control": "no-cache"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as e:
        return e.code, b""


local = (REPO / GAME / "sw.js").read_text(encoding="utf-8")
want = re.search(r"^const VERSION = '([^']+)';$", local, re.M).group(1)
for attempt in range(90):
    status, body = get(f"{LIVE}{GAME}/sw.js")
    served = re.search(rb"^const VERSION = '([^']+)';$", body, re.M)
    if status == 200 and served and served.group(1).decode() == want:
        break
    print(f"{GAME}: waiting for {want} (served {served.group(1).decode() if served else status})", flush=True)
    time.sleep(10)
assets = re.findall(r"^  '([^']+)',?$", local, re.M)
ok = same = 0
bad = []
for a in assets:
    status, body = get(f"{LIVE}{GAME}/{'' if a == './' else a}")
    path = REPO / GAME / ("index.html" if a == "./" else a)
    if status == 200:
        ok += 1
        same += hashlib.md5(body).digest() == hashlib.md5(path.read_bytes()).digest()
    else:
        bad.append(f"{status} {a}")
print(f"{GAME}: VERSION {want} live; {ok}/{len(assets)} precached files 200, {same} byte-identical to the repo; "
      f"bad: {bad}", flush=True)

down = []
for other in OTHERS:
    status, body = get(f"{LIVE}{other}/")
    sw_status, _ = get(f"{LIVE}{other}/sw.js")
    print(f"{other}: page {status} ({len(body)} bytes), sw.js {sw_status}", flush=True)
    if status != 200 or sw_status != 200:
        down.append(other)

status, root = get(LIVE)
links = [g for g in (GAME, *OTHERS, "_memory-game", "-memory/") if g.encode() in root]
print(f"root index: {status}, mentions: {links or 'none'}", flush=True)
sys.exit(1 if bad or same != len(assets) or down or links else 0)
