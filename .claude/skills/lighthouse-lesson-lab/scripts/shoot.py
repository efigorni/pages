#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright"]
# ///
"""shoot.py — the visual check of a built lesson (D43). Headless Chrome, no MCP browser.

    uv run --with playwright python3 .claude/skills/lighthouse-lesson-lab/scripts/shoot.py lesson-lab/lessons/<slug> [...]

Shoots, into lesson-lab/lessons/<slug>/.shots/ (git-ignored, emptied on every run):
  slides-1.png …   every slide of the deck with all fragments shown, six per sheet (900px wide each —
                   the art-guide's "back row of the class" size). Single slides: .shots/slides/slide-NN.png
  phone-1.png …    המערך at a true 420px phone width (inside a 420px iframe), three 1500px strips per sheet
  desk-1.png …     המערך at 1280px desktop width — the 960px reading column, 1500px per tile

and checks the layout automatically:
  ✗ horizontal scroll at 420px (and the elements that stick out)
  ✗ a slide whose words leave the text area (they run into the timer and the slide number) or whose
    picture leaves the slide
The ✗ lines are errors (exit code 1). Then LOOK at every sheet — the checks can't see a bad picture.

Uses the installed Google Chrome through Playwright (channel="chrome"), like export_pdf.py; with no Chrome:
`uv run --with playwright playwright install chromium` and pass --bundled.
"""
from __future__ import annotations

import math
import shutil
import sys
from pathlib import Path

STRIP = 1500          # px of page per strip/tile
SLIDE_W, SLIDE_H = 1440, 810
SHEET_SLIDE_W = 900   # art-guide: the focus must read at 900px
PER_SHEET = 6
PHONE = 420
DESK = 1280
DESK_COL = (160, 960)  # x, width of the reading column at 1280 (.wrap = 880 + padding)

SLIDE_CHECK = r"""() => {
  const s = Reveal.getCurrentSlide(), out = [];
  const frame = s.querySelector('.frame'); if (!frame) return out;
  const f = frame.getBoundingClientRect(), cs = getComputedStyle(frame);
  const top = f.top + parseFloat(cs.paddingTop), bottom = f.bottom - parseFloat(cs.paddingBottom);
  const txt = frame.querySelector('.txt');
  if (txt) {
    const kids = [...txt.children].map(e => e.getBoundingClientRect()).filter(r => r.height > 0);
    if (kids.length) {
      const t = Math.min(...kids.map(r => r.top)), b = Math.max(...kids.map(r => r.bottom));
      if (b - t > bottom - top + 1) out.push(`הטקסט גבוה מאזור הטקסט (${Math.round(b - t)} > ${Math.round(bottom - top)} פיקסלים) — קצרי, או פצלי לשני שקפים`);
      else if (t < top - 1 || b > bottom + 1) out.push('הטקסט יוצא מאזור הטקסט (נוגע בטיימר או במספר השקף)');
    }
    if (txt.scrollWidth > txt.clientWidth + 1) out.push('מילה ארוכה מדי לרוחב טור הטקסט');
  }
  const pic = frame.querySelector('.pic svg');
  if (pic) {
    const r = pic.getBoundingClientRect(), sr = s.getBoundingClientRect();
    if (r.left < sr.left - 1 || r.right > sr.right + 1 || r.top < sr.top - 1 || r.bottom > sr.bottom + 1)
      out.push('האיור יוצא מהשקף');
    if (r.width < 200) out.push(`האיור קטן מאוד (${Math.round(r.width)} פיקסלים)`);
  }
  return out;
}"""

PAGE_CHECK = r"""() => {
  const W = document.documentElement.clientWidth, out = [];
  const sw = document.documentElement.scrollWidth;
  if (sw > W + 1) out.push(`גלילה אופקית: רוחב התוכן ${sw} > ${W}`);
  const seen = new Set();
  const name = el => {
    const tag = el.tagName.toLowerCase() + (el.className && typeof el.className === 'string' ? '.' + el.className.trim().split(/\s+/).join('.') : '');
    const sec = el.closest('section[id]');
    return tag + (sec ? ' #' + sec.id : '');
  };
  const all = [...document.querySelectorAll('body *')].filter(el => !el.closest('.hero-art'));  // decorative, clipped
  for (const el of all) {
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height || getComputedStyle(el).position === 'fixed') continue;
    if (r.right > W + 1 || r.left < -1) {
      const key = name(el);
      if (!seen.has(key)) { seen.add(key); out.push(`בולט מהמסך: ${key} (${Math.round(r.left)}…${Math.round(r.right)})`); }
      if (seen.size >= 6) break;
    }
  }
  // text that overflows its own box (a long unbroken word, a URL): the deepest element whose content is wider than it
  const over = all.filter(el => el.clientWidth && el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).overflowX === 'visible');
  for (const el of over.filter(el => !over.some(o => o !== el && el.contains(o))).slice(0, 6))
    out.push(`תוכן רחב מהתיבה: ${name(el)} — "${el.textContent.trim().slice(0, 40)}…"`);
  return out;
}"""


