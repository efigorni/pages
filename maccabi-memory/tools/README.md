# maccabi-memory tools

What this game needs besides the shared tools: its scraper. Everything after the scrape
(photos, voice clips, the page, the test) is the same for every club; see "Refresh a
club" in [`_memory-game/README.md`](../../_memory-game/README.md).

| Here | What it is |
|---|---|
| `scrape/` | Reads the club site (stats list, roster, line-ups, player pages) into `<work>/data/`: `players.json`, raw photos, contact sheets |
| `tts/pronunciations.json` | Each name's pinned IPA; the rest of `tts/` is the bake-off that chose the engine |
| `page/icons/` | The two icon SVGs (`render_icons.sh --game maccabi-memory`) |

## Scrape

About 100 polite requests, cached in `<work>/data/html/`:

```sh
uv run --with requests --with beautifulsoup4 --with pillow python -I -u \
    maccabi-memory/tools/scrape/scrape_maccabi.py --out <work>/data --refresh
uv run --with pillow python -I -u maccabi-memory/tools/scrape/contact_sheet.py --data <work>/data
```

- **Selection** (decisions D1/R3/R4) happens here. Eligible = on the season stats list
  and with a player page and photo. Starters = the goalkeeper with the most starts plus
  the 10 outfield players with the most starts (tiebreak: minutes, then appearances).
  Bench = every other eligible outfield player. Other goalkeepers are excluded.
- Check `players.json` before trusting a run: the stats page has no season parameter, so
  confirm the season label and goal totals agree with the player pages. Expect 11 starters
  and at least 4 bench players. Look at `contact-sheet.png`.
- **Photos** are framed by their alpha outline (`club.json`: `images.mode` is `auto`):
  hair top at 4%, shoulder line at 90% of the square. Fix an outlier in `crops.png` with
  `build_images.py --game maccabi-memory --work <work> --overrides <file>.json`, e.g.
  `{"some-id": {"dy": 0.02, "zoom": 1.1}}`.
- This scraper still has its own fetcher and selection code; it moves onto
  `_memory-game/tools/scrape/` at its next real refresh, when its output can be compared.
- The voice: `tts/eval_probe.py`, `probe_set.json`, `make_compare.py` and `render_torch.py`
  are the bake-off that chose BlueTTS; `generate.py --engine piper|say` with
  `--phonemes-from <manifest>` renders the runner-up engines for comparison
  (`setup.sh --install --all` installs Piper).
