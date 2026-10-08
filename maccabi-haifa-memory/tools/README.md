# maccabi-haifa-memory tools

Scripts that build the game's data, photos, voice clips and offline cache. The game
itself (`../index.html`) needs none of them at runtime; they're here so the roster can be
refreshed when the squad changes (a new season, transfers).

| Folder | What it does |
|---|---|
| `scrape/` | Reads mhaifafc.com (the /players cards, each player page, the season's game records) into a data directory: `players.json`, raw photos, contact sheets, design reference |
| `images/` | Crops each player's cutout photo to a consistent head-and-shoulders WebP in `../img/` |
| `tts/` | Generates the Hebrew voice clips in `../audio/` |
| `page/` | Embeds the roster into `../index.html`, lists which clips exist, and refreshes the service worker's precache list; `page/icons/` renders the PWA icons |

Downloads are untrusted data: keep them in a work directory **outside the repo**, run
Python with `-I`, and pass paths as arguments. Commands below run from the repo root;
`<work>` is that scratch directory.

## Refreshing the roster

1. **Scrape** (about 75 polite requests, cached in `<work>/data/html/`):

   ```sh
   uv run --with requests --with beautifulsoup4 --with pillow python -I -u \
       maccabi-haifa-memory/tools/scrape/scrape_haifa.py --out <work>/data \
       --shoulder-override pedro-barzao=0.415 --shoulder-override adam-grimberg=0.39 --refresh
   uv run --with pillow python -I -u maccabi-haifa-memory/tools/scrape/contact_sheet.py --data <work>/data
   ```

   - **Selection** happens here. The metric is this season's appearances in all
     competitions, counted from the club's own game records (`/matches/<id>`): the
     "הופעות" number in a player page's header carries last season over, so it is not
     used. Pool = the top 23 by appearances; main 11 = the goalkeeper with the most
     appearances plus the 10 outfield players with the most (tiebreaks: starts, minutes,
     lower number); bench = the other outfield players in the pool; backup goalkeepers
     are excluded.
   - **Names**: `name_he` is the name as the site shows it, `card_name_lines` is the
     card's own split (small first line, bold second line), and `speak_he` is what the
     voice says: the text inside a trailing "(...)" when there is one, else the name.
   - Check `players.json` before trusting a run: expect 11 starters and at least 4 bench
     players, and look at `contact-sheet-crops.png`. The `metric` and `crop_rule` texts
     in the script describe the 2026/27 season; update them for a new one.
   - The `--shoulder-override` values are hand-read for two photos where the alpha
     outline's shoulder test fires inside the hair. A new photo set needs a fresh look
     (`contact-sheet-auto.png` shows where auto framing fails).
   - `design_capture.py` (Playwright) retakes the /players reference screenshots and
     computed styles. `check_games.py`, `compare_apps.py` and `explore_*.py` are the
     cross-checks behind the metric choice; each takes the scrape folder (for `rsc.py`)
     and a saved page or folder as arguments.

2. **Photos**:

   ```sh
   uv run --with pillow python -I maccabi-haifa-memory/tools/images/build_images.py \
       <work>/data/players.json maccabi-haifa-memory/img --mode box --sheet <work>/crops.png
   ```

   - `--mode box` uses each player's `crop` from the scrape. Open `crops.png`: faces
     should be the same size and height. Fix an outlier with `--overrides <file>.json`,
     e.g. `{"some-id": {"dy": 0.02, "zoom": 1.1}}`.
   - Output: WebP with alpha at the crop's native resolution, capped at 400 px, never
     upscaled, with the shirt faded out over the bottom 14% (`--fade`) so it never ends
     in a hard line on a card taller than the photo. `git rm` the `img/<id>.webp` of
     players who left.

3. **Voice clips**: see [Voice clips](#voice-clips) below.

4. **Page data and offline cache**:

   ```sh
   python3 -I maccabi-haifa-memory/tools/page/build_page.py <work>/data/players.json maccabi-haifa-memory
   ```

   Rewrites `const DATA` in `index.html` (starters, bench, names, which clips exist) and
   the `VERSION` / `ASSETS` lines of `sw.js`. Run it after **any** change to `index.html`,
   images, audio, fonts or icons: the new cache version is what makes installed copies
   pick up the change. It refuses a name split that doesn't reproduce `name_he` exactly.

5. **Test**: `python3 -m http.server 8765` from the repo root, open
   `http://localhost:8765/maccabi-haifa-memory/`, and play a full round in portrait and
   landscape. Every card should show its own face, number and name, the console should be
   clean, and the voice should read the right name (only the nickname for a name in
   parentheses).

6. **Commit** with explicit paths (`git add maccabi-haifa-memory/...`). Never touch
   `maccabi-memory/`: the two games share nothing.

## Voice clips

Generated locally with BlueTTS 2.5 (ONNX, MIT) and the `noa` voice: the same engine, voice
and settings as maccabi-memory. The voice reads each player's `speak_he`, so a name ending
in parentheses is read as the nickname alone. Each name's pronunciation is pinned as IPA in
`tts/pronunciations.json` (with the reason for every change and what to listen for), the
same IPA is used in the name clip and inside the match clip, and every final MP3 is checked
by an ivrit.ai Whisper round-trip (and a second model with `--second-opinion`). Needs uv,
git, ffmpeg and whisper-cli (`brew install uv ffmpeg whisper-cpp`). `<work>` is the same
directory the scrape wrote `data/` into.

```sh
# once: finds a working install ($MACCABI_TTS_ENGINES, then <work>/tts) or installs one under <work>/tts
MACCABI_ROOT=<work> bash maccabi-haifa-memory/tools/tts/setup.sh

# every refresh: reads <work>/data/players.json, writes <work>/tts/out/ (+ manifest and listen.html)
MACCABI_ROOT=<work> <engines>/.venv-stt/bin/python -u maccabi-haifa-memory/tools/tts/generate.py \
    --takes 8 --second-opinion --ready

# into the game, then run step 4
cp <work>/tts/out/audio/name/*.mp3 maccabi-haifa-memory/audio/name/
cp <work>/tts/out/audio/match/*.mp3 maccabi-haifa-memory/audio/match/
```

- `<engines>` is the folder `setup.sh` reports (it holds `.venv-blue`, `.venv-stt` and
  `_engines/BlueTTS`). Export `MACCABI_TTS_ENGINES=<engines>` when it isn't `<work>/tts`.
- The start and win clips (`audio/ui/`) aren't generated here: they are the same phrases
  as maccabi-memory's and were copied from there.
- `git rm` the clips of players who left; `build_page.py` precaches every file under
  `audio/`.
- A new player missing from `pronunciations.json` falls back to the G2P reading of
  `speak_he` and is logged as having no pinned IPA. Listen to those first in
  `<work>/tts/listen.html` (it also shows the second model's transcript and the
  judgement calls). To fix a name, edit its `ipa` and re-run with `--only <id>`.
- `ab_ipa.py` compares candidate pronunciations across seeds in both clip contexts before
  one is pinned. `render_blue.py --g2p "טקסט"` (run with `<engines>/.venv-blue/bin/python`
  and `MACCABI_TTS_ENGINES` set) prints what the G2P would say.
- The scripts only read the engine install (no bytecode written, Hugging Face offline), so
  an install shared with another project stays untouched.
- The voice needs its credit line: keep [`../CREDITS.md`](../CREDITS.md) in step with the
  engine and voice actually shipped. It also credits the fonts and the club's photos.

## Icons

Only needed if the card-back design changes:

```sh
bash _memory-game/tools/icons/render_icons.sh maccabi-haifa-memory/tools/page/icons maccabi-haifa-memory/icons
```

Uses headless Chrome (`CHROME=<binary>` to override the macOS default) and Pillow.
