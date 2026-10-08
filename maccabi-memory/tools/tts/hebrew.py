"""Hebrew text helpers for the Maccabi memory-game voice clips.

Pure stdlib, importable from any of the engine venvs.

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
    # "ושתיים" vs "ושתים": both spellings are standard.
    t = re.sub(r"שתים\b", "שתיימ", t)
    t = re.sub(r"שתיימ\b", "שתיימ", t)
    return t


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
    print(match_text(42, "דור פרץ"))
    print(normalize_for_compare("מס' 42, דור פרץ!"), "|", normalize_for_compare(match_text(42, "דור פרץ")))
    print(compare("מספר ארבעים ושתיים, דור פרץ!", "מספר 42 דור פרץ"))
