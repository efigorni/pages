# _memory-game

The shared source of every memory game. A game is a folder at the repo root with `club/club.json`;
`python3 -I _memory-game/tools/page/build_page.py list` lists them. This folder is not a page: it has no
`index.html`, no card in the root `index.html`, and the games never fetch anything from it. Don't delete
it as an orphan.

| File | What it is |
|---|---|
| `engine.js` | The game, in three modes: memory (deal, flips), the quiz (who is this? / what is this?) and flash cards (the shelf of every item, one card big); what she has learned, audio, overlays, confetti, wake lock, install, service-worker registration, and the face kit a card face is drawn with |
| `base.css` | Every style the games share; colours and fonts come from each club's tokens |
| `page.template.html` | The page with slots, filled per game: head, club style, base, title, trophy, DATA, club script, engine; the mode icons |
| `sw.template.js` | The service worker; each game's `sw.js` is this file with `VERSION`, `ASSETS`, `PREFIX` and `RUNTIME` filled in |
| `audio/ui/` | The start and win clips (the engine's own lines); every game ships a copy |
| `new/` | The templates `build_page.py new` fills: `CREDITS.md`, the club's `tools/README.md` |
| `tools/page/build_page.py` | `new`, `data`, `assemble [--check] [--watch]`, `list [--json]` (below) |
| `tools/refresh.sh` | Everything after a club's scrape, in one command |
| `tools/images/` | `build_images.py` crops the cutout photos; `framing.py` is the alpha-outline framing the scrapers use too |
| `tools/tts/` | The voice clips: `tts.sh` is the entry point; `setup.sh` the engine install |
| `tools/scrape/` | The scraper kit: `common.py` (fetcher, ids, atomic write, photo facts), `roster.py` (the squad rule and a players.json check), `transfermarkt.py`, `contact_sheet.py` |
| `tools/fonts/add_font.py` | Fetches a Google Fonts family's Hebrew and Latin subsets and its OFL into a game |
| `tools/icons/` | `render_icons.sh --game <game>` renders a game's PWA icons from its two SVGs |
| `tools/og/` | `render_og.sh [<game>...]` renders each game's link-preview image, `og.jpg`: its own start screen at 1200×630 with three card faces, starters or first words (`og.js`, on the harness's Playwright) |
| `tools/verify/` | `verify.sh`: `sanity`, the gate every change runs, and the thorough `full` (below) |

## How a game is built

Each game's `index.html` stays self-contained, so it works offline and from `file://`, and an installed
copy upgrades the way it always did. `build_page.py` writes it whole, and `sw.js`, from:

| Source | What it holds |
|---|---|
| `<game>/manifest.webmanifest` | The club's identity: name, short name, colours, id. The head and the title come from it. Never written by a tool after `new` |
| `<game>/club/club.json` | What it teaches (`kind`: `squad`, the default, or `words`), its script (`play`, below), the name model (`names`), the title style (`title`), the board's `scheme`, the trophy's paints, the photo flags (`images`), a word game's link-preview text (`og`), the words it leaves out (`leave_out`) and the engine lines it says in its own words (`lines`: a word game's win; its `audio/ui/` clip is then its own, not the master) |
| `<game>/club/style.css` | Hand-written: fonts, colour tokens, card back, card face, title |
| `<game>/club/club.js` | Hand-written: `CLUB = { confetti, fonts, face(kit) }` |
| `<game>/club/roster.json` | The players with their roles (starter, bench, backup: quiz only), or a word game's words in teaching order; written by `build_page.py data` |
| `_memory-game/*` | The engine, the base styles and the two templates |

The head also carries the link preview that WhatsApp and the like show (Open Graph and Twitter tags): the
manifest name, one shared description, and absolute URLs under `SITE` in `build_page.py`, the one place the
site's address is written. The image is the game's `og.jpg`, at its root, outside the precached folders, so
a device never downloads it.

Every place a game starts (the start screen, the win screen, the ↻ confirm) offers the three modes side by side:
memory, the quiz and flash cards. Memory deals the 11 starters and 4 of the bench. The quiz asks every roster player once in random order:
"מי זה מספר N, <name>?" in text, his match clip out loud, four photo-only cards. A wrong pick teaches too:
a soft sound, then that card turns to its face (grey, smaller, marked ✗, out of play) and plays that
player's match clip; her next pick or the replay button cuts it off. The right one turns to the club's
card face, says the name and moves on. The squad rule
(`tools/scrape/roster.py`) gives the pool's backup goalkeepers role `backup`: in the roster's `players`, asked
in the quiz, never dealt. Every tool that images, voices, checks, syncs or prunes takes `roster.SHIPPED`
(starter, bench, backup), so a refresh keeps them.

