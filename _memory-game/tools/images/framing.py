"""Head-and-shoulders framing from a cutout photo's alpha outline (build_images.py's auto mode and the scrapers).

The square crop puts the hair top TOP_MARGIN below its top edge and the shoulder line at SHOULDER_AT of its
height, centred on the head, so faces come out the same size on every card. By default the shoulder line is
the first row at least half as wide as the widest row. A club whose photos need another rule sets it in its
club/club.json `images` (shoulder_share, shoulder_from), and a hand-read line per player
(shoulder_overrides) where no rule works, e.g. 3/4-turned poses with big hair, where the test fires inside
the hair.
"""

from __future__ import annotations

from PIL import Image

TOP_MARGIN = 0.04
SHOULDER_AT = 0.90
ALPHA_SOLID = 128


def row_widths(img: Image.Image) -> list[tuple[int, int] | None]:
    """Per row, the (left, right) extent of the solid alpha, or None for an empty row. img is RGBA."""
    alpha = img.getchannel("A").point(lambda v: 255 if v >= ALPHA_SOLID else 0)
    w, h = img.size
    rows = []
    for y in range(h):
        box = alpha.crop((0, y, w, y + 1)).getbbox()
        rows.append((box[0], box[2]) if box else None)
    return rows


def outline(img: Image.Image) -> tuple[list[int], float, int, int]:
    """(row widths, head centre x, hair top y, shoulder line y) in source pixels. img is RGBA."""
    w, h = img.size
    rows = row_widths(img)
    widths = [(r[1] - r[0]) if r else 0 for r in rows]
    top = next(y for y, wd in enumerate(widths) if wd >= max(3, 0.02 * w))
    shoulder = shoulder_row(widths, top)
    head_rows = [rows[y] for y in range(top, top + max(1, int(0.6 * (shoulder - top)))) if rows[y]]
    centres = sorted((r[0] + r[1]) / 2 for r in head_rows)
    return widths, centres[len(centres) // 2], top, shoulder


def shoulder_row(widths: list[int], start: int, share: float = 0.5) -> int:
    """The first row from `start` whose solid alpha is at least `share` of the widest row."""
    widest = max(widths)
    return next(y for y in range(start, len(widths)) if widths[y] >= share * widest)


def landmarks(img: Image.Image, shoulder_share: float = 0.5, shoulder_from: float | None = None) -> dict:
    """Fractions of the image: hair top, head centre x, shoulder line, neck (narrowest row).

    The shoulder line follows the club's rule: the first row at least `shoulder_share` of the widest,
    searched from `shoulder_from` (a fraction of the height) or else from the hair top. The head centre
    and the neck always come from the default rule."""
    img = img.convert("RGBA")
    w, h = img.size
    widths, cx, top, shoulder = outline(img)
    if shoulder_share != 0.5 or shoulder_from is not None:
        shoulder = shoulder_row(widths, top if shoulder_from is None else int(shoulder_from * h), shoulder_share)
    lo, hi = top + int(0.12 * h), min(h - 1, top + int(0.42 * h))
    neck = min(range(lo, hi), key=lambda y: widths[y] or w)
    return {
        "hair_top": round(top / h, 3),
        "head_cx": round(cx / w, 3),
        "shoulder_y": round(shoulder / h, 3),
        "neck_y": round(neck / h, 3),
        "shoulder_detector_failed": (shoulder - top) < 0.2 * h,
    }


def pick_shoulder(lm: dict, hand: float | None = None) -> tuple[float, str]:
    """The shoulder line a crop uses and where it came from: a hand-read line, else the outline's, else
    (the detector fired too close to the hair) the neck plus 7% of the height."""
    if hand is not None:
        return hand, "hand-read"
    if lm["shoulder_detector_failed"]:
        return round(lm["neck_y"] + 0.07, 3), "neck + 0.07 (alpha detector failed; add a club.json shoulder_overrides line)"
    return lm["shoulder_y"], "alpha outline"


def square_crop(img: Image.Image, lm: dict, shoulder_y: float | None = None) -> dict:
    """Crop box as fractions {x0, y0, x1, y1}; a square in pixels."""
    w, h = img.size
    top, cx = lm["hair_top"] * h, lm["head_cx"] * w
    shoulder = (shoulder_y if shoulder_y is not None else lm["shoulder_y"]) * h
    side = (shoulder - top) / (SHOULDER_AT - TOP_MARGIN)
    x0, y0 = cx - side / 2, top - TOP_MARGIN * side
    return {"x0": round(x0 / w, 4), "y0": round(y0 / h, 4), "x1": round((x0 + side) / w, 4), "y1": round((y0 + side) / h, 4)}
