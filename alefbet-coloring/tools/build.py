#!/usr/bin/env python3
"""Build the alef-bet coloring pages: alefbet-coloring/index.html, one self-contained file.

    uv run --quiet --with svgelements==1.9.6 python -I alefbet-coloring/tools/build.py art
    uv run --quiet --with fonttools==4.60.1 --with brotli==1.1.0 python -I alefbet-coloring/tools/build.py glyphs
    python3 -I alefbet-coloring/tools/build.py assemble [--check]

The sources, all hand-owned except the two files `art` and `glyphs` write:

  src/words.json     per letter its name (with niqqud) and its words: the word with niqqud, its drawing
                     ("openmoji:<hexcode>" or "custom:<name>") and where the word comes from (keys of
                     `sources`). The first DEFAULT_PICKS words are the page's default picks, or
                     the first "picks" words for a letter that sets its own count.
  src/page.html      the page: style, controls and the layout script, with the {{…}} slots assemble fills
  art-src/<name>.svg a hand-drawn drawing for "custom:<name>", in OpenMoji's line style (72×72, stroke 2)
  art/*.svg          every drawing words.json names, normalized: written by `art`
  src/letters.json   the 22 letters' outlines in Fredoka Bold: written by `glyphs`
  fonts/             Fredoka's Hebrew subset (the english-words game's), inlined in the page

`art` brings art/ in line with words.json: it downloads the OpenMoji drawings it lacks (the black line
set at OPENMOJI, cached outside the repo), normalizes them and the custom ones, and removes drawings no
word names. Normalized means flat: no groups or ids, every paint explicit, black as currentColor, and each
stroke width as calc(var(--sw) * k), k its width over OpenMoji's 2, so the page sets one printed line
weight for every drawing at every size. Each file carries its geometry's bounding box in data-box.
`assemble` writes index.html; `--check` writes nothing and fails if index.html is not what it would write,
or if a word's drawing or a letter's outline is missing. Run it before committing: the repo has no CI.
"""
import argparse
import base64
import io
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the repo
ROOT = Path(__file__).resolve().parents[1]
WORDS = ROOT / "src/words.json"
TEMPLATE = ROOT / "src/page.html"
LETTERS = ROOT / "src/letters.json"
ART = ROOT / "art"
ART_SRC = ROOT / "art-src"
FONT = ROOT / "fonts/fredoka-400-700-hebrew.woff2"
PAGE = ROOT / "index.html"

OPENMOJI = "17.0.0"
OPENMOJI_URL = "https://cdn.jsdelivr.net/npm/openmoji@{version}/black/svg/{hexcode}.svg"
CACHE = Path.home() / ".cache/alefbet-coloring" / f"openmoji-{OPENMOJI}"
DEFAULT_PICKS = 8
PER_SHEET = range(3, 13)  # words on a sheet, as the page allows (its PER_SHEET)
LETTER_WEIGHT = 700

SVG_NS = "http://www.w3.org/2000/svg"
SHAPES = {"path", "line", "polyline", "polygon", "rect", "circle", "ellipse"}
# A normalized shape lists these in this fixed order, so `art` writes the same file every run. It is the
# order the own drawings' files have; a few older OpenMoji files differ until `art --force` rewrites them.
GEOMETRY = ("d", "points", "y2", "x1", "x2", "y1", "r", "x", "y", "height", "width", "cx", "rx", "ry", "cy")
INHERITED = {"fill": "#000", "stroke": "none", "stroke-width": "1", "stroke-linecap": "butt",
             "stroke-linejoin": "miter", "fill-rule": "nonzero", "paint-order": "normal"}
IGNORED = {"id", "class", "stroke-miterlimit", "data-name"}
BLACK = {"#000", "#000000", "black", "#1d1d1b"}
WHITE = {"#fff", "#ffffff", "white"}


def load_words():
    return json.loads(WORDS.read_text(encoding="utf-8"))


def art_refs(words):
    """Every drawing words.json names, in order of first use."""
    refs = []
    for letter in words["letters"].values():
        for word in letter.get("words", []):
            if word["art"] not in refs:
                refs.append(word["art"])
    return refs


def art_file(ref):
    kind, name = ref.split(":", 1)
    if kind not in ("openmoji", "custom") or not re.fullmatch(r"[A-Za-z0-9-]+", name):
        sys.exit(f"bad drawing reference {ref!r}: openmoji:<hexcode> or custom:<name>")
    return ART / f"{kind}-{name}.svg"


def raw_svg(ref):
    kind, name = ref.split(":", 1)
    if kind == "custom":
        path = ART_SRC / f"{name}.svg"
        if not path.exists():
            sys.exit(f"{ref}: no {path.relative_to(ROOT)}")
        return path.read_text(encoding="utf-8")
    cached = CACHE / f"{name}.svg"
    if not cached.exists():
        url = OPENMOJI_URL.format(version=OPENMOJI, hexcode=name)
        print(f"  download {url}", flush=True)
        with urllib.request.urlopen(url, timeout=30) as response:
            data = response.read()
        CACHE.mkdir(parents=True, exist_ok=True)
        cached.write_bytes(data)
    return cached.read_text(encoding="utf-8")


