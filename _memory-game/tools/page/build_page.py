#!/usr/bin/env python3
"""Build the memory games from _memory-game/ and each game's club sources.

    python3 -I _memory-game/tools/page/build_page.py data <players.json> <game> [--prune]
    python3 -I _memory-game/tools/page/build_page.py assemble [--check] [<game> ...] [--watch]
    python3 -I _memory-game/tools/page/build_page.py list [--json]
    python3 -I _memory-game/tools/page/build_page.py new <game> --like <club> --name … --short … --color "#…"
Every command takes --repo <dir>: build the games in another folder (a scratch copy, to try a design
with stand-in data before the real roster exists) with this checkout's _memory-game/.

A game is a folder at the repo root with club/club.json. Its sources, all hand-owned except the roster:

  manifest.webmanifest  the club's identity; its name, short_name and theme_color fill the page's head and
                        title. Read, never written.
  club/club.json        {"names": "full"|"first-last", "title": "plain"|"tiers", "scheme": "dark"|"light",
                         "trophy": {"cup", "stem", "star", "shine", "shine_opacity"?, "shade"?}, "images": {...}}
                        `scheme` (default dark) is the board's: the head's color-scheme and iOS status bar
                        follow it, and a light club's style sets --scheme: light for base.css.
  club/style.css        the club's style: fonts, tokens, card back, card face, title
  club/club.js          const CLUB = { confetti, fonts, face(kit) }
  club/roster.json      season and players (roles starter, bench, backup, in that order); written by `data`
  club/avoid.json       a word game's sound-alikes, {id: {other id: why}}: tools/words/neighbours.py writes it;
                        checked against the roster, and each word's list (with play.quiz.apart) is its `avoid`
  tools/tts/en_pins.json  a word game's English voice pins; a `take` picked by ear must stay the shipped clip

The builder writes two files per game, whole:

  index.html  _memory-game/page.template.html filled in: the head, the club style, base.css, the title, the
              trophy, DATA (the roster plus the clips that exist under audio/, in roster order), the club
              script and engine.js. The page plays two modes: memory deals the starters and bench; the
              quiz ("who is this?") asks every player in the roster once, the backups too. The head carries
              the link preview (Open Graph): the manifest name, OG_DESCRIPTION and the absolute URLs, under
              SITE, of the game and of its og.jpg, which tools/og/render_og.sh renders and nothing precaches
  sw.js       _memory-game/sw.template.js with VERSION, ASSETS and PREFIX filled in. VERSION hashes every
              precached file and the template, so any change installs a fresh cache.

`data` writes club/roster.json from players.json (one player per line), then assembles that game; --prune
deletes photos and clips of players who are no longer in it. The roster keeps every role in roster.SHIPPED; role
"backup" (the pool's backup goalkeepers, roster.py's squad rule) is asked in the quiz and never dealt in the memory
game, and his photo and clips are made, checked and shipped like everyone else's. The name model (club.json `names`): "full"
shows name_he on one card line; "first-last" adds the card's two tiers (first_he / last_he). speak_he, the
text the voice reads, ships whenever it differs from name_he (and always with "first-last").
`assemble` writes every game's index.html and sw.js, or the named games'. `--check` writes nothing and fails
if a page or sw.js is not what assemble would write, or if img/ or audio/ holds a player the roster
doesn't (every file there is precached), or if the fonts and CREDITS.md disagree: every shipped .woff2 has
an @font-face, the declared families are the ones credited under Fonts, every OFL link resolves and every
OFL file is linked, the Voice section is _memory-game/new/CREDITS.md's, and no TODO is left; or if the
club sets a CSS variable nothing reads, or reads one (without a fallback) nothing defines; or if a game's
start/win clip isn't the master in _memory-game/audio/ui/ (the engine's lines, which tools/tts/hebrew.py
renders); or if its og.jpg is missing, not a JPEG or over OG_MAX_KB. Run it before committing: the repo
has no CI. `--watch`
assembles the named games again whenever one of their sources or a shared file changes.
`new` starts a club: it checks the id, the cache prefix and the app id first and writes nothing if one
clashes; then it writes the manifest (from --like's, with the new name, colours and id), copies --like's
club/ sources, fonts and icon designs as the design's starting point, the start/win clips from
_memory-game/audio/ui/, and writes CREDITS.md
and tools/README.md from _memory-game/new/ with TODOs. No page until `data` has a roster.
"""
import argparse
import hashlib
import html
import json
import re
import shutil
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

sys.dont_write_bytecode = True  # no __pycache__ in the repo
SHARED = Path(__file__).resolve().parents[2]
REPO = SHARED.parent
sys.path.insert(0, str(SHARED / "tools/tts"))
sys.path.insert(0, str(SHARED / "tools/scrape"))
from hebrew import UI_TEXTS, speak_text, split_display_name  # noqa: E402
from roster import SHIPPED, check as check_players  # noqa: E402

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CONFIG = "club/club.json"
# A word game's sound-alikes, {id: {other id: why}}: tools/words/neighbours.py writes it from CMUdict.
AVOID = "club/avoid.json"
# A word game's English voice pins; a pin's `take` is a clip picked by ear, with the shipped file's sha256.
EN_PINS = "tools/tts/en_pins.json"
PRECACHE_DIRS = ("fonts", "img", "audio", "icons")
PRECACHE_SUFFIXES = {".woff2", ".webp", ".png", ".mp3"}
UI_CLIPS = tuple(UI_TEXTS)
# What a game teaches (club.json `kind`): a squad's players, or words. Each records its own kinds of clip,
# under audio/<kind>/<id>.mp3, and its quiz asks its own question (the quiz buttons' label).
KINDS = {"squad": ("name", "match"), "words": ("en", "he")}
ASK = {"squad": "מי זה?", "words": "מה זה?"}
# A squad's script when its club.json says nothing else (club.json `play` overrides keys of it); a word game
# writes its own.
SQUAD_PLAY = {"voice": {"flip": ["name"], "match": ["name", "match"], "ask": ["match"], "wrong": ["match"],
                        "right": ["name"], "card": ["match"]},
              "deal": {"policy": "squad", "pairs": 15}, "quiz": {"pool": "all"}, "progress": "inventory",
              "precache": {"policy": "all"}}