Flash cards show the shelf: a tile per item in teaching order, the learned ones in full colour with a tick,
the others dimmed with a dot, and a button to the next new one. A tile opens its card big (the club's face),
which says its line, counts as learned, and pages with ← →. What she has learned (a match in memory, or a
flash card) is kept on the device per game, in `localStorage` under `<game>:learned` (the games share one
origin); when storage is blocked it lasts the visit.

### Play config

`club.json` `play` is the game's script; the builder checks it and puts it in DATA:

| Key | Squad (the football games) | Words (`english-words`) |
|---|---|---|
| `voice` | flip `name`; match `name`, `match`; ask `match`; wrong `match`; right `name`; card `match` | flip `en`; match `en`, `he`; ask `en`; wrong and right `en`, `he`; card `en`, `he` |
| `deal` | `squad`: the starters, the rest of the 15 pairs from the bench | `new-first`: up to `new` (8) unlearned words in teaching order, the rest a random review of learned ones, more new ones while few are learned |
| `quiz` | `all`: every player once | `learned`: up to `size` (15) random learned words, locked below `unlock` (4) learned; the three others are learned words |
| `progress` | `inventory`: the marks on the shelf only | `bar`: "learned X / N" on every screen |
| `precache` | `all`: every file, strictly | `core` with `items` (30): the page, fonts, icons, start/win and the first 30 words strictly; every other picture and clip in `RUNTIME` |

A clip kind is a folder, `audio/<kind>/<id>.mp3`: a squad records `name` and `match`, a word game `en` and `he`
(`KINDS` in `build_page.py`). With `precache` `core`, the worker keeps every other picture and clip it fetches
in its runtime cache, whose name hashes those files, so it outlives a new version unless one of them
changed; online, the page fetches ahead what the next game needs (every learned word and the next new
ones), so a learned word and the next deal play offline.

Scripts run in the order data, club, engine. `CLUB.face(kit)` returns the card face's four hooks:
`prepare(items)`, `apply(style, cw, ch, mode)`, `build(p)` (its front must keep `.photo > img`, where a
match flight starts) and `fit(cardEl, p, geo)`. The kit has `el`, `textEm`, `words`, `bestSplit`,
`photoFront`, `splits`, `fitLines`, `renderName`, `setVars` and `digitEm`. The club style defines the tokens
`base.css` reads (`--font`, `--accent`, `--surface`, `--back-line`, `--edge`, `--found`, ...); a light
board also sets the optional ones (`--scheme`, `--hud-btn-bg`, `--pip-bg`, ...).

```sh
python3 -I _memory-game/tools/page/build_page.py assemble            # every game
python3 -I _memory-game/tools/page/build_page.py assemble --check    # before every commit: nothing stale
python3 -I _memory-game/tools/page/build_page.py assemble <game> --watch   # while designing
```

- Never edit `index.html` or `sw.js` by hand: the next `assemble` overwrites them, and `--check` fails
  until it does. The repo has no CI, so run `--check` before every commit. It also fails when a photo or
  clip has no roster entry, the fonts and `CREDITS.md` disagree, a club CSS variable is set but never read,
  a start/win clip isn't the master, or `og.jpg` is missing, not a JPEG or over 300 KB.
- `VERSION` hashes every precached file and the template. Any change to a page, a photo, a clip, a font or
  an icon gives a new cache, and that is what makes installed copies pick it up (one full re-download).
- A shared change changes every game: assemble, commit and verify all of them.
- The builder refuses a cache prefix that isn't the folder name, a prefix another game's starts with, and
  a manifest `id` that resolves to the origin root or to another game's app (Tel Aviv's `"./"` is
  grandfathered: changing it would break installed copies).

## Add a club

1. **Start it from the closest club**, which also checks the id, the cache prefix and the app id first:

   ```sh
   python3 -I _memory-game/tools/page/build_page.py new <club>-memory --like <closest club> \
       --name "זיכרון …" --short "זיכרון …" --color "#rrggbb"
   ```

   It writes the manifest, `club/` (from the `--like` club), its fonts and icon SVGs, the start/win clips,
   an empty `pronunciations.json`, and `CREDITS.md` and `tools/README.md` with TODOs. No page yet.
2. **Design** the club's look: `club/style.css` (tokens, card back, face, title), `club/club.js` (geometry
   and fit), `club/club.json` (title style, scheme, trophy paints, photo flags) and the icon SVGs. A new
   font: `python3 -I _memory-game/tools/fonts/add_font.py "<Family>" <weight> <game>`. Try it with stand-in
   data in a scratch folder outside the repo: `build_page.py assemble <game> --watch --repo <scratch>`.
3. **Scrape**: the club's scraper in `<game>/tools/scrape/`, built on `tools/scrape/` (fetcher, ids, the
   squad rule, the players.json check), writes `<work>/data/players.json`.
4. **Refresh**: `_memory-game/tools/refresh.sh <game> <work>` (below), which ends with the link preview
   (look at `<game>/og.jpg`), and render the icons: `bash _memory-game/tools/icons/render_icons.sh --game <game>`.
5. **Test and commit**: `verify.sh sanity <game>`, and look at its design in `verify.sh local <game>`'s
   seeded screenshots at both sizes; then `git add` with explicit paths. Fill in the TODOs of
   `CREDITS.md` and `tools/README.md` first: `--check` fails while one is left.

