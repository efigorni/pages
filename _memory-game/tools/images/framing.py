"""Head-and-shoulders framing from a cutout photo's alpha outline (build_images.py's auto mode and the scrapers).

The square crop puts the hair top TOP_MARGIN below its top edge and the shoulder line at SHOULDER_AT of its
height, centred on the head, so faces come out the same size on every card. The shoulder line is the first
row at least half as wide as the widest row; that test fails for 3/4-turned poses with big hair (it fires
inside the hair), so a hand-read shoulder line can be passed per player.
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
    body_max = max(widths)
    shoulder = next(y for y in range(top, h) if widths[y] >= 0.5 * body_max)
    head_rows = [rows[y] for y in range(top, top + max(1, int(0.6 * (shoulder - top)))) if rows[y]]
    centres = sorted((r[0] + r[1]) / 2 for r in head_rows)
    return widths, centres[len(centres) // 2], top, shoulder


def landmarks(img: Image.Image) -> dict:
    """Fractions of the image: hair top, head centre x, shoulder line, neck (narrowest row)."""
    img = img.convert("RGBA")
    w, h = img.size
    widths, cx, top, shoulder = outline(img)
    lo, hi = top + int(0.12 * h), min(h - 1, top + int(0.42 * h))
    neck = min(range(lo, hi), key=lambda y: widths[y] or w)
    return {
        "hair_top": round(top / h, 3),
        "head_cx": round(cx / w, 3),
        "shoulder_y": round(shoulder / h, 3),
        "neck_y": round(neck / h, 3),
        "shoulder_detector_failed": (shoulder - top) < 0.2 * h,
    }


def square_crop(img: Image.Image, lm: dict, shoulder_y: float | None = None) -> dict:
    """Crop box as fractions {x0, y0, x1, y1}; a square in pixels."""
    w, h = img.size
    top, cx = lm["hair_top"] * h, lm["head_cx"] * w
    shoulder = (shoulder_y if shoulder_y is not None else lm["shoulder_y"]) * h
    side = (shoulder - top) / (SHOULDER_AT - TOP_MARGIN)
    x0, y0 = cx - side / 2, top - TOP_MARGIN * side
    return {"x0": round(x0 / w, 4), "y0": round(y0 / h, 4), "x1": round((x0 + side) / w, 4), "y1": round((y0 + side) / h, 4)}