# The moments the voice script (club.json play.voice) gives clips to: memory's flip and match, the quiz's
# question, wrong pick and right pick, and a flash card.
MOMENTS = ("flip", "match", "ask", "wrong", "right", "card")
# How a word game's quiz picks its questions and how every game scores an answer (engine.js LEARN, whose
# defaults are round 2's simulation's): play.quiz may set any of these.
LEARN_KEYS = {
    "size": ("questions per quiz, >= 1", lambda v, q: _int(v) and v >= 1),
    "master": ("first-pick successes that make an item fully learned, >= 1", lambda v, q: _int(v) and v >= 1),
    "newMin": ("never-asked words per quiz, at least, >= 0", lambda v, q: _int(v) and v >= 0),
    "newMax": ("never-asked words per quiz, at most, >= newMin", lambda v, q: _int(v) and v >= q.get("newMin", 1)),
    "sureMin": ("fully learned words per quiz, >= 0", lambda v, q: _int(v) and v >= 0),
    "growth": ("a learning level's wait multiplier, >= 1", lambda v, q: _num(v) and v >= 1),
    "jitter": ("the random spread on the overdue order, >= 0", lambda v, q: _num(v) and v >= 0),
    "decrement": ("\"none\", \"demote\" or \"dec\"", lambda v, q: v in ("none", "demote", "dec")),
}


def _int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)
# Element ids the engine looks up, and the CSS variables base.css reads that the engine sets itself.
ENGINE_IDS = ("app", "board", "pips", "start", "confirm", "win", "fan", "play", "replay", "again", "yes", "no",
              "mute", "confetti", "install", "play-quiz", "replay-quiz", "yes-quiz", "picks", "question", "say",
              "play-cards", "replay-cards", "yes-cards", "cards", "shelf", "shelf-count", "next-new", "flash",
              "flash-slot", "prev", "next", "hear", "close", "progress", "progress-count")
RUNTIME_VARS = {"--i"}
# Where GitHub Pages publishes the games. A link preview needs absolute URLs; the verify tools read it here too.
SITE = "https://efigorni.github.io/pages/"
# The link preview's image, at the game's root (tools/og/render_og.sh renders it). Outside PRECACHE_DIRS, so
# a device never downloads it: only the crawlers of WhatsApp and the like do.
OG_IMAGE = "og.jpg"
OG_MAX_KB = 300
OG_DESCRIPTION = "משחק זיכרון וחידון שחקנים — לומדים פרצופים, מספרים ושמות"
# Tel Aviv's manifest id "./" resolves to the origin root. It shipped that way and changing it would
# break installed copies, so it is the only game allowed a root id.
ROOT_ID_GAMES = {"maccabi-memory"}
# The trophy on the win screen: one geometry, painted from club.json `trophy`.
TROPHY = (
    '<path d="M31 13h58v27c0 19-13 34-29 34S31 59 31 40z" fill="{cup}"/>',
    '<path d="M31 22H15v7c0 13 9 22 21 22M89 22h16v7c0 13-9 22-21 22" fill="none" stroke="{cup}" stroke-width="7" '
    'stroke-linecap="round"/>',
    '<path d="M53 72h14v15H53z" fill="{stem}"/>',
    '<path d="M39 86h42a5 5 0 0 1 5 5v12H34V91a5 5 0 0 1 5-5z" fill="{cup}"/>',
    '<path d="M60 25l3.64 9.98 10.63.38-8.37 6.56 2.92 10.22L60 46.2l-8.82 5.94 2.92-10.22-8.37-6.56 10.63-.38z" '
    'fill="{star}"/>',
    '<path d="M38 19v19c0 6 2 11 5 15" fill="none" stroke="{shine}"{shine_opacity} stroke-width="3.5" '
    'stroke-linecap="round"/>',
)
SHADE = '<path d="M82 18v20c0 9-4 17-10 22" fill="none" stroke="{shade}" stroke-width="3" stroke-linecap="round"/>'


def fail(msg):
    sys.exit(f"build_page: {msg}")


def clean(text):
    return " ".join(str(text or "").split())


def read(path, hint=None):
    if not path.is_file():
        fail(f"missing {path.relative_to(REPO) if REPO in path.parents else path}" + (f" ({hint})" if hint else ""))
    return path.read_text(encoding="utf-8")


def games(names=None):
    found = sorted(d.name for d in REPO.iterdir() if (d / CONFIG).is_file())
    for name in names or []:
        if name.rstrip("/") not in found:
            fail(f"{name} is not a game (no {CONFIG})")
    return [n.rstrip("/") for n in names] if names else found


def config(game):
    return json.loads(read(REPO / game / CONFIG))


def kind_of(game):
    kind = config(game).get("kind", "squad")
    if kind not in KINDS:
        fail(f"{game}/{CONFIG}: kind must be one of {', '.join(KINDS)}, not {kind!r}")
    return kind


