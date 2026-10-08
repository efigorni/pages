"""Parse the htafc.co.il homepage fixture list ("לוח משחקים" popup + the upcoming strip).

Usage: uv run --with beautifulsoup4 python -I -u club_fixtures.py <home.html> [--json <out.json>]
Prints one line per match item: date, time, venue, home, away, score, competition logo file.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bs4 import BeautifulSoup


def text(el) -> str:
    return " ".join(el.get_text(" ").split()) if el else ""


def parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for item in soup.select("div.matches-list__match-item"):
        place = [text(s) for s in item.select(".matches-list__match-item__place span")]
        t1 = item.select_one(".matches-list__match-item__team-1")
        t2 = item.select_one(".matches-list__match-item__team-2")
        score = [text(s) for s in item.select(".matches-list__match-item__score span")]
        logo = item.select_one(".matches-list__match-item__ligue img")
        in_popup = item.find_parent(id="popup-matches-list") is not None
        out.append({
            "place": place,
            "home": text(t1.select_one(".matches-list__match-item__name, .matches-list__match-item__team-name")) if t1 else "",
            "away": text(t2.select_one(".matches-list__match-item__name, .matches-list__match-item__team-name")) if t2 else "",
            "score": score,
            "competition_logo": (logo.get("src") or "").rsplit("/", 1)[-1] if logo else None,
            "in_popup": in_popup,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("home", type=Path)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args()
    items = parse(a.home.read_text(encoding="utf-8"))
    for i, m in enumerate(items):
        print(i, "popup" if m["in_popup"] else "strip", m["place"], m["home"], "-", m["away"], m["score"], m["competition_logo"])
    if a.json:
        a.json.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