## Refresh a club

Downloads are untrusted data: keep them in a work directory outside the repo (`<work>`), run Python with
`-I`, and pass paths as arguments.

1. **Scrape** with the club's own scraper (its `tools/README.md`); it writes `<work>/data/players.json`
   and the photos, and fails loudly if the result isn't usable by the tools below.
2. **Everything else**: `_memory-game/tools/refresh.sh <game> <work>`
   - photos: `build_images.py --game` with the club's flags; look at `<work>/crops.png`;
   - it stops when a starter or bench player has no pinned pronunciation, so a person listens first:
     `tts.sh <game> <work> g2p` (what the G2P says for every name), `ab --ids <id> --cand <id>:<label>=<ipa>`
     (compare candidates), `listen --alt <id>=<label>:<ipa>` (judge by ear in `<work>/tts/listen.html`),
     then pin the IPA in `<game>/tools/tts/pronunciations.json` (its schema is in `tools/tts/generate.py`);
   - voice: `tts.sh generate --stale` renders only new or changed clips, `check` tests every clip (STT,
     loudness, format) and `sync` copies them into the game and removes leavers;
   - page: `build_page.py data`, the link preview (`tools/og/render_og.sh`; look at `<game>/og.jpg`), then
     `assemble --check`. WhatsApp keeps a link's old preview for a while: a link shared again may need a
     query such as `?v=2` to show the new one.
3. **Test** (below) and commit with explicit paths.

The voice is BlueTTS 2.5 with the `noa` voice and an ivrit.ai Whisper round-trip per clip. Its install
lives in `~/.cache/memory-game-tts`, which belongs to no club: `tools/tts/setup.sh` reports on it and
`setup.sh --install` makes it (about 1 GB). Needs uv, git, ffmpeg and whisper-cli.

## Test

```sh
_memory-game/tools/verify/verify.sh sanity [<game>...]   # the gate for every PR: all the games in about a minute
_memory-game/tools/verify/verify.sh live [<game>...]     # after a merge: the deployed games
_memory-game/tools/verify/verify.sh full [<game>...]     # a deliberate engine-wide behaviour refactor, or on request
```

**`sanity` is the default gate**: run it before every commit and on every PR. It checks the named games
(default: all) at once, in parallel and headless at 600×960 touch:
- static: `assemble --check` (with the builder's lints) and the format of every shipped clip
  (`clips.py format`: the format `tts.sh check` enforces, without the work directory and its STT);
- per game, no console error and no 404; the worker controls the page and `installability` is `[]`;
- memory: three flips say their clip and their matches the second (the game's voice script);
- the quiz's first question: a wrong pick turns over and says its line, the right one says its own (a
  word game starts with 25 words learned, so its quiz is open and its deal reaches past the precached core);
- offline: a reload with the network off keeps what she learned, shows the pictures, plays cached clips,
  asks a quiz question and opens the next new flash card, which turns up, speaks and counts as learned;
- the state machine (`states/scenarios.js`): a squad's suites, the flash cards and the whole-roster quiz;
  a word game's new-first deal, the quiz locked below 4 and asking only learned words, the voice script,
  a flash card counting as learned and moving the bar, and what she learned surviving a reload;
- a quick upgrade from `origin/main` (`--from <ref>`), online then offline, for the games that exist there.

Each failure names what broke: the URL, the console line, the clips it heard. `live` (`sanity --live`)
checks the deployed games after a merge: it waits until GitHub Pages serves the new `sw.js`, compares every
precached file with the repo, then runs the same browser checks on the live site.

**`full` is only for a deliberate refactor of the engine's behaviour across every game, or when asked**
(about an hour): `local`, then `compare` and `upgrade` from `origin/main`. Each also runs alone:
- `verify.sh local [<game>...]`, P9: `assemble --check`; seeded start, mid and win screenshots at 600×960
  and 960×600; one audio playthrough (the right clip on every flip); a whole quiz at both sizes (every
  player once, a wrong pick, the clips in order, question/wrong/reveal/end screenshots); the worker online,
  offline (memory and quiz) and installable, and the link preview (its tags, and `og.jpg` as served); the
  state machine;
- `verify.sh compare <ref-a> <ref-b>` checks a refactor is pixel-, DOM- and audio-identical;
- `verify.sh upgrade <old-ref> <new-ref>` simulates the GitHub Pages upgrade under `/pages/` with whole
  games, online then offline.

Outputs go to `--out <dir>` (default: one folder per checkout under `$TMPDIR`; never inside the repo).
`MEMORY_GAME_VERIFY_PORTS=8801-8804` pins the test servers' ports when several runs share a machine
(`sanity` takes one more than the games it upgrades). To look at a game by hand, serve the repo with
`python3 -I _memory-game/tools/verify/serve.py 8765 .` (the stock `http.server` resets connections while
a worker precaches ~80 files).