def play_of(game):
    """club.json `play`, checked: the voice script and the deal, quiz, progress and precache policies
    (README, "Play config"). The engine reads it from DATA; the precache policy is the builder's too."""
    kind, play = kind_of(game), config(game).get("play")
    if kind == "squad":
        play = {**SQUAD_PLAY, **(play or {})}
    where = f"{game}/{CONFIG} play"
    if not isinstance(play, dict):
        fail(f"{where}: missing")
    voice = play.get("voice")
    if not isinstance(voice, dict) or set(voice) != set(MOMENTS):
        fail(f"{where}.voice: one list of clips per moment: {', '.join(MOMENTS)}")
    for moment, clips in voice.items():
        if not clips or any(c not in KINDS[kind] for c in clips):
            fail(f"{where}.voice.{moment}: a list of {' / '.join(KINDS[kind])} (a {kind} game's clips), not {clips!r}")
    deal, quiz, precache = play.get("deal") or {}, play.get("quiz") or {}, play.get("precache") or {}
    if deal.get("pairs") != 15:
        fail(f"{where}.deal.pairs: 15 (the board is 5 x 6)")
    policies = {"squad": kind == "squad",
                "new-first": isinstance(deal.get("new"), int) and 0 < deal.get("new", 0) <= deal["pairs"]}
    if not policies.get(deal.get("policy")):
        fail(f"{where}.deal: policy \"squad\" (a squad's game) or \"new-first\" with 0 < new <= pairs")
    if quiz.get("pool") == "learned":
        if not (isinstance(quiz.get("unlock"), int) and quiz["unlock"] >= 4 and isinstance(quiz.get("size"), int)
                and quiz["size"] >= 1):
            fail(f"{where}.quiz: pool \"learned\" wants unlock >= 4 (the four cards) and size >= 1")
    elif quiz.get("pool") != "all":
        fail(f"{where}.quiz.pool: \"all\" or \"learned\"")
    for key, (want, ok) in LEARN_KEYS.items():
        if key in quiz and not ok(quiz[key], quiz):
            fail(f"{where}.quiz.{key}: {want}, not {quiz[key]!r}")
    apart = quiz.get("apart", [])
    if not (isinstance(apart, list) and all(isinstance(p, list) and len(p) == 2 and all(isinstance(i, str) for i in p)
                                            for p in apart)):
        fail(f"{where}.quiz.apart: a list of [id, id] pairs never offered against each other")
    if play.get("progress") not in ("inventory", "bar"):
        fail(f"{where}.progress: \"inventory\" (the shelf's marks only) or \"bar\" (on every screen)")
    if precache.get("policy") == "core":
        if not (isinstance(precache.get("items"), int) and precache["items"] >= deal["pairs"]):
            fail(f"{where}.precache: policy \"core\" wants items >= deal.pairs, so the first game plays offline")
    elif precache.get("policy") != "all":
        fail(f"{where}.precache.policy: \"all\" or \"core\"")
    return play


def items_of(roster):
    """The roster's items in teaching order: the words, or the players."""
    return roster["words"] if "words" in roster else roster["players"]


def entry(p, page, model):
    pid = p["id"]
    if not ID_RE.match(pid):
        fail(f"unsafe player id: {pid!r}")
    if p.get("number") is None:
        fail(f"{pid}: no shirt number (the card shows one)")
    number = int(p["number"])
    if not 0 <= number <= 99:
        fail(f"{pid}: shirt number out of range: {number}")
    name = clean(p["name_he"])
    lines = p.get("card_name_lines")
    if isinstance(lines, list) and len(lines) == 2:
        first, last = clean(lines[0]), clean(lines[1])
    elif isinstance(lines, list) and len(lines) == 1:
        first, last = "", clean(lines[0])
    elif p.get("last_he"):
        first, last = clean(p.get("first_he")), clean(p["last_he"])
    else:
        first, last = split_display_name(name)
    speak = clean(p.get("speak_he")) or speak_text(name)
    for label, text in (("name_he", name), ("first_he", first), ("last_he", last), ("speak_he", speak)):
        if any(ch in text for ch in "<>&\"`"):
            fail(f"{pid}: unexpected characters in {label}: {text!r}")
    if not name or not last or not speak:
        fail(f"{pid}: empty name field")
    if clean(f"{first} {last}") != name:
        fail(f"{pid}: first/last {first!r} + {last!r} do not reproduce name_he {name!r}")
    if speak != speak_text(name):
        print(f"note: {pid}: speak_he {speak!r} differs from the parentheses rule ({speak_text(name)!r})", flush=True)
    img = f"img/{pid}.webp"
    if not (page / img).is_file():
        fail(f"{pid}: missing {img} (run the image tool first)")
    out = {"id": pid, "name_he": name}
    if model == "first-last":
        out.update(first_he=first, last_he=last, speak_he=speak)
    elif speak != name:  # the voice's text ships whenever it isn't the card's, whatever the card shows
        out["speak_he"] = speak
    out.update(number=number, role=p["role"], img=img)
    return out


def word_entry(w, page):
    wid = w.get("id", "")
    if not ID_RE.match(wid):
        fail(f"unsafe word id: {wid!r}")
    out = {"id": wid}
    for key in ("en", "he", "he_niqqud", "theme"):
        text = clean(w.get(key))
        if any(ch in text for ch in "<>&\"`"):
            fail(f"{wid}: unexpected characters in {key}: {text!r}")
        if text:
            out[key] = text
    if not out.get("en") or not out.get("he"):
        fail(f"{wid}: a word needs en and he")
    missing = [rel for rel in (f"img/{wid}.webp", *(f"audio/{k}/{wid}.mp3" for k in KINDS["words"]))
               if not (page / rel).is_file()]
    if missing:
        fail(f"{wid}: missing {', '.join(missing)} (copy the pictures and clips in first)")
    out["img"] = f"img/{wid}.webp"
    return out


def roster_text(roster):
    """club/roster.json: one item per line, so a refresh diffs per player or word."""
    key = "words" if "words" in roster else "players"
    head = "".join(f"  {json.dumps(k)}: {json.dumps(v, ensure_ascii=False)},\n" for k, v in roster.items() if k != key)
    rows = ",\n".join("    " + json.dumps(p, ensure_ascii=False, separators=(", ", ": ")) for p in roster[key])
    return f'{{\n{head}  "{key}": [\n{rows}\n  ]\n}}\n'


def has_roster(game):
    return (REPO / game / "club/roster.json").is_file()


def read_roster(game):
    return json.loads(read(REPO / game / "club/roster.json", f"run `build_page.py data <players.json> {game}`"))


def orphans(game, roster):
    """Pictures and clips of items the roster doesn't have: shipped, never shown or played."""
    page = REPO / game
    ids = {p["id"] for p in items_of(roster)}
    dirs = [("img", ".webp")] + [(f"audio/{kind}", ".mp3") for kind in KINDS[kind_of(game)]]
    return sorted(f.relative_to(page).as_posix() for d, suffix in dirs
                  for f in (page / d).glob(f"*{suffix}") if f.stem not in ids)


