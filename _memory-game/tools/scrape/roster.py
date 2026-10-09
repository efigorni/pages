"""The squad rule every club uses, and a check of the players.json fields the shared tools read.

    from roster import check, output_key, rank_key, select

The rule (P3 / H3): rank everyone with at least one appearance this season by appearances, then
starts, then minutes, then the lower shirt number (`pool_rank`); the pool is the top 23. The main 11
are the goalkeeper with the most appearances and the 10 outfield players of the pool with the most;
the bench is the pool's other outfield players. Backup goalkeepers are never dealt; one in the pool
may have role "quiz" (asked in the quiz only), and then the tools make his photo and clips too. Each scraper
counts `stats` from its own site and words its own `excluded_reason`.
"""

from __future__ import annotations

import re
from typing import NamedTuple

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


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


def select(eligible: list[dict], pool_size: int = 23) -> Selection:
    """Sets pool_rank on the ranked players and role ("starter" / "bench") on the chosen ones; the
    caller marks everyone else excluded, with its own reason."""
    ranked = sorted((p for p in eligible if p["stats"]["appearances"] >= 1), key=rank_key)
    for i, p in enumerate(ranked, 1):
        p["pool_rank"] = i
    pool = ranked[:pool_size]
    gks = [p for p in ranked if p["is_gk"]]
    top_gk = gks[0] if gks else None
    outfield = [p for p in pool if not p["is_gk"]]
    starters = ([top_gk] if top_gk else []) + outfield[:10]
    bench = outfield[10:]
    for p in starters:
        p["role"] = "starter"
    for p in bench:
        p["role"] = "bench"
    return Selection(ranked, pool, gks, top_gk, outfield, starters, bench)


def output_key(p: dict) -> tuple:
    """players.json order: starters, bench, excluded; goalkeepers first; by pool_rank, then number."""
    order = {"starter": 0, "bench": 1, "excluded": 2}
    return (order[p["role"]], not p["is_gk"], p["pool_rank"] or 999, p["number"] if p["number"] is not None else 999)


def check(payload: dict) -> list[str]:
    """What build_page.py, build_images.py and generate.py need from players.json; [] when it's all there."""
    problems = []
    dealt = [p for p in payload.get("players", []) if p.get("role") in ("starter", "bench")]
    starters = sum(p["role"] == "starter" for p in dealt)
    if starters != 11:
        problems.append(f"{starters} starters, not 11")
    if len(dealt) - starters < 4:
        problems.append(f"{len(dealt) - starters} bench players, fewer than 4")
    if sum(1 for p in dealt if p.get("role") == "starter" and p.get("is_gk")) != 1:
        problems.append("the main 11 has no goalkeeper (or more than one)")
    for p in dealt + [p for p in payload.get("players", []) if p.get("role") == "quiz"]:
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
