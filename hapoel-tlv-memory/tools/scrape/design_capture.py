"""Design reference for the Hapoel Tel Aviv team & players page: screenshots + computed styles.

Adapted from maccabi-haifa-memory/tools/scrape/design_capture.py. Runs a standalone headless Chromium
(Playwright Python library, throwaway profile). Font files are only fetched by the browser to render the
page; nothing font-related is saved except URLs and @font-face rules.

Usage:
  uv run --with playwright python -I -u design_capture.py --out <design-dir> --chrome <chromium binary> \
      [--url <listing url>] [--member <data-id of the card whose popup to open>]

Writes into <design-dir>:
  players-1440-full.png, players-960-full.png   full-page screenshots (men's first team tab)
  players-cards-closeup.png                     three cards at 2x
  player-popup-1440.png, player-popup-960.png   one player's popup (the site's individual player view)
  computed-styles.json                          computed styles of the parts, :root vars, @font-face, network log
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
DEFAULT_URL = "https://www.htafc.co.il/%d7%a6%d7%95%d7%95%d7%aa-%d7%95%d7%a9%d7%97%d7%a7%d7%a0%d7%99%d7%9d/"

STYLE_PROPS = [
    "font-family", "font-weight", "font-size", "line-height", "letter-spacing", "color", "text-transform",
    "-webkit-text-fill-color", "-webkit-text-stroke", "background-image", "background-color", "background-size",
    "background-position", "background-clip", "text-shadow", "box-shadow", "border-radius", "border", "object-fit",
    "object-position", "opacity", "direction", "text-align", "padding", "margin", "mix-blend-mode", "filter",
]

EXTRACT_JS = """
([props, selectors]) => {
  const pick = (el) => {
    if (!el) return null;
    const cs = getComputedStyle(el);
    const out = {tag: el.tagName.toLowerCase(), cls: typeof el.className === 'string' ? el.className : null,
                 text: (el.innerText || '').trim().slice(0, 80)};
    for (const p of props) out[p] = cs.getPropertyValue(p);
    for (const pseudo of ['::before', '::after']) {
      const ps = getComputedStyle(el, pseudo);
      if (ps.content && ps.content !== 'none' && ps.content !== 'normal') {
        out[pseudo] = {content: ps.content, 'background-image': ps.backgroundImage, 'background-color': ps.backgroundColor,
                       width: ps.width, height: ps.height, opacity: ps.opacity, inset: ps.inset};
      }
    }
    const r = el.getBoundingClientRect();
    out.box = {x: Math.round(r.x), y: Math.round(r.y + scrollY), w: Math.round(r.width), h: Math.round(r.height)};
    if (el.tagName === 'IMG') { out.currentSrc = el.currentSrc; out.natural = [el.naturalWidth, el.naturalHeight]; }
    return out;
  };
  const res = {url: location.href, lang: document.documentElement.lang, dir: document.documentElement.dir,
               viewport: [innerWidth, innerHeight], scrollHeight: document.documentElement.scrollHeight};
  for (const [name, sel] of Object.entries(selectors)) res[name] = pick(document.querySelector(sel));
  const rootVars = {};
  const rs = getComputedStyle(document.documentElement);
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules; } catch (e) { continue; }
    for (const r of rules) {
      if (r.selectorText === ':root' && r.style) {
        for (const n of r.style) if (n.startsWith('--')) rootVars[n] = rs.getPropertyValue(n).trim();
      }
    }
  }
  res.root_vars = rootVars;
  const faces = [];
  for (const sheet of document.styleSheets) {
    let rules; try { rules = sheet.cssRules; } catch (e) { faces.push({sheet: sheet.href, blocked: true}); continue; }
    for (const r of rules) if (r.type === CSSRule.FONT_FACE_RULE) faces.push({sheet: sheet.href, css: r.cssText.slice(0, 600)});
  }
  res.font_face_rules = faces;
  const fonts = [];
  document.fonts.forEach(f => fonts.push({family: f.family, weight: f.weight, style: f.style, status: f.status}));
  res.fonts_loaded = fonts;
  return res;
}
"""

LISTING_SELECTORS = {
    "body": "body", "main": "main, #main, .site-main",
    "header": "header, #site-header, .site-header",
    "page_banner": ".page-banner", "page_banner_img": ".page-banner img", "page_title_h1": ".page-banner__title",
    "our_team": "section.our-team", "our_team_container": ".our-team__container",
    "tab_active": ".our-team__tab-name.active", "tab_inactive": ".our-team__tab-name:not(.active)",
    "subtab_active": ".our-team__subtab-name.active", "subtab_inactive": ".our-team__subtab-name:not(.active)",
    "row_title": "#tab-1-subtab-1 .our-team__row-title",
    "card": "#tab-1-subtab-1 .our-team__member", "card_img_wrapper": "#tab-1-subtab-1 .our-team__member-img-wrapper",
    "card_img": "#tab-1-subtab-1 .our-team__member-img", "card_bottom": "#tab-1-subtab-1 .our-team__member-bottom",
    "card_name": "#tab-1-subtab-1 .our-team__member-name", "card_button": "#tab-1-subtab-1 .our-team__member-btn",
    "footer": "footer, #site-footer",
}
POPUP_SELECTORS = {
    "popup": "#get-team-member-popup", "popup_inner": "#get-team-member-popup .popup-wrapper-inner",
    "team_popup": ".team-popup", "net": ".team-popup__net", "net_wrapper": ".team-popup__net-wrapper",
    "main": ".team-popup__main", "main_info": ".team-popup__main-info", "name": ".team-popup__name",
    "position": ".team-popup__position", "age": ".team-popup__age", "experience": ".team-popup__experience",
    "content": ".team-popup__content", "img_wrapper": ".team-popup__main-img-wrapper",
    "main_player": ".team-popup__main-player", "main_bg": ".team-popup__main-bg", "number": ".team-popup__main-number",
    "gallery": ".team-popup__gallery", "gallery_img": ".team-popup__gallery-img", "overlay": "#get-team-member-popup .my_overlay",
}


def settle(page, seconds: float = 1.5) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=30000)
    except Exception:  # noqa: BLE001  (analytics keep the network busy)
        pass
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


def block_noise(route) -> None:
    u = route.request.url
    if any(k in u for k in ("googletagmanager", "google-analytics", "recaptcha", "facebook", "hotjar", "clarity")):
        route.abort()
    else:
        route.continue_()


def accept_cookies(page) -> None:
    for label in ("Accept", "אישור", "מאשר"):
        try:
            btn = page.get_by_role("button", name=label)
            if btn.count():
                btn.first.click(timeout=2000)
                time.sleep(0.5)
                return
        except Exception:  # noqa: BLE001
            pass


def open_popup(page, member: str) -> None:
    page.locator(f'#tab-1-subtab-1 button[data-id="{member}"]').scroll_into_view_if_needed()
    time.sleep(0.5)
    page.locator(f'#tab-1-subtab-1 button[data-id="{member}"]').click()
    page.wait_for_selector("#get-team-member-popup .team-popup__name", timeout=30000)
    settle(page, 1.5)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--chrome", default=None)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--member", default="53295", help="data-id of the card whose popup is captured")
    ap.add_argument("--closeup", default="53295,53303,53302", help="data-ids of the close-up cards")
    ap.add_argument("--no-bust", action="store_true",
                    help="use the Cloudflare-cached page as is (its nonce is days old, so the popup fails with 'Invalid nonce')")
    a = ap.parse_args()
    if not a.no_bust:
        a.url += ("&" if "?" in a.url else "?") + f"hta={int(time.time())}"
    out = a.out.expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    net, result = [], {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True, executable_path=a.chrome)
        print("browser", browser.version, flush=True)
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=1, locale="he-IL", user_agent=UA)
        page = ctx.new_page()
        page.route("**/*", block_noise)
        page.on("response", lambda r: net.append({"url": r.url, "status": r.status, "type": r.request.resource_type}))
        print("goto", a.url, flush=True)
        page.goto(a.url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("#tab-1-subtab-1 .our-team__member", timeout=45000)
        settle(page)
        accept_cookies(page)
        scroll_through(page)
        settle(page, 1.0)
        result["w1440"] = page.evaluate(EXTRACT_JS, [STYLE_PROPS, LISTING_SELECTORS])
        page.screenshot(path=str(out / "players-1440-full.png"), full_page=True)
        print("shot 1440 full", result["w1440"]["scrollHeight"], flush=True)

        open_popup(page, a.member)
        result["popup_1440"] = page.evaluate(EXTRACT_JS, [STYLE_PROPS, POPUP_SELECTORS])
        page.screenshot(path=str(out / "player-popup-1440.png"))
        print("shot popup 1440", flush=True)
        page.keyboard.press("Escape")
        try:
            page.locator("#get-team-member-popup .js-popup-close").last.click(timeout=3000)
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.8)

        page.set_viewport_size({"width": 960, "height": 900})
        time.sleep(1.0)
        scroll_through(page)
        settle(page, 1.0)
        result["w960"] = page.evaluate(EXTRACT_JS, [STYLE_PROPS, LISTING_SELECTORS])
        page.screenshot(path=str(out / "players-960-full.png"), full_page=True)
        print("shot 960 full", result["w960"]["scrollHeight"], flush=True)
        open_popup(page, a.member)
        result["popup_960"] = page.evaluate(EXTRACT_JS, [STYLE_PROPS, POPUP_SELECTORS])
        page.screenshot(path=str(out / "player-popup-960.png"))
        print("shot popup 960", flush=True)
        ctx.close()

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, device_scale_factor=2, locale="he-IL", user_agent=UA)
        page = ctx.new_page()
        page.route("**/*", block_noise)
        page.goto(a.url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_selector("#tab-1-subtab-1 .our-team__member", timeout=45000)
        settle(page)
        accept_cookies(page)
        ids = a.closeup.split(",")
        cards = [page.locator(f'#tab-1-subtab-1 button[data-id="{i}"]').locator("xpath=..") for i in ids]
        cards[0].scroll_into_view_if_needed()
        time.sleep(1.0)
        boxes = [c.bounding_box() for c in cards]
        x0 = min(b["x"] for b in boxes) - 16
        x1 = max(b["x"] + b["width"] for b in boxes) + 16
        y0 = min(b["y"] for b in boxes) - 16
        y1 = max(b["y"] + b["height"] for b in boxes) + 16
        page.screenshot(path=str(out / "players-cards-closeup.png"), clip={"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0})
        print("close-up", [round(v) for v in (x0, y0, x1 - x0, y1 - y0)], flush=True)
        ctx.close()
        browser.close()
    result["network"] = net
    (out / "computed-styles.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("requests", len(net), "| wrote", out / "computed-styles.json", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
