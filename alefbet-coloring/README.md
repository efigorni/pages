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
  font's strokes overlap). A letter that looks too large or small gets `"scale"` in `src/words.json`.
- **The words:** the first 8 in `src/words.json` by default; the panel adds or removes words (3 to 12).
  Each is a drawing with 1.2 mm lines and its word under it in Fredoka with niqqud, the first letter bold.
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
     a 72×72 `viewBox`, `stroke-width="2"`, round caps and joins, no fills.
3. Build, then look at the page in both orientations and a few seeds, and print one:

   ```sh
   uv run --quiet --with svgelements==1.9.6 python -I alefbet-coloring/tools/build.py art
   python3 -I alefbet-coloring/tools/build.py assemble
   ```

`art` downloads the OpenMoji drawings the words name (cached in `~/.cache/alefbet-coloring/`), writes
them normalized into `art/`, and removes the ones no word names. `glyphs` rewrites `src/letters.json`
from the font (only needed if the font or its weight changes):
`uv run --quiet --with fonttools==4.60.1 --with brotli==1.1.0 python -I alefbet-coloring/tools/build.py glyphs`.
Before committing, `python3 -I alefbet-coloring/tools/build.py assemble --check` (the repo has no CI).

## Choosing words with the picker

[`picker/index.html`](picker/index.html) is a local tool for choosing a letter's words, never linked from
the site (it is `noindex`). It is hand-written, not built: `build.py` doesn't touch `picker/`.

1. Open the file straight from disk (`open alefbet-coloring/picker/index.html`, or add `?l=bet` for a
   letter). It needs the internet only for the OpenMoji drawings.
2. Each candidate word is a card: **✓ אהבתי** keeps the word, **★ בדף** makes it one of the page's default
   words (and keeps it), the small drawings under the big one choose its drawing when there are several,
   and **✎** adds a note. Badges show whether the word is in `src/words.json` today (בדף היום / נוספת היום)
   and its sources. The bar on top counts the choices and filters the cards. Choices are kept per letter in
   that browser; **התחלה מחדש** clears them.
3. **ייצוא** shows the choice as JSON; **העתקה** copies it. Paste it to Claude, who updates
   `src/words.json` from it. `picked` follows the candidates' order, `default` is ★, and `dropped_current`
   lists today's words left unpicked:

   ```json
   {"letter": "ב", "picked": [{"w": "בַּיִת", "art": "openmoji:1F3E0", "default": true, "note": ""}],
    "dropped_current": ["בִּנְייָן"]}
   ```

A letter is offered once it has `picker/candidates/<letter-name>.js` (alef bet gimel dalet he vav zayin het
tet yod kaf lamed mem nun samekh ayin pe tsadi qof resh shin tav); the page finds it on its own:

```js
PICKER.load({
  "letter": "ב",
  "name": "בֵּית",
  "candidates": [
    {"w": "בַּיִת", "art": ["openmoji:1F3E0", "openmoji:1F3E1"], "src": ["moe-acq", "en-roster"],
     "current": "default", "note": "optional, one line"}
  ]
});
```

- `w`: the word with niqqud, spelled as in `src/words.json` (full spelling with vowels).
- `art`: its drawing options, the suggested one first: `openmoji:<hexcode>`, `custom:<name>` (from
  `art-src/`), or `draft:<name>`, a proposed drawing of our own in `picker/drafts/<name>.svg`, drawn like
  the ones in `art-src/` and named `<letter-name>-<english-word>`.
- `src`: the keys of the sources it is in (as in `src/words.json`), `[]` when none.
- `current`: `"default"` or `"extra"` when the word is in `src/words.json` today (that role), else `null`.

A file with mistakes lists them at the top of the page, and a drawing that doesn't load shows its reference.
