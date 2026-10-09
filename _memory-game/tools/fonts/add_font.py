"""Add a Google Fonts family to a game: its Hebrew and Latin woff2 subsets and its OFL, into <game>/fonts/.

    python3 -I _memory-game/tools/fonts/add_font.py "<Family>" <weight> <game>    e.g. "Barlow Condensed" 800

Prints the @font-face pair to paste into <game>/club/style.css and the line to add under Fonts in
<game>/CREDITS.md (`build_page.py assemble --check` fails until both agree with fonts/). A variable weight
range is written as "300 900". Downloads are untrusted data: only the woff2 files and the licence text are
kept, and nothing downloaded is run.
"""
import re
import sys
import urllib.request
from pathlib import Path

# A browser that takes woff2: Google Fonts answers with the format the user agent supports.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
SUBSETS = ("hebrew", "latin")


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60) as r:
        return r.read()


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    family, weight, game = sys.argv[1], sys.argv[2].replace(" ", ".."), Path(sys.argv[3])
    if not (game / "club/club.json").is_file():
        sys.exit(f"{game} is not a game folder")
    slug = re.sub(r"[^a-z0-9]+", "-", family.lower()).strip("-")
    css = get(f"https://fonts.googleapis.com/css2?family={family.replace(' ', '+')}:wght@{weight}&display=swap").decode()
    faces = {}
    for subset, body in re.findall(r"/\* ([\w-]+) \*/\s*@font-face\s*\{(.*?)\}", css, re.S):
        if subset in SUBSETS:
            faces[subset] = (re.search(r"src: url\((https://[^)]+\.woff2)\)", body).group(1),
                             re.search(r"unicode-range: ([^;]+);", body).group(1))
    if not faces:
        sys.exit(f"Google Fonts has no hebrew or latin subset of {family} {weight}")
    fonts = game / "fonts"
    fonts.mkdir(exist_ok=True)
    label = weight.replace("..", "-")
    blocks = []
    for subset in SUBSETS:
        if subset not in faces:
            continue
        url, rng = faces[subset]
        data = get(url)
        if data[:4] != b"wOF2":
            sys.exit(f"{url} is not a woff2 file")
        name = f"{slug}-{label}-{subset}.woff2"
        (fonts / name).write_bytes(data)
        quoted = f'"{family}"' if " " in family else family
        blocks.append(f"@font-face {{\n  font-family: {quoted};\n  font-weight: {weight.replace('..', ' ')};\n"
                      f"  font-display: swap;\n  src: url(fonts/{name}) format(\"woff2\");\n  unicode-range: {rng};\n}}")
    ofl = get(f"https://raw.githubusercontent.com/google/fonts/main/ofl/{family.replace(' ', '').lower()}/OFL.txt")
    licence = f"OFL-{family.replace(' ', '')}.txt"
    (fonts / licence).write_bytes(ofl)
    copyright_line = ofl.decode("utf-8", "replace").splitlines()[0].strip()
    print("\n".join(blocks))
    print(f"\nCREDITS.md, under Fonts:\n- **{family}**: {copyright_line}. SIL Open Font License 1.1; see\n"
          f"  [`fonts/{licence}`](fonts/{licence}).")


if __name__ == "__main__":
    main()
