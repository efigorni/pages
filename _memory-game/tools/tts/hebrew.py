"""Hebrew text helpers for the memory games' voice clips.

Pure stdlib, importable from any of the engine venvs.

- `speak_text` applies the parentheses rule: a name that ends in "(...)" is read
  as the text inside the parentheses only; any other name is read in full.
  `split_display_name` is the card's two-tier split of the same name.
- Number words use the feminine counting form that follows "מספר"
  ("מספר שבע", "מספר ארבעים ושתיים").
- `normalize_for_compare` folds both the expected text and an STT transcript to
  the same shape so a round-trip can be judged mechanically.
"""
from __future__ import annotations

import re
import unicodedata

_UNITS_F = {
    0: "אפס", 1: "אחת", 2: "שתיים", 3: "שלוש", 4: "ארבע", 5: "חמש",
    6: "שש", 7: "שבע", 8: "שמונה", 9: "תשע", 10: "עשר",
}
_TEENS_F = {
    11: "אחת עשרה", 12: "שתים עשרה", 13: "שלוש עשרה", 14: "ארבע עשרה",
    15: "חמש עשרה", 16: "שש עשרה", 17: "שבע עשרה", 18: "שמונה עשרה",
    19: "תשע עשרה",
}
_TENS = {
    20: "עשרים", 30: "שלושים", 40: "ארבעים", 50: "חמישים",
    60: "שישים", 70: "שבעים", 80: "שמונים", 90: "תשעים",
}


def number_words_fem(n: int) -> str:
    """0..99 in the feminine counting form used after "מספר"."""
    if not 0 <= n <= 99:
        raise ValueError(f"shirt number out of range: {n}")
    if n <= 10:
        return _UNITS_F[n]
    if n < 20:
        return _TEENS_F[n]
    tens, unit = divmod(n, 10)
    word = _TENS[tens * 10]
    return word if unit == 0 else f"{word} ו{_UNITS_F[unit]}"


def match_text(number: int | None, name: str) -> str:
    if number is None:
        return f"{name}!"
    return f"מספר {number_words_fem(number)}, {name}!"


START_TEXT = "יאללה, בואי נשחק!"
WIN_TEXT = "כל הכבוד! מצאת את כל השחקנים!"
# The quiz's question opens with this clip; the asked player's match clip follows it.
WHO_TEXT = "מי זה?"


_TRAILING_PARENS = re.compile(r"\(([^()]*)\)\s*$")


def _squash(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def nickname(display_name: str) -> str | None:
    """The text inside a trailing "(...)" of a name as the site displays it, else None.

    Only a parenthetical at the very end counts, and an empty one is ignored. This is
    the one definition of the parentheses rule: the scraper, the page builder and the
    voice tools all go through it.
    """
    m = _TRAILING_PARENS.search(_squash(display_name))
    if m and m.group(1).strip():
        return m.group(1).strip()
    return None


def speak_text(display_name: str) -> str:
    """The words the voice reads for a name as the site displays it.

    "ז'וזה דה סילבה (ז'וזינייו)" -> "ז'וזינייו"; "דור פרץ" -> "דור פרץ".
    """
    return nickname(display_name) or _squash(display_name)


def split_display_name(display_name: str) -> tuple[str, str]:
    """The club card's two tiers: a trailing "(...)", else the last word, is the big line.

    "ברונו רוברטו פריירה דה סילבה (ברוניניו)" -> ("ברונו רוברטו פריירה דה סילבה", "(ברוניניו)").
    """
    name = _squash(display_name)
    m = _TRAILING_PARENS.search(name)
    if m:
        return name[:m.start()].rstrip(), name[m.start():]
    head, _, tail = name.rpartition(" ")
    return head, tail

_NIKUD = re.compile(r"[֑-ׇ]")
_FINALS = str.maketrans("ךםןףץ", "כמנפצ")
_PUNCT = re.compile(r"[^\w\s]", re.UNICODE)
_DIGITS = re.compile(r"\d+")


def strip_nikud(text: str) -> str:
    return _NIKUD.sub("", unicodedata.normalize("NFC", text))


def _digits_to_words(text: str) -> str:
    def sub(m: re.Match) -> str:
        n = int(m.group(0))
        return number_words_fem(n) if n <= 99 else m.group(0)
    return _DIGITS.sub(sub, text)


def normalize_for_compare(text: str) -> str:
    """Fold nikud, punctuation, digits, final letters and spacing.

    Whisper writes shirt numbers as digits or words, sometimes "מס'" for "מספר",
    and adds or drops punctuation freely; none of that is a pronunciation error.
    """
    t = strip_nikud(text)
    # Whisper hyphenates inside a foreign name ("א-סנטה"); join it back.
    t = t.replace("״", '"').replace("׳", "'").replace("־", " ")
    t = re.sub(r"(?<=\w)-(?=\w)", "", t).replace("-", " ")
    t = re.sub(r"מס'\s*", "מספר ", t)
    t = _digits_to_words(t)
    t = _PUNCT.sub(" ", t)
    t = t.replace("_", " ")
    t = re.sub(r"\s+", " ", t).strip()
    t = t.translate(_FINALS)
    # "ושתיים" vs "ושתים": both spellings are standard. Final letters are folded by now (ם→מ).
    t = re.sub(r"שתימ\b", "שתיימ", t)
    return t


# The fold above once ran with an unfolded final letter and silently never matched.
assert normalize_for_compare("מספר ארבעים ושתים") == normalize_for_compare("מספר ארבעים ושתיים")
assert normalize_for_compare("שתים עשרה") == normalize_for_compare("שתיים עשרה")


# Letters that spell the same sound in Israeli Hebrew whatever the context:
# ט/ת are both /t/, א/ע are both a glottal stop or nothing. (Pairs like כ/ח or
# ב/ו are NOT folded: they only coincide in some words, so folding them would
# let a real mispronunciation pass.)
_HOMOPHONES = str.maketrans("טע", "תא")


def compare(expected: str, heard: str, variants: list[str] | None = None) -> tuple[bool, str]:
    """(ok, how). `variants` are accepted alternative spellings of `expected`."""
    h = normalize_for_compare(heard)
    cands = [expected] + list(variants or [])
    for i, c in enumerate(cands):
        if h == normalize_for_compare(c):
            return True, "exact" if i == 0 else "variant"
    for c in cands:
        if h.translate(_HOMOPHONES) == normalize_for_compare(c).translate(_HOMOPHONES):
            return True, "homophone"
    return False, "mismatch"


def similarity(a: str, b: str) -> float:
    import difflib
    return difflib.SequenceMatcher(None, normalize_for_compare(a), normalize_for_compare(b)).ratio()


if __name__ == "__main__":
    for n in (1, 2, 7, 10, 11, 12, 19, 20, 21, 42, 70, 99):
        print(n, number_words_fem(n))
    for s in ("דור פרץ", "ז'וזה דה סילבה (ז'וזינייו)", "שם ( כינוי ) ", "שם ()", "שם (א) ב"):
        print(repr(s), "->", repr(speak_text(s)), split_display_name(s))
    print(match_text(42, "דור פרץ"))
    print(normalize_for_compare("מס' 42, דור פרץ!"), "|", normalize_for_compare(match_text(42, "דור פרץ")))
    print(compare("מספר ארבעים ושתיים, דור פרץ!", "מספר 42 דור פרץ"))
