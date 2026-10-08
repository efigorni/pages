"""Contact sheet + framing measurements for the downloaded player photos.

Reads <data>/players.json, loads every starter/bench photo from <data>/raw/, and writes:
  * <data>/contact-sheet.png        full photos on navy, crop box drawn, labelled id + number
  * <data>/contact-sheet-crops.png  the same photos cut to the crop box (what a card shows)
and prints per-photo framing numbers (opaque bounding box, head top, head centre)
as fractions of the image, so one crop box can be chosen for all photos.

Usage:
  uv run --with pillow python -I -u contact_sheet.py --data <data-dir> [--crop x0,y0,x1,y1]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

NAVY = (19, 36, 86)
YELLOW = (248, 215, 52)
WHITE = (255, 255, 255)


def framing(img: Image.Image) -> dict:
    alpha = img.convert("RGBA").getchannel("A").point(lambda a: 255 if a > 40 else 0)
    w, h = img.size
    bbox = alpha.getbbox()
    if not bbox:
        return {}
    x0, y0, x1, y1 = bbox
    fig_h = y1 - y0
    head_band = alpha.crop((0, y0, w, y0 + max(1, int(fig_h * 0.18))))
    hb = head_band.getbbox()
    cols = [0] * w
    px = head_band.load()
    for y in range(head_band.height):
        for x in range(w):
            if px[x, y]:
                cols[x] += 1
    total = sum(cols) or 1
    cx = sum(i * c for i, c in enumerate(cols)) / total
    shoulder_y = y0 + int(fig_h * 0.40)
    sb = alpha.crop((0, shoulder_y, w, shoulder_y + 2)).getbbox()
    return {
        "bbox": [round(x0 / w, 3), round(y0 / h, 3), round(x1 / w, 3), round(y1 / h, 3)],
        "head_top": round(y0 / h, 3),
        "head_cx": round(cx / w, 3),
        "head_band_x": [round(hb[0] / w, 3), round(hb[2] / w, 3)] if hb else None,
        "width_at_40pct_fig": [round(sb[0] / w, 3), round(sb[2] / w, 3)] if sb else None,
    }


def font(size: int):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, type=Path)
    ap.add_argument("--crop", default=None, help="x0,y0,x1,y1 fractions; default = players.json crop")
    ap.add_argument("--thumb", type=int, default=220)
    ap.add_argument("--cols", type=int, default=6)
    args = ap.parse_args()

    data_dir = args.data.expanduser().resolve()
    doc = json.loads((data_dir / "players.json").read_text(encoding="utf-8"))
    c = doc.get("crop") or {}
    crop = [float(v) for v in args.crop.split(",")] if args.crop else [c.get("x0", 0), c.get("y0", 0), c.get("x1", 1), c.get("y1", 1)]
    players = [p for p in doc["players"] if p["role"] in ("starter", "bench") and p.get("photo_file")]

    t = args.thumb
    label_h = 44
    cols = args.cols
    rows = (len(players) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (t + 10) + 10, rows * (t + label_h + 10) + 10), NAVY)
    crop_w = int(t * (crop[2] - crop[0]) / max(crop[2] - crop[0], crop[3] - crop[1]))
    crop_h = int(t * (crop[3] - crop[1]) / max(crop[2] - crop[0], crop[3] - crop[1]))
    crops = Image.new("RGB", (cols * (crop_w + 10) + 10, rows * (crop_h + label_h + 10) + 10), NAVY)
    d1, d2 = ImageDraw.Draw(sheet), ImageDraw.Draw(crops)
    f_big, f_small = font(16), font(13)

    print("id, role, px, alpha, bbox, head_top, head_cx, head_band_x, width_at_40pct_fig", flush=True)
    default_crop = crop
    for i, p in enumerate(players):
        own = p.get("crop") if not args.crop else None
        crop = [own["x0"], own["y0"], own["x1"], own["y1"]] if own else default_crop
        img = Image.open(data_dir / p["photo_file"]).convert("RGBA")
        fr = framing(img)
        print(p["id"], p["role"], img.size, p.get("photo_has_alpha"), fr.get("bbox"), fr.get("head_top"),
              fr.get("head_cx"), fr.get("head_band_x"), fr.get("width_at_40pct_fig"), flush=True)
        col, row = i % cols, i // cols

        thumb = img.copy()
        thumb.thumbnail((t, t), Image.Resampling.LANCZOS)
        x, y = 10 + col * (t + 10), 10 + row * (t + label_h + 10)
        tile = Image.new("RGBA", (t, t), NAVY + (255,))
        ox, oy = (t - thumb.width) // 2, (t - thumb.height) // 2
        tile.alpha_composite(thumb, (ox, oy))
        sheet.paste(tile.convert("RGB"), (x, y))
        bx0, by0 = x + ox + crop[0] * thumb.width, y + oy + crop[1] * thumb.height
        bx1, by1 = x + ox + crop[2] * thumb.width, y + oy + crop[3] * thumb.height
        d1.rectangle([bx0, by0, bx1, by1], outline=YELLOW, width=2)
        d1.text((x + 4, y + t + 4), f"{p['id']}", fill=WHITE, font=f_big)
        d1.text((x + 4, y + t + 24), f"#{p['number']}  {p['role']}", fill=YELLOW, font=f_small)

        w, h = img.size
        cut = img.crop((int(crop[0] * w), int(crop[1] * h), int(crop[2] * w), int(crop[3] * h)))
        scale = min(crop_w / cut.width, crop_h / cut.height)
        cut = cut.resize((max(1, round(cut.width * scale)), max(1, round(cut.height * scale))), Image.Resampling.LANCZOS)
        cx, cy = 10 + col * (crop_w + 10), 10 + row * (crop_h + label_h + 10)
        ctile = Image.new("RGBA", (crop_w, crop_h), NAVY + (255,))
        ctile.alpha_composite(cut, ((crop_w - cut.width) // 2, (crop_h - cut.height) // 2))
        crops.paste(ctile.convert("RGB"), (cx, cy))
        d2.text((cx + 4, cy + crop_h + 4), f"{p['id']}", fill=WHITE, font=f_big)
        d2.text((cx + 4, cy + crop_h + 24), f"#{p['number']}  {p['role']}" + ("  own crop" if own else ""),
                fill=YELLOW, font=f_small)

    sheet.save(data_dir / "contact-sheet.png")
    crops.save(data_dir / "contact-sheet-crops.png")
    print(f"wrote {data_dir / 'contact-sheet.png'} and contact-sheet-crops.png (default crop {default_crop})", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
