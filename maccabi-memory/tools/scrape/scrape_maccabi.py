"""Scrape the Maccabi Tel Aviv FC senior squad for the memory game.

Sources (all on www.maccabi-tlv.co.il):
  * stats page   - the eligible list (season goal list, includes 0-goal players)
  * roster page  - numbers, sections (GK/DF/MF/FW), profile links, stable player ids
  * results page - every played match of the current season
  * <match>/teams/ - official line-ups: starting XI + substitutes with minutes
  * player pages - Hebrew + English header (name, number, position, photo)

Starts come from the official match line-ups; the per-player match tables on the
player pages are used as an independent cross-check.

Usage:
  uv run --with requests --with beautifulsoup4 --with pillow \
      python -I -u scrape_maccabi.py --out <data-dir> [--refresh] [--crop x0,y0,x1,y1]

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
import time
import unicodedata
from pathlib import Path
from urllib.parse import unquote, urljoin

import requests
from bs4 import BeautifulSoup, NavigableString
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "_memory-game/tools/scrape"))  # the shared kit
from roster import SHIPPED  # noqa: E402

BASE = "https://www.maccabi-tlv.co.il"
STATS_URL = BASE + "/%d7%94%d7%a7%d7%91%d7%95%d7%a6%d7%95%d7%aa/%d7%a7%d7%91%d7%95%d7%a6%d7%94-%d7%91%d7%95%d7%92%d7%a8%d7%aa/stats/"
ROSTER_URL = BASE + "/%D7%94%D7%A7%D7%91%D7%95%D7%A6%D7%95%D7%AA/%D7%A7%D7%91%D7%95%D7%A6%D7%94-%D7%91%D7%95%D7%92%D7%A8%D7%AA/%D7%A1%D7%92%D7%9C/"
RESULTS_URL = BASE + "/%d7%9e%d7%a9%d7%97%d7%a7%d7%99%d7%9d-%d7%95%d7%aa%d7%95%d7%a6%d7%90%d7%95%d7%aa/%d7%94%d7%a7%d7%91%d7%95%d7%a6%d7%94-%d7%94%d7%91%d7%95%d7%92%d7%a8%d7%aa/%d7%aa%d7%95%d7%a6%d7%90%d7%95%d7%aa/"
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
CLUB_HE = "מכבי תל אביב"
SUBS_MARK = "מחליפים"
GK_SECTION = "שוערים"
SECTION_EN = {"שוערים": "goalkeeper", "הגנה": "defender", "קישור": "midfielder", "התקפה": "forward"}
FULL_MATCH = 90
WP_SIZE_SUFFIX = re.compile(r"-\d+x\d+(?=\.(?:png|jpe?g|webp|gif)$)", re.I)
TRANSLIT_EXTRA = {"ł": "l", "Ł": "l", "đ": "d", "Đ": "d", "ø": "o", "Ø": "o", "æ": "ae", "ß": "ss", "ı": "i"}


def log(msg: str) -> None:
    print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


class Fetcher:
    def __init__(self, cache_dir: Path, delay: float, refresh: bool):
        self.cache_dir = cache_dir
        self.delay = delay
        self.refresh = refresh
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept-Language": "he-IL,he;q=0.9,en;q=0.8",
        })
        self._last = 0.0
        self.network_requests = 0
        self.newest_fetch = 0.0  # mtime of the newest cached source page actually used

    def _note(self, path: Path) -> None:
        self.newest_fetch = max(self.newest_fetch, path.stat().st_mtime)

    def _wait(self) -> None:
        gap = time.monotonic() - self._last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last = time.monotonic()

    def get_bytes(self, url: str) -> bytes:
        self._wait()
        self.network_requests += 1
        resp = self.session.get(url, timeout=40)
        resp.raise_for_status()
        return resp.content

    def text(self, url: str, rel_path: str) -> str:
        path = self.cache_dir / rel_path
        if path.exists() and not self.refresh:
            data = path.read_bytes()
        else:
            log(f"GET {unquote(url)}")
            data = self.get_bytes(url)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        self._note(path)
        return data.decode("utf-8", "replace")

    def page(self, url: str, rel_path: str) -> BeautifulSoup:
        return BeautifulSoup(self.text(url, rel_path), "html.parser")


def clean(text: str) -> str:
    text = unicodedata.normalize("NFC", text or "")
    text = text.replace("‏", "").replace("‎", "").replace("‪", "").replace("‬", "")
    return re.sub(r"\s+", " ", text).strip()


def norm_name(text: str) -> str:
    """Key for matching the same player across pages (spacing / geresh variants / captain mark)."""
    text = clean(text)
    text = re.sub(r"\(ק\)", "", text)
    for ch in ("׳", "’", "‘", "`", "´"):
        text = text.replace(ch, "'")
    text = text.replace("״", '"')
    return re.sub(r"\s+", " ", text).strip()


def ascii_slug(text: str) -> str:
    text = "".join(TRANSLIT_EXTRA.get(c, c) for c in text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"['’`]", "", text.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


HE_TRANSLIT = {
    "א": "a", "ב": "b", "ג": "g", "ד": "d", "ה": "h", "ו": "v", "ז": "z", "ח": "ch", "ט": "t",
    "י": "y", "כ": "k", "ך": "ch", "ל": "l", "מ": "m", "ם": "m", "נ": "n", "ן": "n", "ס": "s",
    "ע": "", "פ": "p", "ף": "f", "צ": "tz", "ץ": "tz", "ק": "k", "ר": "r", "ש": "sh", "ת": "t",
}


def hebrew_slug(text: str) -> str:
    """Last-resort id when the site has no English name; flagged in the output."""
    return ascii_slug("".join(HE_TRANSLIT.get(c, c) for c in norm_name(text).replace("'", "")))


def minute_of(text: str) -> int | None:
    m = re.search(r"(\d+)(?:\s*\+\s*(\d+))?", text or "")
    if not m:
        return None
    return int(m.group(1)) + (int(m.group(2)) if m.group(2) else 0)


# ---------------------------------------------------------------- stats page

def parse_stats(soup: BeautifulSoup) -> list[dict]:
    main = soup.find("main", id="main")
    out = []
    for bar in main.select("div.yellowbar"):
        label = clean(bar.select_one(".bluelabel").get_text())
        m = re.match(r"(\d+)\.\s*(.+)", label)
        rank, name = (int(m.group(1)), m.group(2)) if m else (None, label)
        goals_txt = clean(bar.find("p").get_text()) if bar.find("p") else ""
        goals = minute_of(goals_txt)
        out.append({"rank": rank, "name": clean(name), "goals": goals, "goals_text": goals_txt})
    return out


# ---------------------------------------------------------------- roster page

def parse_roster(soup: BeautifulSoup) -> list[dict]:
    main = soup.find("main", id="main")
    players, section = [], None
    for el in main.find_all(["h2", "ul"]):
        if el.name == "h2":
            section = clean(el.get_text())
            continue
        if "players" not in (el.get("class") or []):
            continue
        for li in el.find_all("li", recursive=False):
            a = li.find("a", href=True)
            img = li.find("img")
            num = li.select_one(".number")
            name = li.select_one("h3")
            players.append({
                "lineup_id": li.get("id"),
                "section_he": section,
                "profile_url": a["href"] if a else None,
                "number": minute_of(num.get_text()) if num else None,
                "name": clean(name.get_text()) if name else None,
                "thumb_url": img.get("src") if img else None,
            })
    return players


# ---------------------------------------------------------------- results page

def parse_season(soup: BeautifulSoup) -> tuple[str | None, str | None]:
    label = None
    for a in soup.select(".row-filter .dropdown a"):
        m = re.search(r"\((\d{4}[/-]\d{2})\)", a.get_text())
        if m:
            label = m.group(1)
            break
    season_id = None
    if label:
        for a in soup.select(".row-filter a[href*='season=']"):
            if clean(a.get_text()) == label:
                m = re.search(r"season=(\d+)", a["href"])
                season_id = m.group(1) if m else None
                break
    return label, season_id


def parse_results(soup: BeautifulSoup) -> list[dict]:
    main = soup.find("main", id="main")
    matches, seen = [], set()
    for holder in main.select("div.fixtures-holder"):
        a = holder.find("a", href=True)
        if not a or "/match/" not in a["href"] or a["href"] in seen:
            continue
        seen.add(a["href"])
        classes = holder.get("class") or []
        loc = holder.select_one(".location")
        date_txt = clean(loc.find("span").get_text()) if loc and loc.find("span") else ""
        score = [clean(s.get_text()) for s in holder.select(".split .ss")]
        matches.append({
            "url": a["href"],
            "competition": clean(holder.select_one(".league-title").get_text()) if holder.select_one(".league-title") else None,
            "round": clean(holder.select_one(".round").get_text()) if holder.select_one(".round") else None,
            "opponent": clean(holder.select_one(".notmaccabi").get_text()) if holder.select_one(".notmaccabi") else None,
            "venue": "away" if "filter-away" in classes else ("home" if "filter-home" in classes else None),
            "date_text": date_txt,
            "score_text": " - ".join(score),
        })
    return matches


HE_MONTHS = {"ינו": 1, "פבר": 2, "מרץ": 3, "אפר": 4, "מאי": 5, "יונ": 6, "יול": 7, "אוג": 8,
             "ספט": 9, "אוק": 10, "נוב": 11, "דצמ": 12}


def parse_he_date(text: str) -> str | None:
    m = re.match(r"(\d{1,2})\s+(\S+)\s+(\d{4})", text or "")
    if not m:
        return None
    month = HE_MONTHS.get(m.group(2)[:3])
    return f"{m.group(3)}-{month:02d}-{int(m.group(1)):02d}" if month else None


# ---------------------------------------------------------------- line-ups

def parse_lineups(soup: BeautifulSoup) -> dict:
    # The page header also has a div.teams (score widget); the line-ups are the one holding div.p50 blocks.
    teams = next((t for t in soup.select("div.teams") if t.select("div.p50")), None)
    out = {"xi": [], "subs": [], "blocks": []}
    if not teams:
        return out
    for block in teams.select("div.p50"):
        title = clean(block.find("h3").get_text()) if block.find("h3") else ""
        out["blocks"].append(title)
        if title == CLUB_HE:
            is_subs = False
        elif title.startswith(CLUB_HE) and SUBS_MARK in title:
            is_subs = True
        else:
            continue  # opponent blocks and the coach blocks "(מאמן)"
        for li in block.select("ul > li"):
            if li.find("b", class_="playerLabel"):
                continue
            num_el = li.find("b")
            name_txt = "".join(t for t in li.find_all(string=True, recursive=False) if isinstance(t, NavigableString))
            pid = None
            for div in li.select("div[id]"):
                m = re.match(r"p(\d+)-", div["id"])
                if m:
                    pid = m.group(1)
                    break

            def cell(suffix: str):
                return li.find("div", id=f"p{pid}-{suffix}") if pid else None

            goals_el, exch_el, card_el = cell("goal"), cell("exchange"), cell("red")
            goal_minutes = [minute_of(x) for x in re.findall(r"\d+(?:\+\d+)?'", goals_el.get_text())] if goals_el else []
            exch = minute_of(exch_el.get_text()) if exch_el and clean(exch_el.get_text()) else None
            cards = []
            if card_el:
                mins = re.findall(r"\d+(?:\+\d+)?", card_el.get_text())
                imgs = [os.path.basename(i.get("src", "")) for i in card_el.find_all("img")]
                for i, src in enumerate(imgs):
                    cards.append({"minute": minute_of(mins[i]) if i < len(mins) else None, "icon": src})
            entry = {
                "lineup_id": pid,
                "number": minute_of(num_el.get_text()) if num_el else None,
                "name": norm_name(name_txt),
                "captain": "(ק)" in name_txt,
                "goal_minutes": goal_minutes,
                "exchange_minute": exch,
                "cards": cards,
            }
            (out["subs"] if is_subs else out["xi"]).append(entry)
    return out


def sent_off_minute(entry: dict) -> int | None:
    for c in entry["cards"]:
        icon = c["icon"].lower()
        if ("red" in icon) and c["minute"] is not None:
            return c["minute"]
    return None


# ---------------------------------------------------------------- player pages

def parse_player_page(soup: BeautifulSoup) -> dict:
    header = soup.select_one("div.player-header")
    info = header.select_one(".info") if header else None
    out: dict = {"header_found": bool(info)}
    if not info:
        return out
    h1 = info.find("h1")
    h2 = info.find("h2")
    out["number_text"] = clean(h1.get_text()) if h1 else None
    out["number"] = minute_of(out["number_text"]) if h1 else None
    out["name"] = clean(h2.get_text()) if h2 else None
    pos = []
    node = h2.next_sibling if h2 else None
    while node is not None and not (getattr(node, "name", None) == "div"):
        if isinstance(node, NavigableString):
            pos.append(str(node))
        node = node.next_sibling
    out["position"] = clean(" ".join(pos)) or None
    stats = {}
    for p33 in info.select(".stats .p33, .stats .p50"):
        val = p33.find("p")
        label = clean("".join(t for t in p33.find_all(string=True, recursive=False))).rstrip(":")
        stats[label] = clean(val.get_text()) if val else None
    out["header_stats"] = stats
    photo = header.select_one(".photo img")
    out["photo_src"] = photo.get("src") if photo else None
    out["photo_srcset"] = photo.get("srcset") if photo else None
    out["photo_attr_size"] = [photo.get("width"), photo.get("height")] if photo else None
    alt_en = soup.find("link", rel="alternate", hreflang="en")
    out["en_url"] = alt_en["href"] if alt_en and alt_en.get("href") else None
    blue = soup.select_one("div.blue-header[style]")
    m = re.search(r"url\(['\"]?([^'\")]+)", blue["style"]) if blue else None
    out["texture_url"] = m.group(1) if m else None
    rows = []
    for ul in soup.select("ul.player-stats"):
        if "player-stats-header" in (ul.get("class") or []):
            continue
        season = next((c.split("-")[-1] for c in ul.get("class", []) if c.startswith("filter-season-")), None)
        li = ul.find("li")
        if not li:
            continue
        cells = li.find_all("div", recursive=False)
        if len(cells) < 6:
            continue
        minute_cell = cells[4]
        icon = minute_cell.find("img")
        icon_name = os.path.basename(icon["src"]) if icon and icon.get("src") else ""
        link = cells[5].find("a", href=True)
        rows.append({
            "season_id": season,
            "date": clean(cells[0].get_text()),
            "competition": clean(cells[1].get_text()),
            "opponent": clean(cells[2].get_text()),
            "venue": clean(cells[3].get_text()),
            "minute": minute_of(minute_cell.get_text()),
            "icon": icon_name,
            "came_on": "-in" in icon_name,
            "went_off": "-out" in icon_name,
            "match_url": link["href"] if link else None,
            "goals": minute_of(cells[-1].get_text()) or 0,
        })
    out["rows"] = rows
    return out


# ---------------------------------------------------------------- photos

def inspect_image(data: bytes) -> dict:
    img = Image.open(io.BytesIO(data))
    img.load()
    has_alpha_channel = img.mode in ("RGBA", "LA", "PA") or (img.mode == "P" and "transparency" in img.info)
    transparent_share = None
    if has_alpha_channel:
        alpha = img.convert("RGBA").getchannel("A")
        hist = alpha.histogram()
        total = img.width * img.height
        transparent_share = round(hist[0] / total, 3)
        has_alpha_channel = alpha.getextrema()[0] < 255
    return {
        "format": img.format,
        "mode": img.mode,
        "px": [img.width, img.height],
        "has_alpha": bool(has_alpha_channel),
        "transparent_share": transparent_share,
        "bytes": len(data),
    }


def photo_candidates(page: dict, roster: dict) -> list[str]:
    cands = []
    for url in (page.get("photo_src"), roster.get("thumb_url")):
        if not url:
            continue
        for u in (WP_SIZE_SUFFIX.sub("", url), url):
            if u not in cands:
                cands.append(u)
    srcset = page.get("photo_srcset")
    if srcset:
        for part in srcset.split(","):
            u = part.strip().split(" ")[0]
            if u and u not in cands:
                cands.insert(0, u)
    return cands


# ---------------------------------------------------------------- design tokens

def hex_of(rgb) -> str:
    return "#%02x%02x%02x" % tuple(int(round(c)) for c in rgb[:3])


def norm_hex(value: str | None) -> str | None:
    if not value:
        return None
    v = value.strip().lower()
    if re.fullmatch(r"#[0-9a-f]{3}", v):
        v = "#" + "".join(c * 2 for c in v[1:])
    return v


def texture_colours(data: bytes) -> dict:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    small = img.resize((max(1, img.width // 8), max(1, img.height // 8)))
    raw = small.tobytes()
    n = len(raw) // 3
    mean = [sum(raw[i::3]) / n for i in range(3)]
    q = small.quantize(colors=6, method=Image.Quantize.MEDIANCUT)
    pal = q.getpalette()[: 6 * 3]
    counts = sorted(q.getcolors(), reverse=True)
    dominant = [{"hex": hex_of(pal[idx * 3: idx * 3 + 3]), "share": round(c / n, 3)} for c, idx in counts]
    w, h = img.size
    centre = img.crop((w * 2 // 5, h * 2 // 5, w * 3 // 5, h * 3 // 5)).resize((1, 1), Image.Resampling.BOX).getpixel((0, 0))
    return {"px": [w, h], "mean": hex_of(mean), "centre": hex_of(centre), "dominant": dominant}


def css_rule(css: str, selector: str) -> str | None:
    m = re.search(re.escape(selector) + r"\s*\{([^}]*)\}", css)
    return m.group(1) if m else None


def css_prop(block: str | None, prop: str) -> str | None:
    if not block:
        return None
    m = re.search(r"(?:^|;|\s)" + re.escape(prop) + r"\s*:\s*([^;]+)", block)
    return m.group(1).strip() if m else None


def design_tokens(fetcher: Fetcher, player_soup: BeautifulSoup, texture_url: str | None, out_dir: Path) -> dict:
    sheets = {}
    for link in player_soup.find_all("link", rel="stylesheet", href=True):
        href = link["href"]
        name = os.path.basename(href.split("?")[0])
        if "/themes/maccabitlv/" in href and name in ("style.css", "rtl.css"):
            sheets[name] = fetcher.text(urljoin(BASE, href), f"css/{name}")
    style, rtl = sheets.get("style.css", ""), sheets.get("rtl.css", "")
    info = css_rule(style, ".player-header .info")
    h1 = css_rule(style, ".player-header .info h1")
    h2 = css_rule(style, ".player-header .info h2")
    rtl_h2 = css_rule(rtl, ".player-header .info h2")
    # Hebrew site: rtl.css gives .player-header the family (with !important) and resets h1 to
    # `font-family: inherit`, so the number (h1) and the name (h2) both inherit it.
    header_family = css_prop(css_rule(rtl, ".player-header"), "font-family")
    header_family = header_family.replace("!important", "").strip() if header_family else None
    tokens = {
        "yellow": css_prop(info, "color"),
        "white": css_prop(h1, "color"),
        "name_font": header_family,
        "number_font": header_family,
        "name_font_weight": css_prop(h2, "font-weight"),
        "number_font_weight": css_prop(h1, "font-weight"),
        "name_font_size": css_prop(rtl_h2, "font-size") or css_prop(h2, "font-size"),
        "name_line_height": css_prop(rtl_h2, "line-height") or css_prop(h2, "line-height"),
        "name_letter_spacing": css_prop(h2, "letter-spacing"),
        "number_font_size": css_prop(h1, "font-size"),
        "english_site_number_font": "LeagueGothic (global h1 rule; rtl.css not loaded on /en/)",
        "texture_url": texture_url,
        "css_navy_constants": sorted(set(re.findall(r"#(?:132456|192e6d|162963|011947)\b", style + rtl, re.I))),
    }
    if texture_url:
        tex_path = out_dir / "raw" / "design" / ("texture" + Path(texture_url).suffix)
        if tex_path.exists() and not fetcher.refresh:
            data = tex_path.read_bytes()
        else:
            log(f"GET {texture_url}")
            data = fetcher.get_bytes(texture_url)
            tex_path.parent.mkdir(parents=True, exist_ok=True)
            tex_path.write_bytes(data)
        tokens["texture_file"] = str(tex_path.relative_to(out_dir))
        tokens["texture_colours"] = texture_colours(data)
    return tokens


# ---------------------------------------------------------------- main

def write_json_atomic(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, path)


def url_key(url: str) -> str:
    return hashlib.sha1(url.encode()).hexdigest()[:10]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True, type=Path, help="data directory (html/ cache, raw/ photos, players.json)")
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between network requests")
    ap.add_argument("--refresh", action="store_true", help="ignore the HTML/image cache and refetch everything")
    ap.add_argument("--crop", default="0,0,1,1", help="head-and-shoulders crop box as fractions x0,y0,x1,y1")
    ap.add_argument("--crop-override", action="append", default=[], metavar="ID=x0,y0,x1,y1",
                    help="per-player crop for a photo framed differently (repeatable)")
    ap.add_argument("--navy", default=None, help="override the navy token (hex); default = mean colour of the header texture")
    ap.add_argument("--mark-ready", action="store_true", help="create PLAYERS_READY after players.json is written")
    args = ap.parse_args()

    out: Path = args.out.expanduser().resolve()
    (out / "html").mkdir(parents=True, exist_ok=True)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    fetcher = Fetcher(out / "html", args.delay, args.refresh)
    def parse_box(text: str) -> list[float]:
        box = [float(x) for x in text.split(",")]
        if len(box) != 4 or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1):
            ap.error(f"bad crop box {text!r}: need x0,y0,x1,y1 fractions with x0<x1, y0<y1")
        return box

    crop = parse_box(args.crop)
    crop_overrides = {}
    for item in args.crop_override:
        pid, _, box = item.partition("=")
        crop_overrides[pid.strip()] = parse_box(box)

    log("stats page")
    stats_list = parse_stats(fetcher.page(STATS_URL, "stats.html"))
    log(f"  {len(stats_list)} players on the stats list")

    log("roster page")
    roster = parse_roster(fetcher.page(ROSTER_URL, "roster.html"))
    log(f"  {len(roster)} roster entries")
    roster_by_name = {}
    for r in roster:
        roster_by_name.setdefault(norm_name(r["name"]), r)

    log("results page")
    results_soup = fetcher.page(RESULTS_URL, "results.html")
    season_label, season_id = parse_season(results_soup)
    matches = parse_results(results_soup)
    log(f"  season {season_label} (id {season_id}): {len(matches)} played matches")

    lineup_matches = []
    for i, m in enumerate(matches, 1):
        m["date"] = parse_he_date(m["date_text"])
        teams_url = m["url"].rstrip("/") + "/teams/"
        log(f"  line-up {i}/{len(matches)}: {m['date']} {m['competition']} vs {m['opponent']}")
        lu = parse_lineups(fetcher.page(teams_url, f"matches/{m['date']}_{url_key(m['url'])}.teams.html"))
        m.update({"teams_url": teams_url, "xi": lu["xi"], "subs": lu["subs"]})
        if len(lu["xi"]) != 11:
            log(f"    WARNING: starting XI has {len(lu['xi'])} players")
        lineup_matches.append(m)
    lineup_matches.sort(key=lambda m: m["date"] or "")

    players = []
    texture_url, first_soup = None, None
    for i, s in enumerate(stats_list, 1):
        key = norm_name(s["name"])
        r = roster_by_name.get(key)
        rec = {"stats_name": s["name"], "stats_goals": s["goals"], "roster": r}
        log(f"player {i}/{len(stats_list)}: {key}")
        if not r or not r.get("profile_url"):
            rec["error"] = "not on the current roster page"
            players.append(rec)
            continue
        pid = r["lineup_id"]
        he_soup = fetcher.page(r["profile_url"], f"players/{pid}.he.html")
        he = parse_player_page(he_soup)
        first_soup = first_soup or he_soup
        texture_url = texture_url or he.get("texture_url")
        en = {}
        if he.get("en_url"):
            en = parse_player_page(fetcher.page(he["en_url"], f"players/{pid}.en.html"))
        rec.update({"he": he, "en": en})
        players.append(rec)

    # ---- appearances / starts / minutes from the official line-ups
    for rec in players:
        r = rec.get("roster")
        if not r or "he" not in rec:
            continue
        pid, key = r["lineup_id"], norm_name(r["name"])
        per_match = []
        for m in lineup_matches:
            role, entry = None, None
            for lst, role_name in ((m["xi"], "start"), (m["subs"], "sub")):
                for e in lst:
                    if (e["lineup_id"] and e["lineup_id"] == pid) or (not e["lineup_id"] and e["name"] == key):
                        role, entry = role_name, e
            if not entry:
                continue
            red = sent_off_minute(entry)
            if role == "start":
                end = min(x for x in (entry["exchange_minute"], red, FULL_MATCH) if x is not None)
                mins, played = end, True
            elif entry["exchange_minute"] is not None:
                start = entry["exchange_minute"]
                end = min(x for x in (red, FULL_MATCH) if x is not None)
                mins, played = max(1, end - start), True
                role = "sub_on"
            else:
                mins, played, role = 0, False, "unused_sub"
            per_match.append({"date": m["date"], "match_url": m["url"], "role": role, "minutes": mins,
                              "played": played, "goals": len(entry["goal_minutes"])})
        starts = sum(1 for x in per_match if x["role"] == "start")
        apps = sum(1 for x in per_match if x["played"])
        rec["lineup_stats"] = {
            "appearances": apps,
            "starts": starts,
            "sub_appearances": apps - starts,
            "unused_sub": sum(1 for x in per_match if x["role"] == "unused_sub"),
            "minutes": sum(x["minutes"] for x in per_match),
            "goals_from_lineups": sum(x["goals"] for x in per_match),
            "matches": per_match,
        }
        rows = [row for row in rec["he"].get("rows", []) if not season_id or row["season_id"] == season_id]
        rec["page_stats"] = {
            "appearances": len(rows),
            "starts": sum(1 for row in rows if not row["came_on"]),
            "goals": sum(row["goals"] for row in rows),
        }

    # ---- photos
    for rec in players:
        if "he" not in rec:
            continue
        cands = photo_candidates(rec["he"], rec["roster"])
        best = None
        rec["photo_checks"] = []
        for u in cands:
            cache = out / "html" / "img" / (url_key(u) + Path(u).suffix.lower())
            try:
                if cache.exists() and not args.refresh:
                    data = cache.read_bytes()
                else:
                    log(f"  GET {u}")
                    data = fetcher.get_bytes(u)
                    cache.parent.mkdir(parents=True, exist_ok=True)
                    cache.write_bytes(data)
                meta = inspect_image(data)
            except Exception as exc:  # noqa: BLE001 - record and move on
                rec["photo_checks"].append({"url": u, "error": str(exc)})
                continue
            meta["url"] = u
            rec["photo_checks"].append(meta)
            score = (meta["px"][0] * meta["px"][1], meta["has_alpha"], not WP_SIZE_SUFFIX.search(u))
            if not best or score > best[0]:
                best = (score, meta, data)
        rec["photo"] = best[1] if best else None
        rec["_photo_bytes"] = best[2] if best else None

    # ---- ids, roles
    used_ids = set()
    final = []
    for rec in players:
        r = rec.get("roster") or {}
        he, en = rec.get("he", {}), rec.get("en", {})
        name_en = en.get("name")
        base_id = ascii_slug(name_en) if name_en else hebrew_slug(he.get("name") or rec["stats_name"])
        pid = base_id or f"player-{r.get('lineup_id')}"
        n = 2
        while pid in used_ids:
            pid, n = f"{base_id}-{n}", n + 1
        used_ids.add(pid)
        ls = rec.get("lineup_stats", {})
        photo = rec.get("photo") or {}
        is_gk = (r.get("section_he") == GK_SECTION) or (he.get("position") == "שוער")
        final.append({
            "id": pid,
            "id_from": "english_name" if name_en else "hebrew_transliteration",
            "name_he": he.get("name") or rec["stats_name"],
            "name_en": name_en,
            "name_on_stats_page": rec["stats_name"],
            "number": he.get("number") if he.get("number") is not None else r.get("number"),
            "position_he": he.get("position"),
            "position_en": en.get("position"),
            "roster_section_he": r.get("section_he"),
            "roster_section_en": SECTION_EN.get(r.get("section_he")),
            "is_gk": is_gk,
            "lineup_id": r.get("lineup_id"),
            "profile_url": r.get("profile_url"),
            "profile_url_en": he.get("en_url"),
            "photo_url": photo.get("url"),
            "photo_file": None,
            "photo_px": photo.get("px"),
            "photo_has_alpha": photo.get("has_alpha"),
            "photo_transparent_share": photo.get("transparent_share"),
            "photo_format": photo.get("format"),
            "photo_bytes": photo.get("bytes"),
            "photo_candidates_checked": [
                {k: c.get(k) for k in ("url", "px", "has_alpha", "error") if k in c} for c in rec.get("photo_checks", [])
            ],
            "stats": {
                "appearances": ls.get("appearances"),
                "starts": ls.get("starts"),
                "minutes": ls.get("minutes"),
                "goals": rec["stats_goals"],
                "sub_appearances": ls.get("sub_appearances"),
                "unused_sub": ls.get("unused_sub"),
            },
            "crosscheck": {
                "roster_number": r.get("number"),
                "site_header_appearances": minute_of((he.get("header_stats") or {}).get("הופעות") or ""),
                "site_header_goals": minute_of((he.get("header_stats") or {}).get("שערים") or ""),
                "player_page_rows_appearances": (rec.get("page_stats") or {}).get("appearances"),
                "player_page_rows_starts": (rec.get("page_stats") or {}).get("starts"),
                "player_page_rows_goals": (rec.get("page_stats") or {}).get("goals"),
                "lineup_goals": ls.get("goals_from_lineups"),
            },
            "match_log": ls.get("matches", []),
            "role": None,
            "excluded_reason": rec.get("error"),
            "_photo_bytes": rec.get("_photo_bytes"),
        })

    def rank_key(p):
        s = p["stats"]
        return (-(s["starts"] or 0), -(s["minutes"] or 0), -(s["appearances"] or 0))

    eligible = []
    for p in final:
        if p["excluded_reason"]:
            p["role"] = "excluded"
        elif not p["photo_url"]:
            p["role"], p["excluded_reason"] = "excluded", "no photo on the player page"
        else:
            eligible.append(p)
    gks = sorted((p for p in eligible if p["is_gk"]), key=rank_key)
    outfield = sorted((p for p in eligible if not p["is_gk"]), key=rank_key)
    tie_notes = []
    if gks:
        gks[0]["role"] = "starter"
        for g in gks[1:]:
            if g["stats"]["appearances"] >= 1:
                g["role"] = "backup"  # never dealt, asked in the quiz
            else:
                g["role"], g["excluded_reason"] = "excluded", f"goalkeeper, not the most-started GK ({gks[0]['id']})"
        if len(gks) > 1 and rank_key(gks[0]) == rank_key(gks[1]):
            tie_notes.append(f"GK tie between {gks[0]['id']} and {gks[1]['id']}")
    for i, p in enumerate(outfield):
        p["role"] = "starter" if i < 10 else "bench"
    if len(outfield) > 10 and rank_key(outfield[9]) == rank_key(outfield[10]):
        tie_notes.append(f"exact tie at the 10th outfield slot: {outfield[9]['id']} vs {outfield[10]['id']}")

    for p in final:
        data = p.pop("_photo_bytes")
        if p["role"] in SHIPPED and data:
            ext = Path(p["photo_url"]).suffix.lower() or ".png"
            dest = out / "raw" / f"{p['id']}{ext}"
            dest.write_bytes(data)
            p["photo_file"] = f"raw/{p['id']}{ext}"
        box = crop_overrides.pop(p["id"], None)
        p["crop"] = {"x0": box[0], "y0": box[1], "x1": box[2], "y1": box[3]} if box else None
    if crop_overrides:
        ap.error(f"--crop-override for unknown ids: {', '.join(crop_overrides)}")

    log("design tokens")
    design = design_tokens(fetcher, first_soup, texture_url, out) if first_soup else {}
    tex = design.get("texture_colours") or {}
    navy = norm_hex(args.navy) or tex.get("mean")
    if tex.get("dominant"):
        design["navy_ground"] = tex["dominant"][0]["hex"]
        design["navy_lettering"] = tex["dominant"][1]["hex"] if len(tex["dominant"]) > 1 else None
    design_out = {
        "navy": navy,
        "yellow": norm_hex(design.get("yellow")),
        "white": norm_hex(design.get("white")),
        "name_font": design.get("name_font"),
        "number_font": design.get("number_font"),
        "texture_url": design.get("texture_url"),
        "details": design,
    }

    role_order = {"starter": 0, "bench": 1, "backup": 2, "excluded": 3}
    final.sort(key=lambda p: (role_order[p["role"]], not p["is_gk"], rank_key(p)))
    now = dt.datetime.now(dt.timezone.utc).astimezone()
    fetched = dt.datetime.fromtimestamp(fetcher.newest_fetch, dt.timezone.utc).astimezone() if fetcher.newest_fetch else now
    payload = {
        "season": season_label,
        "season_id": season_id,
        "scraped_at": fetched.isoformat(timespec="seconds"),
        "built_at": now.isoformat(timespec="seconds"),
        "sources": {"stats": unquote(STATS_URL), "roster": unquote(ROSTER_URL), "results": unquote(RESULTS_URL)},
        "starts_method": (
            "Counted from the club's official match line-ups (<match>/teams/ pages, starting XI vs "
            "'מחליפים') for every played match on the club results page for the season, all competitions; "
            "cross-checked against each player page's per-match table (rows without the sub-in icon)."
        ),
        "minutes_method": (
            "Starter: until the substitution/red-card minute, else 90. Substitute: 90 minus the minute he came on. "
            "Stoppage and extra time ignored (tiebreak only)."
        ),
        "matches_counted": [
            {"date": m["date"], "competition": m["competition"], "round": m["round"], "opponent": m["opponent"],
             "venue": m["venue"], "url": unquote(m["url"]), "xi_size": len(m["xi"])}
            for m in lineup_matches
        ],
        "tie_notes": tie_notes,
        "design": design_out,
        "crop": {"x0": crop[0], "y0": crop[1], "x1": crop[2], "y1": crop[3]},
        "players": final,
    }
    write_json_atomic(out / "players.json", payload)
    write_json_atomic(out / "matches.json", {"season": season_label, "matches": lineup_matches})
    log(f"wrote {out / 'players.json'} ({sum(p['role'] == 'starter' for p in final)} starters, "
        f"{sum(p['role'] == 'bench' for p in final)} bench, {sum(p['role'] == 'backup' for p in final)} backup, "
        f"{sum(p['role'] == 'excluded' for p in final)} excluded); "
        f"{fetcher.network_requests} network requests")
    if tie_notes:
        log("TIES: " + "; ".join(tie_notes))
    if args.mark_ready:
        (out / "PLAYERS_READY").write_text(payload["scraped_at"] + "\n", encoding="utf-8")
        log("created PLAYERS_READY")
    return 0


if __name__ == "__main__":
    sys.exit(main())
