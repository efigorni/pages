"""Design reference for the Maccabi Haifa /players page: screenshots + computed styles.

Runs a standalone headless Chromium (Playwright Python library, its own throwaway profile). Font files
are only fetched by the browser to render the page; nothing font-related is saved except URLs.

Usage:
  uv run --with playwright python -I -u design_capture.py --out <design-dir> \
      [--chrome <path to a Chromium/Chrome binary>] [--url https://www.mhaifafc.com/players]

Writes into <design-dir>:
  players-1440-full.png, players-960-full.png   full-page screenshots
  players-cards-closeup.png                     the first three cards at 2x
  computed-styles.json                          computed styles of the card parts, fonts, network log
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36"
)

STYLE_PROPS = [
    "font-family", "font-weight", "font-size", "line-height", "letter-spacing", "color",
    "-webkit-text-fill-color", "background-image", "background-color", "background-clip",
    "text-shadow", "border-radius", "object-fit", "object-position", "opacity", "direction", "text-align",
]

EXTRACT_JS = """
(props) => {
  const pick = (el) => {
    if (!el) return null;
    const cs = getComputedStyle(el);
    const out = {tag: el.tagName.toLowerCase(), cls: el.className && el.className.baseVal === undefined ? el.className : null,
                 text: (el.innerText || '').trim().slice(0, 80)};
    for (const p of props) out[p] = cs.getPropertyValue(p);
    const r = el.getBoundingClientRect();
    out.box = {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)};
    if (el.tagName === 'IMG') { out.currentSrc = el.currentSrc; out.natural = [el.naturalWidth, el.naturalHeight]; }
    return out;
  };
  const card = document.querySelector('a[href^="/players/"]');
  const wrap = card ? card.parentElement : null;
  const imgs = card ? card.querySelectorAll('img') : [];
  const spans = card ? card.querySelectorAll('div.absolute.bottom-0 span') : [];
  const fonts = [];
  document.fonts.forEach(f => fonts.push({family: f.family, weight: f.weight, style: f.style, status: f.status}));
  const faces = [];
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
    for (const r of rules) if (r.type === CSSRule.FONT_FACE_RULE) faces.push({sheet: sheet.href, css: r.cssText});
  }
  const sectionTitles = [...document.querySelectorAll('div.text-4xl.font-medium')].map(pick);
  return {
    url: location.href, lang: document.documentElement.lang, dir: document.documentElement.dir,
    viewport: [innerWidth, innerHeight], scrollHeight: document.documentElement.scrollHeight,
    card_count: document.querySelectorAll('a[href^="/players/"]').length,
    body: pick(document.body), html: pick(document.documentElement),
    content_section: pick(document.querySelector('#content-section')),
    page_title_h1: pick(document.querySelector('h1')),
    section_titles: sectionTitles.slice(0, 4),
    card_wrapper: pick(wrap), card_link: pick(card),
    card_cover_img: pick(imgs[0]), card_photo_img: pick(imgs[1]),
    card_number: pick(card ? card.querySelector('.text-gradient-shirt-number') : null),
    card_first_name: pick(spans[0]), card_last_name: pick(spans[1]), card_position: pick(spans[2]),
    card_bottom_shadow: pick(card ? card.querySelector('.heroBottomShadow') : null),
    header: pick(document.querySelector('#header')),
    footer_band: pick(document.querySelector('.bg-secondary')),
    fonts_loaded: fonts, font_face_rules: faces,
  };
}
"""


def settle(page, seconds: float = 1.5) -> None:
    page.wait_for_load_state("networkidle", timeout=45000)
    page.evaluate("document.fonts.ready.then(() => true)")
    time.sleep(seconds)


def scroll_through(page) -> None:
    h = page.evaluate("document.documentElement.scrollHeight")
    y = 0
    while y < h:
        page.evaluate(f"window.scrollTo(0, {y})")
        time.sleep(0.25)
        y += 700
        h = page.evaluate("document.documentElement.scrollHeight")
    page.evaluate("window.scrollTo(0, 0)")
    time.sleep(0.5)


def block_prefetch(route) -> None:
    """Skip Next.js link prefetches (RSC fetches of every linked route) to keep the visit light."""
    h = route.request.headers
    if h.get("next-router-prefetch") or (h.get("rsc") and route.request.resource_type == "fetch"):
        route.abort()
    else:
        route.continue_()


def clip_cards(page, hrefs: list[str], path: Path) -> list[int]:
    """Screenshot the union box of the given cards, with the fixed site header hidden."""
    page.add_style_tag(content="#header{display:none!important}")
    boxes = [page.locator(f'a[href="{h}"]').bounding_box() for h in hrefs]
    x0 = min(b["x"] for b in boxes) - 12
    x1 = max(b["x"] + b["width"] for b in boxes) + 12
    doc_top = min(b["y"] for b in boxes) + page.evaluate("window.scrollY")  # boxes are viewport-relative
    page.evaluate(f"window.scrollTo(0, {max(0, doc_top - 60)})")
    time.sleep(0.8)
    boxes = [page.locator(f'a[href="{h}"]').bounding_box() for h in hrefs]
    y0 = min(b["y"] for b in boxes) - 12
    y1 = max(b["y"] + b["height"] for b in boxes) + 12
    page.screenshot(path=str(path), clip={"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0})
    return [round(v) for v in (x0, y0, x1 - x0, y1 - y0)]


def closeups(browser, url: str, out: Path) -> None:
    ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2,
                              locale="he-IL", user_agent=UA)
    page = ctx.new_page()
    page.route("**/*", block_prefetch)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_selector('a[href^="/players/"]', timeout=45000)
    settle(page)
    print("close-up GK", clip_cards(page, ["/players/4522", "/players/4548", "/players/4550"],
                                    out / "players-cards-closeup.png"), flush=True)
    print("close-up parens 1", clip_cards(page, ["/players/4549", "/players/4553"],
                                          out / "players-cards-closeup-parens-1.png"), flush=True)
    print("close-up parens 2", clip_cards(page, ["/players/4541", "/players/4543"],
                                          out / "players-cards-closeup-parens-2.png"), flush=True)
    ctx.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--chrome", default=None, help="Chromium/Chrome executable; default = Playwright's own")
    ap.add_argument("--url", default="https://www.mhaifafc.com/players")
    ap.add_argument("--closeups-only", action="store_true", help="only retake the 2x card close-ups")
    a = ap.parse_args()
    out = a.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    net = []
    result = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path=a.chrome)
        print("browser", browser.version, flush=True)
        if a.closeups_only:
            closeups(browser, a.url, out)
            browser.close()
            return 0
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1,
                                  locale="he-IL", user_agent=UA)
        page = ctx.new_page()
        page.route("**/*", block_prefetch)
        page.on("response", lambda r: net.append({"url": r.url, "status": r.status,
                                                    "type": r.request.resource_type}))
        print("goto", a.url, flush=True)
        page.goto(a.url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector('a[href^="/players/"]', timeout=45000)
        settle(page)
        scroll_through(page)
        settle(page, 1.0)
        result["w1440"] = page.evaluate(EXTRACT_JS, STYLE_PROPS)
        page.screenshot(path=str(out / "players-1440-full.png"), full_page=True)
        print("shot 1440 full", result["w1440"]["scrollHeight"], flush=True)

        page.set_viewport_size({"width": 960, "height": 900})
        time.sleep(1.0)
        scroll_through(page)
        settle(page, 1.0)
        result["w960"] = page.evaluate(EXTRACT_JS, STYLE_PROPS)
        page.screenshot(path=str(out / "players-960-full.png"), full_page=True)
        print("shot 960 full", result["w960"]["scrollHeight"], flush=True)
        ctx.close()
        closeups(browser, a.url, out)
        browser.close()
    result["network"] = net
    (out / "computed-styles.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("requests", len(net), "| wrote", out / "computed-styles.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
