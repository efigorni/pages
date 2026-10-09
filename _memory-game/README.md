# _memory-game

The shared source of every memory game. A game is a folder at the repo root with `club/club.json`;
`python3 -I _memory-game/tools/page/build_page.py list` lists them. This folder is not a page: it has no
`index.html`, no card in the root `index.html`, and the games never fetch anything from it. Don't delete
it as an orphan.

| File | What it is |
|---|---|
| `engine.js` | The game, in two modes: memory (deal, flips) and the quiz (who is this?); audio, overlays, confetti, wake lock, install, service-worker registration, and the face kit a club's card face is drawn with |
| `base.css` | Every style the games share; colours and fonts come from each club's tokens |
| `page.template.html` | The page with slots, filled per game: head, club style, base, title, trophy, DATA, club script, engine; the two mode icons |
| `sw.template.js` | The service worker; each game's `sw.js` is this file with `VERSION`, `ASSETS` and `PREFIX` filled in |
| `audio/ui/` | The start, win and who clips (the engine's own lines); every game ships a copy |
| `new/` | The templates `build_page.py new` fills: `CREDITS.md`, the club's `tools/README.md` |
| `tools/page/build_page.py` | `new`, `data`, `assemble [--check] [--watch]`, `list [--json]` (below) |
| `tools/refresh.sh` | Everything after a club's scrape, in one command |
| `tools/images/` | `build_images.py` crops the cutout photos; `framing.py` is the alpha-outline framing the scrapers use too |
| `tools/tts/` | The voice clips: `tts.sh` is the entry point; `setup.sh` the engine install |
| `tools/scrape/` | The scraper kit: `common.py` (fetcher, ids, atomic write, photo facts), `roster.py` (the squad rule and a players.json check), `transfermarkt.py`, `contact_sheet.py` |
| `tools/fonts/add_font.py` | Fetches a Google Fonts family's Hebrew and Latin subsets and its OFL into a game |
| `tools/icons/` | `render_icons.sh --game <game>` renders a game's PWA icons from its two SVGs |
| `tools/verify/` | `verify.sh`: the browser checks every change runs (below) |

## How a game is built

Each game's `index.html` stays self-contained, so it works offline and from `file://`, and an installed
copy upgrades the way it always did. `build_page.py` writes it whole, and `sw.js`, from:

| Source | What it holds |
|---|---|
| `<game>/manifest.webmanifest` | The club's identity: name, short name, colours, id. The head and the title come from it. Never written by a tool after `new` |
| `<game>/club/club.json` | The name model (`names`), the title style (`title`), the board's `scheme`, the trophy's paints, the photo flags (`images`) |
| `<game>/club/style.css` | Hand-written: fonts, colour tokens, card back, card face, title |
| `<game>/club/club.js` | Hand-written: `CLUB = { confetti, fonts, face(kit) }` |
| `<game>/club/roster.json` | Starters, bench and backups (quiz only), written by `build_page.py data` |
| `_memory-game/*` | The engine, the base styles and the two templates |

Every place a game starts (the start screen, the win screen, the ↻ confirm) offers the two modes side by side.
Memory deals the 11 starters and 4 of the bench. The quiz asks every roster player once in random order:
"מי זה" (`audio/ui/who.mp3`) then his match clip, four photo-only cards; a wrong pick greys out with a soft
sound, the right one turns to the club's card face, says the name and moves on. The squad rule
(`tools/scrape/roster.py`) gives the pool's backup goalkeepers role `backup`: the roster's `backup` list, asked
in the quiz, never dealt. Every tool that images, voices, checks, syncs or prunes takes `roster.SHIPPED`
(starter, bench, backup), so a refresh keeps them.

Scripts run in the order data, club, engine. `CLUB.face(kit)` returns the card face's four hooks:
`prepare(players)`, `apply(style, cw, ch, mode)`, `build(p)` (its front must keep `.photo > img`, where a
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
  or a start/win clip isn't the master.
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
4. **Refresh**: `_memory-game/tools/refresh.sh <game> <work>` (below), and render the icons:
   `bash _memory-game/tools/icons/render_icons.sh --game <game>`.
5. **Test and commit**: `verify.sh local --out <dir> <game>`, then `git add` with explicit paths. Fill in
   the TODOs of `CREDITS.md` and `tools/README.md` first: `--check` fails while one is left.

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
   - page: `build_page.py data`, then `assemble --check`.
3. **Test** (below) and commit with explicit paths.

The voice is BlueTTS 2.5 with the `noa` voice and an ivrit.ai Whisper round-trip per clip. Its install
lives in `~/.cache/memory-game-tts`, which belongs to no club: `tools/tts/setup.sh` reports on it and
`setup.sh --install` makes it (about 1 GB). Needs uv, git, ffmpeg and whisper-cli.

## Test

```sh
_memory-game/tools/verify/verify.sh local --out <dir outside the repo> [<game>...]
```

P9 for the named games (default: all): `assemble --check`; seeded start, mid and win screenshots at
600×960 and 960×600; one audio playthrough (the right clip on every flip); a whole quiz at both sizes (every
player once, a wrong pick, the clips in order, question/wrong/reveal/end screenshots); the worker online,
offline (memory and quiz) and installable; the state machine. `verify.sh compare <ref-a> <ref-b>` checks a refactor is pixel-, DOM- and
audio-identical, `verify.sh upgrade <old-ref> <new-ref>` simulates the GitHub Pages upgrade under
`/pages/`, online then offline, and `verify.sh live` checks the deployed game after a merge. To look at a
game by hand, serve the repo with `python3 -I _memory-game/tools/verify/serve.py 8765 .` (the stock
`http.server` resets connections while a worker precaches ~80 files).
