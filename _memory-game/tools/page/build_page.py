#!/usr/bin/env python3
"""Build the memory games from _memory-game/ and each game's roster.

    python3 -I _memory-game/tools/page/build_page.py data <players.json> <game> [--prune]
    python3 -I _memory-game/tools/page/build_page.py assemble [--check] [<game> ...]
    python3 -I _memory-game/tools/page/build_page.py list [--json]

A game is a folder at the repo root whose index.html has an engine script (<script id="engine">);
nothing else in the repo is read or written. In each game:

  index.html  <style id="base">     _memory-game/base.css, stamped in
              <script id="data">    club/roster.json plus the clips that exist under audio/, stamped in
              <script id="engine">  _memory-game/engine.js, stamped in
  sw.js       _memory-game/sw.template.js with VERSION, ASSETS and PREFIX filled in. VERSION hashes
              every precached file and the template, so any change installs a fresh cache.

`data` writes club/roster.json from players.json (one player per line), then assembles that game;
--prune deletes photos and clips of players who are no longer in it. The club's name model comes from
<game>/club/club.json: {"names": "full"} keeps name_he only; {"names": "first-last"} adds the
card's two tiers (first_he / last_he) and speak_he, the text the voice reads.
`assemble` stamps the shared code and the roster into the pages and writes each sw.js; with no games it
does every game. `--check` writes nothing and fails if a page or sw.js is not what assemble would write,
or if img/ or audio/ holds a player the roster doesn't (every file there is precached). Run it before
committing: the repo has no CI. Manifests are only read, never written.
"""
import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from urllib.parse import urljoin

sys.dont_write_bytecode = True  # no __pycache__ in the repo
SHARED = Path(__file__).resolve().parents[2]
REPO = SHARED.parent
sys.path.insert(0, str(SHARED / "tools/tts"))
from hebrew import speak_text, split_display_name  # noqa: E402

ID_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
PRECACHE_DIRS = ("fonts", "img", "audio", "icons")
PRECACHE_SUFFIXES = {".woff2", ".webp", ".png", ".mp3"}
UI_CLIPS = ("start", "win")
MARKER = '<script id="engine">'
# Element ids the engine looks up, and the CSS variables base.css reads that the engine sets itself.
ENGINE_IDS = ("app", "board", "pips", "start", "confirm", "win", "fan", "play", "replay", "again", "yes", "no",
              "mute", "confetti", "install")
RUNTIME_VARS = {"--i"}
# Tel Aviv's manifest id "./" resolves to the origin root. It shipped that way and changing it would
# break installed copies, so it is the only game allowed a root id.
ROOT_ID_GAMES = {"maccabi-memory"}


def fail(msg):
    sys.exit(f"build_page: {msg}")


def clean(text):
    return " ".join(str(text or "").split())


def games(names=None):
    found = sorted(d.name for d in REPO.iterdir() if (d / "index.html").is_file()
                   and MARKER in (d / "index.html").read_text(encoding="utf-8"))
    for name in names or []:
        if name.rstrip("/") not in found:
            fail(f"{name} is not a game (no {MARKER} in its index.html)")
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
    if model == "full":
        return {"id": pid, "name_he": name, "number": number, "role": p["role"], "img": img}
    return {"id": pid, "name_he": name, "first_he": first, "last_he": last, "speak_he": speak,
            "number": number, "role": p["role"], "img": img}


def roster_text(roster):
    """club/roster.json: one player per line, so a roster refresh diffs per player."""
    def rows(players):
        return ",\n".join("    " + json.dumps(p, ensure_ascii=False, separators=(", ", ": ")) for p in players)
    return (f'{{\n  "season": {json.dumps(roster["season"], ensure_ascii=False)},\n'
            f'  "starters": [\n{rows(roster["starters"])}\n  ],\n  "bench": [\n{rows(roster["bench"])}\n  ]\n}}\n')


def read_roster(game):
    path = REPO / game / "club/roster.json"
    if not path.is_file():
        fail(f"{game}: no club/roster.json (run `build_page.py data <players.json> {game}`)")
    return json.loads(path.read_text(encoding="utf-8"))


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
    config = json.loads((page / "club/club.json").read_text(encoding="utf-8"))
    model = config.get("names")
    if model not in ("full", "first-last"):
        fail(f"{game}/club/club.json: names must be \"full\" or \"first-last\", not {model!r}")
    data = json.loads(Path(players_json).read_text(encoding="utf-8"))
    starters = [entry(p, page, model) for p in data["players"] if p.get("role") == "starter"]
    bench = [entry(p, page, model) for p in data["players"] if p.get("role") == "bench"]
    if len(starters) != 11:
        fail(f"expected 11 starters, found {len(starters)}")
    if len(bench) < 4:
        fail(f"need at least 4 bench players, found {len(bench)}")
    roster = {"season": data.get("season"), "starters": starters, "bench": bench}
    (page / "club").mkdir(exist_ok=True)
    (page / "club/roster.json").write_text(roster_text(roster), encoding="utf-8")
    print(f"{game}: club/roster.json: starters={len(starters)} bench={len(bench)}", flush=True)
    for rel in orphans(game, roster):
        if prune:
            (page / rel).unlink()
        print(f"{game}: {'removed' if prune else 'not in the roster (data --prune removes it)'}: {rel}", flush=True)


