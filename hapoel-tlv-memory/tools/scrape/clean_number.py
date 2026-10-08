"""Remove the shirt number the club bakes into every player photo (a flat red numeral behind the player).

The numeral is one flat colour (measured per photo: the most common opaque colour in the top-right quarter,
#FF1521 in every photo so far); the shirt reds are shaded and differ. Pixels within --tol of that colour are labelled
into connected blobs, and only blobs of at least --min-area pixels that start in the top 15% of the photo (the
glyphs), plus any number-coloured blob lying wholly within the glyphs' rows and slivers within 25 px of them and no
lower than their bottom (the pieces where the white outline cuts a glyph), are cleared. A flat shirt highlight can match the colour (Toriel's shoulder does), but it never starts
in the top band, so the shirt is never punched out. The glyphs' anti-aliased rim (a red-to-white or red-to-transparent blend) is cleared within --rim px
when it is redder than it is white. The white sticker outline was drawn semi-transparent over the numeral, so where
they overlapped it is pink: pinkish pixels within 24 px of a glyph are set to white. The player and the shirt are
untouched.

Usage:
  uv run --with pillow --with numpy --with scipy python -I -u clean_number.py <in.png> <out.png> [--tol 14] [--min-area 3000] [--rim 3]
  (or import clean(img) -> (img, stats))
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def number_colour(arr: np.ndarray) -> tuple[int, int, int]:
    h, w, _ = arr.shape
    q = arr[: h // 2, w // 2:].reshape(-1, 4)
    q = q[q[:, 3] == 255]
    red = q[(q[:, 0] > 200) & (q[:, 1] < 80) & (q[:, 2] < 90)]
    vals, counts = np.unique(red[:, :3], axis=0, return_counts=True)
    return tuple(int(v) for v in vals[counts.argmax()])


def clean(img: Image.Image, tol: int = 14, min_area: int = 3000, rim: int = 3, top_band: float = 0.15):
    arr = np.array(img.convert("RGBA"))
    c = np.array(number_colour(arr), dtype=np.int16)
    rgb = arr[:, :, :3].astype(np.int16)
    close = (np.abs(rgb - c) <= tol).all(axis=2) & (arr[:, :, 3] > 0)
    labels, n = ndimage.label(close, structure=np.ones((3, 3)))
    areas = ndimage.sum(close, labels, index=np.arange(1, n + 1))
    h = close.shape[0]
    # glyphs: big blobs that start in the top band (every numeral starts at y ~0.07); a flat shirt highlight can
    # match the colour and be big, but it never starts that high
    slices = ndimage.find_objects(labels)
    glyph_ids = [i + 1 for i, sl in enumerate(slices)
                 if sl is not None and areas[i] >= min_area and sl[0].start <= top_band * h]
    keep = np.isin(labels, glyph_ids)
    if keep.any():
        rows = np.nonzero(keep.any(axis=1))[0]
        top, bottom = rows.min(), rows.max()
        # pieces the white outline cuts off a glyph: number-coloured blobs lying wholly within the numeral's rows
        pieces = [i + 1 for i, sl in enumerate(slices)
                  if sl is not None and areas[i] >= 20 and sl[0].start >= top - 5 and sl[0].stop - 1 <= bottom + 3]
        keep |= np.isin(labels, pieces)
        # slivers: number-coloured pixels close to a glyph and no lower than its bottom
        near = ndimage.binary_dilation(keep, iterations=25)
        near[bottom + 1:] = False
        keep |= close & near
    # rim: within `rim` px of a glyph, clear pixels that are a red/white or red/transparent blend (reddish, not shirt)
    near = ndimage.binary_dilation(keep, iterations=rim) & ~keep
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    reddish = (r > 180) & (r - g > 40) & (np.abs(g - b) < 40)
    rim_mask = near & reddish
    out = arr.copy()
    out[keep | rim_mask, 3] = 0
    # the white sticker outline was drawn semi-transparent over the numeral, so where they overlapped it is pink:
    # whiten pinkish pixels within 24 px of a glyph (only outline lives there; hair and skin are beyond it)
    halo = ndimage.binary_dilation(keep, iterations=24) & ~keep & ~rim_mask
    pink = (r >= 235) & (g >= 40) & (np.abs(g - b) <= 30) & (r - g >= 15) & (arr[:, :, 3] > 0)
    out[halo & pink, :3] = 255
    stats = {"number_rgb": [int(v) for v in c], "blobs": len(glyph_ids),
             "cleared_px": int(keep.sum() + rim_mask.sum()), "cleared_share": round(float((keep | rim_mask).mean()), 4),
             "outline_px_whitened": int((halo & pink).sum()), "bbox_number": None}
    ys, xs = np.nonzero(keep)
    if len(xs):
        h, w = keep.shape
        stats["bbox_number"] = [round(xs.min() / w, 3), round(ys.min() / h, 3), round(xs.max() / w, 3), round(ys.max() / h, 3)]
    return Image.fromarray(out, "RGBA"), stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--tol", type=int, default=14)
    ap.add_argument("--min-area", type=int, default=3000)
    ap.add_argument("--rim", type=int, default=3)
    a = ap.parse_args()
    img, stats = clean(Image.open(a.src), a.tol, a.min_area, a.rim)
    img.save(a.dst, optimize=True)
    print(stats)
    return 0


if __name__ == "__main__":
    sys.exit(main())
