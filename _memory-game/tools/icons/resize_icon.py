"""usage: python -I resize_icon.py <src.png> <size> <dest.png>"""
import sys
from PIL import Image

src, size, dest = sys.argv[1], int(sys.argv[2]), sys.argv[3]
Image.open(src).convert("RGBA").resize((size, size), Image.LANCZOS).save(dest, optimize=True)
