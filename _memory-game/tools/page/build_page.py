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
PRECACHE_DIRS = ("fonts", "img", "audio", "icons")
PRECACHE_SUFFIXES = {".woff2", ".webp", ".png", ".mp3"}
UI_CLIPS = tuple(UI_TEXTS)
# Element ids the engine looks up, and the CSS variables base.css reads that the engine sets itself.
ENGINE_IDS = ("app", "board", "pips", "start", "confirm", "win", "fan", "play", "replay", "again", "yes", "no",
              "mute", "confetti", "install", "play-quiz", "replay-quiz", "yes-quiz", "picks", "question", "say")
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


def roster_text(roster):
    """club/roster.json: one player per line, so a roster refresh diffs per player."""
    rows = ",\n".join("    " + json.dumps(p, ensure_ascii=False, separators=(", ", ": ")) for p in roster["players"])
    return f'{{\n  "season": {json.dumps(roster["season"], ensure_ascii=False)},\n  "players": [\n{rows}\n  ]\n}}\n'


def has_roster(game):
    return (REPO / game / "club/roster.json").is_file()


def read_roster(game):
    return json.loads(read(REPO / game / "club/roster.json", f"run `build_page.py data <players.json> {game}`"))


def orphans(game, roster):
    """Photos and clips of players the roster doesn't have: precached, never shown or played."""
    page = REPO / game
    ids = {p["id"] for p in roster["players"]}
    return sorted(f.relative_to(page).as_posix() for d, suffix in (("img", ".webp"), ("audio/name", ".mp3"),
                                                                    ("audio/match", ".mp3"))
                  for f in (page / d).glob(f"*{suffix}") if f.stem not in ids)


def data_line(game, roster):
    """The DATA script: the roster plus the clips that exist, in roster order."""
    page = REPO / game
    ids = [p["id"] for p in roster["players"]]
    audio = {
        "ui": [k for k in UI_CLIPS if (page / "audio" / "ui" / f"{k}.mp3").is_file()],
        "name": [i for i in ids if (page / "audio" / "name" / f"{i}.mp3").is_file()],
        "match": [i for i in ids if (page / "audio" / "match" / f"{i}.mp3").is_file()],
    }
    payload = {**roster, "audio": audio}
    return "const DATA = " + json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + ";"


def write_data(players_json, game, prune):
    page = REPO / game
    model = json.loads(read(page / CONFIG)).get("names")
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
    for rel in orphans(game, roster):
        if prune:
            (page / rel).unlink()
        print(f"{game}: {'removed' if prune else 'not in the roster (data --prune removes it)'}: {rel}", flush=True)


def lint_credits(game):
    """The fonts the club style declares vs the files it ships vs what CREDITS.md credits."""
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
    voice = read(SHARED / "new/CREDITS.md").split("## Voice", 1)[1]
    return ([f"CREDITS.md: a TODO is left" for _ in [1] if "TODO" in credits]
            + [f"{f} is shipped but no @font-face uses it" for f in sorted(shipped - srcs)]
            + [f"an @font-face uses {f}, which isn't shipped" for f in sorted(srcs - shipped)]
            + [f"CREDITS.md doesn't credit the font {f}" for f in sorted(declared - credited)]
            + [f"CREDITS.md credits {f}, which no @font-face declares" for f in sorted(credited - declared)]
            + [f"CREDITS.md links {f}, which doesn't exist" for f in sorted(licences) if not (page / f).is_file()]
            + [f"CREDITS.md doesn't link fonts/{f.name}" for f in sorted((page / "fonts").glob("OFL-*.txt"))
               if f"fonts/{f.name}" not in licences]
            + ["CREDITS.md's Voice section differs from _memory-game/new/CREDITS.md's"
               for _ in [1] if credits.split("## Voice", 1)[-1] != voice])


