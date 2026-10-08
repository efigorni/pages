"""Exploration: list the games in a saved /matches page's flight payload.

Usage: python -I explore_matches.py <tools-dir> <matches.html>
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, sys.argv[1])
from rsc import flight_text  # noqa: E402

html = open(sys.argv[2], encoding="utf-8").read()
text = flight_text(html)


def walk(o, found):
    if isinstance(o, dict):
        if "hostTeam" in o and "guestTeam" in o and "gameTime" in o:
            found.append(o)
        for v in o.values():
            walk(v, found)
    elif isinstance(o, list):
        for v in o:
            walk(v, found)


# flight rows look like  <hex>:<json>\n ; decode every row that parses as JSON
rows = []
for line in text.split("\n"):
    k, sep, rest = line.partition(":")
    if not sep or not rest or rest[0] not in "[{":
        continue
    try:
        rows.append(json.loads(rest))
    except json.JSONDecodeError:
        pass
games = []
for r in rows:
    walk(r, games)
seen = {}
for g in games:
    seen.setdefault(g.get("id"), g)
print("games", len(games), "distinct", len(seen))
for gid, g in sorted(seen.items(), key=lambda kv: kv[1].get("gameTime") or ""):
    host = (g.get("hostTeam") or {}).get("teamName")
    guest = (g.get("guestTeam") or {}).get("teamName")
    lg = g.get("league") or {}
    st = g.get("leagueStage") or {}
    ag = g.get("afterGame") or {}
    print(gid, g.get("gameTime"), "|", host, "-", guest, "|", lg.get("leagueName") if isinstance(lg, dict) else lg,
          "|", st.get("stageName") if isinstance(st, dict) else st,
          "| session", json.dumps(g.get("session"), ensure_ascii=False),
          "| after", json.dumps(ag, ensure_ascii=False)[:160])
print(json.dumps(next(iter(seen.values())), ensure_ascii=False)[:3000])
