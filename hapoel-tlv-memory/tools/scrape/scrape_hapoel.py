"""Hapoel Tel Aviv FC roster + 2026/27 appearances -> players.json (Haifa's shape).

Sources (all cached under <data>/html/, re-runs make no network calls unless --refresh):
  * htafc.co.il team & players page (Hebrew, uncached render for a fresh nonce) + its English twin
  * the member popup per player (admin-ajax get_team_member_info): number, position, age, bio
  * the club's own match reports (WP posts, category 30): the "שיחקו בהפועל:" line-up block per game
  * the club's fixture list (homepage): date, opponent, score, competition logo
  * Transfermarkt (club 1017) squad stats, all competitions 2026/27: cross-check only
Photos: the listing card image (original upload) per starter/bench player -> <data>/raw/<id>.png

Usage:
  uv run --with requests --with beautifulsoup4 --with pillow python -I -u scrape_hapoel.py --data <data-dir> \
      [--crop-override id=x0,y0,x1,y1 ...] [--mark-ready]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
import unicodedata
from collections import defaultdict
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[3] / "_memory-game/tools/images"))  # framing.py

from PIL import Image  # noqa: E402

from fetch import Fetcher, log_line  # noqa: E402
from framing import landmarks, pick_shoulder, square_crop  # noqa: E402
from htafc import LISTING_EN, LISTING_HE, SECTION_EN, parse_lineup_block, parse_listing, parse_popup, report_text  # noqa: E402
from tm_parse import parse_squadstats  # noqa: E402

SEASON = "2026/27"
TZ = dt.timezone(dt.timedelta(hours=3))
COMP_BY_LOGO = {
    "logo-winner-ligat.png": "ליגת ווינר",
    "gvia-hatoto.png": "גביע הטוטו",
    "uefa-conference-league-full-logo-2024-version1.png": "קונפרנס ליג - מוקדמות",
}
# Stage names from the club's own match records (wp-json/wp/v2/htafc_match titles), keyed by fixture date.
STAGE_BY_DATE = {
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
}
TM_REPORT_BY_DATE = {
    "2026-07-23": 4897987, "2026-07-30": 4898025, "2026-08-06": 4973731, "2026-08-12": 4973761,
    "2026-08-20": 5013818, "2026-08-27": 5013842, "2026-08-30": 4912901, "2026-09-03": 4912932,
    "2026-09-07": 4912945, "2026-09-14": 4912916, "2026-09-18": 4912958,
}
# The club's photo rules (club/club.json `images`). The shared shoulder rule (50%) fires inside the head on
# these chest-up photos, whose white sticker outline makes the head about half as wide as the chest: the
# first row >= 75% of the widest, from 30% of the height down, lands on the shoulder slope instead.
IMAGES = json.loads((Path(__file__).resolve().parents[2] / "club/club.json").read_text(encoding="utf-8"))["images"]
SHOULDER_RULE = {k: IMAGES[k] for k in ("shoulder_share", "shoulder_from") if k in IMAGES}
POSITION_EN = {"שוער": "Goalkeeper", "הגנה": "Defender", "קישור": "Midfielder", "קשר": "Midfielder", "התקפה": "Forward"}
SENT_OFF = "הורחק"
HOME_NAMES = ("הפועל תל-אביב", "הפועל תל אביב")
METRIC = (
    "2026/27 appearances in all competitions (13 official games played 2026-07-18 to 2026-09-18: 2x גביע הטוטו "
    "(משחק האירופאיות, חצי גמר), 6x UEFA Conference League qualifying (2nd round, 3rd round, play-off), 5x ליגת ווינר "
    "rounds 1-5), counted from the club's own match reports on htafc.co.il (the 'שיחקו בהפועל:' block: the starting "
    "eleven, each substitute in parentheses with his minute). Pre-season friendlies are not counted. Neither the "
    "listing nor the player popup shows any 2026/27 number (the popup bio only quotes 2025/26 totals in prose). "
    "Cross-check: Transfermarkt's all-competitions squad stats (which lack the two Toto Cup games) match the club "
    "count over the other 11 games for every player (appearances, substitutions on/off)."
)
POOL_RULE = (
    "P3: pool = top 23 by appearances (>= 1) across all players on the team & players page, ranked by appearances, "
    "then starts, then minutes, then lower jersey number (pool_rank); main 11 = the goalkeeper with the most "
    "appearances + the 10 outfield players with the most; bench = the other outfield players in the pool; backup "
    "goalkeepers excluded."
)


def norm_name(s: str) -> str:
    s = s.replace("׳", "'").replace("״", '"').replace("’", "'").replace("`", "'")
    return " ".join(s.split())


def slug(en: str) -> str:
    s = unicodedata.normalize("NFKD", en).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def season_date(ddmm: str) -> str:
    d, m = (int(x) for x in ddmm.split("."))
    return f"{2026 if m >= 7 else 2027:04d}-{m:02d}-{d:02d}"


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
        notes, unknown = [], []
        if len(block) != 11:
            notes.append(f"line-up block has {len(block)} starters")
        appearances = []  # (name, role, on, off, red)
        for s in block:
            chain = [(s["name"], 0)]
            red_at = None
            for x in s["subs"]:
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
    m = re.search(r"שיחקו בהפועל\s*:?\s*\n+\s*(.+?)\n", text, re.S)
    return " ".join(m.group(1).split()) if m else ""


def tm_crosscheck(html_dir: Path, players: list[dict], logs: dict) -> dict:
    d = parse_squadstats((html_dir / "ext/tm-leistungsdaten-2026.html").read_text(encoding="utf-8"))
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
    result = {"mismatches": [], "compared": 0, "tm_only": []}
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
            "tm_id": t["tm_id"], "tm_name": t["tm_name"], "scope": "Transfermarkt 'all competitions' 2026/27 = the 11 "
            "league + Conference League games (no Toto Cup)", "tm": {k: t[k] for k in ("appearances", "subs_on", "subs_off", "minutes", "in_squad")},
            "club_count_same_11_games": club, "match": same,
        }
        result["compared"] += 1
        if not same:
            result["mismatches"].append(f"{p['id']}: club {club} vs TM {t}")
    for rows in by_number.values():
        for t in rows:
            if t["tm_id"] not in matched_tm and t["appearances"]:
                result["tm_only"].append(f"{t['tm_name']} #{t['number']}: {t['appearances']} apps (not on the club listing)")
    return result


def photo_facts(path: Path) -> dict:
    raw = path.read_bytes()
    im = Image.open(path)
    fmt, mode, size = im.format, im.mode, im.size
    rgba = im.convert("RGBA")
    hist = rgba.getchannel("A").histogram()
    n = size[0] * size[1]
    return {"photo_px": list(size), "photo_format": fmt, "photo_mode": mode,
            "photo_has_alpha": hist[255] != n, "photo_transparent_share": round(hist[0] / n, 3),
            "photo_alpha_levels": sum(1 for v in hist if v), "photo_bytes": len(raw),
            "photo_sha1": hashlib.sha1(raw).hexdigest()}


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


def atomic_write(path: Path, data: str) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(data)
    os.chmod(tmp, 0o644)  # mkstemp creates 0600
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("--crop-override", action="append", default=[], help="id=x0,y0,x1,y1 (fractions)")
    ap.add_argument("--shoulder-override", action="append", default=[],
                    help="id=y (hand-read shoulder line, fraction); adds to club.json's shoulder_overrides")
    ap.add_argument("--mark-ready", action="store_true")
    a = ap.parse_args()
    data = a.data.expanduser().resolve()
    html_dir = data / "html"
    f = photos = Fetcher(data, 0.6, a.refresh)  # only photos are fetched here; pages are cached by the explore/fetch steps

    he_html = (html_dir / "players-fresh.html").read_text(encoding="utf-8")
    en_html = (html_dir / "players-en.html").read_text(encoding="utf-8")
    he, en = parse_listing(he_html), parse_listing(en_html)
    if len(he) != len(en) or any(x["section_index"] != y["section_index"] for x, y in zip(he, en)):
        raise SystemExit("HE and EN listings differ in shape")

    players = []
    for x, y in zip(he, en):
        pop = parse_popup(load_json(html_dir / f"members/{x['member_id']}.json")["data"])
        if norm_name(pop["name"]) != norm_name(x["name"]):
            raise SystemExit(f"popup name differs: {pop['name']} vs {x['name']}")
        pid = slug(y["name"])
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

    tm = tm_crosscheck(html_dir, players, logs)
    log_line(f"TM cross-check: {tm['compared']} compared, mismatches: {tm['mismatches'] or 'none'}")
    for s in tm["tm_only"]:
        log_line(f"  TM only: {s}")

    # selection (P3)
    ranked = sorted([p for p in players if p["stats"]["appearances"] >= 1],
                    key=lambda p: (-p["stats"]["appearances"], -p["stats"]["starts"], -p["stats"]["minutes"], p["number"]))
    for i, p in enumerate(ranked, 1):
        p["pool_rank"] = i
    for p in players:
        p.setdefault("pool_rank", None)
    pool = [p for p in ranked if p["pool_rank"] <= 23]
    gks = [p for p in pool if p["is_gk"]]
    outfield = [p for p in pool if not p["is_gk"]]
    starters = set([gks[0]["id"]] + [p["id"] for p in outfield[:10]])
    bench = set(p["id"] for p in outfield[10:])
    for p in players:
        if p["id"] in starters:
            p["role"], p["excluded_reason"] = "starter", None
        elif p["id"] in bench:
            p["role"], p["excluded_reason"] = "bench", None
        else:
            p["role"] = "excluded"
            if p["stats"]["appearances"] == 0:
                p["excluded_reason"] = ("goalkeeper, " if p["is_gk"] else "") + "0 appearances in 2026/27 (in no club line-up of the 13 official games)"
            elif p["is_gk"]:
                p["excluded_reason"] = f"backup goalkeeper (pool_rank {p['pool_rank']})"
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
        if p["role"] not in ("starter", "bench"):
            p["photo_file"] = None
            continue
        ext = Path(p["photo_url"]).suffix.lower() or ".png"
        rel = f"raw/{p['id']}{ext}"
        dest = data / rel
        if not dest.exists() or a.refresh:
            photos.cached(p["photo_url"], rel, force=True)
        p["photo_file_original"] = rel
        p.update(photo_facts(dest))
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

    order = {"starter": 0, "bench": 1, "excluded": 2}
    players.sort(key=lambda p: (order[p["role"]], not p["is_gk"], p["pool_rank"] or 99, p["number"]))
    pooled = [p for p in players if p.get("crop")]
    shared = {"x0": round(min(p["crop"]["x0"] for p in pooled), 4), "y0": round(min(p["crop"]["y0"] for p in pooled), 4),
              "x1": round(max(p["crop"]["x1"] for p in pooled), 4), "y1": round(max(p["crop"]["y1"] for p in pooled), 4)}

    design_path = data / "design/design.json"
    design = load_json(design_path) if design_path.exists() else None
    doc = {
        "season": SEASON, "season_id": 11226,
        "scraped_at": dt.datetime.fromtimestamp((html_dir / "players-fresh.html").stat().st_mtime, TZ).isoformat(timespec="seconds"),
        "built_at": dt.datetime.now(TZ).isoformat(timespec="seconds"),
        "sources": {
            "players": LISTING_HE, "players_en": LISTING_EN,
            "player_page": "https://www.htafc.co.il/?p=<site_member_id> (redirects to /team/<slug>/, a bare banner page); "
                           "the real player page is the listing's popup: POST admin-ajax.php action=get_team_member_info",
            "season_games": "https://www.htafc.co.il/ (fixture list) + https://www.htafc.co.il/wp-json/wp/v2/htafc_match",
            "game_page": "https://www.htafc.co.il/wp-json/wp/v2/posts?categories=30 (the club's match report per game)",
            "crosscheck": "https://www.transfermarkt.com/hapoel-tel-aviv/leistungsdaten/verein/1017/reldata/%262026/plus/1",
        },
        "metric": METRIC, "pool_rule": POOL_RULE,
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
    atomic_write(data / "players.json", json.dumps(doc, ensure_ascii=False, indent=2) + "\n")
    log_line(f"wrote players.json: {sum(p['role']=='starter' for p in players)} starters, {sum(p['role']=='bench' for p in players)} bench, "
             f"{sum(p['role']=='excluded' for p in players)} excluded; requests this run: {f.requests}")
    for p in players:
        s = p["stats"]
        print(f"{p['role']:8} {str(p['pool_rank'] or '-'):>3} #{p['number']:<3} {p['id']:22} {p['name_he']:18} apps {s['appearances']:2} st {s['starts']:2} "
              f"min {s['minutes']:4} | TM {'ok' if (p['crosscheck'].get('transfermarkt') or {}).get('match') else (p['crosscheck'].get('transfermarkt') or {}).get('tm')} "
              f"| {p['excluded_reason'] or ''}", flush=True)
    if a.mark_ready:
        (data / "PLAYERS_READY").write_text(dt.datetime.now(TZ).isoformat(timespec="seconds") + "\n", encoding="utf-8")
        log_line("PLAYERS_READY written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
