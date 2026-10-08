"""Polite cached fetcher (sequential, >= delay s between requests, desktop Chrome UA).

Adapted from maccabi-haifa-memory/tools/scrape/fetch.py; adds POST (WordPress admin-ajax) support.
Importable only: Fetcher(cache_dir, delay, refresh).cached(url, rel) / .cached_post(url, form, rel).
"""

from __future__ import annotations

import datetime as dt
import time
from pathlib import Path

import requests

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)


def log_line(msg: str) -> None:
    print(f"[{dt.datetime.now():%H:%M:%S}] {msg}", flush=True)


class Fetcher:
    def __init__(self, cache_dir: Path, delay: float = 0.6, refresh: bool = False):
        self.cache_dir = cache_dir
        self.delay = delay
        self.refresh = refresh
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "he-IL,he;q=0.9,en;q=0.8"})
        self._last = 0.0
        self.requests = 0

    def _wait(self) -> None:
        gap = time.monotonic() - self._last
        if gap < self.delay:
            time.sleep(self.delay - gap)

    def request(self, method: str, url: str, **kw) -> requests.Response:
        self._wait()
        self.requests += 1
        try:
            return self.session.request(method, url, timeout=60, **kw)
        finally:
            self._last = time.monotonic()  # the gap counts from the end of the previous response

    def cached(self, url: str, rel: str, force: bool = False) -> bytes:
        path = self.cache_dir / rel
        if force or self.refresh or not path.exists():
            log_line(f"GET {url}")
            resp = self.request("GET", url)
            resp.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(resp.content)
        return path.read_bytes()

    def cached_post(self, url: str, form: dict, rel: str, headers: dict | None = None,
                    accept=lambda body: True) -> bytes:
        """POST once and cache the body; a cached body that `accept` rejects is re-fetched."""
        path = self.cache_dir / rel
        if path.exists() and not self.refresh and accept(path.read_bytes()):
            return path.read_bytes()
        log_line(f"POST {url} {form.get('action')} {form.get('memberID', '')}")
        resp = self.request("POST", url, files={k: (None, str(v)) for k, v in form.items()}, headers=headers or {})
        resp.raise_for_status()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
        return resp.content
