"""P9's verdict for each game, from what verify.sh local wrote into <out-dir>.

    python3 -I report.py <out-dir> <game>... [--worker-only]
    python3 -I report.py <out-dir> <game>... --sanity [--upgraded a,b --from <ref>]

Per game: the seeded shots at 600x960 and 960x600 (won, no failure, no 404, a clean console), the
audio playthrough (the right clip on every flip, the match's second clip after it, start and win, no
speech fallback), the quiz at both sizes (every player once, or a word game's learned words; four
distinct cards; a wrong pick that turns over to its face and says its line until the right pick cuts it
off; the clips in order, the reveal moving on by itself), the worker (controls the page, flips online
with their match clips, installability [], an offline reload keeps what she learned and plays the
memory game with every picture, the quiz with its clips and the next new flash card, everything the quiz
can ask cached, the link preview's tags and og.jpg as served) and the state machine. The clips are each
game's voice script (club.json play.voice). --sanity (verify.sh sanity) reads the worker, the quiz's first question
at 600x960, and, for the --upgraded games, sim.js --quick's verdict. Exits 1 if any game fails.
"""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ in the repo
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "page"))
from build_page import OG_IMAGE, OG_MAX_KB, SITE  # noqa: E402

OUT = Path(sys.argv[1])
# Playwright's own notices.
NOISE = ("Service Worker registration blocked by Playwright", "Banner not shown")


