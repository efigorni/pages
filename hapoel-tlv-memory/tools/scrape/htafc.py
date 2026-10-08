"""htafc.co.il parsers: the team & players listing, the member popup, the club's match reports.

Importable only (used by scrape_hapoel.py).
"""

from __future__ import annotations

import html as H
import re

from bs4 import BeautifulSoup

BASE = "https://www.htafc.co.il"
LISTING_HE = BASE + "/%d7%a6%d7%95%d7%95%d7%aa-%d7%95%d7%a9%d7%97%d7%a7%d7%a0%d7%99%d7%9d/"
LISTING_EN = BASE + "/en/staff-and-players/"
AJAX = BASE + "/wp-admin/admin-ajax.php"

SECTION_EN = {"שוערים": "goalkeeper", "הגנה": "defender", "קישור": "midfielder", "התקפה": "forward"}


def squash(text: str | None) -> str:
    return " ".join((text or "").split())


def largest_src(img) -> tuple[str, int]:
    best, best_w = img.get("src"), int(img.get("width") or 0)
    for part in (img.get("srcset") or "").split(","):
        bits = part.strip().split()
        if len(bits) == 2 and bits[1].endswith("w"):
            w = int(bits[1][:-1])
            if w > best_w:
                best, best_w = bits[0], w
    return best, best_w


def parse_listing(html: str, tab: str = "tab-1", subtab: str = "tab-1-subtab-1") -> list[dict]:
    """Players of one squad tab (default: the men's first team, 'בוגרים' > 'שחקנים'), in page order."""
    soup = BeautifulSoup(html, "html.parser")
    pane = soup.select_one(f"div#{subtab}")
    if pane is None:
        raise SystemExit(f"listing: no #{subtab}")
    out = []
    for row in pane.select("div.our-team__row"):
        section = squash(row.select_one(".our-team__row-title").get_text(" ")) if row.select_one(".our-team__row-title") else ""
        for i, m in enumerate(row.select("div.our-team__member")):
            btn = m.select_one("button[data-role='show-team-member-info']")
            img = m.select_one("img.our-team__member-img")
            name_el = m.select_one(".our-team__member-name")
            src, w = largest_src(img) if img else (None, 0)
            out.append({
                "member_id": int(btn["data-id"]) if btn else None,
                "name": squash(H.unescape(name_el.get_text(" "))) if name_el else "",
                "section": section,
                "section_index": i,
                "card_img": img.get("src") if img else None,
                "card_img_px": [int(img.get("width") or 0), int(img.get("height") or 0)] if img else None,
                "card_img_largest": src,
                "card_img_largest_w": w,
                "card_img_alt": img.get("alt") if img else None,
                "bottom_extra": squash(m.select_one(".our-team__member-bottom").get_text(" ")) if m.select_one(".our-team__member-bottom") else "",
            })
    return out


def nonce_of(html: str) -> str | None:
    m = re.search(r'"nonce":"([0-9a-f]+)"', html)
    return m.group(1) if m else None


def parse_popup(fragment: str) -> dict:
    soup = BeautifulSoup(fragment, "html.parser")

    def txt(sel):
        el = soup.select_one(sel)
        return squash(H.unescape(el.get_text(" "))) if el else None

    main = soup.select_one("img.team-popup__main-player")
    main_src = soup.select_one(".team-popup__main-img-wrapper source")
    gal = soup.select_one("img.team-popup__gallery-img")
    gal_src = soup.select_one(".team-popup__gallery source")
    bio = soup.select_one(".team-popup__content")
    number = txt(".team-popup__main-number")
    return {
        "name": txt(".team-popup__name"),
        "position": txt(".team-popup__position"),
        "age": txt(".team-popup__age"),
        "seasons": txt(".team-popup__experience"),
        "number": int(number) if number and number.isdigit() else None,
        "number_raw": number,
        "bio": "\n".join(squash(H.unescape(p.get_text(" "))) for p in bio.select("p")) if bio else None,
        "main_img": (main.get("src") or None) if main else None,
        "main_img_px": [int(main.get("width") or 0), int(main.get("height") or 0)] if main else None,
        "main_img_mobile": (main_src.get("srcset") or None) if main_src else None,
        "gallery_img": (gal.get("src") or None) if gal else None,
        "gallery_img_mobile": (gal_src.get("srcset") or None) if gal_src else None,
        "extra_classes": sorted({c for el in soup.select("[class]") for c in el.get("class", []) if c.startswith("team-popup")}),
    }


def report_text(content_html: str) -> str:
    t = re.sub(r"<br ?/?>", "\n", content_html)
    t = re.sub(r"</p>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    return H.unescape(t)


LINEUP_RE = re.compile(r"שיחקו בהפועל\s*:?\s*\n+\s*(.+?)\n", re.S)


def parse_lineup_block(text: str) -> list[dict]:
    """'שיחקו בהפועל:' then one line: 'A, B (C – 62), D (E – 46) ...'. Returns the starters in order,
    each with its chain of substitutes [(name, minute), ...] (a sub can himself be replaced: 'B (C – 46) (D – 80)'
    or nested 'B (C – 46, D – 80)')."""
    m = LINEUP_RE.search(text)
    if not m:
        return []
    line = m.group(1).strip()
    # split on commas that are not inside parentheses
    parts, depth, cur = [], 0, ""
    for ch in line:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(cur)
            cur = ""
        else:
            cur += ch
    if cur.strip():
        parts.append(cur)
    out = []
    for part in parts:
        part = part.strip()
        name = squash(part.split("(")[0])
        subs = []
        for inner in re.findall(r"\(([^()]*)\)", part):
            for piece in inner.split(","):
                mm = re.match(r"\s*(.+?)\s*[–\-—]\s*(\d+)(?:\s*\+\s*(\d+))?\s*$", piece)
                if mm:
                    subs.append({"name": squash(mm.group(1)), "minute": int(mm.group(2)),
                                 "added": int(mm.group(3)) if mm.group(3) else 0})
                else:
                    subs.append({"name": squash(piece), "minute": None, "added": 0, "unparsed": piece})
        out.append({"name": name, "raw": part, "subs": subs})
    return out
