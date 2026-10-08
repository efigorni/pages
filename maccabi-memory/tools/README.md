# maccabi-memory tools

Scripts that build the game's data, photos, voice clips and offline cache. The game
itself (`../index.html`) needs none of them at runtime; they're here so the roster can be
refreshed when the squad changes (a new season, transfers).

| Folder | What it does |
|---|---|
| `scrape/` | Reads the club site (stats list, roster, line-ups, player pages) into a data directory: `players.json`, raw photos, contact sheets |
| `images/` | Crops each player's cutout photo to a consistent head-and-shoulders WebP in `../img/` |
| `tts/` | Generates the Hebrew voice clips in `../audio/` |
| `page/` | Embeds the roster into `../index.html`, lists which clips exist, and refreshes the service worker's precache list; `page/icons/` renders the PWA icons |

Downloads are untrusted data: keep them in a work directory **outside the repo**, run
Python with `-I`, and pass paths as arguments. Commands below run from the repo root;
`<work>` is that scratch directory.

## Refreshing the roster

1. **Scrape** (about 100 polite requests, cached in `<work>/data/html/`):

   ```sh
   uv run --with requests --with beautifulsoup4 --with pillow python -I -u \
       maccabi-memory/tools/scrape/scrape_maccabi.py --out <work>/data --refresh
   uv run --with pillow python -I -u maccabi-memory/tools/scrape/contact_sheet.py --data <work>/data
   ```

   - Selection (decisions D1/R3/R4) happens here. Eligible = on the season stats list
     and with a player page and photo. Starters = the goalkeeper with the most starts plus
     the 10 outfield players with the most starts (tiebreak: minutes, then appearances).
     Bench = every other eligible outfield player. Other goalkeepers are excluded.
   - Check `players.json` before trusting a run: the stats page has no season
     parameter, so confirm the season label and goal totals agree with the player
     pages. Expect 11 starters and at least 4 bench players. Look at `contact-sheet.png`.

2. **Photos**:

   ```sh
   uv run --with pillow python -I maccabi-memory/tools/images/build_images.py \
       <work>/data/players.json maccabi-memory/img --mode auto --sheet <work>/crops.png
   ```

   - `--mode auto` frames every photo from its alpha outline: hair top at 4%, shoulder
     line at 90% of the square. Open `crops.png`; faces should be the same size and
     height. Fix an outlier with `--overrides <file>.json`, e.g.
     `{"some-id": {"dy": 0.02, "zoom": 1.1}}`.
   - Output: WebP with alpha at the crop's native resolution, capped at 400 px, never
     upscaled. `git rm` the `img/<id>.webp` of players who left.

3. **Voice clips**: see [Voice clips](#voice-clips) below.

4. **Page data and offline cache**:

   ```sh
   python3 -I maccabi-memory/tools/page/build_page.py <work>/data/players.json maccabi-memory
   ```

   Rewrites `const DATA` in `index.html` (starters, bench, which clips exist) and the
   `VERSION` / `ASSETS` lines of `sw.js`. Run it after **any** change to `index.html`,
   images, audio, fonts or icons: the new cache version is what makes installed copies
   pick up the change.

5. **Test**: `python3 -m http.server 8765` from the repo root, open
   `http://localhost:8765/maccabi-memory/`, and play a full round in portrait and
   landscape. Every card should show a face, number and name, the console should be
   clean, and the voice should read the right name.

6. **Commit** with explicit paths (`git add maccabi-memory/...`).

## Voice clips

Generated locally with BlueTTS 2.5 (ONNX, MIT) and the `noa` voice. Each name's
pronunciation is pinned as IPA in `tts/pronunciations.json`, and every clip is checked
by an ivrit.ai Whisper round-trip. Needs uv, git, ffmpeg and whisper-cli
(`brew install uv ffmpeg whisper-cpp`). `<work>` is the same directory the scrape
wrote `data/` into.

```sh
# once (idempotent): BlueTTS checkout, venvs and models under <work>/tts
MACCABI_WORK=<work> bash maccabi-memory/tools/tts/setup.sh

# every refresh: reads <work>/data/players.json, writes <work>/tts/out/
<work>/tts/.venv-stt/bin/python -u maccabi-memory/tools/tts/generate.py \
    --work <work> --takes 8 --second-opinion

# into the game, then run step 4
cp -R <work>/tts/out/audio/name <work>/tts/out/audio/match <work>/tts/out/audio/ui maccabi-memory/audio/
```

- `git rm` the `audio/name/<id>.mp3` and `audio/match/<id>.mp3` of players who left;
  `build_page.py` precaches every file under `audio/`.
- A new player missing from `pronunciations.json` falls back to the G2P reading of
  `name_he` and shows `pinned_ipa: false` in `<work>/tts/qa/<run>.json`. Listen to
  those first. To fix a name, edit its `ipa` and re-run with `--only <id>`.
- Hear what the G2P would say:
  `MACCABI_WORK=<work> <work>/tts/.venv-blue/bin/python maccabi-memory/tools/tts/render_blue.py --g2p "טקסט" 2`
  (`2` = a female listener, for phrases like מצאת).
- `generate.py --voice adam` switches to a male voice. `make_compare.py` builds a
  side-by-side listening page. `eval_probe.py`, `probe_set.json` and `render_torch.py`
  are the bake-off that chose the engine.
- The voice needs its credit line: keep [`../CREDITS.md`](../CREDITS.md) in step
  with the engine and voice actually shipped. It also credits the fonts and the
  club's photos.

## Icons

Only needed if the card-back design changes:

```sh
bash _memory-game/tools/icons/render_icons.sh maccabi-memory/tools/page/icons maccabi-memory/icons
```

Uses headless Chrome (`CHROME=<binary>` to override the macOS default) and Pillow.
