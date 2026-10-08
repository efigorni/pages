# maccabi-memory tools

What this game needs to refresh its roster when the squad changes (a new season,
transfers). The game itself (`../index.html`) needs none of it at runtime. The engine,
the shared styles, the service worker and the generic tools live in
[`_memory-game/`](../../_memory-game/README.md), which also explains which parts of
`../index.html` are generated.

| Here | What it is |
|---|---|
| `scrape/` | Reads the club site (stats list, roster, line-ups, player pages) into a data directory: `players.json`, raw photos, contact sheets |
| `tts/` | `pronunciations.json` (each name's pinned IPA), plus the bake-off that chose the engine |
| `page/icons/` | The two icon SVGs |
| `game.json` | The name model `build_page.py data` writes into DATA: `"full"`, `name_he` only |

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
   uv run --with pillow python -I _memory-game/tools/images/build_images.py \
       <work>/data/players.json maccabi-memory/img --mode auto --fade 0 \
       --sheet <work>/crops.png --sheet-colors 020f24,061e3f,f8d734
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
   python3 -I _memory-game/tools/page/build_page.py data <work>/data/players.json maccabi-memory
   ```

   Rewrites `const DATA` in `index.html` (starters, bench, which clips exist), then
   assembles the game: it stamps the shared code into the page and writes `sw.js` with a
   new cache `VERSION`. After any other change (images, audio, fonts, icons, the club parts
   of `index.html`) run `python3 -I _memory-game/tools/page/build_page.py assemble maccabi-memory`:
   the new cache version is what makes installed copies pick up the change.

5. **Test**: `python3 -m http.server 8765` from the repo root, open
   `http://localhost:8765/maccabi-memory/`, and play a full round in portrait and
   landscape. Every card should show a face, number and name, the console should be
   clean, and the voice should read the right name.

6. **Commit** with explicit paths (`git add maccabi-memory/...`). A roster refresh touches
   only this game. A change in `_memory-game/` changes both games: assemble, commit and
   verify both (see [`_memory-game/README.md`](../../_memory-game/README.md)).

## Voice clips

Generated locally with BlueTTS 2.5 (ONNX, MIT) and the `noa` voice. Each name's
pronunciation is pinned as IPA in `tts/pronunciations.json`, and every clip is checked
by an ivrit.ai Whisper round-trip. Needs uv, git, ffmpeg and whisper-cli
(`brew install uv ffmpeg whisper-cpp`). `<work>` is the same directory the scrape
wrote `data/` into.

```sh
# once: finds a working install ($MACCABI_TTS_ENGINES, then <work>/tts) or installs one under <work>/tts
MACCABI_ROOT=<work> bash _memory-game/tools/tts/setup.sh

# every refresh: reads <work>/data/players.json, writes <work>/tts/out/ (+ manifest and listen.html)
MACCABI_ROOT=<work> <engines>/.venv-stt/bin/python -u _memory-game/tools/tts/generate.py \
    --pron maccabi-memory/tools/tts/pronunciations.json --ui --takes 8 --second-opinion --ready

# into the game, then run step 4
cp -R <work>/tts/out/audio/name <work>/tts/out/audio/match <work>/tts/out/audio/ui maccabi-memory/audio/
```

- `<engines>` is the folder `setup.sh` reports (it holds `.venv-blue`, `.venv-stt` and
  `_engines/BlueTTS`). Export `MACCABI_TTS_ENGINES=<engines>` when it isn't `<work>/tts`.
- `--ui` also makes the start and win clips (`audio/ui/`).
- `git rm` the `audio/name/<id>.mp3` and `audio/match/<id>.mp3` of players who left;
  `build_page.py` precaches every file under `audio/`.
- A new player missing from `pronunciations.json` falls back to the G2P reading of
  `name_he` and shows `pinned_ipa: false` in `<work>/tts/qa/<run>.json`. Listen to
  those first. To fix a name, edit its `ipa` and re-run with `--only <id>`.
- Hear what the G2P would say:
  `MACCABI_TTS_ENGINES=<engines> <engines>/.venv-blue/bin/python _memory-game/tools/tts/render_blue.py --g2p "טקסט" 2`
  (`2` = a female listener, for phrases like מצאת).
- `generate.py --voice adam` switches to a male voice; `--engine piper|say` with
  `--phonemes-from <manifest>` renders the runner-up engines for comparison
  (`setup.sh --all` installs Piper). `make_compare.py` builds a side-by-side listening
  page. `eval_probe.py`, `probe_set.json` and `render_torch.py` are the bake-off that
  chose the engine.
- The voice needs its credit line: keep [`../CREDITS.md`](../CREDITS.md) in step
  with the engine and voice actually shipped. It also credits the fonts and the
  club's photos.

## Icons

Only needed if the card-back design changes:

```sh
bash _memory-game/tools/icons/render_icons.sh maccabi-memory/tools/page/icons maccabi-memory/icons
```

Uses headless Chrome (`CHROME=<binary>` to override the macOS default) and Pillow.
