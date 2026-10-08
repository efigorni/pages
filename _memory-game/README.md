# _memory-game

The shared source of the memory games (`maccabi-memory/`, `maccabi-haifa-memory/`). It is not a
page: it has no `index.html`, no card in the root `index.html`, and the games never fetch anything
from it. Don't delete it as an orphan.

| File | What it is |
|---|---|
| `engine.js` | The game: deal, flips, audio, overlays, confetti, wake lock, install, service-worker registration |
| `base.css` | Every style both games share; colours and the font come from each club's tokens |
| `sw.template.js` | The service worker; each game's `sw.js` is this file with `VERSION`, `ASSETS` and `PREFIX` filled in |
| `tools/page/build_page.py` | Builds the games (below) |
| `tools/images/` | `build_images.py` crops the cutout photos; `framing.py` is the alpha-outline framing the scrapers also use |
| `tools/tts/` | The voice-clip pipeline (`setup.sh`, `generate.py`, `hebrew.py`, ...) |
| `tools/icons/` | `render_icons.sh <svg-dir> <out-dir>` renders a game's PWA icons |

## How a game's page is built

Each game's `index.html` stays self-contained, so it works offline and from `file://`, and an
installed copy upgrades the same way it always did. Some of it is written by hand, some by
`build_page.py`:

| Part of `index.html` | Who writes it |
|---|---|
| head, markup (HUD, overlays, title, trophy) | by hand, per club |
| `<style>` (first): fonts, colour tokens, card back, card face, title | by hand, per club |
| `<style id="base">` | `assemble`, from `base.css` |
| `<script id="data">` | `data`, from the club's `players.json` |
| `<script id="club">`: `CLUB = { confetti, fonts, face(kit) }` | by hand, per club |
| `<script id="engine">` | `assemble`, from `engine.js` |

`sw.js` is generated whole. Scripts run in the order data, club, engine. `CLUB.face(kit)` returns the
card face's four hooks: `prepare(players)`, `apply(style, cw, ch, mode)`, `build(p)` (its front must
keep `.photo > img`, where a match flight starts) and `fit(cardEl, p, geo)`. Each club's `<style>`
defines the tokens `base.css` reads (`--font`, `--accent`, `--surface`, ...); a token left undefined
would silently drop a whole declaration, which is why `assemble` checks them.

```sh
# a shared change: edit engine.js, base.css or sw.template.js, then
python3 -I _memory-game/tools/page/build_page.py assemble        # every game
python3 -I _memory-game/tools/page/build_page.py assemble --check   # before committing: no drift
# a roster refresh (the club README has the full sequence):
python3 -I _memory-game/tools/page/build_page.py data <work>/data/players.json <game>
```

- Never edit a generated region or a `sw.js` by hand: the next `assemble` overwrites it, and
  `--check` fails until it does. The repo has no CI, so run `--check` before every commit.
- A shared change changes both games: commit both, and verify both in the browser.
- `VERSION` hashes every precached file and the template. Any change to a page, a photo, a clip, a
  font or an icon gives a new cache, and that is what makes installed copies pick it up.
- `data` takes the club's name model from `<game>/tools/game.json`: `"full"` (Tel Aviv: `name_he`
  only) or `"first-last"` (Haifa: the card's two tiers and `speak_he`, the text the voice reads).
- The builder only writes `index.html` and `sw.js` in folders whose page has an engine script, and
  never writes a manifest. It refuses a cache prefix that isn't the folder name, a prefix that
  another game's starts with, and a manifest `id` that resolves to the origin root or to another
  game's app (Tel Aviv's `"./"` is grandfathered: changing it would break installed copies).

## The refresh pipeline

Downloads are untrusted data: keep them in a work directory outside the repo, run Python with
`-I`, and pass paths as arguments. Each club's `tools/README.md` has the exact commands; the steps:

1. **Scrape** with the club's own scraper (`<game>/tools/scrape/`), which writes `players.json`.
2. **Photos**: `tools/images/build_images.py <players.json> <game>/img --mode box|auto ...`. The
   club README passes its mode and fade; there is no default mode.
3. **Voice clips**: `tools/tts/setup.sh` once, then `tools/tts/generate.py --pron
   <game>/tools/tts/pronunciations.json ...` (BlueTTS 2.5, voice `noa`, an ivrit.ai Whisper
   round-trip per clip), and copy the clips into `<game>/audio/`.
4. **Page and cache**: `build_page.py data <players.json> <game>`.
5. **Test** both portrait and landscape at `http://localhost:8765/<game>/` (a `python3 -m http.server
   8765` at the repo root), then commit with explicit paths.
