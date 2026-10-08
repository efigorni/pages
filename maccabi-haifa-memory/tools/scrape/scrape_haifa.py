"""Scrape the Maccabi Haifa FC senior squad (www.mhaifafc.com, Hebrew site) for the memory game.

Sources (all server-rendered Next.js pages; the data sits in the page's flight payload):
  * /players                 the squad as displayed: cards (number, name lines, position, photo), plus
                             per-player CMS data (English name, original photo, role, position)
  * /players/<id>            the individual page: header (name, number, position, "הופעות / בישולים /
                             שערים") and the career table "סטטיסטיקה כללית" (club totals per competition)
  * /history?tab=כל העונות   the current season's games (played + upcoming)
  * /matches/<id>            each played game's synced record: starting line-up, every squad member with
                             substitution minute / goals / assists / cards, and the event log

The individual page's "הופעות" is NOT season-specific (see docs/data.md): for returning players it is last
season's total carried into the new season entry plus this season's games. The season metric is therefore
counted from the game records, which is exactly what the site adds to that header after each game.

Usage:
  uv run --with requests --with beautifulsoup4 --with pillow python -I -u scrape_haifa.py --out <data-dir> \
      [--refresh] [--delay 0.6] [--pool-size 23] [--crop x0,y0,x1,y1] [--crop-override ID=x0,y0,x1,y1] \
      [--design-dir <data-dir>/design] [--mark-ready]

Everything downloaded is treated as data: HTML is parsed, never executed.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import os
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from urllib.parse import quote, unquote

sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script dir; these helpers are ours
sys.path.insert(1, str(Path(__file__).resolve().parents[3] / "_memory-game/tools/tts"))  # hebrew.py
sys.path.insert(2, str(Path(__file__).resolve().parents[3] / "_memory-game/tools/images"))  # framing.py

from bs4 import BeautifulSoup  # noqa: E402
from PIL import Image  # noqa: E402

from fetch import Fetcher, log_line  # noqa: E402
from framing import landmarks, square_crop  # noqa: E402
from hebrew import nickname  # noqa: E402
from rsc import page_objects  # noqa: E402

BASE = "https://www.mhaifafc.com"
PLAYERS_URL = BASE + "/players"
HISTORY_URL = BASE + "/history?tab=" + quote("כל העונות")
CDN = "https://images.api.mhaifafc.com/"
CLUB_HE = "מכבי חיפה"
GK_SECTION = "שוערים"
SECTION_EN = {"שוערים": "goalkeeper", "הגנה": "defender", "קישור": "midfielder", "התקפה": "forward"}
POSITION_EN = {  # translation of the site's Hebrew position labels (the site shows no English positions)
    "שוער": "Goalkeeper", "בלם": "Centre-back", "מגן ימני": "Right-back", "מגן שמאלי": "Left-back",
    "קשר": "Midfielder", "קשר אחורי": "Defensive midfielder", "קשר התקפי": "Attacking midfielder",
    "כנף": "Winger", "חלוץ": "Striker",
}
FULL_MATCH = 90
TRANSLIT_EXTRA = {"ł": "l", "Ł": "l", "đ": "d", "Đ": "d", "ø": "o", "Ø": "o", "æ": "ae", "ß": "ss", "ı": "i"}


def log(msg: str) -> None:
    log_line(msg)


def clean(text: str | None) -> str:
    text = unicodedata.normalize("NFC", text or "")
    for ch in ("‏", "‎", "‪", "‫", "‬", "\xa0"):
        text = text.replace(ch, " " if ch == "\xa0" else "")
    return re.sub(r"\s+", " ", text).strip()


def ascii_slug(text: str) -> str:
    text = "".join(TRANSLIT_EXTRA.get(c, c) for c in text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"['’`]", "", text.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def speak_he(name: str) -> tuple[str, str | None]:
    """H4: the text inside a trailing (...) when there is one, else the full name."""
    nick = nickname(name)
    return (nick, nick) if nick else (name, None)


def minute(text) -> int | None:
    m = re.search(r"(\d+)(?:\s*\+\s*(\d+))?", str(text or ""))
    if not m:
        return None
    return int(m.group(1)) + (int(m.group(2)) if m.group(2) else 0)


def int_or_none(text) -> int | None:
    m = re.search(r"-?\d+", str(text or ""))
    return int(m.group(0)) if m else None


def write_json_atomic(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


# ---------------------------------------------------------------- /players

def parse_cards(html: str) -> list[dict]:
    """The squad exactly as the /players cards display it (streamed content block S:1)."""
    start = html.find('<div hidden id="S:1">')
    end = html.find("<script", start)
    soup = BeautifulSoup(html[start:end] if start >= 0 else html, "html.parser")
    cards, section = [], None
    for el in soup.find_all(["div", "a"]):
        cls = " ".join(el.get("class") or [])
        if el.name == "div" and cls == "text-4xl font-medium":
            section = clean(el.get_text())
            continue
        href = el.get("href", "") if el.name == "a" else ""
        if not re.fullmatch(r"/players/\d+", href):
            continue
        num = el.select_one("span.text-gradient-shirt-number")
        lines = [clean(sp.get_text()) for sp in el.select("div.absolute.bottom-0 span")]
        imgs = el.find_all("img")
        cards.append({
            "site_id": int(href.rsplit("/", 1)[1]),
            "href": href,
            "section_he": section,
            "number_text": clean(num.get_text()) if num else None,
            "name_lines": lines[:2],
            "position_he": lines[2] if len(lines) > 2 else None,
            "cover_src": imgs[0].get("src") if imgs else None,
            "photo_src": imgs[1].get("src") if len(imgs) > 1 else None,
        })
    return cards


def payload_players(html: str) -> tuple[dict[int, dict], dict]:
    groups = page_objects(html, lambda o: "playersByRole" in o and "playerRole" in o)
    out: dict[int, dict] = {}
    for g in groups:
        for p in g.get("playersByRole") or []:
            out.setdefault(p["id"], p)
    covers = page_objects(html, lambda o: "playerCardCoverImage" in o)
    meta = {"card_cover_url": ((covers[0].get("playerCardCoverImage") or {}).get("url")) if covers else None}
    sessions = page_objects(html, lambda o: "session" in o and isinstance(o.get("session"), dict) and "players" in o)
    meta["season"] = (sessions[0]["session"].get("session") if sessions else None)
    return out, meta


# ---------------------------------------------------------------- /players/<id>

def parse_player_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    out: dict = {}
    band = soup.select_one("div.bg-blackLight")
    if band:
        num = band.select_one("span.text-secondary")
        name = band.select_one("span.text-white.text-5xl")
        pos = band.select_one("span.text-white.text-2xl")
        out["number_text"] = clean(num.get_text()) if num else None
        out["name"] = clean(name.get_text()) if name else None
        out["position"] = clean(pos.get_text()) if pos else None
    stats = {}
    for lab in soup.select("span.text-xl.text-blackLight"):
        val = lab.find_next_sibling("span")
        stats[clean(lab.get_text())] = int_or_none(val.get_text()) if val else None
    out["header_stats"] = stats
    career = []
    title = soup.find(string=re.compile("סטטיסטיקה כללית"))
    table = title.find_parent().find_next("table") if title else None
    if table:
        heads = [clean(th.get_text()) for th in table.select("thead th")]
        for tr in table.select("tbody tr"):
            cells = [clean(td.get_text()) for td in tr.find_all("td")]
            row = dict(zip(heads, cells))
            career.append({
                "competition": row.get("מפעל"),
                "appearances": int_or_none(row.get("הופעות")),
                "goals": int_or_none(row.get("שערים")),
                "assists": int_or_none(row.get("בישולים")),
                "yellows": int_or_none(row.get("צהובים")),
                "reds": int_or_none(row.get("אדומים")),
            })
    out["career_table"] = career
    title_tag = soup.find("title")
    out["title"] = clean(title_tag.get_text()) if title_tag else None
    objs = page_objects(html, lambda o: "statistics" in o and "basePlayer" in o and "playerShirtNumber" in o)
    out["payload"] = objs[0] if objs else {}
    return out


# ---------------------------------------------------------------- games

def season_games(html: str, season: str) -> list[dict]:
    games = {}
    for g in page_objects(html, lambda o: "hostTeam" in o and "gameDetails" in o and "entryDescription" in o):
        games.setdefault(g["id"], g)
    out = []
    for gid, g in games.items():
        desc = clean(g.get("entryDescription"))
        if season not in desc:
            continue
        mg = g.get("gameMGMT") or {}
        gd = mg.get("gameDetails") or {}
        out.append({
            "id": gid,
            "entry": desc,
            "time": (g.get("gameDetails") or {}).get("gameTime"),
            "stage": (g.get("leagueStageBySession") or {}).get("stageName"),
            "host": (g.get("hostTeam") or {}).get("teamName"),
            "guest": (g.get("guestTeam") or {}).get("teamName"),
            "finished": bool(gd.get("isGameFinished")),
            "synced": mg.get("gameSynced"),
        })
    return sorted(out, key=lambda x: x["time"] or "")


def parse_game(html: str, gid: int) -> dict:
    mgs = page_objects(html, lambda o: "gameLineUp" in o and "team" in o)
    mg = max(mgs, key=lambda o: len(json.dumps(o))) if mgs else {}
    heads = [g for g in page_objects(html, lambda o: "hostTeam" in o and "gameDetails" in o) if g.get("id") == gid]
    head = heads[0] if heads else {}
    lineup = (mg.get("gameLineUp") or {}).get("team") or {}
    starters = []
    for line, entries in lineup.items():
        for e in ([entries] if isinstance(entries, dict) else entries or []):
            p = e.get("player") or {}
            if p.get("id") is not None:
                starters.append({"site_id": p["id"], "name": clean(p.get("playerName")), "line": line,
                                 "finished_on_pitch": e.get("isComposition")})
    squad = []
    for e in (mg.get("team") or {}).get("players") or []:
        p = e.get("player") or {}
        squad.append({
            "entry_id": e.get("id"),
            "site_id": p.get("id"),
            "name": clean(e.get("playerName")),
            "number": int_or_none(p.get("playerShirtNumber")),
            "is_composition": e.get("isComposition"),
            "is_substitution": e.get("isSubstitution"),
            "substitution_time": e.get("substitutionTime"),
            "goals": e.get("goals") or 0,
            "assists": e.get("assists") or 0,
            "yellow_cards": e.get("yellowCards") or 0,
            "red_card": bool(e.get("redCard")),
        })
    by_entry = {s["entry_id"]: s for s in squad}
    events = []
    for ev in mg.get("gameEvents") or []:
        key = (ev.get("eventType") or {}).get("key") or (ev.get("gameEventType") or {}).get("key")
        if key in ("SUBSTITUTION", "RED-CARD", "GOAL", "OWN_GOAL") and ev.get("teamName") == CLUB_HE:
            pin = ((ev.get("substitution") or {}).get("playerIn") or {})
            events.append({
                "minute_text": ev.get("gameTime"),
                "type": key,
                "player": clean((ev.get("player") or {}).get("playerName")),
                "player_in": clean(pin.get("playerName")) or None,
                "player_in_site_id": (by_entry.get(pin.get("playerID")) or {}).get("site_id"),
            })
    details = mg.get("gameDetails") or {}
    return {
        "id": gid,
        "entry": clean(mg.get("entryDescription")),
        "time": (head.get("gameDetails") or {}).get("gameTime"),
        "stage": (head.get("leagueStageBySession") or {}).get("stageName"),
        "host": (head.get("hostTeam") or {}).get("teamName"),
        "guest": (head.get("guestTeam") or {}).get("teamName"),
        "score": [details.get("hostTeamScore"), details.get("guestTeamScore")],
        "finished": details.get("isGameFinished"),
        "synced": mg.get("gameSynced"),
        "coach": (mg.get("team") or {}).get("coach"),
        "starters": starters,
        "squad": squad,
        "events": events,
    }


def game_roles(game: dict) -> dict[int, dict]:
    """Per player: start / sub_on / unused_sub with approximate minutes (from the line-up record)."""
    starter_ids = {s["site_id"] for s in game["starters"]}
    red_minutes = {}
    for ev in game["events"]:
        if ev["type"] == "RED-CARD":
            red_minutes[ev["player"]] = minute(ev["minute_text"])
    out = {}
    for s in game["squad"]:
        pid = s["site_id"]
        t = minute(s["substitution_time"]) if s["is_substitution"] else None
        red = red_minutes.get(s["name"]) if s["red_card"] else None
        if pid in starter_ids:
            end = min(x for x in (t, red, FULL_MATCH) if x is not None)
            role, mins = "start", end
        elif s["is_substitution"]:
            end = min(x for x in (red, FULL_MATCH) if x is not None)
            role, mins = "sub_on", max(1, end - (t if t is not None else FULL_MATCH))
        else:
            role, mins = "unused_sub", 0
        out[pid] = {"role": role, "minutes": mins, "goals": s["goals"], "assists": s["assists"],
                    "sub_minute": t}
    for s in game["starters"]:  # a starter missing from the squad list still started
        out.setdefault(s["site_id"], {"role": "start", "minutes": FULL_MATCH, "goals": 0, "assists": 0, "sub_minute": None})
    return out


def game_anomalies(game: dict) -> list[str]:
    notes = []
    starter_ids = {s["site_id"] for s in game["starters"]}
    if len(starter_ids) != 11:
        notes.append(f"line-up has {len(starter_ids)} starters")
    subs = [e for e in game["events"] if e["type"] == "SUBSTITUTION"]
    outs = [e["player"] for e in subs]
    dup = sorted({o for o in outs if outs.count(o) > 1})
    if dup:
        notes.append(f"event log subs off the same player twice: {', '.join(dup)}")
    came_on = {s["name"] for s in game["squad"] if s["is_substitution"] and s["site_id"] not in starter_ids}
    ev_in = {e["player_in"] for e in subs if e["player_in"]}
    if came_on != ev_in:
        notes.append(f"came on per line-up record {sorted(came_on - ev_in)} vs per event log {sorted(ev_in - came_on)}")
    starters_named = {s["name"] for s in game["starters"]}
    ev_out_not_starter = sorted({o for o in outs if o and o not in starters_named and o not in came_on
                                 and not any(o.replace("'", "") == n.replace("'", "") for n in starters_named)})
    if ev_out_not_starter:
        notes.append(f"event log subs off a non-starter: {', '.join(ev_out_not_starter)}")
    off_record = sum(1 for s in game["squad"] if s["site_id"] in starter_ids and s["is_substitution"])
    if off_record != len(subs):
        notes.append(f"{len(subs)} substitutions in the event log but {off_record} starters marked subbed off")
    return notes


# ---------------------------------------------------------------- photos

def inspect_image(data: bytes) -> dict:
    img = Image.open(io.BytesIO(data))
    img.load()
    rgba = img.convert("RGBA")
    alpha = rgba.getchannel("A")
    hist = alpha.histogram()
    total = img.width * img.height
    return {
        "format": img.format,
        "mode": img.mode,
        "px": [img.width, img.height],
        "has_alpha": alpha.getextrema()[0] < 255,
        "transparent_share": round(hist[0] / total, 3),
        "alpha_levels": sum(1 for v in hist if v),
        "bytes": len(data),
        "sha1": hashlib.sha1(data).hexdigest(),
    }


# ---------------------------------------------------------------- design tokens

def design_tokens(data_dir: Path, design_dir: Path, css_text: str, cover_url: str | None) -> dict:
    def rule(sel: str) -> str | None:
        m = re.search(re.escape(sel) + r"\s*\{([^}]*)\}", css_text)
        return m.group(1) if m else None

    def rgb_hex(sel: str) -> str | None:
        m = re.search(r"rgb\((\d+) (\d+) (\d+)", rule(sel) or "")
        return "#%02x%02x%02x" % tuple(int(x) for x in m.groups()) if m else None

    faces = re.findall(r"@font-face\{font-family:([^;]+);[^}]*?src:url\(([^)]+)\)", css_text)
    computed = {}
    cs_path = design_dir / "computed-styles.json"
    if cs_path.exists():
        cs = json.loads(cs_path.read_text(encoding="utf-8")).get("w1440", {})
        keep = ("font-family", "font-weight", "font-size", "line-height", "letter-spacing", "color",
                "background-image", "box")
        for k in ("card_wrapper", "card_number", "card_first_name", "card_last_name", "card_position",
                  "card_bottom_shadow", "page_title_h1", "section_titles"):
            v = cs.get(k)
            if isinstance(v, list):
                v = v[0] if v else None
            computed[k] = {kk: v.get(kk) for kk in keep} if v else None

    def rel(p: Path) -> str | None:
        return str(p.relative_to(data_dir)) if p.exists() else None

    shots = {name: rel(design_dir / name) for name in (
        "players-1440-full.png", "players-960-full.png", "players-cards-closeup.png",
        "players-cards-closeup-parens-1.png", "players-cards-closeup-parens-2.png")}
    return {
        "card_ground": "#204126",
        "card_stripes": "#ffffff",
        "card_stripe_mask": "#d9d9d9",
        "primary_green": rgb_hex(".text-primary"),
        "secondary_green": rgb_hex(".bg-secondary"),
        "dark_green": rgb_hex(".bg-darkGreen"),
        "row_green": rgb_hex(".bg-greenRow"),
        "white": "#ffffff",
        "black": "#000000",
        "name_font": "Atlas AAA, Hebrew cut (CSS families Atlas-AAA-Bold / __atlasBoldHE for the surname line, "
                     "Atlas-AAA-Regular / __atlasRegularHE for the first-name and position lines)",
        "number_font": "Atlas AAA, Hebrew cut, Medium (Atlas-AAA-Medium / __atlasMediumHE)",
        "font_licence": "proprietary: self-hosted by the club from /_next/static/media/ (AtlasAAA-*.woff2, "
                        "atlas-*-aaa.otf); no open-licence notice anywhere in the CSS; not on Google Fonts. Do not "
                        "download or self-host it; use an OFL Hebrew stand-in (H5).",
        "background": {
            "card_cover_url": cover_url,
            "card_cover_file": rel(design_dir / "player-card-cover.svg"),
            "card_cover_px": [292, 356],
            "card_cover_recipe": (
                "solid #204126; 18 thin white 45° pinstripes (top-left to bottom-right, ~9.7 px apart on a "
                "290 px card, stopping at ~75% of the height) under an alpha mask: horizontal gradient "
                "#d9d9d9 74%→37%→0% opacity (left→right) times 0.6; then a bottom band (y 254→355 of 356) "
                "black 0→51% opacity"),
            "bottom_shadow_css": "linear-gradient(360deg, #000, transparent) over the bottom half of the card",
            "number_css": "linear-gradient(180deg, #fff 33%, #ffffff00 97.3%) clipped to the text "
                          "(background-clip: text; -webkit-text-fill-color: transparent)",
            "page_hero_url": CDN + "2627_12352716c7.svg",
            "page_hero_file": rel(design_dir / "players-hero.svg"),
            "page_hero_photo_file": rel(design_dir / "players-hero-photo.jpg"),
            "page_hero_note": "4 MB SVG wrapping a 3280x2187 JPEG team-huddle photo; page decoration only",
            "page_ground": "#ffffff",
            "footer_ground": rgb_hex(".bg-secondary"),
        },
        "screenshots": shots,
        "details": {
            "card_px": [290, 354],
            "card_px_mobile": [160, 246],
            "card_radius_px": 6,
            "layout": "number top-start (RTL: top-right) with 18px inline-start / 12px top padding; cutout photo "
                      "object-fit cover, object-position top, full card; name block bottom-start with 8px side / "
                      "24px bottom padding: first-name line, surname line, position line",
            "number": {"font": "Atlas Medium HE", "weight": 500, "size_px": 60, "line_height_px": 60,
                       "size_px_mobile": 36},
            "first_name_line": {"font": "Atlas Regular HE", "weight": 400, "size_px": 24, "size_px_mobile": 20,
                                "colour": "#ffffff"},
            "surname_line": {"font": "Atlas Bold HE", "weight": 700, "size_px": 48, "size_px_mobile": 36,
                             "letter_spacing": "-0.05em (-2.4px at 48px)", "colour": "#ffffff"},
            "position_line": {"font": "Atlas Regular HE", "weight": 400, "size_px": 20, "size_px_mobile": 18,
                              "colour": "#ffffff"},
            "name_split": "the card puts everything before the last space on the first line and the last word "
                          "(or the trailing parenthetical) on the bold line",
            "font_faces": [{"family": f, "src": BASE + u if u.startswith("/") else u} for f, u in faces],
            "css_vars": {"--atlas-regular": "Atlas Regular HE", "--atlas-medium": "Atlas Medium HE",
                         "--atlas-bold": "Atlas Bold HE", "--atlas-light": "Atlas Light HE"},
            "palette": {
                "primary": rgb_hex(".text-primary"), "secondary": rgb_hex(".bg-secondary"),
                "darkGreen": rgb_hex(".bg-darkGreen"), "greenRow": rgb_hex(".bg-greenRow"),
                "lightGreenPoint": rgb_hex(".bg-lightGreenPoint"), "grayLight": rgb_hex(".text-grayLight"),
                "gradients": {"startGreenGrad": "#294f31", "throughGreenGrad": "#5ab76c",
                              "stopsGreenGrad": "#284d2f", "modalTopGreen": "#1d5318",
                              "modalCenterGreen": "#5e9159", "modalBottomGreen": "#3a7735"},
            },
            "computed_1440": computed,
        },
    }


# ---------------------------------------------------------------- main

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path, help="data dir (html/ cache, raw/ photos, players.json)")
    ap.add_argument("--delay", type=float, default=0.6, help="seconds between network requests")
    ap.add_argument("--refresh", action="store_true", help="ignore the HTML/image cache and refetch")
    ap.add_argument("--pool-size", type=int, default=23)
    ap.add_argument("--crop", default="0.235,0.03,0.785,0.47",
                    help="shared head-and-shoulders box x0,y0,x1,y1 (fallback; every pool player also gets its own `crop`)")
    ap.add_argument("--crop-override", action="append", default=[], metavar="ID=x0,y0,x1,y1",
                    help="replace a player's computed crop box (repeatable)")
    ap.add_argument("--shoulder-override", action="append", default=[], metavar="ID=y",
                    help="hand-read shoulder line (fraction of the image height) where the alpha detector fails")
    ap.add_argument("--design-dir", type=Path, default=None, help="default <out>/design")
    ap.add_argument("--mark-ready", action="store_true", help="create PLAYERS_READY after players.json")
    args = ap.parse_args()

    out: Path = args.out.expanduser().resolve()
    design_dir = (args.design_dir or out / "design").expanduser().resolve()
    html_dir = out / "html"
    (out / "raw").mkdir(parents=True, exist_ok=True)
    f = Fetcher(html_dir, args.delay, args.refresh)

    def parse_box(text: str) -> list[float]:
        box = [float(x) for x in text.split(",")]
        if len(box) != 4 or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
            ap.error(f"bad crop box {text!r}")
        return box

    crop = parse_box(args.crop)
    crop_overrides = {}
    for item in args.crop_override:
        pid, _, box = item.partition("=")
        crop_overrides[pid.strip()] = parse_box(box)
    shoulder_overrides = {}
    for item in args.shoulder_override:
        pid, _, val = item.partition("=")
        shoulder_overrides[pid.strip()] = float(val)

    log("players page")
    players_html = f.cached(PLAYERS_URL, "players.html").decode("utf-8", "replace")
    cards = parse_cards(players_html)
    cms, meta = payload_players(players_html)
    season = meta.get("season") or "2026 / 27"
    season_label = season.replace(" ", "")
    log(f"  {len(cards)} cards, {len(cms)} CMS player records, season {season_label}")

    pages = {}
    for i, c in enumerate(cards, 1):
        url = BASE + c["href"]
        pages[c["site_id"]] = parse_player_page(f.cached(url, f"players/{c['site_id']}.html").decode("utf-8", "replace"))
        if i % 10 == 0 or i == len(cards):
            log(f"  player pages {i}/{len(cards)}")

    log("season games")
    games_list = season_games(f.cached(HISTORY_URL, "history.html").decode("utf-8", "replace"), season)
    played = [g for g in games_list if g["finished"]]
    log(f"  {len(games_list)} games in {season_label}, {len(played)} finished")
    games = []
    for g in played:
        html = f.cached(f"{BASE}/matches/{g['id']}", f"games/{g['id']}.html").decode("utf-8", "replace")
        game = parse_game(html, g["id"])
        game["anomalies"] = game_anomalies(game)
        game["roles"] = game_roles(game)
        games.append(game)
        log(f"  game {g['id']} {(game['time'] or '')[:10]} {game['stage']} {game['host']} - {game['guest']} "
            f"{game['score'][0]}:{game['score'][1]} starters={len(game['starters'])}"
            + (f" NOTES: {'; '.join(game['anomalies'])}" if game["anomalies"] else ""))

    # ---- per-player records
    used_ids, players = set(), []
    for c in cards:
        sid = c["site_id"]
        p = cms.get(sid, {})
        page = pages.get(sid, {})
        en = next((l for l in p.get("localizations") or [] if l.get("locale") == "en"), {})
        name_en = clean(en.get("playerName")) or None
        name_he = page.get("name") or clean(p.get("playerName")) or " ".join(c["name_lines"])
        base_id = ascii_slug(name_en) if name_en else f"player-{sid}"
        pid, n = base_id, 2
        while pid in used_ids:
            pid, n = f"{base_id}-{n}", n + 1
        used_ids.add(pid)
        spoken, parens = speak_he(name_he)
        log_rows, apps, starts, subs, unused, mins, goals, assists = [], 0, 0, 0, 0, 0, 0, 0
        for game in games:
            r = game["roles"].get(sid)
            if not r:
                continue
            played_flag = r["role"] in ("start", "sub_on")
            apps += played_flag
            starts += r["role"] == "start"
            subs += r["role"] == "sub_on"
            unused += r["role"] == "unused_sub"
            mins += r["minutes"]
            goals += r["goals"]
            assists += r["assists"]
            opp = game["guest"] if game["host"] == CLUB_HE else game["host"]
            log_rows.append({"date": (game["time"] or "")[:10], "game_id": game["id"], "competition": game["stage"],
                             "opponent": opp, "venue": "home" if game["host"] == CLUB_HE else "away",
                             "role": r["role"], "minutes": r["minutes"], "played": played_flag, "goals": r["goals"],
                             "assists": r["assists"]})
        hdr = page.get("header_stats") or {}
        st = p.get("statistics") or {}
        career = page.get("career_table") or []
        role_he = (p.get("playerRole") or {}).get("role") or c["section_he"]
        position_he = page.get("position") or c["position_he"]
        profile = p.get("profileImage") or {}
        photo_url = profile.get("url")
        photo_cdn = CDN + Path(photo_url).name if photo_url else None
        players.append({
            "id": pid,
            "id_from": "english_name" if name_en else "site_id",
            "name_he": name_he,
            "speak_he": spoken,
            "name_parenthetical": parens,
            "card_name_lines": c["name_lines"],
            "name_en": name_en,
            "number": int_or_none(c["number_text"]) if c["number_text"] else int_or_none(p.get("playerShirtNumber")),
            "position_he": position_he,
            "position_en": POSITION_EN.get(position_he),
            "roster_section_he": role_he,
            "roster_section_en": SECTION_EN.get(role_he),
            "is_gk": role_he == GK_SECTION or position_he == "שוער",
            "site_player_id": sid,
            "lineup_id": str(sid),
            "base_player_id": (p.get("basePlayer") or {}).get("id"),
            "profile_url": BASE + c["href"],
            "profile_url_en": None,
            "photo_url": photo_url,
            "photo_url_cdn": photo_cdn,
            "photo_url_card": BASE + c["photo_src"] if (c.get("photo_src") or "").startswith("/") else c.get("photo_src"),
            "photo_file": None,
            "photo_px": None, "photo_has_alpha": None, "photo_transparent_share": None, "photo_format": None,
            "photo_mode": None, "photo_alpha_levels": None, "photo_bytes": None, "photo_sha1": None,
            "stats": {
                "appearances": apps, "starts": starts, "sub_appearances": subs, "unused_sub": unused,
                "minutes": mins, "goals": goals, "assists": assists,
            },
            "crosscheck": {
                "card_number": int_or_none(c["number_text"]),
                "page_number": int_or_none(page.get("number_text")),
                "page_name": page.get("name"),
                "site_header_appearances": hdr.get("הופעות"),
                "site_header_assists": hdr.get("בישולים"),
                "site_header_goals": hdr.get("שערים"),
                "payload_statistics": {k: st.get(k) for k in ("appearances", "goals", "assists")} if st else None,
                "header_minus_season_appearances": (hdr.get("הופעות") - apps) if isinstance(hdr.get("הופעות"), int) else None,
                "career_table_appearances_total": sum(r["appearances"] or 0 for r in career),
                "career_table": career,
                "entry_created": (p.get("createdAt") or "")[:10] or None,
                "entry_updated": (p.get("updatedAt") or "")[:10] or None,
                "base_player_created": ((p.get("basePlayer") or {}).get("createdAt") or "")[:10] or None,
            },
            "match_log": log_rows,
            "role": None,
            "excluded_reason": None,
            "pool_rank": None,
            "crop": None,
            "framing": None,
        })

    # ---- H3: pool of the top N by appearances, main 11 = top GK + 10 outfield
    def rank_key(pl):
        s = pl["stats"]
        return (-s["appearances"], -s["starts"], -s["minutes"], pl["number"] if pl["number"] is not None else 999)

    eligible = [pl for pl in players if pl["photo_url"] and pl["profile_url"]]
    for pl in players:
        if not pl["photo_url"]:
            pl["role"], pl["excluded_reason"] = "excluded", "no photo on the site"
    ranked = sorted((pl for pl in eligible if pl["stats"]["appearances"] >= 1), key=rank_key)
    for i, pl in enumerate(ranked, 1):
        pl["pool_rank"] = i
    pool = ranked[: args.pool_size]
    tie_notes = []
    if len(ranked) > args.pool_size and rank_key(ranked[args.pool_size - 1])[:3] == rank_key(ranked[args.pool_size])[:3]:
        tie_notes.append(f"pool cut decided by jersey number: {ranked[args.pool_size - 1]['id']} vs {ranked[args.pool_size]['id']}")
    gks = sorted((pl for pl in eligible if pl["is_gk"]), key=rank_key)
    top_gk = gks[0] if gks and gks[0]["stats"]["appearances"] >= 1 else None
    outfield_pool = [pl for pl in pool if not pl["is_gk"]]
    for pl in eligible:
        if pl["role"]:
            continue
        if pl["stats"]["appearances"] == 0:
            pl["role"], pl["excluded_reason"] = "excluded", f"0 appearances in {season_label}"
        elif pl["is_gk"] and pl is not top_gk:
            pl["role"], pl["excluded_reason"] = "excluded", f"backup goalkeeper (the main 11 uses {top_gk['id']})"
        elif pl is top_gk:
            pl["role"] = "starter"
        elif pl not in pool:
            pl["role"], pl["excluded_reason"] = "excluded", f"outside the top {args.pool_size} by appearances (pool_rank {pl['pool_rank']})"
    for i, pl in enumerate(outfield_pool):
        pl["role"] = "starter" if i < 10 else "bench"
    if len(outfield_pool) > 10 and rank_key(outfield_pool[9])[:3] == rank_key(outfield_pool[10])[:3]:
        tie_notes.append(f"10th outfield slot decided by jersey number: {outfield_pool[9]['id']} vs {outfield_pool[10]['id']}")
    for a_, b_ in zip(outfield_pool[9:10], outfield_pool[10:11]):
        if rank_key(a_)[0] == rank_key(b_)[0]:
            how = "starts" if rank_key(a_)[1] != rank_key(b_)[1] else ("minutes" if rank_key(a_)[2] != rank_key(b_)[2] else "jersey number")
            tie_notes.append(f"10th outfield slot: {a_['id']} over {b_['id']} on {how} (equal appearances)")
    if top_gk and len(gks) > 1 and rank_key(gks[0])[0] == rank_key(gks[1])[0]:
        tie_notes.append(f"GK decided on starts/minutes: {gks[0]['id']} over {gks[1]['id']}")

    # starts-based XI for information (H3)
    def starts_key(pl):
        s = pl["stats"]
        return (-s["starts"], -s["minutes"], -s["appearances"], pl["number"] if pl["number"] is not None else 999)

    s_gk = sorted((pl for pl in eligible if pl["is_gk"]), key=starts_key)[:1]
    s_out = sorted((pl for pl in eligible if not pl["is_gk"]), key=starts_key)[:10]
    starts_xi = [pl["id"] for pl in s_gk + s_out]
    apps_xi = [pl["id"] for pl in players if pl["role"] == "starter"]
    s_sorted = sorted((pl for pl in eligible if not pl["is_gk"]), key=starts_key)
    starts_cut = None
    if len(s_sorted) > 10:
        starts_cut = {"tenth": s_sorted[9]["id"], "eleventh": s_sorted[10]["id"],
                      "tenth_starts": s_sorted[9]["stats"]["starts"], "eleventh_starts": s_sorted[10]["stats"]["starts"],
                      "decided_by": "starts" if s_sorted[9]["stats"]["starts"] != s_sorted[10]["stats"]["starts"] else "minutes"}

    # ---- photos for starters + bench
    for pl in players:
        if pl["role"] not in ("starter", "bench"):
            continue
        url = pl["photo_url_cdn"] or pl["photo_url"]
        ext = Path(url).suffix.lower() or ".png"
        rel = f"img/{Path(url).name}"
        data = f.cached(url, rel)
        meta_img = inspect_image(data)
        dest = out / "raw" / f"{pl['id']}{ext}"
        dest.write_bytes(data)
        pl.update({"photo_file": f"raw/{pl['id']}{ext}", "photo_px": meta_img["px"], "photo_has_alpha": meta_img["has_alpha"],
                   "photo_transparent_share": meta_img["transparent_share"], "photo_format": meta_img["format"],
                   "photo_mode": meta_img["mode"], "photo_alpha_levels": meta_img["alpha_levels"],
                   "photo_bytes": meta_img["bytes"], "photo_sha1": meta_img["sha1"]})
        img = Image.open(io.BytesIO(data)).convert("RGBA")
        lm = landmarks(img)
        hand = shoulder_overrides.pop(pl["id"], None)
        if lm["shoulder_detector_failed"] and hand is None:
            hand_src, used = "neck + 0.07 (alpha detector failed; pass --shoulder-override)", round(lm["neck_y"] + 0.07, 3)
            log(f"  WARNING {pl['id']}: shoulder detector failed, using {used}")
        elif hand is not None:
            hand_src, used = "hand-read", hand
        else:
            hand_src, used = "alpha outline", lm["shoulder_y"]
        box = square_crop(img, lm, used)
        pl["crop"] = box
        pl["framing"] = {**lm, "shoulder_y_used": used, "shoulder_source": hand_src,
                         "crop_px": round((box["x1"] - box["x0"]) * img.width)}
    for pl in players:
        box = crop_overrides.pop(pl["id"], None)
        if box:
            pl["crop"] = {"x0": box[0], "y0": box[1], "x1": box[2], "y1": box[3]}
            pl["framing"] = (pl.get("framing") or {}) | {"crop_source": "--crop-override"}
    if crop_overrides or shoulder_overrides:
        ap.error(f"overrides for unknown or non-pool ids: {', '.join([*crop_overrides, *shoulder_overrides])}")

    # ---- design tokens
    css_text = ""
    for link in re.findall(r'<link rel="stylesheet" href="(/_next/static/css/[^"]+\.css)"', players_html):
        css_text += f.cached(BASE + link, "css/" + Path(link).name).decode("utf-8", "replace")
    design = design_tokens(out, design_dir, css_text, meta.get("card_cover_url"))

    role_order = {"starter": 0, "bench": 1, "excluded": 2}
    players.sort(key=lambda pl: (role_order[pl["role"]], not pl["is_gk"], pl["pool_rank"] or 999, rank_key(pl)))
    now = dt.datetime.now(dt.timezone.utc).astimezone()
    fetched = dt.datetime.fromtimestamp(f.newest_fetch, dt.timezone.utc).astimezone() if f.newest_fetch else now
    comps = sorted({g["stage"] for g in games})
    first, last = (games[0]["time"] or "")[:10], (games[-1]["time"] or "")[:10]
    payload = {
        "season": season_label,
        "season_id": None,
        "scraped_at": fetched.isoformat(timespec="seconds"),
        "built_at": now.isoformat(timespec="seconds"),
        "sources": {
            "players": PLAYERS_URL,
            "player_page": BASE + "/players/<site_player_id>",
            "season_games": unquote(HISTORY_URL),
            "game_page": BASE + "/matches/<game_id>",
        },
        "metric": (
            f"{season_label} appearances in all competitions ({len(games)} official games played {first} to {last}: "
            f"{', '.join(f'{sum(1 for g in games if g['stage'] == c)}x {c}' for c in comps)}), counted from the club's own "
            "synced game records (mhaifafc.com/matches/<id>: the starting line-up plus every substitute who came on). "
            "The individual page header 'הופעות' is not season-specific: for returning players it is their 2025/26 "
            "total carried into the 2026/27 entry plus 2026/27 games; it equals this count only for players new in "
            "summer 2026 (crosscheck.site_header_appearances / header_minus_season_appearances)."
        ),
        "pool_rule": (
            f"H3: pool = top {args.pool_size} by appearances (>= 1) across all /players players, ranked by appearances, "
            "then starts, then minutes, then lower jersey number (pool_rank); main 11 = the goalkeeper with the most "
            "appearances + the 10 outfield players with the most; bench = the other outfield players in the pool; "
            "backup goalkeepers excluded."
        ),
        "starts_method": "Starter = in the game's starting line-up (gameLineUp); sub = not in it but marked as substituted on.",
        "minutes_method": ("Starter: until the substitution/red-card minute, else 90. Substitute: 90 minus the minute he "
                           "came on. Stoppage and extra time ignored (tiebreak only)."),
        "matches_counted": [
            {"date": (g["time"] or "")[:10], "game_id": g["id"], "competition": g["stage"], "opponent":
             g["guest"] if g["host"] == CLUB_HE else g["host"], "venue": "home" if g["host"] == CLUB_HE else "away",
             "score": f"{g['score'][0]}:{g['score'][1]} ({g['host']} - {g['guest']})", "url": f"{BASE}/matches/{g['id']}",
             "xi_size": len(g["starters"]), "notes": g["anomalies"]}
            for g in games
        ],
        "tie_notes": tie_notes,
        "starts_based_xi": {"ids": starts_xi,
                            "differs_from_main_11": {"only_in_starts_xi": [x for x in starts_xi if x not in apps_xi],
                                                     "only_in_appearances_xi": [x for x in apps_xi if x not in starts_xi]},
                            "cut": starts_cut},
        "design": design,
        "crop": {"x0": crop[0], "y0": crop[1], "x1": crop[2], "y1": crop[3]},
        "crop_rule": ("Each starter/bench player has its own square `crop` (fractions of the 800x1000 source): hair top "
                      "4% below the top edge, shoulder line at 90% of the height, centred on the head (the TLV image "
                      "tool's auto rule, so `--mode box` reproduces it). Shoulder lines for pedro-barzao and "
                      "adam-grimberg are hand-read: the alpha detector fires inside their hair. The top-level `crop` is "
                      "a shared fallback box that fits all 22 heads and shoulders."),
        "players": players,
    }
    write_json_atomic(out / "players.json", payload)
    write_json_atomic(out / "matches.json", {"season": season_label, "matches": [
        {k: v for k, v in g.items() if k != "roles"} | {"roles": {str(k): v for k, v in g["roles"].items()}} for g in games]})
    counts = {r: sum(pl["role"] == r for pl in players) for r in ("starter", "bench", "excluded")}
    log(f"wrote {out / 'players.json'} ({counts}); {f.requests} network requests")
    for note in tie_notes:
        log("TIE: " + note)
    if args.mark_ready:
        (out / "PLAYERS_READY").write_text(payload["built_at"] + "\n", encoding="utf-8")
        log("created PLAYERS_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
