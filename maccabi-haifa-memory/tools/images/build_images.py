#!/usr/bin/env python3
"""Crop the club's cutout player photos to one consistent head-and-shoulders square WebP.

The Maccabi Haifa photos are transparent cutouts (palette PNGs with a transparency
chunk), so framing comes from the alpha mask.

Two framing modes:
  box   the crop box from players.json (the shared `crop`, or a player's own `crop`),
        as fractions of the source image.
  auto  framing derived from the alpha mask: the hair top sits --top below the crop's
        top edge and the shoulder line sits at --shoulder of the crop height, so faces
        come out the same size on every card.

Output is written at the crop's native resolution, capped at --max-size, and never
upscaled.

usage:
  uv run --with pillow python -I build_images.py <players.json> <out-dir>
      [--mode box|auto] [--top 0.04] [--shoulder 0.90] [--max-size 400]
      [--quality 82] [--sheet sheet.png] [--overrides overrides.json]

<players.json> is the scrape output; each player's `photo_file` is resolved relative to
the JSON's directory and must stay inside it. Only role starter/bench is processed.
overrides.json maps a player id to {"dx": .., "dy": .., "zoom": ..}, applied after
framing (dx/dy as fractions of the crop side, zoom > 1 = tighter).
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ALPHA_SOLID = 128


def row_extents(alpha):
    w, h = alpha.size
    solid = alpha.point(lambda v: 255 if v >= ALPHA_SOLID else 0)
    rows = []
    for y in range(h):
        box = solid.crop((0, y, w, y + 1)).getbbox()
        rows.append((box[0], box[2]) if box else None)
    return rows


def landmarks(img):
    """(head centre x, hair top y, shoulder line y) in source pixels."""
    w, h = img.size
    rows = row_extents(img.getchannel("A"))
    widths = [(r[1] - r[0]) if r else 0 for r in rows]
    top = next(y for y, wd in enumerate(widths) if wd >= max(3, 0.02 * w))
    body_max = max(widths)
    shoulder = next(y for y in range(top, h) if widths[y] >= 0.5 * body_max)
    head_rows = [rows[y] for y in range(top, top + max(1, int(0.6 * (shoulder - top)))) if rows[y]]
    centres = sorted((r[0] + r[1]) / 2 for r in head_rows)
    return centres[len(centres) // 2], top, shoulder


def box_from_fractions(img, crop):
    w, h = img.size
    return (crop["x0"] * w, crop["y0"] * h, crop["x1"] * w, crop["y1"] * h)


def box_auto(img, top_margin, shoulder_at):
    cx, top, shoulder = landmarks(img)
    side = (shoulder - top) / (shoulder_at - top_margin)
    x0, y0 = cx - side / 2, top - top_margin * side
    return (x0, y0, x0 + side, y0 + side)


def adjust(box, override):
    """Shift by dx/dy and zoom about the horizontal centre, keeping the top edge."""
    if not override:
        return box
    x0, y0, x1, _ = box
    side = x1 - x0
    new_side = side / override.get("zoom", 1.0)
    cx = (x0 + x1) / 2 + override.get("dx", 0.0) * side
    top = y0 + override.get("dy", 0.0) * side
    return (cx - new_side / 2, top, cx + new_side / 2, top + new_side)


def render(img, box, size, fade):
    x0, y0, x1, _ = box
    scale = size / (x1 - x0)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    scaled = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    canvas.alpha_composite(scaled, (round(-x0 * scale), round(-y0 * scale)))
    if fade > 0:
        # Ramp the alpha to zero over the bottom `fade` of the square, so the shirt never ends
        # in a hard line on a card that is taller than the photo.
        start = size * (1 - fade)
        ramp = Image.new("L", (1, size), 255)
        for y in range(size):
            if y > start:
                ramp.putpixel((0, y), round(255 * max(0.0, 1 - (y - start) / (size - start))))
        alpha = canvas.getchannel("A")
        canvas.putalpha(Image.composite(alpha, Image.new("L", (size, size), 0), ramp.resize((size, size))))
    return canvas


def contact_sheet(entries, path, guides, cell=200, cols=6):
    rows = (len(entries) + cols - 1) // cols
    label_h = 36
    sheet = Image.new("RGB", (cols * (cell + 10) + 10, rows * (cell + label_h + 10) + 10), (0, 29, 5))
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=14)
    except TypeError:
        font = ImageFont.load_default()
    guide = (134, 208, 148)
    for i, (pid, img, kb) in enumerate(entries):
        x = 10 + (i % cols) * (cell + 10)
        y = 10 + (i // cols) * (cell + label_h + 10)
        tile = Image.new("RGBA", (cell, cell), (32, 65, 38, 255))
        tile.alpha_composite(img.resize((cell, cell), Image.LANCZOS))
        sheet.paste(tile.convert("RGB"), (x, y))
        for frac in guides:
            gy = y + int(cell * frac)
            draw.line([(x, gy), (x + 14, gy)], fill=guide, width=2)
            draw.line([(x + cell - 14, gy), (x + cell, gy)], fill=guide, width=2)
        draw.text((x, y + cell + 4), pid, fill=(255, 255, 255), font=font)
        draw.text((x, y + cell + 20), f"{img.width}px  {kb:.1f} KB", fill=guide, font=font)
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("players_json", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--mode", choices=("box", "auto"), default="auto")
    ap.add_argument("--top", type=float, default=0.04, help="hair top, as a fraction of the crop (auto)")
    ap.add_argument("--shoulder", type=float, default=0.90, help="shoulder line, as a fraction of the crop (auto)")
    ap.add_argument("--fade", type=float, default=0.14, help="alpha ramp over the bottom of the crop (0 = off)")
    ap.add_argument("--max-size", type=int, default=400)
    ap.add_argument("--quality", type=int, default=82)
    ap.add_argument("--sheet", type=Path)
    ap.add_argument("--overrides", type=Path)
    args = ap.parse_args()

    data = json.loads(args.players_json.read_text(encoding="utf-8"))
    base = args.players_json.parent.resolve()
    overrides = json.loads(args.overrides.read_text(encoding="utf-8")) if args.overrides else {}
    args.out_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for p in data["players"]:
        if p.get("role") not in ("starter", "bench"):
            continue
        src = (base / p["photo_file"]).resolve()
        if base not in src.parents:
            sys.exit(f"{p['id']}: photo path escapes the data dir: {p['photo_file']}")
        img = Image.open(src).convert("RGBA")
        if args.mode == "box":
            box = box_from_fractions(img, p.get("crop") or data["crop"])
        else:
            box = box_auto(img, args.top, args.shoulder)
        box = adjust(box, overrides.get(p["id"], {}))
        native = int(box[2] - box[0])
        size = min(args.max_size, native)
        out = render(img, box, size, args.fade)
        dest = args.out_dir / f"{p['id']}.webp"
        out.save(dest, "WEBP", quality=args.quality, alpha_quality=90, method=6)
        kb = dest.stat().st_size / 1024
        cx, top, shoulder = landmarks(img)
        print(f"{p['id']:24} src={img.width}x{img.height} box=({box[0]:.0f},{box[1]:.0f},{box[2]:.0f},{box[3]:.0f}) "
              f"native={native} out={size} hair={(top - box[1]) / (box[3] - box[1]):.3f} "
              f"shoulder={(shoulder - box[1]) / (box[3] - box[1]):.3f} {kb:5.1f} KB", flush=True)
        entries.append((p["id"], out, kb))

    total = sum(kb for _, _, kb in entries)
    print(f"{len(entries)} images, {total:.0f} KB total, max {max(kb for _, _, kb in entries):.1f} KB", flush=True)
    if args.sheet:
        contact_sheet(entries, args.sheet, (args.top, args.shoulder))
        print(f"sheet: {args.sheet}", flush=True)


if __name__ == "__main__":
    main()
