"""Transfermarkt, the cross-check source every club's scraper can use: URLs and parsers for saved pages.

Usage:
  uv run --with beautifulsoup4 python -I -u transfermarkt.py fixtures <spielplan.html>
  uv run --with beautifulsoup4 python -I -u transfermarkt.py squadstats <leistungsdaten.html>
  uv run --with beautifulsoup4 python -I -u transfermarkt.py report <spielbericht.html>

Importable: squadstats_url(club_slug, club_id, season_start), parse_fixtures(html), parse_squadstats(html),
parse_report(html). A club is its Transfermarkt slug and id (Hapoel Tel Aviv: "hapoel-tel-aviv", 1017).
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from bs4 import BeautifulSoup



def squadstats_url(club_slug: str, club_id: int, season_start: int) -> str:
    """All competitions of the season that starts in `season_start`, every player's appearances and minutes."""
    return f"https://www.transfermarkt.com/{club_slug}/leistungsdaten/verein/{club_id}/reldata/%26{season_start}/plus/1"


def text(el) -> str:
    return " ".join(el.get_text(" ").split()) if el else ""


def parse_fixtures(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for box in soup.select("div.box"):
        head = box.select_one("h2, .content-box-headline")
        comp = text(head)
        table = box.select_one("table")
        if not table or not box.select("a[href*='/spielbericht/index/spielbericht/']"):
            continue
        for tr in table.select("tbody tr"):
            tds = tr.find_all("td", recursive=False)
            if len(tds) < 8:
                continue
            link = tr.select_one("a[href*='/spielbericht/index/spielbericht/']")
            cells = [text(td) for td in tds]
            out.append({
                "competition": comp,
                "cells": cells,
                "report_id": re.search(r"/spielbericht/(\d+)", link["href"]).group(1) if link else None,
                "result": text(link) if link else None,
            })
    return out


def parse_squadstats(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "html.parser")
    table = soup.select_one("table.items")
    head = [text(th) or (th.get("title") or "") for th in table.select("thead th")]
    heads_title = []
    for th in table.select("thead th"):
        t = th.get("title") or ""
        span = th.select_one("[title]")
        heads_title.append(t or (span.get("title") if span else "") or text(th))
    rows = []
    for tr in table.select("tbody > tr"):
        tds = tr.find_all("td", recursive=False)
        if not tds:
            continue
        name_a = tr.select_one("td.hauptlink a[href*='/profil/spieler/']")
        pid = re.search(r"/spieler/(\d+)", name_a["href"]).group(1) if name_a else None
        rows.append({
            "tm_id": pid,
            "name": text(name_a),
            "slug": name_a["href"].split("/")[1] if name_a else None,
            "cells": [text(td) for td in tds],
        })
    return {"head": head, "head_titles": heads_title, "rows": rows}


def _player_links(el) -> list[tuple[str, str]]:
    out = []
    for a in el.select("a[href*='/profil/spieler/'], a[href*='/spieler/']"):
        m = re.search(r"/spieler/(\d+)", a.get("href", ""))
        if m:
            out.append((m.group(1), a.get("title") or text(a)))
    return out


def parse_report(html: str) -> dict:
    """Line-ups and substitutions from a TM match report (spielbericht)."""
    soup = BeautifulSoup(html, "html.parser")
    res = {"title": text(soup.title), "teams": [], "subs": [], "cards": [], "goals": []}
    # team names in the header
    for a in soup.select(".sb-team .sb-vereinslink, .sb-heim a.sb-vereinslink, .sb-gast a.sb-vereinslink"):
        m = re.search(r"/verein/(\d+)", a.get("href", ""))
        res["teams"].append({"club_id": m.group(1) if m else None, "name": text(a)})
    res["result"] = text(soup.select_one(".sb-endstand"))
    res["date_line"] = text(soup.select_one(".sb-datum"))
    res["competition"] = text(soup.select_one(".direct-headline__header, .spielbericht-headline h2, .data-header__club"))
    # line-ups: two .large-6 columns inside the "Line-Ups" box; each has an aufstellung box
    lineups = []
    for box in soup.select("div.box"):
        head = text(box.select_one("h2"))
        if head.lower().startswith("line-ups") or "Line-Ups" in head:
            for col in box.select("div.large-6.columns, div.large-6"):
                club_a = col.select_one("a[href*='/verein/']")
                club_id = re.search(r"/verein/(\d+)", club_a["href"]).group(1) if club_a else None
                starters = []
                # formation view: .aufstellung-spieler-container ... ; list view: table rows
                for sp in col.select(".aufstellung-spieler-container"):
                    links = _player_links(sp)
                    if links:
                        starters.append(links[0])
                bench = []
                for tr in col.select("table.ersatzbank tr"):
                    links = _player_links(tr)
                    if links:
                        bench.append(links[0])
                starting_list = []
                if not starters:
                    for tr in col.select("table.items tr, table tr"):
                        links = _player_links(tr)
                        if links:
                            starting_list.append(links[0])
                manager = None
                lineups.append({"club_id": club_id, "club": text(club_a), "starters": starters,
                                "bench": bench, "list_fallback": starting_list})
    res["lineups"] = lineups
    # substitutions box
    for box in soup.select("div.box"):
        head = text(box.select_one("h2"))
        if head.startswith("Substitutions"):
            for li in box.select("li"):
                club_a = li.select_one(".sb-aktion-wappen a[href*='/verein/']")
                club_id = re.search(r"/verein/(\d+)", club_a["href"]).group(1) if club_a else None
                on = li.select_one(".sb-aktion-spielerwechsel-ein, .sb-aktion-wechsel-ein")
                off = li.select_one(".sb-aktion-spielerwechsel-aus, .sb-aktion-wechsel-aus")
                clock = li.select_one(".sb-sprite-uhr-klein, .sb-aktion-uhr span")
                minute = None
                style = clock.get("style", "") if clock else ""
                m = re.search(r"background-position:\s*-?(\d+)px\s+-?(\d+)px", style)
                if m:
                    x, y = int(m.group(1)), int(m.group(2))
                    minute = (x // 36) + 1 + (y // 36) * 10
                extra = text(clock) if clock else ""
                res["subs"].append({
                    "club_id": club_id,
                    "on": _player_links(on)[0] if on and _player_links(on) else None,
                    "off": _player_links(off)[0] if off and _player_links(off) else None,
                    "minute": minute,
                    "clock_text": extra,
                })
        if head.startswith("Cards"):
            for li in box.select("li"):
                club_a = li.select_one(".sb-aktion-wappen a[href*='/verein/']")
                club_id = re.search(r"/verein/(\d+)", club_a["href"]).group(1) if club_a else None
                who = _player_links(li.select_one(".sb-aktion-aktion") or li)
                kind = text(li.select_one(".sb-aktion-aktion"))
                clock = li.select_one(".sb-sprite-uhr-klein")
                style = clock.get("style", "") if clock else ""
                m = re.search(r"background-position:\s*-?(\d+)px\s+-?(\d+)px", style)
                minute = (int(m.group(1)) // 36) + 1 + (int(m.group(2)) // 36) * 10 if m else None
                res["cards"].append({"club_id": club_id, "player": who[0] if who else None,
                                     "kind": kind, "minute": minute, "clock_text": text(clock)})
    return res


def main() -> int:
    mode, path = sys.argv[1], Path(sys.argv[2])
    html = path.read_text(encoding="utf-8")
    if mode == "fixtures":
        for f in parse_fixtures(html):
            print(f["competition"], "|", f["cells"], "|", f["report_id"], f["result"])
    elif mode == "squadstats":
        d = parse_squadstats(html)
        print(d["head"])
        print(d["head_titles"])
        for r in d["rows"]:
            print(r["tm_id"], r["name"], r["cells"])
    elif mode == "report":
        print(json.dumps(parse_report(html), ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