def load(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def console_clean(lines):
    return [m for m in lines if not any(n in m for n in NOISE) and not m.startswith(("log:", "info:", "debug:"))]


def first(label, found):
    """A check's label, naming the first thing that broke it and how many there were."""
    if not found:
        return label
    item = found[0] if isinstance(found[0], str) else json.dumps(found[0], ensure_ascii=False)
    return f"{label} (got {len(found)}: {item[:200]})"


def drive_checks(r, mode):
    if r is None:
        return {"ran": False}
    a = r["analysis"]
    checks = {first("ran", [r["failure"].splitlines()[0]] if r.get("failure") else []): not r.get("failure")}
    if mode != "first question":
        checks["won"] = bool(r.get("won"))
    dirty = console_clean(r["console"])
    checks.update({first("no 404", r["http"]): not r["http"], first("clean console", dirty): not dirty,
                   first("no errors", a["errors"]): not a["errors"], first("no speech fallback", a["speech"]): not a["speech"],
                   first("all fetches 200", a["fetchBad"]): not a["fetchBad"]})
    if mode == "shots":
        fan = r.get("fanNames") or []
        checks[f"start-screen name fits ({', '.join(n.get('text') or '?' for n in fan)})"] = len(fan) == 1 and all(
            n.get("inside") for n in fan)
    if mode == "audio":
        marks = [e for e in r["log"] if e["type"] == "mark" and e["label"].split(" ")[0] in ("flip", "hurry", "match")]
        checks.update({
            f"the right clip on every flip ({a['effectiveFlips']}/{len(marks)})": a["effectiveFlips"] == len(marks) and not a["badFlips"],
            f"the match's second clip after it ({a['matchesWithFollow']} of {a['matches']} let finish)": a["matchesWithFollow"] > 0,
            "start and win clips": a["startClip"] == 1 and a["winClip"] == 1,
        })
    if mode == "quiz":
        checks.update(quiz_checks(r))
    if mode == "first question":
        checks.update(quiz_checks(r, whole=False))
    return checks


def quiz_checks(r, whole=True):
    """The whole quiz, or (whole=False) its first question: asked with its question clip, a wrong pick, the right one.
    The pool is a squad's every player, or a word game's learned words."""
    q, qs = r.get("quiz") or {}, r.get("questions") or []
    one = qs[0] if qs else {}
    wrong = one.get("wrong") or {}
    checks = {}
    if whole:
        checks[f"every question once, from the pool ({len(qs)}/{r.get('total') or len(r.get('pool') or [])})"] = bool(
            q.get("everyPlayerOnce"))
    else:
        checks[f"asks {one.get('id')} with its question clip"] = bool(one.get("asked")) and bool(one.get("heard"))
    hud = one.get("hud") or {}
    checks[f"the mute button beside ↻ ({hud.get('muteToAgain')} px), away from the hear-it-again bubble "
           f"({hud.get('muteToSay')} px), which is no speaker and no circle ({hud.get('sayRadius')})"] = (
        bool(hud) and hud["muteToAgain"] <= hud["size"] * 1.5 and hud["muteToSay"] >= hud["saySize"] * 2.5
        and not hud["sayIsSpeaker"] and hud["sayRadius"] != "50%")
    checks.update({
        "4 distinct cards from the pool, the answer among them": bool(q.get("fourDistinct")),
        f"wrong pick turns to {wrong.get('id')}'s face, says its line, stays on the question":
            wrong.get("state") == "out" and wrong.get("turned") is True and wrong.get("shows") is True
            and wrong.get("phase") == "ask" and wrong.get("answer") == one.get("id") and bool(q.get("wrongTeaches")),
        "the right pick cuts off the wrong one's line": bool(q.get("wrongCut")),
    })
    if not whole:
        checks["the right pick says its line and reveals"] = bool(one.get("named")) and one.get("revealed") == "reveal"
        checks[first("clips: start, the question, the wrong one's line, the right one's",
                      [] if q.get("sequenceOk") else [" > ".join(q.get("sequence") or ["none"])])] = bool(q.get("sequenceOk"))
        return checks
    # The first three reveals move on by themselves, but the last question ends in the win screen.
    advancing = qs[:min(3, len(qs) - 1)]
    times = ", ".join(f"{x.get('advanceMs')} ms" for x in advancing)
    checks.update({
        "clips: start, each question's, the wrong one's line, the right one's, win":
            bool(q.get("sequenceOk")),
        f"the reveal moves on by itself ({times} after the pick)":
            bool(advancing) and all(x.get("auto") for x in advancing),
    })
    return checks


def og_checks(r):
    """The head's link-preview tags (absolute, under SITE) and the image they name, as the server serves it."""
    og = r.get("og") or {}
    tags, img = og.get("tags") or {}, og.get("image") or {}
    want = {"og:type": "website", "og:locale": "he_IL", "og:url": f"{SITE}{r['game']}/",
            "og:image": f"{SITE}{r['game']}/{OG_IMAGE}", "og:image:type": "image/jpeg",
            "twitter:card": "summary_large_image"}
    return {
        f"link preview tags (og:image {tags.get('og:image')})": all(tags.get(k) == v for k, v in want.items())
        and all(tags.get(k) for k in ("og:title", "og:description", "og:image:alt")),
        f"{OG_IMAGE} served: {img.get('width')}x{img.get('height')} {img.get('type')}, {(img.get('bytes') or 0) // 1024} KB, "
        f"the size the tags give":
            img.get("status") == 200 and img.get("type") == "image/jpeg" and 0 < img.get("bytes", 0) <= OG_MAX_KB * 1024
            and [str(img.get("width")), str(img.get("height"))] == [tags.get("og:image:width"), tags.get("og:image:height")],
    }


def sw_checks(r):
    if r is None:
        return {"ran": False}
    console = console_clean(r["console"])
    # A page error first: it is usually what broke the rest.
    dirty = [m for m in console if m.startswith("pageerror")] + r["http"] + [m for m in console if not m.startswith("pageerror")]
    if r.get("failure"):
        return {"worker controls the page": bool(r.get("controlled")), first("ran to the end", [r["failure"]]): False,
                first("no 404, clean console", dirty): not dirty}
    on, off = r["online"]["audio"], r["offline"]["audio"]
    imgs = r["offline"]["imgs"]
    cache = r["offline"].get("quizCache") or {}
    kept = r["offline"].get("learned") or {}
    before, after = (kept.get("before") or {}).get("ids") or [], (kept.get("after") or {}).get("ids") or []
    bar = (kept.get("after") or {}).get("bar")
    card = r["offline"].get("card") or {}
    return {
        "worker controls the page": bool(r["controlled"]),
        first("installability []", (r["installability"] or []) + (r["manifestErrors"] or [])):
            r["installability"] == [] and not r["manifestErrors"],
        first(f"online flips say their clip ({on['rightNameClip']}/{on['of']})", on["bad"]):
            on["rightNameClip"] == on["of"] > 0 and not on["errors"] and not on["fetchBad"],
        f"online matches say the second clip ({on['matchFollows']}/{on['matches']})": on["matchFollows"] > 0,
        "offline reload controlled": bool(r["offline"]["state"]["controlled"]),
        f"what she learned survives the offline reload ({len(after)}, bar {bar})":
            len(before) >= 3 and sorted(after) == sorted(before) and bar == f"{len(after)} / {(kept.get('after') or {}).get('of')}",
        f"offline pictures ({imgs[1]}/{imgs[0]})": imgs[0] > 0 and imgs[0] == imgs[1],
        first(f"offline flips say their clip ({off['rightNameClip']}/{off['of']})", off["bad"]):
            off["rightNameClip"] == off["of"] > 0 and not off["errors"] and not off["fetchBad"],
        f"offline quiz: start + its question, {(r['offline'].get('quiz') or {}).get('imgs')} pictures":
            bool((r["offline"].get("quiz") or {}).get("ok")),
        first(f"cached: everything the quiz can ask ({cache.get('checked')})", cache.get("missing") or []):
            cache.get("missing") == [],
        first(f"offline flash card: the next new one ({card.get('id')}) turns up, says its line, is learned",
              [] if card.get("ok") else [json.dumps({k: card.get(k) for k in ("state", "phase", "picture", "tile", "clips")})]):
            bool(card.get("ok")),
        **og_checks(r),
        first("no 404, clean console", dirty): not dirty,
    }


def upgrade_checks(r, game, ref):
    """sim.js's verdict for one game: its old version installed from <ref>, this tree's taking over online, then offline."""
    if r is None:
        return {"ran": False}
    v = r.get("versions") or {}
    old, new = ((v.get(t) or {}).get(game, {}).get("version") for t in ("old", "new"))
    verdict = r.get(f"{game}:verdict") or "no verdict"
    return {f"{ref} {old} -> {new}: {verdict}": verdict == "PASS"}


def option(name):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else ""


worker_only = "--worker-only" in sys.argv
sanity = "--sanity" in sys.argv
upgraded, ref = [g for g in option("--upgraded").split(",") if g], option("--from")
values = {option("--upgraded"), ref}
failed = []
for game in [a for a in sys.argv[2:] if not a.startswith("--") and a not in values]:
    sections = {"worker": sw_checks(load(OUT / f"sw-{game}.json"))}
    states_path = OUT / f"states-{game}.txt"
    states = states_path.read_text(encoding="utf-8").strip().splitlines() if states_path.exists() else []
    failing = [s for s in states if s.startswith("FAIL")]
    machine = {first(states[-1] if states else "ran", failing): bool(states) and " 0 fail" in states[-1]}
    if sanity:
        sections["quiz 600x960, first question"] = drive_checks(load(OUT / game / "tab-portrait-quiz/result.json"),
                                                               "first question")
        if states_path.exists():  # not on the live site
            sections["state machine"] = machine
        if game in upgraded:
            sections["upgrade"] = upgrade_checks(load(OUT / "upgrade" / game / "result.json"), game, ref)
    elif not worker_only:
        sections["shots 600x960"] = drive_checks(load(OUT / game / "tab-portrait-shots/result.json"), "shots")
        sections["shots 960x600"] = drive_checks(load(OUT / game / "tab-landscape-shots/result.json"), "shots")
        sections["audio 600x960"] = drive_checks(load(OUT / game / "tab-portrait-audio/result.json"), "audio")
        sections["quiz 600x960"] = drive_checks(load(OUT / game / "tab-portrait-quiz/result.json"), "quiz")
        sections["quiz 960x600"] = drive_checks(load(OUT / game / "tab-landscape-quiz/result.json"), "quiz")
        sections["state machine"] = machine
    bad = [f"{s}: {c}" for s, checks in sections.items() for c, ok in checks.items() if not ok]
    for s, checks in sections.items():
        print(f"{game} {s}: {'PASS' if all(checks.values()) else 'FAIL'} ({'; '.join(checks)})")
    kind = "sanity" if sanity else "worker" if worker_only else "local"
    print(f"{'' if sanity else 'P9 '}{kind} {game}: {'PASS' if not bad else 'FAIL: ' + ' | '.join(bad)}", flush=True)
    if bad:
        failed.append(game)
sys.exit(1 if failed else 0)