def sound_alikes(game):
    """A word game's club/avoid.json, {id: {other id: why}}, or None when it has none."""
    path = REPO / game / AVOID
    if not path.is_file():
        return None
    data = json.loads(read(path))
    if not (isinstance(data, dict) and all(isinstance(v, dict) for v in data.values())):
        fail(f"{game}/{AVOID}: {{id: {{other id: why}}}}, one line per word (tools/words/neighbours.py writes it)")
    return data


def avoid_of(game):
    """What a word game's quiz never offers as a wrong answer to each word: its sound-alikes (club/avoid.json)
    and its look-alike pictures (club.json play.quiz.apart). {id: sorted ids}, for the words that have any."""
    avoid = {wid: set(others) for wid, others in (sound_alikes(game) or {}).items()}
    for a, b in play_of(game)["quiz"].get("apart", []):
        avoid.setdefault(a, set()).add(b)
        avoid.setdefault(b, set()).add(a)
    return {wid: sorted(others) for wid, others in avoid.items() if others}


def data_line(game, roster):
    """The DATA script: the roster (a word game's words with their `avoid`), the clips that exist (per kind,
    in roster order), the game's folder (the key of what she knows) and its play config."""
    page = REPO / game
    if "words" in roster:
        avoid = avoid_of(game)
        roster = {**roster, "words": [{**w, "avoid": avoid[w["id"]]} if w["id"] in avoid else w for w in roster["words"]]}
    ids = [p["id"] for p in items_of(roster)]
    audio = {"ui": [k for k in UI_CLIPS if (page / "audio" / "ui" / f"{k}.mp3").is_file()]}
    for kind in KINDS[kind_of(game)]:
        audio[kind] = [i for i in ids if (page / "audio" / kind / f"{i}.mp3").is_file()]
    payload = {**roster, "audio": audio, "game": game, "play": play_of(game)}
    if config(game).get("lines"):  # the engine's lines this game says in its own words (check_ui_clips)
        payload["lines"] = config(game)["lines"]
    return "const DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"


def write_words(words_json, game):
    """A word game's club/roster.json from words.json (a list, or {"words": [...]}), in teaching order (`rank`
    when the list has one): id, en, he, he_niqqud when given, theme and the picture. Every word needs its
    picture and both clips. club.json `leave_out` ({id: why}) keeps a listed word out of the game."""
    page = REPO / game
    data = json.loads(Path(words_json).read_text(encoding="utf-8"))
    words = data["words"] if isinstance(data, dict) else data
    ids = [w.get("id") for w in words]
    if len(set(ids)) != len(ids):
        fail(f"{words_json}: duplicate ids: {sorted({i for i in ids if ids.count(i) > 1})}")
    for wid, why in config(game).get("leave_out", {}).items():
        print(f"{game}: left out {wid}{'' if wid in ids else ' (not in the list)'}: {why}", flush=True)
    words = [w for w in words if w["id"] not in config(game).get("leave_out", {})]
    ordered = sorted(words, key=lambda w: w.get("rank", 0)) if all("rank" in w for w in words) else words
    roster = {"words": [word_entry(w, page) for w in ordered]}
    (page / "club/roster.json").write_text(roster_text(roster), encoding="utf-8")
    print(f"{game}: club/roster.json: {len(roster['words'])} words", flush=True)
    return roster


def write_players(players_json, game):
    page = REPO / game
    model = config(game).get("names")
    if model not in ("full", "first-last"):
        fail(f"{game}/{CONFIG}: names must be \"full\" or \"first-last\", not {model!r}")
    data = json.loads(Path(players_json).read_text(encoding="utf-8"))
    problems = check_players(data)
    if problems:
        fail(f"{players_json}: {'; '.join(problems)}")
    shipped = [entry(p, page, model) for role in SHIPPED for p in data["players"] if p.get("role") == role]
    roster = {"season": data.get("season"), "players": shipped}
    (page / "club/roster.json").write_text(roster_text(roster), encoding="utf-8")
    counts = " ".join(f"{role}={sum(p['role'] == role for p in shipped)}" for role in SHIPPED)
    print(f"{game}: club/roster.json: {counts}", flush=True)
    return roster


def write_data(players_json, game, prune):
    page = REPO / game
    if kind_of(game) == "words":
        roster = write_words(players_json, game)
    else:
        roster = write_players(players_json, game)
    for rel in orphans(game, roster):
        if prune:
            (page / rel).unlink()
        print(f"{game}: {'removed' if prune else 'not in the roster (data --prune removes it)'}: {rel}", flush=True)


def lint_credits(game):
    """The fonts the club style declares vs the files it ships vs what CREDITS.md credits; a squad's Voice
    section is the shared one, a word game's credits its pictures and voices."""
    page = REPO / game
    style = read(page / "club/style.css")
    credits = read(page / "CREDITS.md")
    faces = re.findall(r"@font-face\s*\{(.*?)\}", style, re.S)
    declared = {re.search(r"font-family:\s*\"?([^\";]+)\"?;", f).group(1) for f in faces}
    srcs = {re.search(r"url\(([^)]+)\)", f).group(1) for f in faces}
    shipped = {f"fonts/{f.name}" for f in (page / "fonts").glob("*.woff2")}
    fonts_md = credits.split("## Fonts", 1)[-1].split("\n## ", 1)[0]
    credited = set(re.findall(r"^- \*\*([^*]+)\*\*", fonts_md, re.M))
    licences = set(re.findall(r"\((fonts/OFL-[^)]+)\)", credits))
    if kind_of(game) == "words":
        sections = {s.split("\n", 1)[0].strip() for s in credits.split("\n## ")[1:]}
        voice = [f"CREDITS.md has no {s} section" for s in ("Pictures", "Voice") if s not in sections]
    else:
        shared = read(SHARED / "new/CREDITS.md").split("## Voice", 1)[1]
        voice = ["CREDITS.md's Voice section differs from _memory-game/new/CREDITS.md's"
                 for _ in [1] if credits.split("## Voice", 1)[-1] != shared]
    return ([f"CREDITS.md: a TODO is left" for _ in [1] if "TODO" in credits]
            + [f"{f} is shipped but no @font-face uses it" for f in sorted(shipped - srcs)]
            + [f"an @font-face uses {f}, which isn't shipped" for f in sorted(srcs - shipped)]
            + [f"CREDITS.md doesn't credit the font {f}" for f in sorted(declared - credited)]
            + [f"CREDITS.md credits {f}, which no @font-face declares" for f in sorted(credited - declared)]
            + [f"CREDITS.md links {f}, which doesn't exist" for f in sorted(licences) if not (page / f).is_file()]
            + [f"CREDITS.md doesn't link fonts/{f.name}" for f in sorted((page / "fonts").glob("OFL-*.txt"))
               if f"fonts/{f.name}" not in licences]
            + voice)


