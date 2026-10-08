"""Contact sheets for the downloaded Hapoel Tel Aviv player photos.

Reads <data>/players.json, loads every starter/bench photo from <data>/raw/, and writes:
  * <data>/contact-sheet.png        full photos on a dark ground, each player's crop box drawn (white), the
                                    shared fallback box (dashed grey), labelled id / number / role
  * <data>/contact-sheet-crops<suffix>.png  every photo (`photo_file`, the number-free version) cut to its own crop
                                    box on --card-colour, with tick marks at the 4% hair-top and 90% shoulder guides

Usage:
  uv run --with pillow python -I -u contact_sheet.py --data <data-dir> [--card-colour ffffff] [--suffix -dark]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(1, str(Path(__file__).resolve().parents[3] / "_memory-game/tools/images"))  # framing.py

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from framing import SHOULDER_AT, TOP_MARGIN  # noqa: E402

SHEET_BG = (24, 24, 24)
DARK_TILE = (60, 60, 60)
WHITE = (255, 255, 255)
GREY = (160, 160, 160)
LABEL = (230, 230, 230)


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def tile_of(img: Image.Image, box_px: tuple, width: int, ground: tuple) -> Image.Image:
    x0, y0, x1, y1 = box_px
    scale = width / (x1 - x0)
    tile = Image.new("RGBA", (width, round((y1 - y0) * scale)), ground + (255,))
    scaled = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.Resampling.LANCZOS)
    tile.alpha_composite(scaled, (round(-x0 * scale), round(-y0 * scale)))
    return tile


def px_box(img: Image.Image, b: dict) -> tuple:
    w, h = img.size
    return (b["x0"] * w, b["y0"] * h, b["x1"] * w, b["y1"] * h)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--thumb", type=int, default=200)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--card-colour", default="ffffff", help="tile behind the crops (default: the listing's white card)")
    ap.add_argument("--suffix", default="", help="appended to the crop sheet's file name, e.g. -dark")
    args = ap.parse_args()
    ground = tuple(int(args.card_colour[i:i + 2], 16) for i in (0, 2, 4))

    data_dir = args.data.expanduser().resolve()
    doc = json.loads((data_dir / "players.json").read_text(encoding="utf-8"))
    shared = doc["crop"]
    players = [p for p in doc["players"] if p["role"] in ("starter", "bench") and p.get("photo_file")]

    t, label_h, cols = args.thumb, 40, args.cols
    rows = (len(players) + cols - 1) // cols
    full_h = round(t * 2242 / 1617)
    sheet = Image.new("RGB", (cols * (t + 10) + 10, rows * (full_h + label_h + 10) + 10), SHEET_BG)
    crops = Image.new("RGB", (cols * (t + 10) + 10, rows * (t + label_h + 10) + 10), SHEET_BG)
    d1, d2 = ImageDraw.Draw(sheet), ImageDraw.Draw(crops)
    f_big, f_small = font(15), font(12)
    for i, p in enumerate(players):
        img = Image.open(data_dir / p["photo_file"]).convert("RGBA")
        w, h = img.size
        own = p.get("crop") or shared
        col, row = i % cols, i // cols
        x, y = 10 + col * (t + 10), 10 + row * (full_h + label_h + 10)
        sheet.paste(tile_of(img, (0, 0, w, h), t, DARK_TILE).convert("RGB"), (x, y))
        s = t / w
        sx0, sy0, sx1, sy1 = px_box(img, shared)
        for k in range(0, int(sx1 - sx0), 14):
            d1.line([(x + (sx0 + k) * s, y + sy0 * s), (x + min(sx0 + k + 7, sx1) * s, y + sy0 * s)], fill=GREY, width=1)
            d1.line([(x + (sx0 + k) * s, y + sy1 * s), (x + min(sx0 + k + 7, sx1) * s, y + sy1 * s)], fill=GREY, width=1)
        ox0, oy0, ox1, oy1 = px_box(img, own)
        d1.rectangle([x + ox0 * s, y + oy0 * s, x + ox1 * s, y + oy1 * s], outline=WHITE, width=2)
        d1.text((x + 4, y + full_h + 4), p["id"], fill=WHITE, font=f_big)
        d1.text((x + 4, y + full_h + 22), f"#{p['number']}  {p['role']}", fill=LABEL, font=f_small)

        cx_, cy_ = 10 + col * (t + 10), 10 + row * (t + label_h + 10)
        crops.paste(tile_of(img, px_box(img, own), t, ground).crop((0, 0, t, t)).convert("RGB"), (cx_, cy_))
        for frac in (TOP_MARGIN, SHOULDER_AT):
            gy = cy_ + int(t * frac)
            d2.line([(cx_, gy), (cx_ + 12, gy)], fill=WHITE, width=2)
            d2.line([(cx_ + t - 12, gy), (cx_ + t, gy)], fill=WHITE, width=2)
        d2.text((cx_ + 4, cy_ + t + 4), p["id"], fill=WHITE, font=f_big)
        d2.text((cx_ + 4, cy_ + t + 22), f"#{p['number']}  {(p.get('framing') or {}).get('crop_px')}px", fill=LABEL, font=f_small)

    sheet.save(data_dir / "contact-sheet.png")
    crops.save(data_dir / f"contact-sheet-crops{args.suffix}.png")
    print(f"wrote contact-sheet.png, contact-sheet-crops{args.suffix}.png", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
