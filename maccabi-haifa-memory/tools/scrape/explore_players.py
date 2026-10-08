"""Exploration: list the players carried in a saved /players page's flight payload.

Usage: python -I explore_players.py <tools-dir> <players.html>
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, sys.argv[1])
from rsc import find_values, flight_text  # noqa: E402

html = open(sys.argv[2], encoding="utf-8").read()
text = flight_text(html)
print("flight chars", len(text))
groups = find_values(text, "sortedPlayersByRole")
print("sortedPlayersByRole occurrences", len(groups))
g = groups[0]
n = 0
for grp in g:
    role = grp["playerRole"]["role"]
    print("==", role, len(grp["playersByRole"]))
    for p in grp["playersByRole"]:
        n += 1
        en = next((l for l in p.get("localizations", []) if l.get("locale") == "en"), {})
        st = p.get("statistics") or {}
        bp = p.get("basePlayer") or {}
        per = bp.get("statisticsPerLeagues") or []
        print(
            p["id"], repr(p["playerName"]), p["playerShirtNumber"], "|", en.get("playerName"),
            "|", (p.get("playerPosition") or {}).get("position"),
            "| stats", st.get("appearances"), st.get("goals"), st.get("assists"),
            "| upd", p.get("updatedAt"), "| base", bp.get("id"), bp.get("updatedAt"),
            "| perLeague apps", sum((x.get("appearances") or 0) for x in per),
            "| img", (p.get("profileImage") or {}).get("url"), "| body", (p.get("bodyProfileImage") or {}).get("url") if p.get("bodyProfileImage") else None,
        )
print("total", n)
print("keys player", list(g[0]["playersByRole"][0].keys()))
print("keys base", list(g[0]["playersByRole"][0]["basePlayer"].keys()))
for k in ("session", "season"):
    vals = find_values(text, k)
    print(k, json.dumps(vals[:3], ensure_ascii=False)[:400], "distinct", sorted({json.dumps(v, ensure_ascii=False) for v in vals})[:10])