def check_ui_clips(game):
    """Each game ships its own copy of the engine's start and win clips; the master is _memory-game/audio/ui/.
    A line the game says in its own words (club.json `lines`, e.g. a word game's win) is its own clip instead."""
    engine = read(SHARED / "engine.js")
    own = config(game).get("lines", {})
    problems = [f"club.json lines.{key}: the engine has no {key} line ({', '.join(UI_CLIPS)})" for key in own if key not in UI_CLIPS]
    for key, text in UI_TEXTS.items():
        line = re.search(rf"const {key.upper()}_LINE = '([^']*)';", engine)
        if not line:
            problems.append(f"engine.js has no {key.upper()}_LINE, the {key} clip's text")
        elif line.group(1) != text:
            problems.append(f"engine.js's {key.upper()}_LINE is not hebrew.py's UI_TEXTS[{key!r}], which the clip says")
    for clip in UI_CLIPS:
        copy = REPO / game / "audio/ui" / f"{clip}.mp3"
        if clip in own:
            if not copy.is_file():
                problems.append(f"audio/ui/{clip}.mp3 is missing: club.json lines.{clip} ({own[clip]!r}) is the game's own")
        elif not copy.is_file() or copy.read_bytes() != (SHARED / "audio/ui" / f"{clip}.mp3").read_bytes():
            problems.append(f"audio/ui/{clip}.mp3 is not _memory-game/audio/ui/{clip}.mp3")
    return problems


def check_apart(game):
    """play.quiz.apart names words of this game: on the roster, not left out. A word game's club/avoid.json is
    its roster's: a line per word and no other, ids on the roster, never the word itself, every pair both ways."""
    ids = {p["id"] for p in items_of(read_roster(game))}
    left = config(game).get("leave_out", {})
    where = lambda i: "left out" if i in left else "not on the roster"  # noqa: E731
    problems = [f"club.json play.quiz.apart: {i} is {where(i)}"
                for pair in play_of(game)["quiz"].get("apart", []) for i in pair if i not in ids]
    if kind_of(game) != "words":
        return problems
    alike = sound_alikes(game)
    if alike is None:
        return problems + [f"{AVOID} is missing (uv run --with cmudict==1.1.3 python -I "
                           f"_memory-game/tools/words/neighbours.py {game})"]
    stale = [f"{i} has no line" for i in sorted(ids - set(alike))] + [f"{i} is {where(i)}" for i in sorted(set(alike) - ids)]
    if stale:
        more = f" and {len(stale) - 5} more" if len(stale) > 5 else ""
        problems.append(f"{AVOID} is not this roster's (run tools/words/neighbours.py again): {', '.join(stale[:5])}{more}")
    for wid, others in alike.items():
        problems += [f"{AVOID}: {wid}'s {o} is {where(o)}" for o in others if o not in ids]
        problems += [f"{AVOID}: {wid} avoids itself" for o in others if o == wid]
        problems += [f"{AVOID}: {wid} avoids {o}, but not the other way round" for o in others
                     if o in alike and wid not in alike[o]]
    return problems


def check_takes(game):
    """A word game's English clips picked by ear (tools/tts/en_pins.json `take`) are the files it ships, so a
    refresh never replaces one with a default render; every pin names a word on the roster."""
    path = REPO / game / EN_PINS
    if not path.is_file():
        return []
    ids = {p["id"] for p in items_of(read_roster(game))}
    problems = []
    for wid, pin in json.loads(read(path)).get("words", {}).items():
        if wid not in ids:
            problems.append(f"{EN_PINS}: {wid} is not on the roster")
            continue
        want = (pin.get("take") or {}).get("sha256")
        clip = REPO / game / "audio/en" / f"{wid}.mp3"
        if want and not (clip.is_file() and hashlib.sha256(clip.read_bytes()).hexdigest().startswith(want)):
            problems.append(f"audio/en/{wid}.mp3 is not the take picked by ear ({EN_PINS}): put that file back, "
                            "or pick a new take by ear and update its pin")
    return problems


def check_og(game):
    """The link preview's image the head points at: a JPEG small enough for WhatsApp to show."""
    path = REPO / game / OG_IMAGE
    if not path.is_file():
        return [f"{OG_IMAGE} is missing (render it: _memory-game/tools/og/render_og.sh {game})"]
    data = path.read_bytes()
    return ([f"{OG_IMAGE} is not a JPEG" for _ in [1] if data[:3] != b"\xff\xd8\xff"]
            + [f"{OG_IMAGE} is {len(data) // 1024} KB, over {OG_MAX_KB} KB" for _ in [1] if len(data) > OG_MAX_KB * 1024])


def source(path, closer):
    """A shared or club source spliced into the page: it must not close its own element early."""
    text = read(path)
    if closer in text.lower():
        fail(f"{path.relative_to(REPO)} must not contain {closer}")
    if not text.endswith("\n"):
        fail(f"{path.relative_to(REPO)} must end with a newline")
    return text