def check_ui_clips(game):
    """Each game ships its own copy of the engine's start and win clips; the master is _memory-game/audio/ui/."""
    engine = read(SHARED / "engine.js")
    problems = []
    for key, text in UI_TEXTS.items():
        line = re.search(rf"const {key.upper()}_LINE = '([^']*)';", engine)
        if not line:
            problems.append(f"engine.js has no {key.upper()}_LINE, the {key} clip's text")
        elif line.group(1) != text:
            problems.append(f"engine.js's {key.upper()}_LINE is not hebrew.py's UI_TEXTS[{key!r}], which the clip says")
    for clip in UI_CLIPS:
        copy = REPO / game / "audio/ui" / f"{clip}.mp3"
        if not copy.is_file() or copy.read_bytes() != (SHARED / "audio/ui" / f"{clip}.mp3").read_bytes():
            problems.append(f"audio/ui/{clip}.mp3 is not _memory-game/audio/ui/{clip}.mp3")
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
    man, config = manifest(game), json.loads(read(REPO / game / CONFIG))
    base = source(SHARED / "base.css", "</style")
    style = source(REPO / game / "club/style.css", "</style")
    scheme = config.get("scheme", "dark")
    if scheme not in ("dark", "light"):
        fail(f"{game}/{CONFIG}: scheme must be \"dark\" or \"light\", not {scheme!r}")
    said = re.search(r"--scheme:\s*([\w-]+)", style)
    if (said.group(1) if said else "dark") != scheme:
        fail(f"{game}: club.json's scheme is {scheme} but club/style.css sets --scheme: {said.group(1) if said else '(nothing)'}")
    slots = {
        "scheme": scheme, "status_bar": "black-translucent" if scheme == "dark" else "default",
        "theme_color": html.escape(man["theme_color"]), "short_name": html.escape(man["short_name"]),
        "name": html.escape(man["name"]), "style": style, "base": base,
        "url": html.escape(f"{SITE}{game}/"), "og_image": html.escape(f"{SITE}{game}/{OG_IMAGE}"),
        "og_description": html.escape(OG_DESCRIPTION), "og_alt": html.escape(f"{man['name']}: שלושה שחקנים על קלפי המשחק"),
        "title": title_html(man["name"], config.get("title", "plain")), "trophy": trophy_svg(config["trophy"]),
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
    assets = ["./", "index.html", "manifest.webmanifest", *(f.relative_to(page).as_posix() for f in files)]
    digest = hashlib.sha256()
    for rel in assets[1:]:
        path = page / rel
        if rel != "index.html" and not path.is_file():
            fail(f"{game}: precache entry {rel} does not exist")
        digest.update(rel.encode())
        digest.update(html_.encode() if rel == "index.html" else path.read_bytes())
    digest.update(b"sw.template.js")
    digest.update(template.encode())
    version = f"{prefix}{digest.hexdigest()[:12]}"

    new_sw = template
    for pattern, value, flags in (
            (r"^const VERSION = .*;$", f"const VERSION = '{version}';", re.M),
            (r"^const ASSETS = .*?;$", "const ASSETS = " + json.dumps(assets, indent=2).replace('"', "'") + ";", re.M | re.S),
            (r"^const PREFIX = .*;$", f"const PREFIX = '{prefix}';", re.M)):
        new_sw, n = re.subn(pattern, lambda m, v=value: v, new_sw, count=1, flags=flags)
        if n != 1:
            fail(f"_memory-game/sw.template.js is missing its {pattern.split()[1]} line")

    stale = [p.name for p, old, new in ((index, old_html, html_), (sw, old_sw, new_sw)) if old != new]
    strays = orphans(game, read_roster(game))
    for rel in strays:
        print(f"{game}: {rel} is not in the roster but would be precached (data --prune removes it)", flush=True)
    lint = lint_credits(game) + check_ui_clips(game) + lint_variables(game) + check_og(game)
    for msg in lint:
        print(f"{game}: {msg}", flush=True)
    if check:
        print(f"{game}: {'out of date: ' + ', '.join(stale) if stale else 'up to date'} ({version})", flush=True)
        return not stale and not strays and not lint
    index.write_text(html_, encoding="utf-8")
    sw.write_text(new_sw, encoding="utf-8")
    total = sum(f.stat().st_size for f in files) + len(html_.encode())
    print(f"{game}: {len(assets)} precached, {total / 1024:.0f} KB, version {version}"
          f"{'' if stale else ' (unchanged)'}", flush=True)
    return True


def listing(all_games):
    out = []
    for game in all_games:
        sw = REPO / game / "sw.js"
        version = re.search(r"^const VERSION = '([^']*)';$", sw.read_text(encoding="utf-8"), flags=re.M) if sw.is_file() else None
        names = json.loads(read(REPO / game / CONFIG)).get("names")
        installable = (REPO / game / "manifest.webmanifest").is_file()
        out.append({"id": game, "prefix": f"{game}-", "version": version and version.group(1),
                    "app_id": app_id(game).removeprefix("https://origin.invalid") if installable else None,
                    "names": names})
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