def uri(p: Path) -> str:
    return p.resolve().as_uri()


def wait_ready(target, page_or_frame_is_deck: bool = False):
    if page_or_frame_is_deck:
        target.wait_for_function('window.Reveal && Reveal.isReady()')
    target.evaluate('document.fonts.ready.then(() => true)')


def sheet(page, out: Path, name: str, items: list[tuple[str, str]], width: int, cols: int, caption_color: str = '#13100e'):
    """Compose PNGs into one image: items = [(png file name relative to out, caption)]."""
    cells = ''.join(
        f'<figure><img src="{src}" width="{width}"><figcaption style="color:{"#c94f4f" if cap.startswith("✗") else caption_color}">'
        f'{cap}</figcaption></figure>' for src, cap in items)
    html = (f'<!doctype html><html dir="rtl"><head><meta charset="utf-8"><style>'
            f'body{{margin:0;background:#cfc8bf;font:600 22px Arial, sans-serif}}'
            f'.g{{display:grid;grid-template-columns:repeat({cols},{width}px);gap:14px;padding:14px;width:max-content}}'
            f'figure{{margin:0;background:#fff}}img{{display:block;border-bottom:1px solid #999}}'
            f'figcaption{{padding:4px 10px}}</style></head><body><div class="g">{cells}</div></body></html>')
    tmp = out / f'_{name}.html'
    tmp.write_text(html, encoding='utf-8')
    page.set_viewport_size({'width': cols * width + (cols + 1) * 14, 'height': 600})
    page.goto(uri(tmp))
    page.wait_for_load_state('load')
    page.screenshot(path=str(out / f'{name}.png'), full_page=True)
    tmp.unlink()


