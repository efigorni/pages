"""Helpers to read the Next.js App Router flight (RSC) payload embedded in a saved page.

The page carries its server data as `self.__next_f.push([1,"<js string>"])` chunks. Concatenating the
string chunks gives the flight stream: rows of `<hex id>:<json>` (plus text/import rows). The CMS objects
(players, stats, games, images) sit inside the JSON rows; repeated objects are replaced by `"$<hex id>"`
back-references, which `resolve` follows. Everything here only parses text; nothing is executed.
"""

from __future__ import annotations

import json
import re

PUSH_RE = re.compile(r"self\.__next_f\.push\(\[1,(\"(?:[^\"\\]|\\.)*\")\]\)", re.S)
REF_RE = re.compile(r"^\$([0-9a-f]+)((?::[^:]+)*)$")


def flight_text(html: str) -> str:
    return "".join(json.loads(m.group(1)) for m in PUSH_RE.finditer(html))


def json_at(text: str, start: int):
    """Decode the JSON value that starts at text[start]."""
    return json.JSONDecoder().raw_decode(text, start)[0]


def find_values(text: str, key: str) -> list:
    """Every JSON value that follows `"key":` in the flight text (objects/arrays/scalars)."""
    out = []
    needle = json.dumps(key) + ":"
    pos = 0
    while True:
        i = text.find(needle, pos)
        if i < 0:
            break
        j = i + len(needle)
        try:
            out.append(json_at(text, j))
        except json.JSONDecodeError:
            pass
        pos = j
    return out


def rows(text: str) -> dict[str, object]:
    """Parse a flight stream into {row id: value}.

    Rows are `<hex id>:<payload>`. A `T<hex byte length>,<text>` payload is raw text of that many UTF-8
    bytes with no terminator; every other payload runs to the next newline. JSON payloads are decoded,
    text payloads kept as str, anything else skipped.
    """
    data = text.encode("utf-8")
    out: dict[str, object] = {}
    pos, n = 0, len(data)
    while pos < n:
        colon = data.find(b":", pos)
        if colon < 0:
            break
        key = data[pos:colon].decode("ascii", "replace").strip()
        body = colon + 1
        m = re.match(rb"T([0-9a-f]+),", data[body:body + 20])
        if m:
            start = body + m.end()
            end = start + int(m.group(1), 16)
            out[key] = data[start:end].decode("utf-8", "replace")
            pos = end
            continue
        nl = data.find(b"\n", body)
        end = n if nl < 0 else nl
        payload = data[body:end].decode("utf-8", "replace")
        if payload[:1] in ("[", "{", '"') and re.fullmatch(r"[0-9a-f]+", key or "-"):
            try:
                out[key] = json.loads(payload)
            except json.JSONDecodeError:
                pass
        pos = end + 1
    return out


def resolve(value, table: dict[str, object], depth: int = 0):
    """Replace "$<id>" / "$<id>:a:b" back-references with the referenced row (recursively)."""
    if depth > 60:
        return value
    if isinstance(value, str):
        m = REF_RE.match(value)
        if m and m.group(1) in table:
            target = table[m.group(1)]
            for seg in [s for s in m.group(2).split(":") if s]:
                if isinstance(target, list) and seg.isdigit():
                    target = target[int(seg)]
                elif isinstance(target, dict):
                    target = target.get(seg)
            return resolve(target, table, depth + 1)
        return value
    if isinstance(value, list):
        return [resolve(v, table, depth + 1) for v in value]
    if isinstance(value, dict):
        return {k: resolve(v, table, depth + 1) for k, v in value.items()}
    return value


def collect(value, predicate, out: list | None = None) -> list:
    """Every dict inside value for which predicate(dict) is true (depth-first)."""
    out = [] if out is None else out
    if isinstance(value, dict):
        if predicate(value):
            out.append(value)
        for v in value.values():
            collect(v, predicate, out)
    elif isinstance(value, list):
        for v in value:
            collect(v, predicate, out)
    return out


def page_objects(html: str, predicate) -> list:
    """All dicts matching predicate across the page's flight rows, references resolved."""
    table = rows(flight_text(html))
    found: list = []
    for v in table.values():
        collect(v, predicate, found)
    return [resolve(o, table) for o in found]
