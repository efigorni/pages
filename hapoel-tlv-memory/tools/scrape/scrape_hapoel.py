"""Hapoel Tel Aviv FC roster + this season's appearances -> players.json (Haifa's shape).

Sources (all cached under <data>/html/, re-runs make no network calls unless --refresh):
  * htafc.co.il team & players page (Hebrew, uncached render for a fresh nonce) + its English twin
  * the member popup per player (admin-ajax get_team_member_info): number, position, age, bio
  * the club's own match reports (WP posts, category 30): the "שיחקו בהפועל:" line-up block per game
  * the club's fixture list (homepage): date, opponent, score, competition logo
  * Transfermarkt (club 1017) squad stats, all competitions of the season: cross-check only
Photos: the listing card image (original upload) per starter/bench player -> <data>/raw/<id>.png

Usage:
  uv run --with requests --with beautifulsoup4 --with pillow python -I -u scrape_hapoel.py --data <data-dir> \
      [--crop-override id=x0,y0,x1,y1 ...] [--mark-ready]
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[3] / "_memory-game/tools/scrape"))  # the shared kit
sys.path.insert(2, str(Path(__file__).resolve().parents[3] / "_memory-game/tools/images"))  # framing.py

from PIL import Image  # noqa: E402

from common import Fetcher, ascii_slug, log_line, norm_name, photo_facts, write_json_atomic  # noqa: E402
from framing import landmarks, pick_shoulder, square_crop  # noqa: E402
from htafc import (LINEUP_RE, LISTING_EN, LISTING_HE, SECTION_EN, parse_lineup_block, parse_listing,  # noqa: E402
                   parse_popup, report_text)
from roster import SHIPPED, check, output_key, select  # noqa: E402
from transfermarkt import parse_squadstats, squadstats_url  # noqa: E402

# The season this scrape counts. Its dates, the cached Transfermarkt file, the club's season id and every
# text below follow from it; SEASON_DATA and COMP_BY_LOGO are the per-season facts typed in by hand.
SEASON = "2026/27"
SEASON_START = int(SEASON[:4])
TZ = dt.timezone(dt.timedelta(hours=3))
COMP_BY_LOGO = {
    "logo-winner-ligat.png": "ליגת ווינר",
    "gvia-hatoto.png": "גביע הטוטו",
    "uefa-conference-league-full-logo-2024-version1.png": "קונפרנס ליג - מוקדמות",
}
# Per season, keyed by fixture date: each official game's stage name and the club's own match record id
# (wp-json/wp/v2/htafc_match titles), and Transfermarkt's match report id (its fixtures page).
SEASON_DATA = {"2026/27": {"stages": {
    "2026-07-18": ("גביע הטוטו - משחק האירופאיות", 67500),
    "2026-07-23": ("קונפרנס ליג - מוקדמות, סיבוב שני (1)", 67493),
    "2026-07-30": ("קונפרנס ליג - מוקדמות, סיבוב שני (2)", 67494),
    "2026-08-06": ("קונפרנס ליג - מוקדמות, סיבוב שלישי (1)", 68957),
    "2026-08-12": ("קונפרנס ליג - מוקדמות, סיבוב שלישי (2)", 68958),
    "2026-08-16": ("גביע הטוטו - חצי גמר", 69803),
    "2026-08-20": ("קונפרנס ליג - פלייאוף (1)", 69958),
    "2026-08-27": ("קונפרנס ליג - פלייאוף (2)", 69957),
    "2026-08-30": ("ליגת ווינר - מחזור 2", 67448),
    "2026-09-03": ("ליגת ווינר - מחזור 1", 67447),
    "2026-09-07": ("ליגת ווינר - מחזור 3", 67449),
    "2026-09-14": ("ליגת ווינר - מחזור 4", 67450),
    "2026-09-18": ("ליגת ווינר - מחזור 5", 67451),
}, "tm_reports": {
    "2026-07-23": 4897987, "2026-07-30": 4898025, "2026-08-06": 4973731, "2026-08-12": 4973761,
    "2026-08-20": 5013818, "2026-08-27": 5013842, "2026-08-30": 4912901, "2026-09-03": 4912932,
    "2026-09-07": 4912945, "2026-09-14": 4912916, "2026-09-18": 4912958,
}}}
STAGE_BY_DATE = SEASON_DATA.get(SEASON, {}).get("stages", {})
TM_REPORT_BY_DATE = SEASON_DATA.get(SEASON, {}).get("tm_reports", {})
TM_CLUB = ("hapoel-tel-aviv", 1017)
# The club's photo rules (club/club.json `images`). The shared shoulder rule (50%) fires inside the head on
# these chest-up photos, whose white sticker outline makes the head about half as wide as the chest: the
# first row >= 75% of the widest, from 30% of the height down, lands on the shoulder slope instead.
IMAGES = json.loads((Path(__file__).resolve().parents[2] / "club/club.json").read_text(encoding="utf-8"))["images"]
SHOULDER_RULE = {k: IMAGES[k] for k in ("shoulder_share", "shoulder_from") if k in IMAGES}
POSITION_EN = {"שוער": "Goalkeeper", "הגנה": "Defender", "קישור": "Midfielder", "קשר": "Midfielder", "התקפה": "Forward"}
SENT_OFF = "הורחק"
HOME_NAMES = ("הפועל תל-אביב", "הפועל תל אביב")
POOL_RULE = (
    "P3: pool = top 23 by appearances (>= 1) across all players on the team & players page, ranked by appearances, "
    "then starts, then minutes, then lower jersey number (pool_rank); main 11 = the goalkeeper with the most "
    "appearances + the 10 outfield players with the most; bench = the other outfield players in the pool; backup "
    "goalkeepers excluded."
)


def season_date(ddmm: str) -> str:
    d, m = (int(x) for x in ddmm.split("."))
    return f"{SEASON_START if m >= 7 else SEASON_START + 1:04d}-{m:02d}-{d:02d}"


def pair_listings(he: list[dict], en: list[dict]) -> list[tuple[dict, dict]]:
    """Each Hebrew card with its English twin, in Hebrew page order. The two language versions are separate
    WordPress posts with different ids, but they show the same uploaded photo, so that is the key; a card
    without exactly one twin stops the scrape (a wrong pair would put one player's id, clips and photo on
    another's card)."""
    by_photo = {}
    for y in en:
        if not y["card_img_largest"] or y["card_img_largest"] in by_photo:
            raise SystemExit(f"English listing: {y['name']} has no photo of its own ({y['card_img_largest']})")
        by_photo[y["card_img_largest"]] = y
    pairs = []
    for x in he:
        y = by_photo.pop(x["card_img_largest"], None)
        if y is None:
            raise SystemExit(f"Hebrew listing: {x['name']} has no English card with the same photo ({x['card_img_largest']})")
        pairs.append((x, y))
    if by_photo:
        raise SystemExit(f"English listing: no Hebrew card for {', '.join(y['name'] for y in by_photo.values())}")
    return pairs


def load_json(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def official_games(html_dir: Path) -> list[dict]:
    from club_fixtures import parse as parse_fixtures

    fixtures = parse_fixtures((html_dir / "home.html").read_text(encoding="utf-8"))
    seen, games = set(), []
    for f in fixtures:
        if not f["score"] or not f["score"][0]:
            continue  # not played
        date = season_date(f["place"][0])
        key = (date, f["home"], f["away"])
        if key in seen:
            continue
        seen.add(key)
        comp = COMP_BY_LOGO.get(f["competition_logo"])
        home = f["home"] in HOME_NAMES
        games.append({
            "date": date, "kickoff": f["place"][1], "venue_name": f["place"][2],
            "competition": comp or "משחק אימון", "official": comp is not None,
            "opponent": f["away"] if home else f["home"], "venue": "home" if home else "away",
            "score": f"{f['score'][0]}:{f['score'][2]} ({f['home']} - {f['away']})",
            "hapoel_goals": int(f["score"][0] if home else f["score"][2]),
            "opp_goals": int(f["score"][2] if home else f["score"][0]),
        })
    reports = load_json(html_dir / "rest/reports-cat30.json")
    for g in games:
        gd = dt.date.fromisoformat(g["date"])
        cands = []
        for r in reports:
            rd = dt.datetime.fromisoformat(r["date"]).date()
            if 0 <= (rd - gd).days <= 1 and "שיחקו בהפועל" in report_text(r["content"]["rendered"]):
                cands.append(r)
        cands.sort(key=lambda r: r["date"])
        g["report"] = cands[0] if cands else None
    return sorted(games, key=lambda g: g["date"])


def build_lineups(games: list[dict], roster_by_name: dict) -> tuple[dict, list[dict]]:
    """Per roster player: match log entries; per game: notes. Minutes: starter to his sub-off/red minute else 90;
    substitute from his minute to 90 (or his own sub-off/red); stoppage time ignored."""
    logs = defaultdict(list)
    out_games = []
    for g in games:
        if not g["official"]:
            continue
        r = g["report"]
        if r is None:
            raise SystemExit(f"no club report for {g['date']} {g['opponent']}")
        text = report_text(r["content"]["rendered"])
        block = parse_lineup_block(text)
        if not block:
            raise SystemExit(f"{g['date']} {g['opponent']}: the club's report ({r['link']}) has no line-up after "
                             "'שיחקו בהפועל:', so every player would lose this appearance; fix the report text in "
                             "<data>/html/rest/reports-cat30.json and run again")
        notes, unknown = [], []
        if len(block) != 11:
            notes.append(f"line-up block has {len(block)} starters")
        appearances = []  # (name, role, on, off, red)
        for s in block:
            chain = [(s["name"], 0)]
            red_at = None
            for x in s["subs"]:
                if x["minute"] is None:
                    raise SystemExit(f"{g['date']} {g['opponent']}: no minute in «{x['name']}» ({s['raw'].strip()}): a "
                                     "substitution or red card without one can't be counted; fix that report's text in "
                                     "<data>/html/rest/reports-cat30.json and run again")
                if x["name"] == SENT_OFF:
                    red_at = x["minute"]
                    continue
                chain.append((x["name"], x["minute"]))
            for k, (name, on) in enumerate(chain):
                nxt = chain[k + 1][1] if k + 1 < len(chain) else None
                off = nxt if nxt is not None else (red_at if (red_at is not None and k == len(chain) - 1) else 90)
                appearances.append({"name": name, "role": "start" if k == 0 else "sub_on", "on": on, "off": off,
                                    "subbed_off": nxt is not None,
                                    "red": red_at is not None and k == len(chain) - 1})
        for a in appearances:
            key = norm_name(a["name"])
            p = roster_by_name.get(key)
            if p is None:
                unknown.append(a["name"])
                continue
            logs[p["id"]].append({
                "date": g["date"], "club_match_id": STAGE_BY_DATE.get(g["date"], (None, None))[1],
                "competition": STAGE_BY_DATE.get(g["date"], (g["competition"], None))[0],
                "opponent": g["opponent"], "venue": g["venue"], "role": a["role"],
                "on_minute": a["on"] if a["role"] == "sub_on" else None,
                "off_minute": a["off"] if (a["subbed_off"] or a["red"]) else None,
                "sent_off": a["red"], "minutes": max(0, a["off"] - a["on"]), "played": True,
            })
        if unknown:
            notes.append("not on the team & players page: " + ", ".join(unknown))
        out_games.append({
            "date": g["date"], "club_match_id": STAGE_BY_DATE.get(g["date"], (None, None))[1],
            "competition": STAGE_BY_DATE.get(g["date"], (g["competition"], None))[0],
            "opponent": g["opponent"], "venue": g["venue"], "venue_name": g["venue_name"], "score": g["score"],
            "report_post_id": r["id"], "report_url": r["link"], "report_title": r["title"]["rendered"],
            "tm_report_id": TM_REPORT_BY_DATE.get(g["date"]),
            "xi_size": len(block), "subs_used": sum(1 for a in appearances if a["role"] == "sub_on"),
            "red_cards": [a["name"] for a in appearances if a["red"]],
            "lineup_line": LINEUP_LINE(text), "notes": notes,
        })
    return logs, out_games


def LINEUP_LINE(text: str) -> str:
    m = LINEUP_RE.search(text)
    return " ".join(m.group(1).split()) if m else ""


def metric(game_rows: list[dict], tm: dict) -> str:
    comps = {}
    for g in game_rows:
        comps.setdefault(g["competition"].split(" - ")[0], []).append(g["competition"].partition(" - ")[2])
    games = ", ".join(f"{len(stages)}x {comp}" + (f" ({', '.join(s for s in stages if s)})" if any(stages) else "")
                      for comp, stages in comps.items())
    agree = ("match the club count over those games for every player" if not tm["mismatches"]
             else f"differ for {len(tm['mismatches'])} players (see transfermarkt_crosscheck)")
    return (f"{SEASON} appearances in all competitions ({len(game_rows)} official games played {game_rows[0]['date']} to "
            f"{game_rows[-1]['date']}: {games}), counted from the club's own match reports on htafc.co.il (the "
            "'שיחקו בהפועל:' block: the starting eleven, each substitute in parentheses with his minute). Pre-season "
            f"friendlies are not counted. Neither the listing nor the player popup shows any {SEASON} number (the popup "
            f"bio only quotes earlier seasons in prose). Cross-check: Transfermarkt's all-competitions squad stats "
            f"({tm['games']} of the games" + (f"; no {', '.join(tm['missing'])}" if tm["missing"] else "")
            + f") {agree} (appearances, substitutions on/off).")


def season_id(html_dir: Path) -> int:
    slug = f"{SEASON_START}-{SEASON_START + 1}"
    for s in load_json(html_dir / "rest/seasons.json"):
        if s["slug"] == slug:
            return s["id"]
    raise SystemExit(f"no season {slug} in {html_dir / 'rest/seasons.json'} (the club's /wp-json/wp/v2/htafc_season)")


def tm_crosscheck(html_dir: Path, players: list[dict], logs: dict, game_rows: list[dict]) -> dict:
    d = parse_squadstats((html_dir / f"ext/tm-leistungsdaten-{SEASON_START}.html").read_text(encoding="utf-8"))
    by_number = {}
    for row in d["rows"]:
        c = row["cells"]
        num = c[0]
        apps = 0 if not c[5].isdigit() else int(c[5])
        dash = lambda v: 0 if v in ("-", "") else int(v)  # noqa: E731
        mins = c[14].replace("'", "").replace(".", "").replace(",", "")
        by_number.setdefault(num, []).append({
            "tm_id": row["tm_id"], "tm_name": row["name"], "number": num, "in_squad": dash(c[4]),
            "appearances": apps, "goals": dash(c[6]) if apps else 0, "subs_on": dash(c[11]) if apps else 0,
            "subs_off": dash(c[12]) if apps else 0, "minutes": int(mins) if mins.isdigit() else 0,
            "status": c[5] if not c[5].isdigit() else None,
        })
    tm_dates = set(TM_REPORT_BY_DATE)
    missing = sorted({g["competition"].split(" - ")[0] for g in game_rows if g["date"] not in tm_dates})
    scope = (f"Transfermarkt 'all competitions' {SEASON} = the {len(tm_dates)} games it lists"
             + (f" (no {', '.join(missing)})" if missing else ""))
    result = {"mismatches": [], "compared": 0, "tm_only": [], "games": len(tm_dates), "missing": missing}
    matched_tm = set()
    for p in players:
        rows = by_number.get(str(p["number"]), [])
        if len(rows) != 1:
            p["crosscheck"]["transfermarkt"] = None
            result["mismatches"].append(f"{p['id']}: no unique TM row for #{p['number']}")
            continue
        t = rows[0]
        matched_tm.add(t["tm_id"])
        mine = [e for e in logs.get(p["id"], []) if e["date"] in tm_dates]
        club = {"appearances": len(mine), "subs_on": sum(1 for e in mine if e["role"] == "sub_on"),
                "subs_off": sum(1 for e in mine if e["off_minute"] is not None and not e["sent_off"]),
                "minutes_approx": sum(e["minutes"] for e in mine)}
        same = club["appearances"] == t["appearances"] and club["subs_on"] == t["subs_on"] and club["subs_off"] == t["subs_off"]
        p["crosscheck"]["transfermarkt"] = {
            "tm_id": t["tm_id"], "tm_name": t["tm_name"], "scope": scope,
            "tm": {k: t[k] for k in ("appearances", "subs_on", "subs_off", "minutes", "in_squad")},
            "club_count_same_games": club, "match": same,
        }
        result["compared"] += 1
        if not same:
            result["mismatches"].append(f"{p['id']}: club {club} vs TM {t}")
    for rows in by_number.values():
        for t in rows:
            if t["tm_id"] not in matched_tm and t["appearances"]:
                result["tm_only"].append(f"{t['tm_name']} #{t['number']}: {t['appearances']} apps (not on the club listing)")
    return result


def clean_photo(raw_path: Path, clean_path: Path) -> dict:
    """The club photo minus its baked-in shirt number (clean_number.py); cached by mtime."""
    from clean_number import clean

    if clean_path.exists() and clean_path.stat().st_mtime >= raw_path.stat().st_mtime and clean_path.with_suffix(".json").exists():
        return load_json(clean_path.with_suffix(".json"))
    img, stats = clean(Image.open(raw_path))
    clean_path.parent.mkdir(parents=True, exist_ok=True)
    img.save(clean_path, optimize=True)
    stats["bbox_number"] = [float(v) for v in stats["bbox_number"]] if stats["bbox_number"] else None
    clean_path.with_suffix(".json").write_text(json.dumps(stats), encoding="utf-8")
    return stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--crop-override", action="append", default=[], help="id=x0,y0,x1,y1 (fractions)")
    ap.add_argument("--shoulder-override", action="append", default=[],
                    help="id=y (hand-read shoulder line, fraction); adds to club.json's shoulder_overrides")
    ap.add_argument("--mark-ready", action="store_true")
    a = ap.parse_args()
    if SEASON not in SEASON_DATA:
        raise SystemExit(f"no SEASON_DATA row for {SEASON}: add each official game's stage, club match id and "
                         "Transfermarkt report id (see tools/README.md)")
    data = a.data.expanduser().resolve()
    html_dir = data / "html"
    f = photos = Fetcher(data, 0.6, a.refresh)  # only photos are fetched here; pages are cached by the explore/fetch steps

    he_html = (html_dir / "players-fresh.html").read_text(encoding="utf-8")
    en_html = (html_dir / "players-en.html").read_text(encoding="utf-8")
    players = []
    for x, y in pair_listings(parse_listing(he_html), parse_listing(en_html)):
        pop = parse_popup(load_json(html_dir / f"members/{x['member_id']}.json")["data"])
        if norm_name(pop["name"]) != norm_name(x["name"]):
            raise SystemExit(f"popup name differs: {pop['name']} vs {x['name']}")
        pid = ascii_slug(y["name"])
        players.append({
            "id": pid, "id_from": "english_name",
            "name_he": x["name"], "speak_he": x["name"], "name_parenthetical": None,
            "card_name_lines": [x["name"].rsplit(" ", 1)[0], x["name"].rsplit(" ", 1)[1]] if " " in x["name"] else [x["name"]],
            "name_en": y["name"], "number": pop["number"],
            "position_he": pop["position"], "position_en": POSITION_EN.get(pop["position"], pop["position"]),
            "roster_section_he": x["section"], "roster_section_en": SECTION_EN.get(x["section"]),
            "is_gk": x["section"] == "שוערים",
            "site_member_id": x["member_id"], "site_member_id_en": y["member_id"],
            "profile_url": f"https://www.htafc.co.il/?p={x['member_id']}",
            "profile_popup": {"endpoint": "https://www.htafc.co.il/wp-admin/admin-ajax.php",
                              "form": {"action": "get_team_member_info", "memberID": x["member_id"], "nonce": "<from the page>"}},
            "age": pop["age"], "seasons_at_club": pop["seasons"],
            "photo_url": x["card_img_largest"],
            "photo_url_card": x["card_img"],
            "photo_url_gallery": pop["gallery_img"],
            "bio_he": pop["bio"],
        })
    roster_by_name = {norm_name(p["name_he"]): p for p in players}
    if len(roster_by_name) != len(players):
        raise SystemExit("duplicate names on the listing")

    games = official_games(html_dir)
    logs, game_rows = build_lineups(games, roster_by_name)
    for g in game_rows:
        log_line(f"game {g['date']} {g['competition']} vs {g['opponent']} ({g['venue']}) {g['score']}: XI {g['xi_size']}, subs {g['subs_used']}"
                 + (f" | {'; '.join(g['notes'])}" if g["notes"] else ""))
    friendlies = [g for g in games if not g["official"]]

    for p in players:
        lg = sorted(logs.get(p["id"], []), key=lambda e: e["date"])
        p["match_log"] = lg
        p["stats"] = {
            "appearances": len(lg), "starts": sum(1 for e in lg if e["role"] == "start"),
            "sub_appearances": sum(1 for e in lg if e["role"] == "sub_on"), "unused_sub": None,
            "minutes": sum(e["minutes"] for e in lg), "sent_off": sum(1 for e in lg if e["sent_off"]),
        }
        p["crosscheck"] = {"listing_name": p["name_he"], "popup_number": p["number"]}

    tm = tm_crosscheck(html_dir, players, logs, game_rows)
    log_line(f"TM cross-check: {tm['compared']} compared, mismatches: {tm['mismatches'] or 'none'}")
    for s in tm["tm_only"]:
        log_line(f"  TM only: {s}")

    # selection (P3)
    sel = select(players)
    for p in players:
        p.setdefault("pool_rank", None)
    outfield = sel.outfield
    for p in players:
        if p.get("role") in SHIPPED:
            p["excluded_reason"] = None
        else:
            p["role"] = "excluded"
            if p["stats"]["appearances"] == 0:
                p["excluded_reason"] = (("goalkeeper, " if p["is_gk"] else "") + f"0 appearances in {SEASON} (in no club "
                                        f"line-up of the {len(game_rows)} official games)")
            elif p["is_gk"]:
                p["excluded_reason"] = f"goalkeeper outside the top 23 (pool_rank {p['pool_rank']})"
            else:
                p["excluded_reason"] = f"outside the top 23 (pool_rank {p['pool_rank']})"

    # boundary notes
    tie_notes = []
    def key(p):
        return (p["stats"]["appearances"], p["stats"]["starts"], p["stats"]["minutes"])
    if len(outfield) > 10:
        a10, a11 = outfield[9], outfield[10]
        decided = "appearances" if key(a10)[0] != key(a11)[0] else ("starts" if key(a10)[1] != key(a11)[1] else ("minutes" if key(a10)[2] != key(a11)[2] else "number"))
        tie_notes.append(f"10th/11th outfield: {a10['id']} {key(a10)} vs {a11['id']} {key(a11)} -> decided by {decided}")

    # photos (starters + bench)
    raw = data / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    overrides = {}
    for o in a.crop_override:
        pid, _, vals = o.partition("=")
        x0, y0, x1, y1 = (float(v) for v in vals.split(","))
        overrides[pid] = {"x0": x0, "y0": y0, "x1": x1, "y1": y1}
    shoulder_overrides = {**IMAGES.get("shoulder_overrides", {}),
                          **{o.partition("=")[0]: float(o.partition("=")[2]) for o in a.shoulder_override}}
    for p in players:
        if p["role"] not in SHIPPED:
            p["photo_file"] = None
            continue
        ext = Path(p["photo_url"]).suffix.lower() or ".png"
        rel = f"raw/{p['id']}{ext}"
        dest = data / rel
        if not dest.exists() or a.refresh:
            photos.cached(p["photo_url"], rel, force=True)
        p["photo_file_original"] = rel
        p.update({f"photo_{k}": v for k, v in photo_facts(dest.read_bytes()).items()})
        crel = f"clean/{p['id']}.png"
        p["number_removal"] = clean_photo(dest, data / crel)
        nb = p["number_removal"]["bbox_number"]
        if not nb or nb[3] > 0.5 or nb[1] > 0.1:
            raise SystemExit(f"{p['id']}: number removal looks wrong: {p['number_removal']}")
        p["photo_file"] = crel
        img = Image.open(data / crel)
        lm = landmarks(img)
        sh = shoulder_overrides.get(p["id"])
        sh_used, sh_source = pick_shoulder(landmarks(img, **SHOULDER_RULE), sh)
        crop = overrides.get(p["id"]) or square_crop(img, lm, sh_used)
        p["crop"] = crop
        p["framing"] = {"hair_top": lm["hair_top"], "head_cx": lm["head_cx"], "neck_y": lm["neck_y"],
                        "shoulder_y_shared_rule": lm["shoulder_y"], "shoulder_y_used": sh_used,
                        "shoulder_source": sh_source if sh_source != "alpha outline" else
                        f"alpha outline, first row >= {SHOULDER_RULE.get('shoulder_share', 0.5):.0%} of the widest",
                        "crop_source": "override" if p["id"] in overrides else "auto rule on the number-free photo",
                        "crop_px": round((crop["x1"] - crop["x0"]) * img.size[0])}
        log_line(f"photo {p['id']}: {p['photo_px']} {p['photo_mode']} alpha {p['photo_transparent_share']} | number {p['number_removal']['bbox_number']} "
                 f"| {lm} | crop {crop} {p['framing']['crop_px']}px")

    players.sort(key=output_key)
    pooled = [p for p in players if p.get("crop")]
    shared = {"x0": round(min(p["crop"]["x0"] for p in pooled), 4), "y0": round(min(p["crop"]["y0"] for p in pooled), 4),
              "x1": round(max(p["crop"]["x1"] for p in pooled), 4), "y1": round(max(p["crop"]["y1"] for p in pooled), 4)}

    design_path = data / "design/design.json"
    design = load_json(design_path) if design_path.exists() else None
    doc = {
        "season": SEASON, "season_id": season_id(html_dir),
        "scraped_at": dt.datetime.fromtimestamp((html_dir / "players-fresh.html").stat().st_mtime, TZ).isoformat(timespec="seconds"),
        "built_at": dt.datetime.now(TZ).isoformat(timespec="seconds"),
        "sources": {
            "players": LISTING_HE, "players_en": LISTING_EN,
            "player_page": "https://www.htafc.co.il/?p=<site_member_id> (redirects to /team/<slug>/, a bare banner page); "
                           "the real player page is the listing's popup: POST admin-ajax.php action=get_team_member_info",
            "season_games": "https://www.htafc.co.il/ (fixture list) + https://www.htafc.co.il/wp-json/wp/v2/htafc_match",
            "game_page": "https://www.htafc.co.il/wp-json/wp/v2/posts?categories=30 (the club's match report per game)",
            "crosscheck": squadstats_url(*TM_CLUB, SEASON_START),
        },
        "metric": metric(game_rows, tm), "pool_rule": POOL_RULE,
        "starts_method": "Starter = named in the report's line-up block outside parentheses; sub = named inside parentheses with a minute.",
        "minutes_method": "Starter: until his substitution or red-card minute, else 90. Substitute: from his minute to 90 (or to his own "
                          "substitution/red card). Stoppage time ignored (45+6 counts as 45). Tiebreak only.",
        "matches_counted": game_rows,
        "friendlies_not_counted": [{"date": g["date"], "opponent": g["opponent"], "score": g["score"]} for g in friendlies],
        "tie_notes": tie_notes,
        "transfermarkt_crosscheck": tm,
        "design": design,
        "crop": shared,
        "crop_rule": ("Every club photo has the player's shirt number baked in (a flat #FF1521 numeral behind his right shoulder). "
                      "`photo_file` is the photo with that numeral keyed out (clean/<id>.png, tools/scrape/clean_number.py); "
                      "`photo_file_original` is the untouched download. Each starter/bench player has its own square `crop` "
                      "(fractions of the 1617x2242 source) from the TLV/Haifa auto rule run on the number-free photo: hair top 4% "
                      "below the top edge, shoulder line at 90% of the height, centred on the head. The top-level `crop` is the union "
                      "of the per-player boxes (a fallback only). Use build_images.py --mode box with photo_file. On the original "
                      "photos --mode auto frames on the numeral."),
        "players": players,
    }
    write_json_atomic(data / "players.json", doc)
    log_line(f"wrote players.json: {sum(p['role']=='starter' for p in players)} starters, {sum(p['role']=='bench' for p in players)} bench, "
             f"{sum(p['role']=='excluded' for p in players)} excluded; requests this run: {f.requests}")
    for p in players:
        s = p["stats"]
        print(f"{p['role']:8} {str(p['pool_rank'] or '-'):>3} #{'-' if p['number'] is None else p['number']:<3} {p['id']:22} {p['name_he']:18} apps {s['appearances']:2} st {s['starts']:2} "
              f"min {s['minutes']:4} | TM {'ok' if (p['crosscheck'].get('transfermarkt') or {}).get('match') else (p['crosscheck'].get('transfermarkt') or {}).get('tm')} "
              f"| {p['excluded_reason'] or ''}", flush=True)
    problems = check(doc)
    for msg in problems:
        log_line(f"PROBLEM: {msg}")
    if problems:
        log_line("players.json is written but not usable by the game tools; fix the problems above (no PLAYERS_READY)")
        return 1
    if a.mark_ready:
        (data / "PLAYERS_READY").write_text(dt.datetime.now(TZ).isoformat(timespec="seconds") + "\n", encoding="utf-8")
        log_line("PLAYERS_READY written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