def shoot_lesson(d: Path, browser) -> tuple[list[str], list[str], list[str]]:
    """Returns (errors, warnings, sheets) for one lesson folder."""
    errors, warnings, sheets = [], [], []
    out = d / '.shots'
    if out.exists():
        shutil.rmtree(out)
    (out / 'slides').mkdir(parents=True)
    (out / 'strips').mkdir()

    # ---- the deck: every slide, all fragments visible, scale 1
    page = browser.new_page(viewport={'width': SLIDE_W, 'height': SLIDE_H})
    page.goto(uri(d / 'slides.html') + '?fragments=false&transition=none&backgroundTransition=none'
              '&controls=false&progress=false&hash=false&margin=0')
    wait_ready(page, True)
    if not page.evaluate("document.fonts.check('40px \"Secular One\"') && document.fonts.check('20px Assistant')"):
        warnings.append('הגופנים (Google Fonts) לא נטענו — אין רשת? המידות בצילום שונות מהכיתה')
    total = page.evaluate('Reveal.getTotalSlides()')
    captions = []
    for i in range(total):
        page.evaluate(f'Reveal.slide({i})')
        page.wait_for_timeout(80)
        problems = page.evaluate(SLIDE_CHECK)
        for p in problems:
            (warnings if p.startswith('האיור קטן') else errors).append(f'שקף {i + 1}: {p}')
        name = f'slides/slide-{i + 1:02d}.png'
        page.screenshot(path=str(out / name))
        bad = any(not p.startswith('האיור קטן') for p in problems)
        captions.append((name, f'{"✗ " if bad else ""}שקף {i + 1}'))
    for k in range(math.ceil(total / PER_SHEET)):
        name = f'slides-{k + 1}'
        sheet(page, out, name, captions[k * PER_SHEET:(k + 1) * PER_SHEET], SHEET_SLIDE_W, 2)
        sheets.append(str(out / f'{name}.png'))
    page.close()

    # ---- המערך at a true 420px: the page inside a 420px-wide iframe, as tall as the page itself (so the page
    # never scrolls and has no scrollbar); the wrapper scrolls instead, one 1500px viewport at a time — a single
    # capture never passes Chrome's 16384px limit, which otherwise tiles long pages into repeats
    page = browser.new_page(viewport={'width': PHONE, 'height': STRIP})
    wrapper = out / '_phone.html'
    wrapper.write_text('<!doctype html><html><head><meta charset="utf-8"><style>html{scrollbar-width:none}'
                       'html::-webkit-scrollbar{display:none}body{margin:0;background:#cfc8bf}</style></head><body>'
                       f'<iframe id="f" src="../index.html" style="display:block;width:{PHONE}px;height:{STRIP}px;'
                       f'border:0;background:#fff"></iframe><div style="height:{STRIP}px"></div></body></html>',
                       encoding='utf-8')
    page.goto(uri(wrapper))
    frame = next(f for f in page.frames if f.url.endswith('/index.html'))
    frame.wait_for_load_state('load')
    wait_ready(frame)
    height = frame.evaluate('document.documentElement.scrollHeight')
    page.evaluate(f'document.getElementById("f").style.height = "{height}px"')
    page.wait_for_timeout(150)
    inner = frame.evaluate('[innerWidth, document.documentElement.clientWidth]')
    if inner != [PHONE, PHONE]:
        warnings.append(f'רוחב הטלפון יצא {inner} ולא {PHONE}px')
    for p in frame.evaluate(PAGE_CHECK):
        errors.append(f'המערך ב-{PHONE}px: {p}')
    strips = []
    for k in range(math.ceil(height / STRIP)):
        h = min(STRIP, height - k * STRIP)
        page.evaluate(f'window.scrollTo(0, {k * STRIP})')
        page.wait_for_timeout(60)
        name = f'strips/phone-{k + 1:02d}.png'
        page.screenshot(path=str(out / name))
        strips.append((name, f'{PHONE}px · {k * STRIP}–{k * STRIP + h}'))
    wrapper.unlink()
    for k in range(math.ceil(len(strips) / 3)):
        name = f'phone-{k + 1}'
        sheet(page, out, name, strips[k * 3:(k + 1) * 3], PHONE, 3)
        sheets.append(str(out / f'{name}.png'))
    page.close()

    # ---- המערך at desktop width: the reading column, one 1500px viewport at a time (same reason as above)
    page = browser.new_page(viewport={'width': DESK, 'height': STRIP})
    page.goto(uri(d / 'index.html'))
    wait_ready(page)
    for p in page.evaluate(PAGE_CHECK):
        errors.append(f'המערך ב-{DESK}px: {p}')
    height = page.evaluate('document.documentElement.scrollHeight')
    x, w = DESK_COL
    for k in range(math.ceil(height / STRIP)):
        h = min(STRIP, height - k * STRIP)
        if h < STRIP:  # the last tile: a shorter viewport, so the scroll lands exactly on k·STRIP
            page.set_viewport_size({'width': DESK, 'height': h})
        page.evaluate(f'window.scrollTo(0, {k * STRIP})')
        page.wait_for_timeout(60)
        name = f'desk-{k + 1}.png'
        page.screenshot(path=str(out / name), clip={'x': x, 'y': 0, 'width': w, 'height': h})
        sheets.append(str(out / name))
    page.close()
    return errors, warnings, sheets


def main(argv: list[str]) -> int:
    dirs = [Path(a).resolve() for a in argv if not a.startswith('-')]
    if not dirs:
        print(__doc__)
        return 2
    from playwright.sync_api import sync_playwright

    bad = 0
    with sync_playwright() as p:
        browser = p.chromium.launch(**({} if '--bundled' in argv else {'channel': 'chrome'}), headless=True)
        for d in dirs:
            if not (d / 'index.html').exists() or not (d / 'slides.html').exists():
                print(f'✗ {d.name}: אין index.html / slides.html — הריצי קודם את build.py')
                bad += 1
                continue
            errors, warnings, sheets = shoot_lesson(d, browser)
            print(f'{"✓" if not errors else "✗"} {d.name}: {len(errors)} שגיאות תצוגה, {len(warnings)} אזהרות · '
                  f'{len(sheets)} תמונות ב-{d / ".shots"}')
            for e in errors:
                print(f'   ✗ {e}')
            for w in warnings:
                print(f'   ! {w}')
            print('   הסתכלי על כל אחת (Read):')
            for s in sheets:
                print(f'   · {s}')
            bad += bool(errors)
        browser.close()
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
