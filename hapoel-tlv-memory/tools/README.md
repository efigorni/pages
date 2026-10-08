# hapoel-tlv-memory tools

What this game needs to refresh its roster when the squad changes (a new season,
transfers). The game itself (`../index.html`) needs none of it at runtime. The engine,
the shared styles, the service worker and the generic tools live in
[`_memory-game/`](../../_memory-game/README.md), which also explains which parts of
`../index.html` are generated.

| Here | What it is |
|---|---|
| `scrape/` | Reads htafc.co.il (the team & players cards, each player's popup, the club's match reports) into a data directory: `players.json`, raw and number-free photos, contact sheets, design reference |
| `tts/` | `pronunciations.json`: each name's pinned IPA, the reason for every change and what to listen for |
| `page/icons/` | The two icon SVGs |
| `game.json` | The name model `build_page.py data` writes into DATA: `"full"`, one line, as the site shows it |

Downloads are untrusted data: keep them in a work directory **outside the repo**, run
Python with `-I`, and pass paths as arguments. Commands below run from the repo root;
`<work>` is that scratch directory.

## Refreshing the roster

1. **Scrape.** The site is WordPress behind an edge cache whose listing carries a stale
   popup nonce, so start from an uncached render. Save into `<work>/data/html/` (curl, a
   desktop browser user agent, one request at a time):
   - `players-fresh.html`: `https://www.htafc.co.il/צוות-ושחקנים/?hta=<timestamp>`
   - `players-en.html`: `https://www.htafc.co.il/en/staff-and-players/` (English names, for the ids)
   - `home.html`: the homepage (its fixtures strip lists every game and competition)
   - `rest/reports-cat30.json`: `/wp-json/wp/v2/posts?categories=30&after=<season start>T00:00:00&per_page=100`
     (the season's match reports; each ends with the "שיחקו בהפועל:" line-up block)
   - `ext/tm-leistungsdaten-2026.html`: Transfermarkt's all-competitions squad stats (cross-check)

   ```sh
   uv run --with requests --with beautifulsoup4 python -I -u \
       hapoel-tlv-memory/tools/scrape/fetch_popups.py --html <work>/data/html
   uv run --with requests --with beautifulsoup4 --with pillow --with numpy --with scipy python -I -u \
       hapoel-tlv-memory/tools/scrape/scrape_hapoel.py --data <work>/data
   uv run --with pillow python -I -u hapoel-tlv-memory/tools/scrape/contact_sheet.py --data <work>/data
   ```

   - **Selection** happens here. The metric is this season's appearances in all
     competitions, counted from the club's own match reports (a start, or a substitute
     who came on). Nothing on the site is a season counter: the popup's bio quotes last
     season. Pool = the top 23 by appearances; main 11 = the goalkeeper with the most
     appearances plus the 10 outfield players with the most (tiebreaks: starts, minutes,
     lower number); bench = the other outfield players in the pool; backup goalkeepers are
     excluded.
   - `SEASON`, `COMP_BY_LOGO` and `STAGE_BY_DATE` at the top of `scrape_hapoel.py` describe
     the 2026/27 games; update them for a new season.
   - **Photos.** Every club photo has the shirt number baked in as a flat red numeral
     behind the player. The scraper keys it out with `clean_number.py` into
     `<work>/data/clean/` and points `photo_file` there, since the card draws its own number.
     Look at `contact-sheet-crops.png` before trusting a run: same face size and height on
     every tile, and no red left beside the hair.
   - `design_capture.py` (Playwright) retakes the reference screenshots and computed styles.

2. **Photos**:

   ```sh
   uv run --with pillow python -I _memory-game/tools/images/build_images.py \
       <work>/data/players.json hapoel-tlv-memory/img --mode box --fade 0 \
       --sheet <work>/crops.png --sheet-colors 6d052a,ffffff,ff009d
   ```

   - `--mode box` uses each player's `crop` from the scrape. `--fade 0`: the card is white,
     and the name band cuts the shirt as the site's cards do.
   - `git rm` the `img/<id>.webp` of players who left.

3. **Voice clips**: see [Voice clips](#voice-clips) below.

4. **Page data and offline cache**:

   ```sh
   python3 -I _memory-game/tools/page/build_page.py data <work>/data/players.json hapoel-tlv-memory
   ```

   Rewrites `const DATA` in `index.html` (starters, bench, names, which clips exist), then
   assembles the game: it stamps the shared code into the page and writes `sw.js` with a
   new cache `VERSION`. After any other change (images, audio, fonts, icons, the club parts
   of `index.html`) run `python3 -I _memory-game/tools/page/build_page.py assemble hapoel-tlv-memory`.

5. **Test**: `python3 -m http.server 8765` from the repo root, open
   `http://localhost:8765/hapoel-tlv-memory/`, and play a full round in portrait and
   landscape. Every card should show its own face, number and name, the console should be
   clean, and the voice should read the right name.

6. **Commit** with explicit paths (`git add hapoel-tlv-memory/...`). A roster refresh
   touches only this game. A change in `_memory-game/` changes every game: assemble, commit
   and verify all of them (see [`_memory-game/README.md`](../../_memory-game/README.md)).

## Voice clips

Generated locally with BlueTTS 2.5 (ONNX, MIT) and the `noa` voice: the same engine, voice
and settings as the other two games. Each name's pronunciation is pinned as IPA in
`tts/pronunciations.json`, the same IPA is used in the name clip and inside the match clip,
and every final MP3 is checked by an ivrit.ai Whisper round-trip. Needs uv, git, ffmpeg and
whisper-cli (`brew install uv ffmpeg whisper-cpp`). `<work>` is the same directory the
scrape wrote `data/` into.

```sh
# once: finds a working install ($MACCABI_TTS_ENGINES, then <work>/tts) or installs one under <work>/tts
MACCABI_ROOT=<work> bash _memory-game/tools/tts/setup.sh

# every refresh: reads <work>/data/players.json, writes <work>/tts/out/ (+ manifest and listen.html)
MACCABI_ROOT=<work> <engines>/.venv-stt/bin/python -u _memory-game/tools/tts/generate.py \
    --pron hapoel-tlv-memory/tools/tts/pronunciations.json --takes 8 --second-opinion --ready

# into the game, then run step 4
cp <work>/tts/out/audio/name/*.mp3 hapoel-tlv-memory/audio/name/
cp <work>/tts/out/audio/match/*.mp3 hapoel-tlv-memory/audio/match/
```

- `<engines>` is the folder `setup.sh` reports (it holds `.venv-blue`, `.venv-stt` and
  `_engines/BlueTTS`). Export `MACCABI_TTS_ENGINES=<engines>` when it isn't `<work>/tts`.
- The start and win clips (`audio/ui/`) aren't generated here: they are the same phrases
  as the other games' and were copied from there.
- `git rm` the clips of players who left; `build_page.py` precaches every file under
  `audio/`.
- A new player missing from `pronunciations.json` falls back to the G2P reading and is
  logged as having no pinned IPA. Listen to those first in `<work>/tts/listen.html`. To fix
  a name, edit its `ipa` and re-run with `--only <id>`.
- The voice needs its credit line: keep [`../CREDITS.md`](../CREDITS.md) in step with the
  engine and voice actually shipped. It also credits the fonts and the club's photos.

## Icons

Only needed if the card-back design changes:

```sh
bash _memory-game/tools/icons/render_icons.sh hapoel-tlv-memory/tools/page/icons hapoel-tlv-memory/icons
```

Uses headless Chrome (`CHROME=<binary>` to override the macOS default) and Pillow.
