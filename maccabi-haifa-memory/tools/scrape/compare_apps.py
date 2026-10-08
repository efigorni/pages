"""Exploration: 2026/27 appearances from the game records vs the number in each player page header.

Usage: python -I compare_apps.py <tools-dir> <html-dir>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from rsc import page_objects  # noqa: E402

html_dir = Path(sys.argv[2])
apps: dict[int, list] = {}
for path in sorted((html_dir / "games").glob("*.html")):
    html = path.read_text(encoding="utf-8")
    mg = max(page_objects(html, lambda o: "gameLineUp" in o and "team" in o), key=lambda o: len(json.dumps(o)))
    lu = (mg.get("gameLineUp") or {}).get("team") or {}
    starters = set()
    for entries in lu.values():
        for e in ([entries] if isinstance(entries, dict) else entries or []):
            starters.add((e.get("player") or {}).get("id"))
    for e in (mg.get("team") or {}).get("players") or []:
        pid = (e.get("player") or {}).get("id")
        if pid in starters:
            apps.setdefault(pid, []).append((path.stem, "start"))
        elif e.get("isSubstitution"):
            apps.setdefault(pid, []).append((path.stem, "sub"))
        else:
            apps.setdefault(pid, []).append((path.stem, "unused"))

rows = []
for path in sorted((html_dir / "players").glob("*.html")):
    html = path.read_text(encoding="utf-8")
    pl = [o for o in page_objects(html, lambda o: "statistics" in o and "basePlayer" in o and "playerShirtNumber" in o)]
    p = pl[0]
    st = p.get("statistics") or {}
    per = (p.get("basePlayer") or {}).get("statisticsPerLeagues") or []
    rec = apps.get(p["id"], [])
    played = sum(1 for _, r in rec if r != "unused")
    starts = sum(1 for _, r in rec if r == "start")
    unused = sum(1 for _, r in rec if r == "unused")
    rows.append((p["id"], p["playerName"], p["playerShirtNumber"], st.get("appearances"), played, starts, unused,
                 sum(x.get("appearances") or 0 for x in per), (p.get("basePlayer") or {}).get("createdAt", "")[:10], p.get("updatedAt", "")[:10]))
print("id | name | # | header_apps | games_apps | starts | unused | career_apps | base_created | entry_updated | header-games")
for r in sorted(rows, key=lambda r: -r[4]):
    hdr = r[3] if r[3] is not None else 0
    print(" | ".join(str(x) for x in r), "|", hdr - r[4])
