# hapoel-tlv-memory tools

What this game needs besides the shared tools: its scraper. Everything after the scrape
(photos, voice clips, the page, the test) is the same for every club; see "Refresh a
club" in [`_memory-game/README.md`](../../_memory-game/README.md).

| Here | What it is |
|---|---|
| `scrape/` | Reads htafc.co.il (the team & players cards, each player's popup, the club's match reports) into `<work>/data/`: `players.json`, raw and number-free photos, design reference |
| `tts/pronunciations.json` | Each name's pinned IPA, the reason for every change and what to listen for |
| `page/icons/` | The two icon SVGs (`render_icons.sh --game hapoel-tlv-memory`) |
| `look/paint.py` | Renders the cards' dark red wall paint, `img/club/paint.webp` (a seamless tile, fixed seed; its docstring has the command). The icon SVGs draw it too: render the icons again after a change |

## Scrape

The site is WordPress behind an edge cache whose listing carries a stale
popup nonce, so start from an uncached render. Save into `<work>/data/html/` (curl, a
desktop browser user agent, one request at a time):
- `players-fresh.html`: `https://www.htafc.co.il/צוות-ושחקנים/?hta=<timestamp>`
- `players-en.html`: `https://www.htafc.co.il/en/staff-and-players/` (English names, for the ids)
- `home.html`: the homepage (its fixtures strip lists every game and competition)
- `rest/reports-cat30.json`: `/wp-json/wp/v2/posts?categories=30&after=<season start>T00:00:00&per_page=100`
  (the season's match reports; each ends with the "שיחקו בהפועל:" line-up block)
- `ext/tm-leistungsdaten-<start year>.html`: Transfermarkt's all-competitions squad stats (cross-check)
- `rest/seasons.json`: `/wp-json/wp/v2/htafc_season` (the club's season ids)

```sh
uv run --with requests --with beautifulsoup4 python -I -u \
    hapoel-tlv-memory/tools/scrape/fetch_popups.py --html <work>/data/html
uv run --with requests --with beautifulsoup4 --with pillow --with numpy --with scipy python -I -u \
    hapoel-tlv-memory/tools/scrape/scrape_hapoel.py --data <work>/data
uv run --with pillow python -I -u _memory-game/tools/scrape/contact_sheet.py --game hapoel-tlv-memory --data <work>/data
```

- **Selection** happens here. The metric is this season's appearances in all
  competitions, counted from the club's own match reports (a start, or a substitute
  who came on). Nothing on the site is a season counter: the popup's bio quotes last
  season. Pool = the top 23 by appearances; main 11 = the goalkeeper with the most
  appearances plus the 10 outfield players with the most (tiebreaks: starts, minutes,
  lower number); bench = the other outfield players in the pool; backup goalkeepers are
  excluded.
- **A new season** changes three things at the top of `scrape_hapoel.py`: `SEASON`; its
  `SEASON_DATA` row (each official game's stage name and the club's `htafc_match` id by
  date, from `/wp-json/wp/v2/htafc_match`, and Transfermarkt's report id by date, from the
  season's fixtures page); and `COMP_BY_LOGO` if a competition's logo is new. Save that
  season's pages into the cache first (`rest/reports-cat30.json` with `after=<season
  start>`, `rest/seasons.json`, `ext/tm-leistungsdaten-<start year>.html`). The dates, the
  Transfermarkt file and URL, the club's season id and the metric text follow from `SEASON`.
- **Photos.** Every club photo has the shirt number baked in as a flat red numeral
  behind the player. The scraper keys it out with `clean_number.py` into
  `<work>/data/clean/` and points `photo_file` there, since the card draws its own number.
  Look at `contact-sheet-crops.png` before trusting a run: same face size and height on
  every tile, and no red left beside the hair.
- `design_capture.py` (Playwright) retakes the reference screenshots and computed styles.
- The photos' shoulder rule (the first row at least 75% of the widest, from 30% of the
  height down) is in `club/club.json` `images`: the default rule fires inside the head on
  these chest-up photos, whose white sticker outline makes the head half as wide as the chest.
