# english-words tools

A word game (`club.json` `kind: "words"`), not a club: it has no scraper and no roster roles, and its
voice pins are its own (`tts/en_pins.json`, below). Everything it shares with the clubs (the engine, the
page, the worker, the test) is in [`_memory-game/README.md`](../../_memory-game/README.md); its own script
is `club/club.json` `play` (the English then the Hebrew, the new-first deal, the quiz of the words she has
met, the progress bar, the core precache).

| Here | What it is |
|---|---|
| `page/icons/` | The two icon SVGs (`render_icons.sh --game english-words`): the card back's speech bubble with "Aa" in Andika Bold, its outlines taken from the font with fontTools |
| `../club/avoid.json` | Per word, the words that sound like it (CMUdict), which the quiz never offers against it: `_memory-game/tools/words/neighbours.py` writes it, the builder checks it |
| `tts/en_pins.json` | The English voice's pins: how a word is rendered (`phonemes`), and the takes picked by ear (`take`), which the builder keeps as shipped (below) |

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
- **The clips**: `assets/audio/en/<id>.mp3` (Kokoro `am_michael`) and `assets/audio/he/<id>.mp3` (BlueTTS
  `noa`), each checked by a speech-to-text round trip, in the clubs' clip format; `assets/listen.html`
  plays them all. The work directory's `tools/tts/tts_en.sh` renders them (`en`, `he`) and makes
  candidates for words that come out wrong (`fix-words`).

## The English voice's pins and picked takes

`tts/en_pins.json` holds, per word:
- a **render pin**, `phonemes` (Kokoro's tokens, `end` the final punctuation, "" for none) with `why` and
  `listen`: what `tts_en.sh en` renders the word from instead of the front-end's reading. The work
  directory's tools read `<work>/tts/en_pins.json`: copy this file there before a render.
- a **take** picked by ear, `take`: Adam listened to 56 words in round 2 (cat said "cab", fish "vish", dad
  "dab", and a phoneme sweep of every clip) and picked one take each. `method` is how it was made:
  `carrier` (48: the sentence in `carrier`, rendered from `input`, the word cut out at Whisper's word
  timestamps), `phonemes` (7: `input` spelled out, the same as the render pin) or `shipped` (bat: the
  earlier take kept). `sha256` starts the shipped file's hash.

`build_page.py assemble --check` fails when a picked take is no longer the file in `audio/en/`, so a refresh
can't replace one with a default render: copy every other clip, and keep these. To change one, make
candidates (`tts_en.sh fix-words <id>`), pick by ear, copy the file and update its `take`.

**For a word that sounds wrong, try the carrier sentence first, and let a person's ear decide.** "I see a
<word>." and "This is a <word>." cut at the word keep the first and last consonants whole. By ear it beat
"sounds spelled out" almost every time, even where the phoneme recognizer preferred the spelled-out take:
two machines agreeing with each other (the TTS's phonemes and the recognizer's) is not a child hearing the
word. The recognizer and the speech-to-text checks find suspects; a person picks.

## Refresh the words

1. Copy the pictures into `img/` and the clips into `audio/en/` and `audio/he/` (one file per word id),
   except the picked takes in `tts/en_pins.json`, which stay (above).
2. `python3 -I _memory-game/tools/page/build_page.py data <words.json> english-words --prune` writes
   `club/roster.json` in rank order and assembles the page; it fails on a word without its picture or a
   clip, and `--prune` removes the files of words that left the list.
3. The sound-alikes of the new list: `uv run --quiet --with cmudict==1.1.3 python -I
   _memory-game/tools/words/neighbours.py english-words` (`club/avoid.json`; `assemble --check` fails until
   it matches the roster), then `python3 -I _memory-game/tools/page/build_page.py assemble english-words`.
4. `_memory-game/tools/og/render_og.sh english-words` (look at `og.jpg`), then
   `_memory-game/tools/verify/verify.sh sanity english-words`, and commit with explicit paths.

The first 30 words are precached; the worker keeps every other word's picture and clips as they come
(`play.precache`). After a refresh an installed tablet downloads the core once more, and, if any later
word's file changed, fetches the later words again as it meets them (online, the page fetches every
learned word and the next new ones ahead).