def title_html(name, mode):
    if mode == "plain":
        return html.escape(name)
    small, big = name.split(" ", 1)
    return f'<span class="title-small">{html.escape(small)}</span> <span class="title-big">{html.escape(big)}</span>'


def trophy_svg(t):
    paint = {**t, "shine_opacity": f' stroke-opacity="{t["shine_opacity"]}"' if "shine_opacity" in t else ""}
    lines = [line.format(**paint) for line in TROPHY] + ([SHADE.format(**t)] if "shade" in t else [])
    return "".join(f"      {line}\n" for line in lines)


def manifest(game):
    return json.loads(read(REPO / game / "manifest.webmanifest", "it comes before the page"))


def render(game):
    man, cfg = manifest(game), config(game)
    base = source(SHARED / "base.css", "</style")
    style = source(REPO / game / "club/style.css", "</style")
    scheme = cfg.get("scheme", "dark")
    if scheme not in ("dark", "light"):
        fail(f"{game}/{CONFIG}: scheme must be \"dark\" or \"light\", not {scheme!r}")
    said = re.search(r"--scheme:\s*([\w-]+)", style)
    if (said.group(1) if said else "dark") != scheme:
        fail(f"{game}: club.json's scheme is {scheme} but club/style.css sets --scheme: {said.group(1) if said else '(nothing)'}")
    # A word game says what it is in its own link preview (club.json `og`); a squad's uses the shared line.
    og = {"description": OG_DESCRIPTION, "alt": f"{man['name']}: שלושה שחקנים על קלפי המשחק", **cfg.get("og", {})}
    slots = {
        "scheme": scheme, "status_bar": "black-translucent" if scheme == "dark" else "default",
        "theme_color": html.escape(man["theme_color"]), "short_name": html.escape(man["short_name"]),
        "name": html.escape(man["name"]), "style": style, "base": base,
        "url": html.escape(f"{SITE}{game}/"), "og_image": html.escape(f"{SITE}{game}/{OG_IMAGE}"),
        "og_description": html.escape(og["description"]), "og_alt": html.escape(og["alt"]),
        "title": title_html(man["name"], cfg.get("title", "plain")), "trophy": trophy_svg(cfg["trophy"]),
        "progress": "bar" if play_of(game)["progress"] == "bar" else "off", "ask": ASK[kind_of(game)],
        "data": data_line(game, read_roster(game)), "club": source(REPO / game / "club/club.js", "</script"),
        "engine": source(SHARED / "engine.js", "</script"),
    }
    page = re.sub(r"\{\{(\w+)\}\}", lambda m: slots[m.group(1)], read(SHARED / "page.template.html"))
    missing = [i for i in ENGINE_IDS if f'id="{i}"' not in page]
    if missing:
        fail(f"_memory-game/page.template.html lacks the elements the engine needs: {', '.join(missing)}")
    defined = set(re.findall(r"(--[\w-]+)\s*:", style + base))
    undefined = sorted(set(re.findall(r"var\(\s*(--[\w-]+)\s*\)", base)) - defined - RUNTIME_VARS)
    if undefined:
        fail(f"{game}: base.css reads tokens its club style never defines: {', '.join(undefined)}")
    return page


def lint_variables(game):
    """A club variable nobody reads (dead weight, or a typo in an optional token, which falls back silently),
    and a club read without a fallback that nothing defines."""
    style, club = read(REPO / game / "club/style.css"), read(REPO / game / "club/club.js")
    base, engine = read(SHARED / "base.css"), read(SHARED / "engine.js")
    js_set = set(re.findall(r"['`](--[\w-]+)['`]", club))  # setProperty('--x', …) and setVars keys
    engine_set = set(re.findall(r"setProperty\(\s*['`](--[\w-]+)['`]", engine))
    defined = set(re.findall(r"(--[\w-]+)\s*:", style))
    reads = set(re.findall(r"var\(\s*(--[\w-]+)", style + base + club + engine))
    nothing = (set(re.findall(r"var\(\s*(--[\w-]+)\s*\)", style + club)) - defined - js_set - engine_set
               - set(re.findall(r"(--[\w-]+)\s*:", base)))
    # A :root token resolves there, where the per-card variables the engine sets (RUNTIME_VARS) are unset,
    # and every card inherits that one value.
    root = "".join(re.findall(r":root\s*\{(.*?)\}", style, re.S))
    frozen = sorted(name for name, value in re.findall(r"(--[\w-]+)\s*:([^;]*)", root)
                    if any(re.search(rf"var\(\s*{re.escape(v)}\b", value) for v in RUNTIME_VARS))
    return ([f"{v} is set by the club but nothing reads it" for v in sorted((defined | js_set) - reads)]
            + [f"{v} is read by the club but nothing defines it" for v in sorted(nothing)]
            + [f"{v} is declared on :root but reads a per-card variable ({', '.join(sorted(RUNTIME_VARS))}): "
               "it never varies; declare it on the card" for v in frozen])


def app_id(game):
    """The installed app's id, per the manifest spec: `id` resolved against start_url's origin."""
    man = manifest(game)
    origin = "https://origin.invalid/"
    start = urljoin(f"{origin}pages/{game}/manifest.webmanifest", man.get("start_url", "./"))
    return urljoin(origin, man["id"]) if "id" in man else start.split("#")[0]


def check_apps(all_games):
    ids = {}
    for game in all_games:
        if not (REPO / game / "manifest.webmanifest").is_file():
            continue  # it can't be installed, so it can't collide; its own assemble names what's missing
        aid = app_id(game)
        if aid == "https://origin.invalid/" and game not in ROOT_ID_GAMES:
            fail(f"{game}/manifest.webmanifest: its id resolves to the origin root, so it would install as the "
                 "same app as maccabi-memory; give it its own id")
        if aid in ids:
            fail(f"{game} and {ids[aid]} resolve to the same app id {aid}")
        ids[aid] = game


def check_prefixes(all_games):
    for a in all_games:
        for b in all_games:
            if a != b and f"{b}-".startswith(f"{a}-"):
                fail(f"cache prefix {a}- also matches {b}- caches, so {a}'s cleanup would delete them")


