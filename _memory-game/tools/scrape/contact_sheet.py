"""Contact sheets for a club's downloaded player photos, to look at before trusting a scrape.

  * <data>/contact-sheet.png        every photo whole, its own crop box drawn (white) and the shared
                                    fallback box (dashed grey), labelled id / number / role
  * <data>/contact-sheet-crops.png  every photo cut to its own crop box on the card colour, with ticks at
                                    the 4% hair-top and 90% shoulder guides (what a card shows)
  * <data>/contact-sheet-auto.png   with --auto: the default alpha rule's crop, no club rule or hand-read
                                    line, to show where the detector fails
and prints each photo's framing. Colours come from the club's club/club.json `images.sheet_colors`
(sheet, card, guide).

Usage:
  uv run --with pillow python -I -u _memory-game/tools/scrape/contact_sheet.py --game <game> --data <data-dir> [--auto]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "_memory-game/tools/images"))  # framing.py

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

from framing import SHOULDER_AT, TOP_MARGIN, landmarks, square_crop  # noqa: E402
from roster import SHIPPED  # noqa: E402

WHITE = (255, 255, 255)
GREY = (160, 160, 160)
LABEL = (230, 230, 230)


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def rgb(hexa: str) -> tuple:
    hexa = hexa.strip().lstrip("#")
    return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4))


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


def crop_sheet(entries, t, cols, colours, path, caption) -> None:
    sheet_bg, card, guide = colours
    rows = (len(entries) + cols - 1) // cols
    out = Image.new("RGB", (cols * (t + 10) + 10, rows * (t + 50) + 10), sheet_bg)
    d = ImageDraw.Draw(out)
    for i, (p, img, box) in enumerate(entries):
        x, y = 10 + (i % cols) * (t + 10), 10 + (i // cols) * (t + 50)
        out.paste(tile_of(img, px_box(img, box), t, card).crop((0, 0, t, t)).convert("RGB"), (x, y))
        for frac in (TOP_MARGIN, SHOULDER_AT):
            gy = y + int(t * frac)
            d.line([(x, gy), (x + 12, gy)], fill=guide, width=2)
            d.line([(x + t - 12, gy), (x + t, gy)], fill=guide, width=2)
        d.text((x + 4, y + t + 4), p["id"], fill=WHITE, font=font(15))
        d.text((x + 4, y + t + 22), caption(p, img, box), fill=LABEL, font=font(12))
    out.save(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game", required=True, help="the game folder (its club/club.json colours)")
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--thumb", type=int, default=200)
    ap.add_argument("--cols", type=int, default=6)
    ap.add_argument("--auto", action="store_true", help="also the default rule's crops")
    args = ap.parse_args()
    game = Path(args.game) if Path(args.game).is_dir() else REPO / args.game
    images = json.loads((game / "club/club.json").read_text(encoding="utf-8"))["images"]
    colours = [rgb(c) for c in images.get("sheet_colors", "111111,333333,ffffff").split(",")]

    data_dir = args.data.expanduser().resolve()
    doc = json.loads((data_dir / "players.json").read_text(encoding="utf-8"))
    shared = doc["crop"]
    players = [p for p in doc["players"] if p["role"] in SHIPPED and p.get("photo_file")]
    photos = [(p, Image.open(data_dir / p["photo_file"]).convert("RGBA")) for p in players]

    t, cols = args.thumb, args.cols
    rows = (len(photos) + cols - 1) // cols
    full_h = round(t * photos[0][1].height / photos[0][1].width) if photos else t
    sheet = Image.new("RGB", (cols * (t + 10) + 10, rows * (full_h + 50) + 10), colours[0])
    d = ImageDraw.Draw(sheet)
    print("id | role | crop | crop px | framing", flush=True)
    for i, (p, img) in enumerate(photos):
        x, y = 10 + (i % cols) * (t + 10), 10 + (i // cols) * (full_h + 50)
        sheet.paste(tile_of(img, (0, 0, img.width, img.height), t, colours[0]).convert("RGB"), (x, y))
        s = t / img.width
        sx0, sy0, sx1, sy1 = px_box(img, shared)
        for k in range(0, int(sx1 - sx0), 14):
            for sy in (sy0, sy1):
                d.line([(x + (sx0 + k) * s, y + sy * s), (x + min(sx0 + k + 7, sx1) * s, y + sy * s)], fill=GREY, width=1)
        ox0, oy0, ox1, oy1 = px_box(img, p.get("crop") or shared)
        d.rectangle([x + ox0 * s, y + oy0 * s, x + ox1 * s, y + oy1 * s], outline=WHITE, width=2)
        fr = p.get("framing") or {}
        hand = fr.get("shoulder_source") == "hand-read"
        d.text((x + 4, y + full_h + 4), p["id"], fill=WHITE, font=font(15))
        d.text((x + 4, y + full_h + 22), f"#{p['number']}  {p['role']}" + ("  hand-read shoulder" if hand else ""),
               fill=LABEL, font=font(12))
        print(p["id"], "|", p["role"], "|", p.get("crop"), "|", fr.get("crop_px"), "|",
              {k: v for k, v in fr.items() if k != "crop_px"}, flush=True)
    sheet.save(data_dir / "contact-sheet.png")
    crop_sheet([(p, img, p.get("crop") or shared) for p, img in photos], t, cols, colours,
               data_dir / "contact-sheet-crops.png", lambda p, img, box: f"#{p['number']}  {(p.get('framing') or {}).get('crop_px')}px")
    written = ["contact-sheet.png", "contact-sheet-crops.png"]
    if args.auto:
        crop_sheet([(p, img, square_crop(img, landmarks(img))) for p, img in photos], t, cols, colours,
                   data_dir / "contact-sheet-auto.png", lambda p, img, box: f"#{p['number']}  default rule")
        written.append("contact-sheet-auto.png")
    print(f"wrote {', '.join(written)} in {data_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
