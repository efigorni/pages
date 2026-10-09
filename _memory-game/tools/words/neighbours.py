#!/usr/bin/env python3
"""A word game's sound-alikes: the words its quiz never offers as a wrong answer to one another.

    uv run --quiet --with cmudict==1.1.3 python -I _memory-game/tools/words/neighbours.py <game> [--show <id>...]

Reads <game>/club/roster.json and writes <game>/club/avoid.json, one line per word: {id: {other id: why}}.
build_page.py checks it (every word on the roster has its line, every id is on it, each pair both ways) and
puts each word's list in DATA as its `avoid`, with club.json play.quiz.apart's look-alike pictures, and the
engine never deals an avoided word as one of the other three cards. Run it after every change to the words.

Two words sound alike (the pronunciations of CMUdict, every variant of every word in a multi-word name)
when:
  rhyme     they end alike from their last stressed vowel on, the vowels as a Hebrew-speaking child
            hears them: five (ship and sheep, bed and bad, cot and cut are one each) ("cat" "hat",
            "cake" "snake", "father" "mother");
  one sound one sound added, dropped or changed makes one the other ("bed" "red", "bear" "pear");
  start     the same sounds up to a stressed first vowel, a syllable apart at most ("pen" "pencil");
  vowel     as she hears them (five vowels, no r after a vowel), only one vowel tells them apart
            ("house" "horse").
Every early quiz still has three others to offer: with the first 4 to 50 words met, no word of the
English game runs out of them.
"""
import argparse
import itertools
import json
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True
REPO = Path(__file__).resolve().parents[3]
VOWELS = {"AA", "AE", "AH", "AO", "AW", "AY", "EH", "ER", "EY", "IH", "IY", "OW", "OY", "UH", "UW"}
# The vowels a Hebrew speaker hears as one: Hebrew has five.
HEARD = {"IH": "IY", "AE": "EH", "AA": "AH", "AO": "AH", "UH": "UW"}
VARIANTS = 3  # pronunciations per word kept from CMUdict


def fail(msg):
    sys.exit(f"neighbours: {msg}")


def pronunciations(text, cmu):
    """Every pronunciation of a word or a multi-word name, as phonemes with their stress digits."""
    parts = text.lower().replace("-", " ").split()
    missing = [p for p in parts if p not in cmu]
    if missing:
        fail(f"{text!r}: CMUdict doesn't know {', '.join(missing)}")
    return [[ph for part in combo for ph in part] for combo in itertools.product(*(cmu[p][:VARIANTS] for p in parts))]


def bare(pron):
    """The phonemes without their stress."""
    return tuple(re.sub(r"\d", "", ph) for ph in pron)


def five(pron):
    """The phonemes with the vowels she hears: five."""
    return tuple(HEARD.get(ph, ph) for ph in bare(pron))


def heard(pron):
    """As she hears them: five vowels, and no r after a vowel."""
    out = []
    for ph in five(pron):
        if not (ph == "R" and out and out[-1] in VOWELS):
            out.append(ph)
    return tuple(out)


def syllables(pron):
    return sum(ph[-1].isdigit() for ph in pron)


def rhyme(pron):
    """From the last primary-stressed vowel (else the last stressed one, else the last vowel) to the end."""
    for marks in ("1", "12", "012"):
        at = [i for i, ph in enumerate(pron) if ph[-1] in marks]
        if at:
            return five(pron[at[-1]:])
    return None


def start(pron):
    """The onset and the first vowel, when that vowel is stressed."""
    for i, ph in enumerate(pron):
        if ph[-1].isdigit():
            return bare(pron[:i + 1]) if ph[-1] in "12" else None
    return None


def distance(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        prev, row[0] = row[0], i
        for j, y in enumerate(b, 1):
            prev, row[j] = row[j], min(row[j] + 1, row[j - 1] + 1, prev + (x != y))
    return row[-1]


def vowel_only(a, b):
    """Same length, and they differ in one vowel at most."""
    if len(a) != len(b):
        return False
    diff = [(x, y) for x, y in zip(a, b) if x != y]
    return len(diff) <= 1 and all(x in VOWELS and y in VOWELS for x, y in diff)


def alike(pa, pb):
    """Why two pronunciations sound alike, or None."""
    if rhyme(pa) and rhyme(pa) == rhyme(pb):
        return "rhyme"
    if distance(bare(pa), bare(pb)) <= 1:
        return "one sound"
    if start(pa) and start(pa) == start(pb) and abs(syllables(pa) - syllables(pb)) <= 1:
        return "start"
    if vowel_only(heard(pa), heard(pb)):
        return "vowel"
    return None


def neighbours(words, cmu):
    prons = {w["id"]: pronunciations(w["en"], cmu) for w in words}
    out = {w["id"]: {} for w in words}
    for a, b in itertools.combinations([w["id"] for w in words], 2):
        why = next(filter(None, (alike(pa, pb) for pa in prons[a] for pb in prons[b])), None)
        if why:
            out[a][b] = why
            out[b][a] = why
    return out


def text(avoid, order):
    rows = ",\n".join(f"  {json.dumps(i)}: {json.dumps(dict(sorted(avoid[i].items())), separators=(', ', ': '))}"
                      for i in order)
    return "{\n" + rows + "\n}\n"


def main():
    ap = argparse.ArgumentParser(description="Write a word game's club/avoid.json (see the module docstring).")
    ap.add_argument("game")
    ap.add_argument("--show", nargs="*", default=[], help="print these words' sound-alikes")
    args = ap.parse_args()
    import cmudict  # noqa: PLC0415 (uv run --with cmudict==1.1.3)

    page = REPO / args.game
    roster = json.loads((page / "club/roster.json").read_text(encoding="utf-8"))
    words = roster.get("words")
    if not words:
        fail(f"{args.game} is not a word game (its roster has no words)")
    avoid = neighbours(words, cmudict.dict())
    (page / "club/avoid.json").write_text(text(avoid, [w["id"] for w in words]), encoding="utf-8")
    counts = sorted(len(v) for v in avoid.values())
    whys = {}
    for v in avoid.values():
        for why in v.values():
            whys[why] = whys.get(why, 0) + 1
    print(f"{args.game}/club/avoid.json: {len(words)} words, {sum(counts) // 2} pairs "
          f"({', '.join(f'{k} {v // 2}' for k, v in sorted(whys.items()))}); per word: median "
          f"{counts[len(counts) // 2]}, max {counts[-1]}, none {counts.count(0)}", flush=True)
    for wid in args.show:
        print(f"  {wid}: {avoid.get(wid, 'not a word of this game')}", flush=True)


if __name__ == "__main__":
    main()
