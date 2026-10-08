"""Fetch the member popup (admin-ajax get_team_member_info) for every men's first-team player.

Usage: uv run --with requests --with beautifulsoup4 python -I -u fetch_popups.py --html <html-dir> [--refresh]
Reads <html-dir>/players-fresh.html (an uncached render, for a valid nonce); writes members/<id>.json.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[3] / "_memory-game/tools/scrape"))  # the shared kit

from common import Fetcher, log_line  # noqa: E402
from htafc import AJAX, LISTING_HE, nonce_of, parse_listing, parse_popup  # noqa: E402


def ok(body: bytes) -> bool:
    try:
        return bool(json.loads(body).get("success"))
    except ValueError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", required=True, type=Path)
    ap.add_argument("--refresh", action="store_true")
    a = ap.parse_args()
    d = a.html.expanduser().resolve()
    page = (d / "players-fresh.html").read_text(encoding="utf-8")
    nonce = nonce_of(page)
    f = Fetcher(d, 0.6, a.refresh)
    players = parse_listing(page)
    log_line(f"{len(players)} players, nonce {nonce}")
    for p in players:
        body = f.cached_post(AJAX, {"action": "get_team_member_info", "memberID": p["member_id"], "nonce": nonce},
                             f"members/{p['member_id']}.json", headers={"Referer": LISTING_HE}, accept=ok)
        if not ok(body):
            log_line(f"  FAIL {p['member_id']} {p['name']}: {body[:120]!r}")
            continue
        pop = parse_popup(json.loads(body)["data"])
        print(p["member_id"], p["name"], "|", pop["name"], "|", pop["number"], "|", pop["position"], "|", pop["age"], "|",
              (pop["main_img"] or "-").rsplit("/", 1)[-1], pop["main_img_px"], "|", (pop["gallery_img"] or "-").rsplit("/", 1)[-1],
              "|", (pop["main_img_mobile"] or "-").rsplit("/", 1)[-1], flush=True)
    log_line(f"requests: {f.requests}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
