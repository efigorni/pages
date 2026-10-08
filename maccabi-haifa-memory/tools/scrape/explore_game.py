"""Exploration: compact dump of one saved game page's synced game-management record.

Usage: python -I explore_game.py <tools-dir> <game.html>
"""

from __future__ import annotations

import json
import sys

sys.path.insert(0, sys.argv[1])
from rsc import page_objects  # noqa: E402

html = open(sys.argv[2], encoding="utf-8").read()
mg = max(page_objects(html, lambda o: "gameLineUp" in o), key=lambda o: len(json.dumps(o)))
print("entry:", mg.get("entryDescription"), "| synced:", mg.get("gameSynced"))
print("details:", json.dumps(mg.get("gameDetails"), ensure_ascii=False))
lu = (mg.get("gameLineUp") or {}).get("team") or {}
print("lineup keys:", list(lu.keys()))
for line, entries in lu.items():
    if isinstance(entries, dict):
        entries = [entries]
    for e in entries or []:
        p = e.get("player") or {}
        print(f"  {line:22s} comp={e.get('isComposition')!s:5s} #{p.get('playerShirtNumber')} {p.get('playerName')} (id {p.get('id')})")
team = mg.get("team") or {}
print("team keys:", list(team.keys()), "coach:", team.get("coach"))
for e in team.get("players") or []:
    p = e.get("player") or {}
    print(
        f"  comp={e.get('isComposition')!s:5s} sub={e.get('isSubstitution')!s:5s} t={e.get('substitutionTime')!r:8s} "
        f"g={e.get('goals')} a={e.get('assists')} y={e.get('yellowCards')} r={e.get('redCard')} "
        f"#{p.get('playerShirtNumber')} {e.get('playerName')} (id {p.get('id')}) extra={[k for k in e.keys() if k not in ('id','isComposition','playerName','goals','assists','isSubstitution','substitutionTime','yellowCards','redCard','player')]}"
    )
print("events:")
for ev in mg.get("gameEvents") or []:
    sub = ev.get("substitution")
    pl = ev.get("player") or {}
    print(
        f"  t={ev.get('gameTime')!r} type={json.dumps(ev.get('gameEventType'), ensure_ascii=False)[:60]} eventType={json.dumps(ev.get('eventType'), ensure_ascii=False)[:60]} "
        f"title={ev.get('title')!r} player={pl.get('playerName') if isinstance(pl, dict) else pl} team={ev.get('teamName')} goal={ev.get('isTeamGoal')} "
        f"sub={json.dumps(sub, ensure_ascii=False)[:300] if sub else None}"
    )
other = {k: v for k, v in mg.items() if k not in ("gameLineUp", "team", "gameEvents", "gameDetails")}
print("other:", json.dumps(other, ensure_ascii=False)[:800])
