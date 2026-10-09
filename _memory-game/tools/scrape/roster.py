"""The squad rule every club uses, and a check of the players.json fields the shared tools read.

    from roster import SHIPPED, check, output_key, rank_key, select

The rule (P3 / H3): rank everyone with at least one appearance this season by appearances, then
starts, then minutes, then the lower shirt number (`pool_rank`); the pool is the top 23. The main 11
are the goalkeeper with the most appearances and the 10 outfield players of the pool with the most;
the bench is the pool's other outfield players. The pool's other goalkeepers are its backups (role
"backup"): never dealt in the memory game, asked in the quiz. Each scraper counts `stats` from its own
site and words its own `excluded_reason`. SHIPPED is every role a game ships (the image, voice, page
and refresh tools all read it).
"""

from __future__ import annotations

import re
from typing import NamedTuple

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DEALT = ("starter", "bench")
# Every role a game ships with a photo and clips: the dealt ones and the backups, asked in the quiz only.
# The image, voice, page and refresh tools all take exactly these, so none of them drops a backup.
SHIPPED = DEALT + ("backup",)


def rank_key(p: dict) -> tuple:
    s = p["stats"]
    return (-s["appearances"], -s["starts"], -s["minutes"], p["number"] if p["number"] is not None else 999)


class Selection(NamedTuple):
    ranked: list      # everyone with an appearance, best first (pool_rank 1..n)
    pool: list        # the top `pool_size` of ranked
    gks: list         # the ranked goalkeepers, best first
    top_gk: dict | None
    outfield: list    # the pool's outfield players, best first: 10 starters, then the bench
    starters: list
    bench: list
    backup: list      # the pool's goalkeepers after top_gk


def select(eligible: list[dict], pool_size: int = 23) -> Selection:
    """Sets pool_rank on the ranked players and role ("starter" / "bench" / "backup") on the chosen ones;
    the caller marks everyone else excluded, with its own reason."""
    ranked = sorted((p for p in eligible if p["stats"]["appearances"] >= 1), key=rank_key)
    for i, p in enumerate(ranked, 1):
        p["pool_rank"] = i
    pool = ranked[:pool_size]
    gks = [p for p in ranked if p["is_gk"]]
    top_gk = gks[0] if gks else None
    outfield = [p for p in pool if not p["is_gk"]]
    starters = ([top_gk] if top_gk else []) + outfield[:10]
    bench = outfield[10:]
    backup = [p for p in pool if p["is_gk"] and p is not top_gk]
    for role, chosen in (("starter", starters), ("bench", bench), ("backup", backup)):
        for p in chosen:
            p["role"] = role
    return Selection(ranked, pool, gks, top_gk, outfield, starters, bench, backup)


def output_key(p: dict) -> tuple:
    """players.json order: starters, bench, backups, excluded; goalkeepers first; by pool_rank, then number."""
    order = {"starter": 0, "bench": 1, "backup": 2, "excluded": 3}
    return (order[p["role"]], not p["is_gk"], p["pool_rank"] or 999, p["number"] if p["number"] is not None else 999)


def check(payload: dict) -> list[str]:
    """What build_page.py, build_images.py and generate.py need from players.json; [] when it's all there."""
    problems = []
    dealt = [p for p in payload.get("players", []) if p.get("role") in DEALT]
    starters = sum(p["role"] == "starter" for p in dealt)
    if starters != 11:
        problems.append(f"{starters} starters, not 11")
    if len(dealt) - starters < 4:
        problems.append(f"{len(dealt) - starters} bench players, fewer than 4")
    if sum(1 for p in dealt if p.get("role") == "starter" and p.get("is_gk")) != 1:
        problems.append("the main 11 has no goalkeeper (or more than one)")
    for p in [p for p in payload.get("players", []) if p.get("role") in SHIPPED]:
        pid = p.get("id", "?")
        if not ID_RE.match(str(pid)):
            problems.append(f"{pid!r}: not a safe id")
        if not isinstance(p.get("number"), int) or not 0 <= p["number"] <= 99:
            problems.append(f"{pid}: no shirt number 0-99 ({p.get('number')!r}); the card shows one")
        if not (p.get("name_he") or "").strip():
            problems.append(f"{pid}: no name_he")
        if not p.get("photo_file"):
            problems.append(f"{pid}: no photo_file")
        box = p.get("crop") or payload.get("crop")
        if not box or not (box["x0"] < box["x1"] and box["y0"] < box["y1"]):
            problems.append(f"{pid}: no usable crop box")
    return problems