def paint(value, what, ref):
    v = value.strip().lower()
    if v == "none":
        return "none"
    if v in BLACK:
        return "currentColor"
    if v in WHITE:
        return "#fff"
    print(f"  {ref}: {what} {value} is neither black nor white; drawn black", flush=True)
    return "currentColor"


def style_attrs(el):
    """An element's presentation attributes, its style="" declarations winning."""
    attrs = {k: v for k, v in el.attrib.items() if "}" not in k}
    for decl in attrs.pop("style", "").split(";"):
        if ":" in decl:
            key, value = decl.split(":", 1)
            attrs[key.strip()] = value.strip()
    return attrs


def flatten(el, inherited, transform, ref, out):
    attrs = style_attrs(el)
    tag = el.tag.split("}")[-1]
    here = dict(inherited)
    for key in INHERITED:
        if key in attrs:
            here[key] = attrs[key]
    t = " ".join(x for x in (transform, attrs.get("transform", "")) if x)
    if tag in ("svg", "g"):
        for child in el:
            flatten(child, here, t if tag == "g" else transform, ref, out)
        return
    if tag in ("title", "desc", "metadata"):
        return
    if tag not in SHAPES:
        sys.exit(f"{ref}: unsupported <{tag}>; simplify the drawing")
    for key in attrs:
        if key not in GEOMETRY and key not in INHERITED and key not in IGNORED and key != "transform":
            sys.exit(f"{ref}: <{tag}> {key}={attrs[key]!r} is not handled")
    shape = {k: attrs[k] for k in GEOMETRY if k in attrs}
    if t:
        shape["transform"] = t
    shape["fill"] = paint(here["fill"], "fill", ref)
    shape["stroke"] = paint(here["stroke"], "stroke", ref)
    if shape["stroke"] != "none":
        shape["stroke-width"] = float(here["stroke-width"])
        shape["stroke-linecap"] = here["stroke-linecap"]
        shape["stroke-linejoin"] = here["stroke-linejoin"]
    if here["fill-rule"] != "nonzero":
        shape["fill-rule"] = here["fill-rule"]
    if here["paint-order"] != "normal":
        shape["paint-order"] = here["paint-order"]
    if shape["fill"] == "none" and shape["stroke"] == "none":
        return
    out.append((tag, shape))


def num(value):
    return f"{value:.3f}".rstrip("0").rstrip(".")


def shape_xml(tag, shape, sw_style):
    parts = []
    for key, value in shape.items():
        if key == "stroke-width":
            continue
        parts.append(f'{key}="{value}"')
    if "stroke-width" in shape:
        k = shape["stroke-width"] / 2
        parts.append(f'style="stroke-width:calc(var(--sw) * {num(k)})"' if sw_style
                     else f'stroke-width="{num(shape["stroke-width"])}"')
    return f"<{tag} {' '.join(parts)}/>"


def normalize(ref, text):
    root = ET.fromstring(text)
    view_box = root.get("viewBox", "0 0 72 72")
    shapes = []
    flatten(root, INHERITED, "", ref, shapes)
    if not shapes:
        sys.exit(f"{ref}: nothing to draw")
    from svgelements import SVG  # art runs under uv with svgelements

    probe = (f'<svg xmlns="{SVG_NS}" viewBox="{view_box}">'
             + "".join(shape_xml(tag, shape, False) for tag, shape in shapes) + "</svg>")
    x0, y0, x1, y1 = SVG.parse(io.StringIO(probe)).bbox()
    body = "\n  ".join(shape_xml(tag, shape, True) for tag, shape in shapes)
    box = " ".join(num(v) for v in (x0, y0, x1, y1))
    return (f'<svg xmlns="{SVG_NS}" viewBox="{view_box}" data-box="{box}" data-from="{ref}">\n'
            f"  {body}\n</svg>\n")


def cmd_art(args):
    words = load_words()
    refs = art_refs(words)
    ART.mkdir(exist_ok=True)
    wanted = {art_file(ref) for ref in refs}
    for ref in refs:
        target = art_file(ref)
        if target.exists() and not args.force and not ref.startswith("custom:"):
            continue
        print(f"{ref} -> {target.relative_to(ROOT)}", flush=True)
        target.write_text(normalize(ref, raw_svg(ref)), encoding="utf-8")
    for stale in sorted(set(ART.glob("*.svg")) - wanted):
        print(f"remove {stale.relative_to(ROOT)} (no word names it)", flush=True)
        stale.unlink()


