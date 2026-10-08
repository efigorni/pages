"""Polite cached fetcher for www.mhaifafc.com pages (sequential, >= delay s apart, desktop UA).

Usage: python -I fetch.py --out <cache-dir> [--delay 0.6] [--refresh] <name>=<url> [<name>=<url> ...]
Each response body is saved to <cache-dir>/<name>; existing files are reused unless --refresh.
"""

from __future__ import annotations

import argparse
import datetime as dt
import sys
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
        self.newest_fetch = 0.0  # mtime of the newest cached page actually used

    def _wait(self) -> None:
        gap = time.monotonic() - self._last
        if gap < self.delay:
            time.sleep(self.delay - gap)
        self._last = time.monotonic()

    def get(self, url: str, timeout: int = 60) -> requests.Response:
        self._wait()
        self.requests += 1
        try:
            return self.session.get(url, timeout=timeout)
        finally:
            self._last = time.monotonic()  # the gap counts from the end of the previous response

    def cached(self, url: str, rel: str) -> bytes:
        path = self.cache_dir / rel
        if not (path.exists() and not self.refresh):
            log_line(f"GET {url}")
            resp = self.get(url)
            resp.raise_for_status()
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(resp.content)
        if path.suffix in (".html", ".htm"):
            self.newest_fetch = max(self.newest_fetch, path.stat().st_mtime)
        return path.read_bytes()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--delay", type=float, default=0.6)
    ap.add_argument("--refresh", action="store_true")
    ap.add_argument("items", nargs="+")
    a = ap.parse_args()
    f = Fetcher(a.out, a.delay, a.refresh)
    for item in a.items:
        name, _, url = item.partition("=")
        try:
            data = f.cached(url, name)
            print(f"  ok {name}: {len(data)} bytes", flush=True)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAIL {name}: {exc}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
