# דפי צביעה: אותיות ומילים

Printable A4 coloring pages for learning the Hebrew letters: a big hollow letter in the middle, and around
it line drawings of words that start with it, each with its word under it. `index.html` is one
self-contained page (fonts, drawings and data inline): pick a letter, portrait or landscape, which words,
shuffle the layout, print. It is built by [`tools/build.py`](tools/build.py) from `src/`: never edit
`index.html` itself.

## The page

- **The sheet** is one SVG drawn in millimetres, A4 portrait (210×297) or landscape (297×210). Printing
  sets `@page { size: A4 <orientation>; margin: 0 }`, and nothing is drawn within 10 mm of the paper's edge.
- **The head:** "הָאוֹת <the letter's name>" on the right, "שֵׁם:" and a line on the left.
- **The letter** is Fredoka Bold's outline, as large as fits 110×126 mm (portrait) or 112×118 mm
  (landscape), hollow: white, with a 1.9 mm line drawn outside it (under the fill, which hides where the
  font's strokes overlap). A letter that looks too large or small gets `"scale"` in `src/words.json`, a
  factor on that size: ו 1.2 (a thin bar), י 0.6 (fitted to the box it fills 126 mm and reads as a "0") and
  ק 1.15 (its descender shrinks its body when fitted).
- **The words:** the first 8 in `src/words.json` by default (all 6 for ה and ו); the panel adds or removes
  words (3 to 12). Each is a drawing with 1.2 mm lines and its word under it in Fredoka with niqqud, the
  first letter bold.
- **The credit** at the foot: "Drawings: OpenMoji, CC BY-SA 4.0", or "Drawings: OpenMoji and own, CC BY-SA
  4.0" when one of our own drawings (`art-src/`) is on the sheet.
- **The layout** is random from a seed (ערבוב picks a new one):
  1. On a portrait page the strips beside the letter are narrow (26–50 mm): two of the four narrowest
     drawings get one each, as large as the strip allows, so the drawings surround the letter instead of
     forming a row above and below it.
  2. The others start spread out at a small size, then grow together, pushing apart along the shorter
     way, until they can't grow without touching (5 mm between drawings, 7 mm around the letter).
  3. Each then moves to where it is farthest from its neighbours and grows on its own into the room left,
     up to 1.25 times. Every drawing is turned by up to 7° and is up to 14% larger or smaller than the rest.
- **The address keeps the page:** `#l=ב&o=portrait&s=1&w=0.1.2.3.4.5.6.7` (letter, orientation, seed, the
  words by index), so a link opens, and prints, the same sheet.

## Adding a letter

1. In [`src/words.json`](src/words.json), give the letter its `words`: 10 to 16 concrete, picturable words
   a young child knows, the default 8 first. Each word has its niqqud (full spelling with vowels, as the
   english-words game writes it), its drawing, and the sources it is in (`sources` lists them; see
   [`CREDITS.md`](CREDITS.md)). Following the Ministry's curriculum, the default words start with as many
   different vowels as the letter has good words for, and one opens with a cluster (שְׁ, בְּ…) where one
   exists. Words of the Ministry's documents and of the english-words game come first.
2. Each word needs a drawing that reads as that word in black lines alone:
   - an OpenMoji emoji, `"art": "openmoji:<hexcode>"`: find it on <https://openmoji.org/> and look at its
     black version;
   - or a drawing of our own, `"art": "custom:<name>"`, in `art-src/<name>.svg`, in OpenMoji's line style:
     a 72×72 `viewBox`, `stroke-width="2"`, round caps and joins, no fills but small eye dots. It is named
     `<letter-name>-<english-word>` (`vav-curtain`), and [`CREDITS.md`](CREDITS.md) lists it.
3. Build, then look at the page in both orientations and a few seeds, and print one:

   ```sh
   uv run --quiet --with svgelements==1.9.6 python -I alefbet-coloring/tools/build.py art
   python3 -I alefbet-coloring/tools/build.py assemble
   ```

`art` downloads the OpenMoji drawings the words name (cached in `~/.cache/alefbet-coloring/`), writes
them normalized into `art/`, and removes the ones no word names. It normalizes our own drawings from
`art-src/` on every run. `glyphs` rewrites `src/letters.json`
from the font (only needed if the font or its weight changes):
`uv run --quiet --with fonttools==4.60.1 --with brotli==1.1.0 python -I alefbet-coloring/tools/build.py glyphs`.
Before committing, `python3 -I alefbet-coloring/tools/build.py assemble --check` (the repo has no CI).