def shared(name, closer):
    text = (SHARED / name).read_text(encoding="utf-8")
    if closer in text.lower():
        fail(f"_memory-game/{name} must not contain {closer}")
    if not text.endswith("\n"):
        fail(f"_memory-game/{name} must end with a newline")
    return text


def stamp(html, opener, closer, text, game):
    out, n = re.subn(f"({re.escape(opener)}\n).*?({re.escape(closer)})", lambda m: m.group(1) + text + m.group(2),
                     html, count=1, flags=re.S)
    if n != 1:
        fail(f"{game}/index.html has no {opener} block")
    return out


def check_page(html, base, game):
    order = [html.find(f'<script id="{s}">') for s in ("data", "club", "engine")]
    if min(order) < 0 or order != sorted(order):
        fail(f"{game}/index.html needs <script id=\"data\">, then \"club\", then \"engine\"")
    missing = [i for i in ENGINE_IDS if f'id="{i}"' not in html]
    if missing:
        fail(f"{game}/index.html lacks the elements the engine needs: {', '.join(missing)}")
    styles = "".join(re.findall(r"<style>\n(.*?)</style>", html, flags=re.S))
    defined = set(re.findall(r"(--[\w-]+)\s*:", styles + base))
    undefined = sorted(set(re.findall(r"var\((--[\w-]+)", base)) - defined - RUNTIME_VARS)
    if undefined:
        fail(f"{game}: base.css reads tokens its club style never defines: {', '.join(undefined)}")


def app_id(game):
    """The installed app's id, per the manifest spec: `id` resolved against start_url's origin."""
    man = json.loads((REPO / game / "manifest.webmanifest").read_text(encoding="utf-8"))
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
    base, engine = shared("base.css", "</style"), shared("engine.js", "</script")
    template = (SHARED / "sw.template.js").read_text(encoding="utf-8")
    index, sw = page / "index.html", page / "sw.js"
    old_html = index.read_text(encoding="utf-8")
    roster = read_roster(game)
    html = stamp(stamp(stamp(old_html, '<style id="base">', "</style>", base, game),
                       '<script id="data">', "</script>", data_line(game, roster) + "\n", game),
                 '<script id="engine">', "</script>", engine, game)
    check_page(html, base, game)
    strays = orphans(game, roster)

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
        if not path.is_file():
            fail(f"{game}: precache entry {rel} does not exist")
        digest.update(rel.encode())
        digest.update(html.encode() if rel == "index.html" else path.read_bytes())
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

    stale = [p.name for p, old, new in ((index, old_html, html), (sw, old_sw, new_sw)) if old != new]
    for rel in strays:
        print(f"{game}: {rel} is not in the roster but would be precached (data --prune removes it)", flush=True)
    if check:
        print(f"{game}: {'out of date: ' + ', '.join(stale) if stale else 'up to date'} ({version})", flush=True)
        return not stale and not strays
    index.write_text(html, encoding="utf-8")
    sw.write_text(new_sw, encoding="utf-8")
    total = sum(f.stat().st_size for f in files) + len(html.encode())
    print(f"{game}: {len(assets)} precached, {total / 1024:.0f} KB, version {version}"
          f"{'' if stale else ' (unchanged)'}", flush=True)
    return True


def listing(all_games):
    out = []
    for game in all_games:
        sw = REPO / game / "sw.js"
        version = re.search(r"^const VERSION = '([^']*)';$", sw.read_text(encoding="utf-8"), flags=re.M) if sw.is_file() else None
        names = json.loads((REPO / game / "club/club.json").read_text(encoding="utf-8")).get("names")
        installable = (REPO / game / "manifest.webmanifest").is_file()
        out.append({"id": game, "prefix": f"{game}-", "version": version and version.group(1),
                    "app_id": app_id(game).removeprefix("https://origin.invalid") if installable else None,
                    "names": names})
    return out


def main():
    ap = argparse.ArgumentParser(description="Build the memory games (see the module docstring).")
    sub = ap.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("data", help="write a game's club/roster.json from players.json, then assemble it")
    d.add_argument("players_json")
    d.add_argument("game")
    d.add_argument("--prune", action="store_true", help="delete photos and clips of players not in the roster")
    a = sub.add_parser("assemble", help="stamp the shared code into the pages and write each sw.js")
    a.add_argument("--check", action="store_true", help="write nothing; fail if anything is out of date")
    a.add_argument("games", nargs="*")
    li = sub.add_parser("list", help="print the games, one per line (the one place that lists them)")
    li.add_argument("--json", action="store_true", help="id, cache prefix, VERSION, app id and name model")
    args = ap.parse_args()

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
    ok = [assemble(g, args.check) for g in games(args.games)]
    if not all(ok):
        sys.exit("build_page: run `build_page.py assemble` and commit the result")


if __name__ == "__main__":
    main()
