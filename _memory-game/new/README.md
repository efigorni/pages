# {game} tools

What this game needs besides the shared tools: its scraper. Everything after the scrape
(photos, voice clips, the page, the test) is the same for every club; see "Refresh a
club" in [`_memory-game/README.md`](../../_memory-game/README.md).

| Here | What it is |
|---|---|
| `scrape/` | TODO the club's scraper: reads its site into `<work>/data/players.json` and the photos |
| `tts/pronunciations.json` | Each name's pinned IPA, the reason for every change and what to listen for |
| `page/icons/` | The two icon SVGs (`render_icons.sh --game {game}`) |

## Scrape

TODO the site, what the scraper reads, how it counts this season's appearances, and the
command that writes `<work>/data/players.json`; anything about the photos a refresh must
look at.
