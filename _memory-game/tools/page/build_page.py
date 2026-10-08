#!/usr/bin/env python3
"""Build the memory games from _memory-game/ and each game's club sources.

    python3 -I _memory-game/tools/page/build_page.py data <players.json> <game> [--prune]
    python3 -I _memory-game/tools/page/build_page.py assemble [--check] [<game> ...] [--watch]
    python3 -I _memory-game/tools/page/build_page.py list [--json]
Every command takes --repo <dir>: build the games in another folder (a scratch copy, to try a design
with stand-in data before the real roster exists) with this checkout's _memory-game/.

A game is a folder at the repo root with club/club.json. Its sources, all hand-owned except the roster:

  manifest.webmanifest  the club's identity; its name, short_name and theme_color fill the page's head and
                        title. Read, never written.
  club/club.json        {"names": "full"|"first-last", "title": "plain"|"tiers",
                         "trophy": {"cup", "stem", "star", "shine", "shine_opacity"?, "shade"?}, "images": {...}}
  club/style.css        the club's style: fonts, tokens, card back, card face, title
  club/club.js          const CLUB = { confetti, fonts, face(kit) }
  club/roster.json      season, starters and bench; written by `data`

The builder writes two files per game, whole:

  index.html  _memory-game/page.template.html filled in: the head, the club style, base.css, the title, the
              trophy, DATA (the roster plus the clips that exist under audio/, in roster order), the club
              script and engine.js
  sw.js       _memory-game/sw.template.js with VERSION, ASSETS and PREFIX filled in. VERSION hashes every
              precached file and the template, so any change installs a fresh cache.

`data` writes club/roster.json from players.json (one player per line), then assembles that game; --prune
deletes photos and clips of players who are no longer in it. The name model (club.json `names`): "full"
shows name_he on one card line; "first-last" adds the card's two tiers (first_he / last_he). speak_he, the
text the voice reads, ships whenever it differs from name_he (and always with "first-last").
`assemble` writes every game's index.html and sw.js, or the named games'. `--check` writes nothing and fails
if a page or sw.js is not what assemble would write, or if img/ or audio/ holds a player the roster
doesn't (every file there is precached). Run it before committing: the repo has no CI. `--watch`
assembles the named games again whenever one of their sources or a shared file changes.
"""
import argparse
import hashlib
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

sys.dont_write_bytecode = True  # no __pycache__ in the repo
SHARED = Path(__file__).resolve().parents[2]
REPO = SHARED.parent
sys.path.insert(0, str(SHARED / "tools/tts"))
from hebrew import speak_text, split_display_name  # noqa: E402

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CONFIG = "club/club.json"
PRECACHE_DIRS = ("fonts", "img", "audio", "icons")
PRECACHE_SUFFIXES = {".woff2", ".webp", ".png", ".mp3"}
UI_CLIPS = ("start", "win")
# Element ids the engine looks up, and the CSS variables base.css reads that the engine sets itself.
ENGINE_IDS = ("app", "board", "pips", "start", "confirm", "win", "fan", "play", "replay", "again", "yes", "no",
              "mute", "confetti", "install")
RUNTIME_VARS = {"--i"}
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
    def rows(players):
        return ",\n".join("    " + json.dumps(p, ensure_ascii=False, separators=(", ", ": ")) for p in players)
    return (f'{{\n  "season": {json.dumps(roster["season"], ensure_ascii=False)},\n'
            f'  "starters": [\n{rows(roster["starters"])}\n  ],\n  "bench": [\n{rows(roster["bench"])}\n  ]\n}}\n')


def has_roster(game):
    return (REPO / game / "club/roster.json").is_file()


def read_roster(game):
    return json.loads(read(REPO / game / "club/roster.json", f"run `build_page.py data <players.json> {game}`"))


def orphans(game, roster):
    """Photos and clips of players the roster doesn't have: precached, never shown or played."""
    page = REPO / game
    ids = {p["id"] for p in roster["starters"] + roster["bench"]}
    return sorted(f.relative_to(page).as_posix() for d, suffix in (("img", ".webp"), ("audio/name", ".mp3"),
                                                                    ("audio/match", ".mp3"))
                  for f in (page / d).glob(f"*{suffix}") if f.stem not in ids)


def data_line(game, roster):
    """The DATA script: the roster plus the clips that exist, in roster order."""
    page = REPO / game
    ids = [p["id"] for p in roster["starters"] + roster["bench"]]
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
    starters = [entry(p, page, model) for p in data["players"] if p.get("role") == "starter"]
    bench = [entry(p, page, model) for p in data["players"] if p.get("role") == "bench"]
    if len(starters) != 11:
        fail(f"expected 11 starters, found {len(starters)}")
    if len(bench) < 4:
        fail(f"need at least 4 bench players, found {len(bench)}")
    roster = {"season": data.get("season"), "starters": starters, "bench": bench}
    (page / "club/roster.json").write_text(roster_text(roster), encoding="utf-8")
    print(f"{game}: club/roster.json: starters={len(starters)} bench={len(bench)}", flush=True)
    for rel in orphans(game, roster):
        if prune:
            (page / rel).unlink()
        print(f"{game}: {'removed' if prune else 'not in the roster (data --prune removes it)'}: {rel}", flush=True)


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
    slots = {
        "theme_color": html.escape(man["theme_color"]), "short_name": html.escape(man["short_name"]),
        "name": html.escape(man["name"]), "style": style, "base": base,
        "title": title_html(man["name"], config.get("title", "plain")), "trophy": trophy_svg(config["trophy"]),
        "data": data_line(game, read_roster(game)), "club": source(REPO / game / "club/club.js", "</script"),
        "engine": source(SHARED / "engine.js", "</script"),
    }
    page = re.sub(r"\{\{(\w+)\}\}", lambda m: slots[m.group(1)], read(SHARED / "page.template.html"))
    missing = [i for i in ENGINE_IDS if f'id="{i}"' not in page]
    if missing:
        fail(f"_memory-game/page.template.html lacks the elements the engine needs: {', '.join(missing)}")
    defined = set(re.findall(r"(--[\w-]+)\s*:", style + base))
    undefined = sorted(set(re.findall(r"var\((--[\w-]+)", base)) - defined - RUNTIME_VARS)
    if undefined:
        fail(f"{game}: base.css reads tokens its club style never defines: {', '.join(undefined)}")
    return page


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
    if check:
        print(f"{game}: {'out of date: ' + ', '.join(stale) if stale else 'up to date'} ({version})", flush=True)
        return not stale and not strays
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
    args = ap.parse_args()
    if args.repo:
        REPO = args.repo.expanduser().resolve()

    all_games = games()
    check_prefixes(all_games)
    check_apps(all_games)
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
        sys.exit("build_page: run `build_page.py assemble` and commit the result")


if __name__ == "__main__":
    main()
