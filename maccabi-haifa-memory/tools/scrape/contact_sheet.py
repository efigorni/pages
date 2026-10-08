"""Contact sheets for the downloaded Maccabi Haifa player photos.

Reads <data>/players.json, loads every starter/bench photo from <data>/raw/, and writes:
  * <data>/contact-sheet.png        full photos on the card green, each player's crop box drawn (white),
                                    the shared fallback box (dashed grey), labelled id / number / role
  * <data>/contact-sheet-crops.png  every photo cut to its own crop box (what a card shows)
  * <data>/contact-sheet-auto.png   what the TLV image tool's `--mode auto` would produce (no hand-read
                                    shoulder lines), to show where the alpha detector fails
and prints per-photo landmarks (fractions of the image).

Usage:
  uv run --with pillow python -I -u contact_sheet.py --data <data-dir>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))  # -I drops the script dir; framing.py is ours

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from framing import SHOULDER_AT, TOP_MARGIN, landmarks, square_crop  # noqa: E402

GROUND = (32, 65, 38)      # #204126, the /players card ground
SHEET_BG = (12, 23, 15)    # #0c170f
WHITE = (255, 255, 255)
GREY = (150, 170, 155)
LABEL = (190, 230, 196)
WARN = (255, 120, 120)


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def tile_of(img: Image.Image, box_px: tuple, width: int) -> Image.Image:
    x0, y0, x1, y1 = box_px
    scale = width / (x1 - x0)
    tile = Image.new("RGBA", (width, round((y1 - y0) * scale)), GROUND + (255,))
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
    args = ap.parse_args()

    data_dir = args.data.expanduser().resolve()
    doc = json.loads((data_dir / "players.json").read_text(encoding="utf-8"))
    shared = doc["crop"]
    players = [p for p in doc["players"] if p["role"] in ("starter", "bench") and p.get("photo_file")]

    t, label_h, cols = args.thumb, 40, args.cols
    rows = (len(players) + cols - 1) // cols
    full_h = round(t * 1.25)
    sheet = Image.new("RGB", (cols * (t + 10) + 10, rows * (full_h + label_h + 10) + 10), SHEET_BG)
    crops = Image.new("RGB", (cols * (t + 10) + 10, rows * (t + label_h + 10) + 10), SHEET_BG)
    autos = Image.new("RGB", (cols * (t + 10) + 10, rows * (t + label_h + 10) + 10), SHEET_BG)
    d1, d2, d3 = ImageDraw.Draw(sheet), ImageDraw.Draw(crops), ImageDraw.Draw(autos)
    f_big, f_small = font(15), font(12)

    print("id | role | crop (own) | crop px | hair_top | head_cx | shoulder used (source) | detector shoulder", flush=True)
    for i, p in enumerate(players):
        img = Image.open(data_dir / p["photo_file"]).convert("RGBA")
        w, h = img.size
        own = p.get("crop") or shared
        fr = p.get("framing") or {}
        col, row = i % cols, i // cols
        flag = fr.get("shoulder_source") not in (None, "alpha outline")
        label2 = f"#{p['number']}  {p['role']}" + ("  hand-read shoulder" if flag else "")
        print(p["id"], "|", p["role"], "|", own, "|", fr.get("crop_px"), "|", fr.get("hair_top"), "|", fr.get("head_cx"), "|",
              fr.get("shoulder_y_used"), f"({fr.get('shoulder_source')})", "|", fr.get("shoulder_y"), flush=True)

        x, y = 10 + col * (t + 10), 10 + row * (full_h + label_h + 10)
        sheet.paste(tile_of(img, (0, 0, w, h), t).convert("RGB"), (x, y))
        s = t / w
        sx0, sy0, sx1, sy1 = px_box(img, shared)
        for k in range(0, int(sx1 - sx0), 12):  # dashed shared box: top and bottom edges
            d1.line([(x + (sx0 + k) * s, y + sy0 * s), (x + min(sx0 + k + 6, sx1) * s, y + sy0 * s)], fill=GREY, width=1)
            d1.line([(x + (sx0 + k) * s, y + sy1 * s), (x + min(sx0 + k + 6, sx1) * s, y + sy1 * s)], fill=GREY, width=1)
        ox0, oy0, ox1, oy1 = px_box(img, own)
        d1.rectangle([x + ox0 * s, y + oy0 * s, x + ox1 * s, y + oy1 * s], outline=WHITE, width=2)
        d1.text((x + 4, y + full_h + 4), p["id"], fill=WHITE, font=f_big)
        d1.text((x + 4, y + full_h + 22), label2, fill=WARN if flag else LABEL, font=f_small)

        cx_, cy_ = 10 + col * (t + 10), 10 + row * (t + label_h + 10)
        crops.paste(tile_of(img, px_box(img, own), t).crop((0, 0, t, t)).convert("RGB"), (cx_, cy_))
        for frac in (TOP_MARGIN, SHOULDER_AT):
            gy = cy_ + int(t * frac)
            d2.line([(cx_, gy), (cx_ + 12, gy)], fill=LABEL, width=2)
            d2.line([(cx_ + t - 12, gy), (cx_ + t, gy)], fill=LABEL, width=2)
        d2.text((cx_ + 4, cy_ + t + 4), p["id"], fill=WHITE, font=f_big)
        d2.text((cx_ + 4, cy_ + t + 22), f"#{p['number']}  {fr.get('crop_px')}px" + ("  hand-read" if flag else ""),
                fill=WARN if flag else LABEL, font=f_small)

        auto = square_crop(img, landmarks(img))
        autos.paste(tile_of(img, px_box(img, auto), t).crop((0, 0, t, t)).convert("RGB"), (cx_, cy_))
        d3.text((cx_ + 4, cy_ + t + 4), p["id"], fill=WHITE, font=f_big)
        d3.text((cx_ + 4, cy_ + t + 22), f"#{p['number']}  TLV auto {round((auto['x1'] - auto['x0']) * w)}px",
                fill=WARN if flag else LABEL, font=f_small)

    sheet.save(data_dir / "contact-sheet.png")
    crops.save(data_dir / "contact-sheet-crops.png")
    autos.save(data_dir / "contact-sheet-auto.png")
    print("wrote contact-sheet.png, contact-sheet-crops.png, contact-sheet-auto.png", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
