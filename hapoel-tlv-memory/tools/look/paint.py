"""Render the cards' dark red wall paint: img/club/paint.webp.

    uv run --with pillow==12.3.0 --with numpy python -I -u hapoel-tlv-memory/tools/look/paint.py

After the wine panel of the club's team-page banner: dark red paint dabbed and brushed over a darker
ground, in blotches with ragged edges and dry-brush strokes that break into bristle streaks. Every
layer is white noise shaped in the frequency domain, so the tile repeats seamlessly, and a fixed seed
makes the file reproducible. The card draws it as a plain background image: no filters on the device.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.dont_write_bytecode = True
GAME = Path(__file__).resolve().parents[2]
OUT = GAME / "img/club/paint.webp"

GROUND = "#5c0619"
# Painted in order over the ground: a round of dabs (the banner's two-tone mottle), then brush strokes.
# Sizes are fractions of the tile, `along` and `across` the stroke's direction; `cover` is the share of
# the tile a layer paints and `streak` how strongly its bristle lines show.
LAYERS = (
    {"colour": "#6c0a20", "cover": 0.60, "along": 0.08, "across": 0.08, "angle": 0, "streak": 0.2},
    {"colour": "#7a0d22", "cover": 0.42, "along": 0.32, "across": 0.08, "angle": 82, "streak": 0.7},
    {"colour": "#4e0214", "cover": 0.20, "along": 0.28, "across": 0.05, "angle": 98, "streak": 0.8},
    {"colour": "#871327", "cover": 0.14, "along": 0.24, "across": 0.06, "angle": 66, "streak": 0.7},
)


def rgb(hex_):
    return np.array([int(hex_[i:i + 2], 16) for i in (1, 3, 5)], dtype=float)


def shaped(rng, n, along, across, angle):
    """White noise blurred `along` px in the direction `angle` and `across` px across it, unit variance.
    The blur is a product in the frequency domain, so the result wraps around (it tiles)."""
    ky, kx = np.meshgrid(np.fft.fftfreq(n), np.fft.fftfreq(n), indexing="ij")
    t = np.deg2rad(angle)
    ku = kx * np.cos(t) + ky * np.sin(t)
    kv = -kx * np.sin(t) + ky * np.cos(t)
    gain = np.exp(-2 * np.pi ** 2 * ((along * ku) ** 2 + (across * kv) ** 2))
    field = np.real(np.fft.ifft2(np.fft.fft2(rng.standard_normal((n, n))) * gain))
    return (field - field.mean()) / field.std()


def smoothstep(lo, hi, x):
    t = np.clip((x - lo) / (hi - lo), 0, 1)
    return t * t * (3 - 2 * t)


def render(n, seed, ground=GROUND, layers=LAYERS):
    rng = np.random.default_rng(seed)
    img = np.broadcast_to(rgb(ground), (n, n, 3)).copy()
    for layer in layers:
        a = layer["angle"]
        body = shaped(rng, n, n * layer["along"], n * layer["across"], a)
        edge = shaped(rng, n, n * 0.012, n * 0.012, a)               # a ragged rim on every blotch
        bristles = shaped(rng, n, n * layer["along"] * 0.6, n * 0.0026, a)
        paint = body + 0.22 * edge + layer["streak"] * 0.5 * bristles
        level = np.quantile(paint, 1 - layer["cover"])
        alpha = smoothstep(level - 0.04, level + 0.22, paint)
        alpha *= 1 - layer["streak"] * 0.35 * smoothstep(0.2, 1.4, -bristles)  # dry brush: thin streaks
        img = img * (1 - alpha[..., None]) + rgb(layer["colour"]) * alpha[..., None]
    return Image.fromarray(np.clip(np.round(img), 0, 255).astype(np.uint8), "RGB")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--size", type=int, default=512, help="the square tile's side in px")
    ap.add_argument("--seed", type=int, default=1923, help="the club's founding year")
    ap.add_argument("--quality", type=int, default=80)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    tile = render(args.size, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    tile.save(args.out, "WEBP", quality=args.quality, method=6)
    print(f"{args.out}: {args.size}x{args.size}, {args.out.stat().st_size / 1024:.1f} KB", flush=True)


if __name__ == "__main__":
    main()
