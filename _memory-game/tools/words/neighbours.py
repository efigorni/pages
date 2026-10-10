#!/usr/bin/env python3
"""A word game's sound-alikes: the words its quiz never offers as a wrong answer to one another.

    uv run --quiet --with cmudict==1.1.3 python -I _memory-game/tools/words/neighbours.py <game> [--show <id>...]

Reads <game>/club/roster.json and writes <game>/club/avoid.json, one line per word: {id: {other id: why}}.
build_page.py checks it (every word on the roster has its line, every id is on it, each pair both ways) and
puts each word's list in DATA as its `avoid`, with club.json play.quiz.apart's look-alike pictures, and the
engine never deals an avoided word as one of the other three cards. Run it after every change to the words.

Only the most confusing pairs are kept apart. The pronunciations (CMUdict, every variant of every word in a
multi-word name) are taken as an American voice says them: stress aside, a vowel and the r after it one
sound (bear: B EHR, horse: HH AOR S; an r before a vowel starts the next syllable, as in carrot), and AO
as AA (the cot-caught merger: ball is B AA L, like doll). Two words with as many syllables are kept apart
when
  first sound   only their first sound differs, a consonant against a consonant ("ball" "doll", "cat"
                "hat", "bed" "red", "bear" "pear", "sun" "run");
  last sound    only their last sound differs, a consonant against a consonant ("bad" "bag");
  vowel         one syllable each, only the vowel differs ("house" "horse", "hat" "hot", "cat" "kite");
  same sound    nothing differs ("right" "write").
"cake" "snake" (a sound added) and "cat" "camel" (a syllable added) are not. Every run checks these cases
(KEEP_APART, ALLOWED) before it writes.
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
VARIANTS = 3  # pronunciations per word kept from CMUdict
# Adam's cases: pairs the rule must keep apart, and pairs it must allow.
KEEP_APART = (("ball", "doll"), ("cat", "hat"), ("house", "horse"), ("bed", "red"), ("bear", "pear"), ("sun", "run"))
ALLOWED = (("cake", "snake"), ("cat", "camel"))


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


def heard(pron):
    """The sounds as the American voice says them: stress aside, a vowel and an r after it (not one before a
    vowel) one sound, and AO as AA, though AOR stays AOR."""
    ph = bare(pron)
    out = []
    for i, p in enumerate(ph):
        if p == "R" and out and out[-1] in VOWELS and (i + 1 == len(ph) or ph[i + 1] not in VOWELS):
            out[-1] += "R"
        else:
            out.append(p)
    return tuple("AA" if p == "AO" else p for p in out)


def vowel(sound):
    return sound in VOWELS or sound[:-1] in VOWELS


def alike(pa, pb):
    """Why two pronunciations are among the most confusing (module docstring), or None."""
    a, b = heard(pa), heard(pb)
    va, vb = [i for i, s in enumerate(a) if vowel(s)], [i for i, s in enumerate(b) if vowel(s)]
    if len(va) != len(vb):
        return None
    if a == b:
        return "same sound"
    diff = [i for i, (x, y) in enumerate(zip(a, b)) if x != y] if len(a) == len(b) else []
    if len(diff) == 1 and diff[0] in (0, len(a) - 1) and not vowel(a[diff[0]]) and not vowel(b[diff[0]]):
        return "first sound" if diff[0] == 0 else "last sound"
    if len(va) == 1 and a[:va[0]] == b[:vb[0]] and a[va[0] + 1:] == b[vb[0] + 1:]:
        return "vowel"
    return None


def why(prons_a, prons_b):
    """Why two words are kept apart (any pronunciation of each), or None."""
    return next(filter(None, (alike(pa, pb) for pa in prons_a for pb in prons_b)), None)


def neighbours(words, cmu):
    prons = {w["id"]: pronunciations(w["en"], cmu) for w in words}
    out = {w["id"]: {} for w in words}
    for a, b in itertools.combinations([w["id"] for w in words], 2):
        reason = why(prons[a], prons[b])
        if reason:
            out[a][b] = reason
            out[b][a] = reason
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

    cmu = cmudict.dict()
    wrong = [f"{a}/{b} {'must be kept apart' if keep else 'must be allowed'}"
             for keep, pairs in ((True, KEEP_APART), (False, ALLOWED)) for a, b in pairs
             if bool(why(pronunciations(a, cmu), pronunciations(b, cmu))) != keep]
    if wrong:
        fail(f"the rule breaks Adam's cases: {'; '.join(wrong)}")
    page = REPO / args.game
    roster = json.loads((page / "club/roster.json").read_text(encoding="utf-8"))
    words = roster.get("words")
    if not words:
        fail(f"{args.game} is not a word game (its roster has no words)")
    avoid = neighbours(words, cmu)
    (page / "club/avoid.json").write_text(text(avoid, [w["id"] for w in words]), encoding="utf-8")
    counts = sorted(len(v) for v in avoid.values())
    whys = {}
    for v in avoid.values():
        for reason in v.values():
            whys[reason] = whys.get(reason, 0) + 1
    print(f"{args.game}/club/avoid.json: {len(words)} words, {sum(counts) // 2} pairs "
          f"({', '.join(f'{k} {v // 2}' for k, v in sorted(whys.items()))}); per word: median "
          f"{counts[len(counts) // 2]}, max {counts[-1]}, none {counts.count(0)}", flush=True)
    for wid in args.show:
        print(f"  {wid}: {avoid.get(wid, 'not a word of this game')}", flush=True)


if __name__ == "__main__":
    main()
