"""Exploration: consistency check of every saved game page (line-up vs team.players vs events).

Usage: python -I check_games.py <tools-dir> <games-dir>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from rsc import page_objects  # noqa: E402

CLUB = "מכבי חיפה"

for path in sorted(Path(sys.argv[2]).glob("*.html")):
    html = path.read_text(encoding="utf-8")
    mgs = page_objects(html, lambda o: "gameLineUp" in o and "team" in o)
    mg = max(mgs, key=lambda o: len(json.dumps(o)))
    games = page_objects(html, lambda o: "hostTeam" in o and "gameDetails" in o and o.get("id") == int(path.stem))
    g = games[0] if games else {}
    gd = g.get("gameDetails") or {}
    lu = (mg.get("gameLineUp") or {}).get("team") or {}
    starters = []
    for line, entries in lu.items():
        if isinstance(entries, dict):
            entries = [entries]
        for e in entries or []:
            p = e.get("player") or {}
            starters.append((p.get("id"), p.get("playerName"), e.get("isComposition"), line))
    tp = (mg.get("team") or {}).get("players") or []
    by_entry = {e["id"]: e for e in tp}
    st_ids = {s[0] for s in starters}
    came_on, went_off, unused, full = [], [], [], []
    for e in tp:
        pid = (e.get("player") or {}).get("id")
        if pid in st_ids:
            (went_off if e.get("isSubstitution") else full).append(e["playerName"])
        elif e.get("isSubstitution"):
            came_on.append(e["playerName"])
        else:
            unused.append(e["playerName"])
    subs_ev = []
    for ev in mg.get("gameEvents") or []:
        et = (ev.get("eventType") or {}).get("key")
        if et == "SUBSTITUTION" and ev.get("teamName") == CLUB:
            pin = (ev.get("substitution") or {}).get("playerIn") or {}
            pin_entry = by_entry.get(pin.get("playerID"))
            subs_ev.append((ev.get("gameTime"), (ev.get("player") or {}).get("playerName"), pin.get("playerName"), (pin_entry or {}).get("playerName")))
    reds = [(ev.get("gameTime"), (ev.get("player") or {}).get("playerName")) for ev in mg.get("gameEvents") or []
            if (ev.get("eventType") or {}).get("key") in ("RED-CARD", "RED_CARD", "SECOND-YELLOW") and ev.get("teamName") == CLUB]
    tp_starters = [e["playerName"] for e in tp if (e.get("player") or {}).get("id") in st_ids]
    print(f"== {path.stem} {gd.get('gameTime')} {(g.get('hostTeam') or {}).get('teamName')} - {(g.get('guestTeam') or {}).get('teamName')} "
          f"| {(g.get('leagueStageBySession') or {}).get('stageName')} | score {(mg.get('gameDetails') or {}).get('hostTeamScore')}:{(mg.get('gameDetails') or {}).get('guestTeamScore')} "
          f"| synced {mg.get('gameSynced')} | overtime {(mg.get('gameDetails') or {}).get('isGameOverTime')}")
    print(f"   lineup starters {len(starters)} | team.players {len(tp)} | starters in team.players {len(tp_starters)} | came_on {len(came_on)} | unused {len(unused)}")
    print(f"   came on (team.players): {came_on}")
    print(f"   sub events: {subs_ev}")
    print(f"   subbed off (team.players): {went_off}")
    print(f"   lineup comp=False: {[s[1] for s in starters if not s[2]]}")
    print(f"   unused: {unused}")
    if reds:
        print(f"   reds: {reds}")
    missing = [s[1] for s in starters if s[0] not in {(e.get('player') or {}).get('id') for e in tp}]
    if missing:
        print(f"   STARTERS NOT IN team.players: {missing}")
    times = {e['playerName']: e.get('substitutionTime') for e in tp if e.get('isSubstitution')}
    print(f"   sub times: {times}")
    other_types = sorted({(ev.get('eventType') or {}).get('key') or (ev.get('gameEventType') or {}).get('key') for ev in mg.get('gameEvents') or []} - {None})
    print(f"   event types: {other_types}")
