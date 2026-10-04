#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright"]
# ///
"""export_pdf.py — slides.html → slides.pdf (the offline backup of the deck, D28).

    uv run --with playwright python3 .claude/skills/lighthouse-lesson-lab/scripts/export_pdf.py lesson-lab/lessons/<slug> [...]

Drives the installed Google Chrome through Playwright (channel="chrome": nothing is downloaded, nothing
installed globally) to reveal's print view (slides.html?print-pdf), waits for reveal and the fonts, and
prints with the CSS page size (1440×810 + reveal's margin) and backgrounds. One page per slide, all
fragments visible, slide number on every page. Chrome's own --print-to-pdf is not used: it ignores
@page size and prints Letter portrait.
No Chrome on the machine? `uv run --with playwright playwright install chromium` and pass --bundled.
Options: --force (re-export even when slides.pdf is newer than slides.html).
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path


def stale(d: Path) -> bool:
    """The PDF is older than the deck or than anything the deck loads from lessons/_assets."""
    pdf = d / 'slides.pdf'
    if not pdf.exists():
        return True
    shared = d.parent / '_assets'
    deps = [d / 'slides.html', shared / 'slides.css', shared / 'deck.js', shared / 'lesson.js',
            shared / 'reveal' / 'reveal.css', shared / 'reveal' / 'reveal.js']
    return pdf.stat().st_mtime < max(p.stat().st_mtime for p in deps if p.exists())


def export(dirs: list[Path], force: bool = False, bundled: bool = False) -> int:
    from playwright.sync_api import sync_playwright

    todo = [d for d in dirs if (d / 'slides.html').exists() and (force or stale(d))]
    for d in dirs:
        if not (d / 'slides.html').exists():
            print(f'✗ {d.name}: אין slides.html — הריצי קודם את build.py')
    if not todo:
        print('· כל קובצי ה-PDF עדכניים')
        return 0
    bad = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(**({} if bundled else {'channel': 'chrome'}), headless=True)
        for d in todo:
            t0 = time.time()
            html = (d / 'slides.html').read_text(encoding='utf-8')
            expected = len(re.findall(r'<section class="s-pic', html))
            page = browser.new_page()
            page.goto((d / 'slides.html').resolve().as_uri() + '?print-pdf', wait_until='networkidle')
            page.wait_for_function('window.Reveal && Reveal.isReady()')
            page.evaluate('document.fonts.ready.then(() => true)')
            page.wait_for_timeout(300)
            out = d / 'slides.pdf'
            tmp = d / '.slides.pdf.tmp'
            page.pdf(path=str(tmp), prefer_css_page_size=True, print_background=True)
            page.close()
            pages = len(re.findall(rb'/Type\s*/Page[^s]', tmp.read_bytes()))
            tmp.replace(out)
            ok = pages == expected
            bad += not ok
            print(f'{"✓" if ok else "✗"} {d.name}: slides.pdf — {pages} עמודים / {expected} שקפים ({time.time() - t0:.1f} שנ׳)')
        browser.close()
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    dirs = [Path(a).resolve() for a in argv if not a.startswith('-')]
    if not dirs:
        print(__doc__)
        return 2
    return export(dirs, force='--force' in argv, bundled='--bundled' in argv)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