def assemble(game, check):
    page = REPO / game
    template = read(SHARED / "sw.template.js")
    index, sw = page / "index.html", page / "sw.js"
    old_html = index.read_text(encoding="utf-8") if index.exists() else ""
    html_ = render(game)

    prefix = f"{game}-"
    old_sw = sw.read_text(encoding="utf-8") if sw.exists() else ""
    old_version = re.search(r"^const VERSION = '([^']*)';$", old_sw, flags=re.M)
    if old_sw and not (old_version and old_version.group(1).startswith(prefix)):
        fail(f"{game}/sw.js: its VERSION does not start with {prefix}; the cache prefix must stay the folder name")

    files = sorted(f for d in PRECACHE_DIRS if (page / d).is_dir()
                   for f in (page / d).rglob("*") if f.is_file() and f.suffix in PRECACHE_SUFFIXES)
    # play.precache "core": the page, fonts, icons, the start/win clips and the first `items` items' pictures
    # and clips; the worker keeps every other picture and clip as the page fetches it (RUNTIME).
    precache = play_of(game)["precache"]
    if precache["policy"] == "core":
        core = {p["id"] for p in items_of(read_roster(game))[:precache["items"]]}
        later = [f for f in files if f.parts[len(page.parts)] in ("img", "audio") and f.parent.name != "ui"
                 and f.stem not in core]
        files = [f for f in files if f not in later]
    else:
        later = []
    assets = ["./", "index.html", "manifest.webmanifest", *(f.relative_to(page).as_posix() for f in files)]
    digest = hashlib.sha256()
    for rel in assets[1:]:
        path = page / rel
        if rel != "index.html" and not path.is_file():
            fail(f"{game}: precache entry {rel} does not exist")
        digest.update(rel.encode())
        digest.update(html_.encode() if rel == "index.html" else path.read_bytes())
    # Each kept file's content hash: the worker keys its copy by it (sw.template.js RUNTIME_FILES).
    kept = {f.relative_to(page).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()[:12] for f in later}
    digest.update(json.dumps(kept, sort_keys=True).encode() if kept else b"")
    digest.update(b"sw.template.js")
    digest.update(template.encode())
    version = f"{prefix}{digest.hexdigest()[:12]}"
    runtime = f"{prefix}runtime" if kept else ""

    new_sw = template
    for pattern, value, flags in (
            (r"^const VERSION = .*;$", f"const VERSION = '{version}';", re.M),
            (r"^const ASSETS = .*?;$", "const ASSETS = " + json.dumps(assets, indent=2).replace('"', "'") + ";", re.M | re.S),
            (r"^const PREFIX = .*;$", f"const PREFIX = '{prefix}';", re.M),
            (r"^const RUNTIME = .*;$", f"const RUNTIME = '{runtime}';", re.M),
            (r"^const RUNTIME_FILES = .*?;$", "const RUNTIME_FILES = " + (json.dumps(kept, indent=0, sort_keys=True)
             .replace('"', "'") if kept else "{}") + ";", re.M | re.S)):
        new_sw, n = re.subn(pattern, lambda m, v=value: v, new_sw, count=1, flags=flags)
        if n != 1:
            fail(f"_memory-game/sw.template.js is missing its {pattern.split()[1]} line")

    stale = [p.name for p, old, new in ((index, old_html, html_), (sw, old_sw, new_sw)) if old != new]
    strays = orphans(game, read_roster(game))
    for rel in strays:
        print(f"{game}: {rel} is not in the roster but would be precached (data --prune removes it)", flush=True)
    lint = (lint_credits(game) + check_ui_clips(game) + lint_variables(game) + check_og(game) + check_apart(game)
            + check_takes(game))
    for msg in lint:
        print(f"{game}: {msg}", flush=True)
    if check:
        print(f"{game}: {'out of date: ' + ', '.join(stale) if stale else 'up to date'} ({version})", flush=True)
        return not stale and not strays and not lint
    index.write_text(html_, encoding="utf-8")
    sw.write_text(new_sw, encoding="utf-8")
    total = sum(f.stat().st_size for f in files) + len(html_.encode())
    print(f"{game}: {len(assets)} precached, {total / 1024:.0f} KB, version {version}"
          + (f"; {len(later)} more kept as they come, {sum(f.stat().st_size for f in later) / 1024:.0f} KB" if later else "")
          + f"{'' if stale else ' (unchanged)'}", flush=True)
    return True


def listing(all_games):
    out = []
    for game in all_games:
        sw = REPO / game / "sw.js"
        version = re.search(r"^const VERSION = '([^']*)';$", sw.read_text(encoding="utf-8"), flags=re.M) if sw.is_file() else None
        cfg = config(game)
        installable = (REPO / game / "manifest.webmanifest").is_file()
        out.append({"id": game, "prefix": f"{game}-", "version": version and version.group(1),
                    "app_id": app_id(game).removeprefix("https://origin.invalid") if installable else None,
                    "kind": cfg.get("kind", "squad"), "names": cfg.get("names")})
    return out