def cmd_glyphs(args):
    from fontTools.pens.boundsPen import BoundsPen
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    from fontTools.varLib import instancer

    font = instancer.instantiateVariableFont(TTFont(FONT), {"wght": LETTER_WEIGHT})
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    letters = {}
    for letter in load_words()["letters"]:
        name = cmap[ord(letter)]
        pen = SVGPathPen(glyph_set, ntos=lambda v: num(round(v, 1)))
        glyph_set[name].draw(TransformPen(pen, (1, 0, 0, -1, 0, 0)))  # y down, as in SVG
        bounds = BoundsPen(glyph_set)
        glyph_set[name].draw(bounds)
        x0, y0, x1, y1 = bounds.bounds
        letters[letter] = {"d": pen.getCommands(), "box": [x0, -y1, x1, -y0]}
    LETTERS.write_text(json.dumps({"font": f"Fredoka {LETTER_WEIGHT}", "em": font["head"].unitsPerEm,
                                   "letters": letters}, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8")
    print(f"wrote {LETTERS.relative_to(ROOT)}: {len(letters)} letters", flush=True)


def art_defs(refs):
    defs, boxes = [], {}
    for ref in refs:
        path = art_file(ref)
        if not path.exists():
            sys.exit(f"{ref}: no {path.relative_to(ROOT)}; run `build.py art`")
        text = path.read_text(encoding="utf-8")
        box = re.search(r'data-box="([^"]+)"', text).group(1)
        inner = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", text, flags=re.S).strip()
        inner = re.sub(r"\s*\n\s*", "", inner)
        key = path.stem
        boxes[key] = [float(v) for v in box.split()]
        defs.append(f'<g id="a-{key}">{inner}</g>')
    return "\n".join(defs), boxes


def icon(glyph):
    """The tab icon: the letter in white on a berry tile, as a data: URL."""
    x0, y0, x1, y1 = glyph["box"]
    side = max(x1 - x0, y1 - y0) * 1.5
    left, top = (x0 + x1 - side) / 2, (y0 + y1 - side) / 2
    svg = (f'<svg xmlns="{SVG_NS}" viewBox="{num(left)} {num(top)} {num(side)} {num(side)}">'
           f'<rect x="{num(left)}" y="{num(top)}" width="{num(side)}" height="{num(side)}" rx="{num(side * 0.22)}" fill="#b04d88"/>'
           f'<path d="{glyph["d"]}" fill="#fff"/></svg>')
    return "data:image/svg+xml," + urllib.parse.quote(svg, safe="")


def assemble():
    words = load_words()
    letters = json.loads(LETTERS.read_text(encoding="utf-8"))["letters"]
    refs = art_refs(words)
    defs, boxes = art_defs(refs)
    data = {"defaultPicks": DEFAULT_PICKS, "sources": words["sources"], "letters": {}}
    for letter, entry in words["letters"].items():
        if letter not in letters:
            sys.exit(f"{letter}: no outline in src/letters.json; run `build.py glyphs`")
        picks = entry.get("picks")
        if picks is not None and (type(picks) is not int or picks not in PER_SHEET
                                  or picks > len(entry.get("words", []))):
            sys.exit(f"{letter}: \"picks\" is {picks!r}: a whole number from 3 to 12, at most its number of words")
        data["letters"][letter] = {
            "name": entry["name"],
            "glyph": letters[letter],
            **{key: entry[key] for key in ("scale", "picks") if key in entry},
            "words": [{"w": w["w"], "art": art_file(w["art"]).stem, "src": w.get("src", [])}
                      for w in entry.get("words", [])],
        }
    data["art"] = boxes
    page = TEMPLATE.read_text(encoding="utf-8")
    fills = {
        "ICON": icon(letters["ב"]),
        "FONT": base64.b64encode(FONT.read_bytes()).decode("ascii"),
        "ART_DEFS": defs,
        "DATA": json.dumps(data, ensure_ascii=False, separators=(",", ":")),
    }
    for key, value in fills.items():
        if "{{" + key + "}}" not in page:
            sys.exit(f"src/page.html has no {{{{{key}}}}}")
        page = page.replace("{{" + key + "}}", value)
    left = re.findall(r"\{\{[A-Z_]+\}\}", page)
    if left:
        sys.exit(f"src/page.html: unfilled {', '.join(left)}")
    return page


def cmd_assemble(args):
    page = assemble()
    if args.check:
        if not PAGE.exists() or PAGE.read_text(encoding="utf-8") != page:
            sys.exit("index.html is not what assemble writes: run `build.py assemble`")
        print("index.html is up to date")
        return
    PAGE.write_text(page, encoding="utf-8")
    print(f"wrote {PAGE.relative_to(ROOT.parent)} ({len(page.encode()) // 1024} KB)", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    art = sub.add_parser("art", help="download and normalize the drawings words.json names")
    art.add_argument("--force", action="store_true", help="normalize every OpenMoji drawing again")
    art.set_defaults(func=cmd_art)
    sub.add_parser("glyphs", help="write src/letters.json from the font").set_defaults(func=cmd_glyphs)
    asm = sub.add_parser("assemble", help="write index.html")
    asm.add_argument("--check", action="store_true", help="fail if index.html is stale; write nothing")
    asm.set_defaults(func=cmd_assemble)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
