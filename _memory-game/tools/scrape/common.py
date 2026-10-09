"""What every club's scraper needs besides parsing its own site: a polite cached fetcher, ids, names,
an atomic players.json write and the facts of a downloaded photo.

    sys.path.insert(1, str(Path(__file__).resolve().parents[3] / "_memory-game/tools/scrape"))
    from common import Fetcher, ascii_slug, log_line, norm_name, photo_facts, write_json_atomic

Downloads are untrusted data: run the scrapers with `python -I`, keep the cache outside the repo.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import os
import re
import tempfile
import time
import unicodedata
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)
# Letters NFKD can't decompose to ASCII; without them "Łukasz" would lose its first letter.
TRANSLIT_EXTRA = {"ł": "l", "Ł": "l", "đ": "d", "Đ": "d", "ø": "o", "Ø": "o", "æ": "ae", "ß": "ss", "ı": "i"}


def log_line(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


class Fetcher:
    """Sequential, at least `delay` seconds between requests, a desktop Chrome user agent; every body is
    cached under cache_dir/rel and reused unless refresh (or force) is set. `requests` counts network calls;
    `newest_fetch` is the mtime of the newest cached HTML page used."""

    def __init__(self, cache_dir: Path, delay: float = 0.6, refresh: bool = False):
        self.cache_dir = Path(cache_dir)
        self.delay = delay
        self.refresh = refresh
        self.session = None
        self._last = 0.0
        self.requests = 0
        self.newest_fetch = 0.0

    def request(self, method: str, url: str, **kw):
        if self.session is None:
            import requests

            self.session = requests.Session()
            self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "he-IL,he;q=0.9,en;q=0.8"})
        gap = time.monotonic() - self._last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self.requests += 1
        try:
            return self.session.request(method, url, timeout=60, **kw)
        finally:
            self._last = time.monotonic()  # the gap counts from the end of the previous response

    def get(self, url: str):
        return self.request("GET", url)

    def cached(self, url: str, rel: str, force: bool = False) -> bytes:
        path = self.cache_dir / rel
        if force or self.refresh or not path.exists():
            log_line(f"GET {url}")
            resp = self.request("GET", url)
            resp.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(resp.content)
        if path.suffix in (".html", ".htm"):
            self.newest_fetch = max(self.newest_fetch, path.stat().st_mtime)
        return path.read_bytes()

    def cached_post(self, url: str, form: dict, rel: str, headers: dict | None = None,
                    accept=lambda body: True) -> bytes:
        """POST once and cache the body; a cached body that `accept` rejects is fetched again."""
        path = self.cache_dir / rel
        if path.exists() and not self.refresh and accept(path.read_bytes()):
            return path.read_bytes()
        log_line(f"POST {url} {form.get('action')} {form.get('memberID', '')}")
        resp = self.request("POST", url, files={k: (None, str(v)) for k, v in form.items()}, headers=headers or {})
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
        return resp.content


def ascii_slug(text: str) -> str:
    """A player id from a Latin-script name: "Łukasz O'Neil" -> "lukasz-oneil"."""
    text = "".join(TRANSLIT_EXTRA.get(c, c) for c in text)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"['’`]", "", text.lower())
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def norm_name(s: str) -> str:
    """A Hebrew name for matching across pages: one kind of geresh and quote, single spaces."""
    s = s.replace("׳", "'").replace("״", '"').replace("’", "'").replace("`", "'")
    return " ".join(s.split())


def write_json_atomic(path: Path, payload) -> None:
    """players.json and friends: written whole or not at all, mode 0644, a trailing newline."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")
    os.chmod(tmp, 0o644)  # mkstemp creates 0600
    os.replace(tmp, path)


def photo_facts(data: bytes) -> dict:
    """Size, format, alpha and checksum of a downloaded photo."""
    from PIL import Image

    img = Image.open(io.BytesIO(data))
    img.load()
    alpha = img.convert("RGBA").getchannel("A")
    hist = alpha.histogram()
    total = img.width * img.height
    return {
        "px": [img.width, img.height], "format": img.format, "mode": img.mode,
        "has_alpha": alpha.getextrema()[0] < 255, "transparent_share": round(hist[0] / total, 3),
        "alpha_levels": sum(1 for v in hist if v), "bytes": len(data), "sha1": hashlib.sha1(data).hexdigest(),
    }
