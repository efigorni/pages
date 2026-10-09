# english-words tools

A word game (`club.json` `kind: "words"`), not a club: it has no scraper, no roster roles and no
pronunciation pins. Everything it shares with the clubs (the engine, the page, the worker, the test) is
in [`_memory-game/README.md`](../../_memory-game/README.md); its own script is `club/club.json` `play`
(the English then the Hebrew, the new-first deal, the quiz of learned words, the progress bar, the core
precache).

| Here | What it is |
|---|---|
| `page/icons/` | The two icon SVGs (`render_icons.sh --game english-words`): the card back's speech bubble with "Aa" in Andika Bold, its outlines taken from the font with fontTools |

## Where the words, pictures and clips come from

They were made in the work directory of the round that built the game, `~/Documents/ENG-00-english-words/`
(outside the repo, as downloads must be):

- **The words**: `data/words.json`, 348 picturable words in teaching order with their Hebrew, niqqud,
  theme and source, and the 755 excluded entries with their reasons. The game ships 347: `club.json`
  `leave_out` keeps "birthday" out, whose picture reads as "cake". The research behind it (the
  Ministry of Education's Pre-Band I and Band I lists, complemented by Cambridge's Young Learners list)
  is `docs/words.md`. Ranks 1–104 are hand-ordered so the first deals mix themes.
- **The pictures**: Fluent UI Emoji 3D at the pinned commit (`CREDITS.md`), resized to WebP into
  `assets/img/<id>.webp`.
- **The clips**: `assets/audio/en/<id>.mp3` (Kokoro `af_heart`) and `assets/audio/he/<id>.mp3` (BlueTTS
  `noa`), each checked by a speech-to-text round trip, in the clubs' clip format; `assets/audio/listen.html`
  plays them all.

## Refresh the words

1. Copy the pictures into `img/` and the clips into `audio/en/` and `audio/he/` (one file per word id).
2. `python3 -I _memory-game/tools/page/build_page.py data <words.json> english-words --prune` writes
   `club/roster.json` in rank order and assembles the page; it fails on a word without its picture or a
   clip, and `--prune` removes the files of words that left the list.
3. `_memory-game/tools/og/render_og.sh english-words` (look at `og.jpg`), then
   `_memory-game/tools/verify/verify.sh sanity english-words`, and commit with explicit paths.

The first 30 words are precached; the worker keeps every other word's picture and clips as they come
(`play.precache`). After a refresh an installed tablet downloads the core once more, and, if any later
word's file changed, fetches the later words again as it meets them (online, the page fetches every
learned word and the next new ones ahead).