def new_game(game, like, name, short, color, description):
    if not ID_RE.match(game):
        fail(f"{game!r} is not a usable folder name (lowercase letters, digits and dashes)")
    if (REPO / game).exists():
        fail(f"{game} already exists")
    like = games([like])[0]
    check_prefixes(games() + [game])
    taken = {app_id(g): g for g in games() if (REPO / g / "manifest.webmanifest").is_file()}
    if urljoin("https://origin.invalid/", game) in taken:
        fail(f"{game}'s app id is already {taken[urljoin('https://origin.invalid/', game)]}'s")
    if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
        fail(f"--color wants #rrggbb, not {color!r}")
    description = description or f"משחק זיכרון עם שחקני {name.removeprefix('זיכרון ').strip()}"
    text = read(REPO / like / "manifest.webmanifest")
    for key, value in (("name", name), ("short_name", short), ("description", description), ("id", game),
                       ("background_color", color), ("theme_color", color)):
        text, n = re.subn(rf'^(  "{key}": ).*?(,?)$', lambda m, v=value: m.group(1) + json.dumps(v, ensure_ascii=False)
                          + m.group(2), text, count=1, flags=re.M)
        if n != 1:
            fail(f"{like}/manifest.webmanifest has no \"{key}\" line to start from")
    json.loads(text)
    tmp = REPO / f".new-{game}"
    shutil.rmtree(tmp, ignore_errors=True)
    for d in ("club", "tools/page/icons", "tools/tts", "audio/ui"):
        (tmp / d).mkdir(parents=True)
    (tmp / "manifest.webmanifest").write_text(text, encoding="utf-8")
    for f in ("club.json", "style.css", "club.js"):
        shutil.copyfile(REPO / like / "club" / f, tmp / "club" / f)
    for svg in (REPO / like / "tools/page/icons").glob("*.svg"):
        shutil.copyfile(svg, tmp / "tools/page/icons" / svg.name)
    if (REPO / like / "fonts").is_dir():
        shutil.copytree(REPO / like / "fonts", tmp / "fonts")
    for clip in UI_CLIPS:
        shutil.copyfile(SHARED / "audio/ui" / f"{clip}.mp3", tmp / "audio/ui" / f"{clip}.mp3")
    (tmp / "tools/tts/pronunciations.json").write_text('{\n  "players": {}\n}\n', encoding="utf-8")
    for template, dest in (("CREDITS.md", "CREDITS.md"), ("README.md", "tools/README.md")):
        body = read(SHARED / "new" / template).replace("{name}", name).replace("{game}", game)
        (tmp / dest).write_text(body, encoding="utf-8")
    tmp.rename(REPO / game)
    print(f"""{game}: started from {like} (manifest, club/, fonts/, icon designs, start/win clips, CREDITS.md and
tools/README.md with TODOs). Next:
  1. design: club/style.css, club/club.js and club/club.json (title, trophy, images), the icon SVGs, the fonts
     (and CREDITS.md); try it with stand-in data in a scratch folder: build_page.py assemble {game} --watch --repo <scratch>
  2. the club's scraper in {game}/tools/scrape/ writes <work>/data/players.json
  3. _memory-game/tools/refresh.sh {game} <work>: photos, voice, the page, then the link preview (look at {game}/og.jpg)
  4. bash _memory-game/tools/icons/render_icons.sh --game {game}
  5. _memory-game/tools/verify/verify.sh local --out <dir> {game}, then commit with explicit paths""", flush=True)


def watch(names):
    """Assemble `names` again whenever a source changes (Ctrl-C stops)."""
    def stamp():
        paths = [SHARED / f for f in ("base.css", "engine.js", "page.template.html", "sw.template.js")]
        for g in names:
            paths += [REPO / g / "manifest.webmanifest", *(REPO / g / "club").glob("*")]
            paths += [f for d in PRECACHE_DIRS for f in (REPO / g / d).rglob("*")]
        return sorted((str(p), p.stat().st_mtime_ns) for p in paths if p.is_file())
    seen = None
    print(f"watching {', '.join(names)} (Ctrl-C stops)", flush=True)
    while True:
        now = stamp()
        if now != seen:
            for g in names:
                try:
                    assemble(g, check=False)
                except SystemExit as e:
                    print(e, flush=True)
            seen = stamp()
        time.sleep(0.5)


def main():
    global REPO
    ap = argparse.ArgumentParser(description="Build the memory games (see the module docstring).")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--repo", type=Path, help="the folder that holds the games (default: this checkout)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("data", parents=[common], help="write a game's club/roster.json from players.json, then assemble it")
    d.add_argument("players_json")
    d.add_argument("game")
    d.add_argument("--prune", action="store_true", help="delete photos and clips of players not in the roster")
    a = sub.add_parser("assemble", parents=[common], help="write each game's index.html and sw.js")
    a.add_argument("--check", action="store_true", help="write nothing; fail if anything is out of date")
    a.add_argument("--watch", action="store_true", help="assemble the named games again on every change")
    a.add_argument("games", nargs="*")
    li = sub.add_parser("list", parents=[common], help="print the games, one per line (the one place that lists them)")
    li.add_argument("--json", action="store_true", help="id, cache prefix, VERSION, app id and name model")
    n = sub.add_parser("new", parents=[common], help="start a club's game from another club's")
    n.add_argument("game")
    n.add_argument("--like", required=True, help="the club whose design, fonts and tools start it")
    n.add_argument("--name", required=True, help="the manifest name, e.g. \"זיכרון הפועל תל אביב\"")
    n.add_argument("--short", required=True, help="the home-screen name, e.g. \"זיכרון הפועל\"")
    n.add_argument("--color", required=True, help="theme and background colour, #rrggbb")
    n.add_argument("--description", help="default: \"משחק זיכרון עם שחקני <the name without זיכרון>\"")
    args = ap.parse_args()
    if args.repo:
        REPO = args.repo.expanduser().resolve()

    all_games = games()
    check_prefixes(all_games)
    check_apps(all_games)
    if args.cmd == "new":
        new_game(args.game, args.like, args.name, args.short, args.color, args.description)
        return
    if args.cmd == "list":
        rows = listing(all_games)
        print(json.dumps(rows, ensure_ascii=False, indent=2) if args.json else "\n".join(r["id"] for r in rows))
        return
    if args.cmd == "data":
        game = games([args.game])[0]
        write_data(args.players_json, game, args.prune)
        assemble(game, check=False)
        return
    if getattr(args, "watch", False):
        if not args.games or args.check:
            ap.error("--watch needs the games to assemble, and no --check")
        watch(games(args.games))
    ok = []
    for g in games(args.games):
        if not args.games and not args.check and not has_roster(g):
            print(f"{g}: skipped, no club/roster.json yet (`data` makes the page)", flush=True)
            continue
        ok.append(assemble(g, args.check))
    if not all(ok):
        sys.exit("build_page: fix what is listed above, run `build_page.py assemble`, then commit the result")


if __name__ == "__main__":
    main()
