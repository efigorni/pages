# maccabi-haifa-memory tools

What this game needs besides the shared tools: its scraper. Everything after the scrape
(photos, voice clips, the page, the test) is the same for every club; see "Refresh a
club" in [`_memory-game/README.md`](../../_memory-game/README.md).

| Here | What it is |
|---|---|
| `scrape/` | Reads mhaifafc.com (the /players cards, each player page, the season's game records) into `<work>/data/`: `players.json`, `matches.json`, raw photos, design reference |
| `tts/pronunciations.json` | Each name's pinned IPA, the reason for every change and what to listen for |
| `page/icons/` | The two icon SVGs (`render_icons.sh --game maccabi-haifa-memory`) |

## Scrape

About 75 polite requests, cached in `<work>/data/html/`:

```sh
uv run --with requests --with beautifulsoup4 --with pillow python -I -u \
    maccabi-haifa-memory/tools/scrape/scrape_haifa.py --out <work>/data --refresh
uv run --with pillow python -I -u _memory-game/tools/scrape/contact_sheet.py --game maccabi-haifa-memory --data <work>/data --auto
```

- **Selection** happens here (`_memory-game/tools/scrape/roster.py`). The metric is this
  season's appearances in all competitions, counted from the club's own game records
  (`/matches/<id>`): the "הופעות" number in a player page's header carries last season
  over, so it is not used.
- **Names**: `name_he` is the name as the site shows it, `card_name_lines` is the card's
  own split (small first line, bold second line), and `speak_he` is what the voice says:
  the text inside a trailing "(...)" when there is one, else the name.
- Check `players.json` before trusting a run, and look at `contact-sheet-crops.png`. The
  `metric` and `crop_rule` texts in the script describe the 2026/27 season; update them for
  a new one.
- **Photos**: `club/club.json` `images.shoulder_overrides` holds hand-read shoulder lines
  for two photos where the alpha outline's shoulder test fires inside the hair. A new photo
  set needs a fresh look: `contact-sheet-auto.png` shows where the default rule fails. The
  shirt fades out over the bottom 14% (`images.fade`) so it never ends in a hard line.
- `design_capture.py` (Playwright) retakes the /players reference screenshots and computed
  styles. `check_games.py`, `compare_apps.py` and `explore_*.py` are the cross-checks behind
  the metric choice; each takes the scrape folder (for `rsc.py`) and a saved page or folder.
