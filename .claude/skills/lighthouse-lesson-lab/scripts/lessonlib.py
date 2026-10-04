"""lessonlib — the shared model of lighthouse-lesson-lab.

load_lesson → derive (timeline, slide numbers, prep lines, scenes) → render_lesson (Jinja2),
plus the kit (SVG sprite) and the sync of lesson-lab/lessons/_assets/.
The rules live in validate.py; build.py, build_all.py and export_pdf.py call into here.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tarfile
import tempfile
import time
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader
from markupsafe import Markup, escape

SKILL = Path(__file__).resolve().parents[1]
REPO = SKILL.parents[2]
LAB = REPO / 'lesson-lab'
LESSONS = LAB / 'lessons'
SHARED = LESSONS / '_assets'
INVENTORY = LAB / 'docs' / 'lessons.json'

REVEAL_VERSION = '5.2.1'
REVEAL_FILES = ('reveal.js', 'reveal.css', 'reset.css', 'LICENSE')
ASSET_FILES = ('lesson.css', 'slides.css', 'lesson.js', 'deck.js')

PRACTICES = {  # the 11 "חותם על זה" practices → colour family of .pr[data-f]
    'קדימה ללמידה': 'open', 'מה הקשר?': 'open',
    'כולם כותבים': 'think', 'זמן חשיבה': 'think', 'תרגילי שליפה': 'think',
    'Think–Pair–Share': 'talk', 'Jigsaw': 'talk', 'מהלכי שיח': 'talk',
    'הוצאה למשימה': 'run', 'הפסקת מוח': 'run', 'כרטיס יציאה': 'run',
}
SPOTLIGHTS = ('עניין ורלוונטיות', 'אחריות ובחירה', 'דיפרנציאליות וגיוון', 'שיתופיות בלמידה', 'הערכה ורפלקטיביות')
MONTHS = ('ספטמבר', 'אוקטובר', 'נובמבר', 'דצמבר', 'ינואר', 'פברואר', 'מרץ', 'אפריל', 'מאי', 'יוני')
GRADE_LABEL = {6: 'ו׳', 7: 'ז׳', 8: 'ח׳', 9: 'ט׳'}
SENSITIVITY = ('low', 'low-med', 'med', 'med-high', 'high')
SAFE_REQUIRED = {'med', 'med-high', 'high'}
KINDS = ('core', 'extension', 'messages', 'exit')
CORE_MINUTES = 35
LESSON_MINUTES = 45
CANVAS_W, CANVAS_H = 620, 540
COLORS = {
    'teal': '#63b1af', 'teal-deep': '#3f8f8d', 'teal-soft': '#e6f2f1',
    'orange': '#f7ae4d', 'orange-deep': '#e08f36', 'orange-soft': '#fdf0dd',
    'purple': '#8c82c1', 'purple-deep': '#6c60b0', 'purple-soft': '#eeecf7',
    'moss': '#619f88', 'moss-deep': '#4a8571', 'moss-soft': '#e7f1ec',
    'rose': '#e57373', 'blue': '#3b7ab3', 'gray': '#847c74',
    'ink': '#13100e', 'ink-2': '#4a443f', 'ink-3': '#847c74',
    'paper': '#ffffff', 'ground': '#f6f3ef', 'line': '#e8e2da',
}
TRACK_LETTERS = ('א׳', 'ב׳')
TRACK_IDS = ('a', 'b')
# composition rules of assets/art/art-guide.md (the validator warns outside them)
FOCUS_MAX, SCALE_MIN, SCALE_MAX, MARGIN, MAX_USES = 390, 0.6, 1.6, 16, 5
DETAIL_MIN = 0.4  # a small detail drawn inside a container (bubble, board, phone…) may go down to 0.4×
CONTAINERS = {'speech', 'speech-l', 'thought', 'chat', 'board', 'phone', 'phone-notify', 'laptop', 'note', 'sticky',
              'signpost', 'calendar'}
MIN_SIZE = {'circle4': 150, 'crowd': 180, 'hands-help': 160, 'school': 160, 'red-line': 300}  # width; face-*: 100
# D42: one message per slide. Longer messages get a smaller type size; above MSG_MAX the slide overflows.
MSG_TIERS = ((120, ''), (200, 'len-m'), (10_000, 'len-l'))
MSG_MAX = 300
# The cover slide carries the lesson title as it is in the inventory, at any length: longer titles step down in size
# (slides.css, .s-cover.len-*) instead of running off the slide.
COVER_TIERS = ((22, ''), (32, 'len-m'), (44, 'len-l'), (10_000, 'len-xl'))
PALETTE = {'#63b1af', '#f7ae4d', '#8c82c1', '#619f88', '#13100e', '#e57373', '#c94f4f', '#847c74', '#3b7ab3',
           '#e6f2f1', '#fdf0dd', '#eeecf7', '#e7f1ec', '#ffffff'}
PAUSE_UNKNOWN = '[דקה:שנייה]'
CLOCK_RE = re.compile(r'(\d{1,2}):([0-5]\d)')
YOUTUBE_RE = re.compile(r'(?:youtube\.com/(?:watch\?(?:[^#\s]*&)?v=|embed/|shorts/|live/)|youtu\.be/)([\w-]{11})')
SVG_NS = 'http://www.w3.org/2000/svg'
XLINK_NS = 'http://www.w3.org/1999/xlink'


class LessonError(Exception):
    """A lesson.yaml that cannot be loaded or rendered at all."""


# ----------------------------------------------------------------------------- text

def md(text) -> Markup:
    """The only inline markup: **bold** and line breaks. Everything else is escaped."""
    if text is None:
        return Markup('')
    s = str(escape(str(text).strip()))
    s = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s, flags=re.S)
    return Markup(s.replace('\n', '<br>'))


def paras(text) -> Markup:
    """Blank-line separated paragraphs (block scalars with |) → <p>…</p>."""
    parts = [p for p in re.split(r'\n\s*\n', str(text or '').strip()) if p.strip()]
    return Markup(''.join(f'<p>{md(p)}</p>' for p in parts))


def unquote(text) -> str:
    """`.say q` adds ״…״ itself, so surrounding quote marks in the YAML are dropped."""
    return str(text or '').strip().strip('״"„“”\'׳').strip()


def msg_class(text) -> str:
    n = len(str(text or '').strip())
    return next(cls for limit, cls in MSG_TIERS if n <= limit)


def cover_class(title) -> str:
    n = len(str(title or '').replace('**', '').strip())
    return next(cls for limit, cls in COVER_TIERS if n <= limit)


def cover_title(title) -> str:
    """The cover title, with a no-break space before a spaced dash so no line of it starts with "–"."""
    return re.sub(r' ([–—-]) ', chr(0xA0) + r'\1 ', str(title or ''))


def pause_label(at) -> Markup:
    """A video pause time: "1:05" (LTR), or the highlighted [דקה:שנייה] for the teacher to fill in."""
    at = str(at if at is not None else '').strip()
    if at in ('', '?', PAUSE_UNKNOWN):
        return Markup(f'<span class="fill">{PAUSE_UNKNOWN}</span>')
    return Markup(f'<span dir="ltr">{escape(at)}</span>')


def clock_secs(t) -> int | None:
    """'1:05' → 65 (minutes:seconds, as in the YouTube player); None for anything else."""
    m = CLOCK_RE.fullmatch(str(t).strip()) if isinstance(t, str) else None
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


def youtube_id(url) -> str | None:
    m = YOUTUBE_RE.search(str(url or ''))
    return m.group(1) if m else None


def video_clip(v: dict) -> tuple[int, int | None] | None:
    """(start, end) in seconds of `video.clip` — the part of the video the class watches; None without a clip."""
    clip = v.get('clip')
    if not isinstance(clip, dict):
        return None
    start, end = clock_secs(clip.get('start')), clock_secs(clip.get('end'))
    if not start and end is None:  # nothing, or the whole video
        return None
    return start or 0, end


def video_link(v: dict) -> str:
    """The video link in המערך and on the deck. Without a clip — `url` as written. With a clip on YouTube — the watch
    page, opening at the clip (&t=). Never an embed link with start/end: opened from a link it fails (error 153)."""
    url = str(v.get('url') or '')
    clip, vid = video_clip(v), youtube_id(url)
    if not clip or not vid:
        return url
    return f'https://www.youtube.com/watch?v={vid}' + (f'&t={clip[0]}s' if clip[0] else '')


def clip_text(v: dict, pauses: list[dict]) -> dict | None:
    """The wording of a clip in המערך: what to show (after "לפני השיעור") and where to stop (instead of
    "ממשיכים עד הסוף"). None without a clip."""
    clip = video_clip(v)
    if not clip:
        return None
    start, end = clip
    raw = v['clip']
    s, e = pause_label(raw.get('start')), pause_label(raw.get('end'))
    linked = bool(youtube_id(v.get('url')))
    if start and end is not None:
        prep = Markup(f'מקרינים רק את הקטע מ־{s} עד {e}')
    elif start:
        prep = Markup(f'מקרינים מ־{s} עד הסוף')
    else:
        prep = Markup(f'מקרינים רק את ההתחלה, עד {e}.')
    if start:
        prep += Markup(f' — הקישור כבר מתחיל ב־{s}.' if linked else f' — קדמי את הסרטון ל־{s} לפני השיעור.')
    stops = [clock_secs(p.get('at')) for p in pauses if isinstance(p, dict)]
    if end is None:
        tail = Markup('ממשיכים עד הסוף.')
    elif any(t is not None and t >= end for t in stops):
        tail = Markup('')  # the last pause is the end of the clip
    else:
        tail = Markup(f'ממשיכים עד {e} ועוצרים — כאן נגמר הקטע.')
    span = (Markup(f'מ־{s} עד {e}') if start and end is not None else
            Markup(f'מ־{s} עד הסוף') if start else Markup(f'עד {e}'))
    return {'prep': prep, 'tail': tail, 'span': span}


def source_slides(v) -> list[int] | None:
    """`source_slide.slides` → the slide numbers of the original deck: 19 or [19, 24]; None when malformed."""
    s = v.get('slides') if isinstance(v, dict) else None
    nums = [s] if isinstance(s, int) else s if isinstance(s, list) else None
    if not nums or not all(isinstance(n, int) and not isinstance(n, bool) and n > 0 for n in nums):
        return None
    return nums


def source_label(nums: list[int]) -> str:
    """'שקף 19' · 'שקפים 19, 24' — slides of the original deck, as given (not a range)."""
    return f'שקף {nums[0]}' if len(nums) == 1 else 'שקפים ' + ', '.join(str(n) for n in nums)


def src_url(data: dict) -> str:
    """The original deck: the lesson's src_url, or the one in docs/lessons.json."""
    return str(data.get('src_url') or (inventory().get(data.get('_slug')) or {}).get('src_url') or '')


def minutes_label(sec: int) -> str:
    sec = int(sec)
    if sec < 60:
        return f'{sec} שניות'
    m, s = divmod(sec, 60)
    if s == 0:
        return 'דקה' if m == 1 else f'{m} דקות'
    if s == 30:
        return 'דקה וחצי' if m == 1 else f'{m} דקות וחצי'
    return f'{m}:{s:02d} דקות'


def section_clean(section: str) -> str:
    """'חברות, סובלנות ומניעת אלימות (אוקטובר)' → without the trailing month."""
    return re.sub(r'\s*\([^)]*\)\s*$', '', str(section or '')).strip()


def lesson_no(data: dict) -> str:
    """'שיעור N' for a lesson in a unit of several — '' for a one-lesson unit, or when the title already says it
    ("הפיל והיתד – שיעור 1"), so the cover and the hub never print it twice."""
    n = data.get('unit_order')
    if not n or data.get('unit_size') == 1 or f'שיעור {n}' in str(data.get('title') or ''):
        return ''
    return f'שיעור {n}'


def months_of(month: str) -> list[str]:
    """'ספטמבר–נובמבר' → every month the range spans, in school-year order."""
    parts = [p.strip() for p in re.split(r'[–-]', str(month or '')) if p.strip()]
    idx = [MONTHS.index(p) for p in parts if p in MONTHS]
    if not idx:
        return []
    return list(MONTHS[min(idx):max(idx) + 1])


# ----------------------------------------------------------------------------- do the words fit the slide?
# skill-fixes #27: the height of a slide's words, estimated from the text, so the validator warns before shoot.py
# measures. The box and the type mirror assets/slides.css — change both together. The slide is 1440×810, and .frame
# (padding 64/96/96, gap 56, a picture column of 620 — 460 on the exit ticket) leaves the words 572px (732) × 650px:
# the box shoot.py checks. Calibrated on all 1625 slides of 100 built decks: the line counts are Chrome's, except
# for a line that ends a hair's breadth from the edge.
FIT_BOX_H = 650
FIT_COL = {'': 572, 's-exit': 732}
FIT_TYPE = {  # element: (advance table, font size px, line height px, letter-spacing em)
    'kicker': ('bold', 30, 30.0, 0.0),      # .kicker — Assistant 800; reveal's line height (1)
    'title': ('display', 66, 75.9, -0.01),  # h2 — Secular One, line-height 1.15, letter-spacing -.01em
    'sub': ('body', 36, 50.4, 0.0),         # .sub — line-height 1.4, max-width 26ch
    'points': ('body', 36, 46.8, 0.0),      # .pts li — line-height 1.3
}
FIT_MARGIN = {'kicker': (0, 14), 'title': (0, 18), 'sub': (0, 14), 'points': (22, 0), 'link': (26, 0)}  # top, bottom
FIT_SUB_CH = 26              # .sub max-width, in widths of "0"
FIT_POINT_NUMBER = 64        # .pts li padding-right: the column of the number
FIT_POINT_BOX = 14 + 14 + 2  # .pts li padding-top + padding-bottom + border-top
FIT_LINK_H = 58              # .go (the video button) — 30px + padding 14/14
# A line that ends a hair's breadth from the edge counts as fitting: the estimate errs low, so a warning means words
# that really are too tall. shoot.py measures exactly.
FIT_SLACK = 1.005

# Advance widths of the deck fonts (Google Fonts, measured in Chrome with canvas measureText), in thousandths of an em.
# Combining marks (niqqud, cantillation) take no room; a character that is not here counts as ADV_OTHER.
_ADV_CHARS = (' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_`abcdefghijklmnopqrstuvwxyz{|}~'
              '\xa0·־אבגדהוזחטיךכלםמןנסעףפץצקרשת׳״–—‘’“”„•…₪←→')
_ADV_DATA = {
    'body': (  # Assistant 400 — .sub, .pts li
        '200 282 409 492 492 817 600 242 297 297 412 492 242 308 242 352 492 451 492 492 492 492 492 492 492 492 '
        '242 242 492 492 492 419 839 539 585 569 613 524 490 614 648 257 475 573 481 721 644 661 562 661 563 530 '
        '533 643 509 782 505 468 539 297 352 297 492 500 540 501 551 454 552 492 284 500 540 242 242 487 250 825 '
        '543 540 552 552 340 416 331 540 459 710 436 459 419 297 237 297 492 200 242 315 560 526 372 535 546 224 '
        '361 563 553 224 503 471 476 580 605 224 368 565 531 547 541 466 516 549 472 630 605 213 388 480 800 242 '
        '242 409 409 409 298 998 734 1000 1000'
    ),
    'bold': (  # Assistant 800 — .kicker, **bold**
        '200 360 580 540 540 860 690 320 360 360 472 540 320 340 320 334 540 492 540 540 540 540 540 540 540 540 '
        '320 320 540 540 540 478 924 584 612 586 642 556 536 646 682 316 520 628 530 776 672 692 608 692 630 564 '
        '564 672 572 824 588 544 542 360 334 360 540 500 560 536 580 472 580 526 360 546 582 288 290 568 298 868 '
        '582 560 580 580 418 452 400 578 544 798 540 542 474 360 278 360 540 200 320 336 649 552 452 546 588 278 '
        '383 613 612 278 517 493 510 598 662 278 388 627 601 573 566 570 583 613 497 705 651 302 492 480 800 320 '
        '320 580 580 580 360 994 896 1000 1000'
    ),
    'display': (  # Secular One — titles; its bold is synthetic, with the same advances
        '200 391 608 693 581 786 684 346 399 400 570 650 346 541 336 507 586 438 517 486 574 491 542 473 561 542 '
        '386 410 650 650 650 511 823 679 569 594 685 530 517 688 716 301 338 615 485 911 719 741 547 746 560 541 '
        '568 696 644 1022 673 607 590 324 488 324 674 585 600 557 577 480 577 563 452 577 606 398 303 545 393 943 '
        '612 604 577 577 399 469 421 599 547 850 545 542 503 378 490 378 650 200 306 450 583 536 407 526 586 333 '
        '400 605 591 326 470 504 473 609 633 330 389 616 562 546 564 509 515 590 468 737 656 306 568 696 962 316 '
        '306 578 578 568 463 896 1091 1000 1000'
    ),
}
ADVANCE = {k: dict(zip(_ADV_CHARS, (int(x) / 1000 for x in v.split()))) for k, v in _ADV_DATA.items()}
assert all(len(v.split()) == len(_ADV_CHARS) for v in _ADV_DATA.values()), 'a width table and _ADV_CHARS differ'
ADV_OTHER = 0.55


def advance(ch: str, table: str) -> float:
    """The advance width of one character, in em."""
    return 0.0 if unicodedata.combining(ch) else ADVANCE[table].get(ch, ADV_OTHER)


def text_lines(text, width: float, table: str, size: float, spacing: float = 0.0) -> int:
    """How many lines `text` takes in a box `width` px wide, the way Chrome wraps it: greedy, breaking at spaces only;
    a line break in the text (YAML `|`, rendered <br>) starts a new line; **bold** in Assistant 800. 0 when empty."""
    s = str(text or '').strip()
    if not s:
        return 0
    room, lines, line, word, gap = width * FIT_SLACK, 1, 0.0, 0.0, 0.0

    def place():  # the word just read goes on this line, or opens the next one
        nonlocal lines, line, word, gap
        if word:
            if line and line + gap + word > room:
                lines, line = lines + 1, word
            else:
                line += gap + word
            word, gap = 0.0, 0.0

    for i, part in enumerate(re.split(r'\*\*(.+?)\*\*', s, flags=re.S)):  # odd parts were **bold**
        t = 'bold' if i % 2 and table == 'body' else table
        for ch in part:
            if ch == '\n':
                place()
                lines, line, gap = lines + 1, 0.0, 0.0
            elif ch in ' \t':
                place()
                if line:  # spaces collapse into one, and a line never starts with one
                    gap = (advance(' ', t) + spacing) * size
            else:
                word += (advance(ch, t) + spacing) * size
    place()
    return lines


def slide_fit(kicker='', title='', sub='', points=(), *, wide: bool = False, link: bool = False) -> tuple[float, dict]:
    """(the estimated height in px of the words of one deck slide — the block shoot.py measures against FIT_BOX_H —,
    the number of lines of each element: {'kicker': n, 'title': n, 'sub': n, 'points': [n, …]})."""
    col = FIT_COL['s-exit' if wide else '']
    width = {'kicker': col, 'title': col, 'sub': FIT_SUB_CH * advance('0', 'body') * FIT_TYPE['sub'][1],
             'points': col - FIT_POINT_NUMBER}
    parts, lines = [], {}
    for key, text in (('kicker', kicker), ('title', title), ('sub', sub)):
        table, size, lh, spacing = FIT_TYPE[key]
        n = text_lines(text if isinstance(text, str) else '', width[key], table, size, spacing)
        if n:
            parts.append((key, n * lh))
            lines[key] = n
    pts = [p for p in (points if isinstance(points, list) else []) if isinstance(p, str)]
    if pts:
        table, size, lh, spacing = FIT_TYPE['points']
        lines['points'] = [text_lines(p, width['points'], table, size, spacing) for p in pts]
        parts.append(('points', sum(n * lh + FIT_POINT_BOX for n in lines['points'])))
    if link:
        parts.append(('link', FIT_LINK_H))
    height, prev = 0.0, None
    for key, h in parts:
        if prev:  # block margins collapse; the button is inline-flex, so its margin adds to the one above it
            above, below = FIT_MARGIN[prev][1], FIT_MARGIN[key][0]
            height += above + below if key == 'link' else max(above, below)
        height, prev = height + h, key
    return height, lines


# ----------------------------------------------------------------------------- load

def load_lesson(lesson_dir: Path) -> dict:
    path = Path(lesson_dir) / 'lesson.yaml'
    if not path.exists():
        raise LessonError(f'אין {path}')
    raw = path.read_text(encoding='utf-8')
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as e:
        hint = ('רמז: ערך שמתחיל ב־** או שיש בו ": " (נקודתיים ורווח) או " #" — כתבי אותו כבלוק `>-` '
                'בשורה הבאה, או עטפי במירכאות. ברשימה בסוגריים [ … ] אסור "?" או "," בתוך ערך '
                '(למשל "מה הקשר?") — כתבי רשימה בשורות, "- ערך" בכל שורה.')
        raise LessonError(f'שגיאת YAML ב-{path}:\n{e}\n{hint}') from e
    if not isinstance(data, dict):
        raise LessonError(f'{path}: הקובץ צריך להיות מילון של שדות')
    data['_raw'] = raw
    data['_dir'] = Path(lesson_dir)
    data['_slug'] = Path(lesson_dir).name
    return data


def kind_of(step: dict) -> str:
    return step.get('kind') or 'core'


def blocks_of(step_or_track: dict, key: str = 'body') -> list[tuple[str, object]]:
    out = []
    for b in step_or_track.get(key) or []:
        if isinstance(b, dict) and len(b) == 1:
            (k, v), = b.items()
            out.append((k, v))
        elif isinstance(b, str):
            out.append(('p', b))
        else:
            out.append(('?', b))
    return out


def inventory() -> dict:
    """docs/lessons.json keyed by slug ({} when absent)."""
    try:
        data = json.loads(INVENTORY.read_text(encoding='utf-8'))
        return {x['slug']: x for x in data.get('lessons', [])}
    except (OSError, ValueError, KeyError):
        return {}


# ----------------------------------------------------------------------------- kit

def kit_path() -> Path:
    path = SKILL / 'assets' / 'art' / 'kit.svg'
    if not path.exists():
        raise LessonError(f'ערכת האיורים חסרה: {path}')
    return path


def _vb(value: str | None) -> tuple[float, float, float, float]:
    try:
        x, y, w, h = (float(v) for v in re.split(r'[\s,]+', (value or '').strip()))
        return x, y, w, h
    except ValueError:
        return 0.0, 0.0, 100.0, 100.0


class Kit:
    """The shared sprite: <symbol>s plus filters/patterns, subset per deck and inlined."""

    def __init__(self, path: Path | None = None):
        self.path = path or kit_path()
        ET.register_namespace('', SVG_NS)
        ET.register_namespace('xlink', XLINK_NS)
        root = ET.fromstring(self.path.read_text(encoding='utf-8'))
        self.order: list[str] = []
        self.symbols: dict[str, tuple[tuple[float, float, float, float], ET.Element]] = {}
        self.defs: dict[str, ET.Element] = {}
        self.styles: list[ET.Element] = []
        candidates = []
        for child in root:
            tag = child.tag.split('}')[-1]
            if tag == 'defs':
                candidates.extend(list(child))
            else:
                candidates.append(child)
        for el in candidates:
            tag = el.tag.split('}')[-1]
            if tag == 'style':
                self.styles.append(el)
                continue
            i = el.get('id')
            if not i:
                continue
            self.order.append(i)
            if tag == 'symbol':
                self.symbols[i] = (_vb(el.get('viewBox')), el)
            else:
                self.defs[i] = el
        self.tokens = {i for i, el in self.defs.items() if el.tag.endswith('}g') or el.tag == 'g'}
        self.rough = next((i for i, el in self.defs.items()
                           if el.tag.endswith('filter') and 'rough' in i), None)

    def has(self, sid: str) -> bool:
        return sid in self.symbols or sid in self.tokens

    def default_color(self, sid: str) -> str | None:
        return self.symbols[sid][1].get('data-color') if sid in self.symbols else None

    @staticmethod
    def _xml(el: ET.Element) -> str:
        s = ET.tostring(el, encoding='unicode')
        return re.sub(r'\sxmlns(:\w+)?="[^"]+"', '', s)

    def subset(self, used: set[str]) -> Markup:
        need, stack = set(), list(used) + ([self.rough] if self.rough else [])
        while stack:
            i = stack.pop()
            if i in need:
                continue
            el = self.symbols[i][1] if i in self.symbols else self.defs.get(i)
            if el is None:
                continue
            need.add(i)
            stack.extend(re.findall(r'(?:href="#|url\(#)([^")]+)', self._xml(el)))
        parts = [self._xml(s) for s in self.styles]
        for i in self.order:
            if i in need:
                parts.append(self._xml(self.symbols[i][1] if i in self.symbols else self.defs[i]))
        return Markup('<svg class="kit" width="0" height="0" aria-hidden="true" focusable="false" '
                      'style="position:absolute;width:0;height:0;overflow:hidden"><defs>'
                      + ''.join(parts) + '</defs></svg>')


def _color(c, default: str | None = None) -> str:
    if not c:
        return default or COLORS['ink']
    c = str(c).strip()
    return COLORS.get(c, c if re.fullmatch(r'#[0-9a-fA-F]{3,8}', c) else COLORS['ink'])


def art_symbols(spec) -> list[str]:
    """Kit ids a scene uses (for validation and subsetting)."""
    if isinstance(spec, str):
        return [spec]
    if isinstance(spec, list):
        return [str(p['use']) for p in spec if isinstance(p, dict) and p.get('use')]
    return []


def render_art(spec, kit: Kit, lesson_dir: Path, label: str, used: set[str]) -> Markup:
    """A slide scene on the 620×540 canvas (the kit's units): one symbol fitted to the canvas,
    a list of placements ({use, x, y, w?, h?, color?, flip?, rotate?} with x,y = top-left, natural size by
    default; {use: <token>, x, y, color?, scale?} for <g> tokens such as #kid; {text, x, y, size?, color?}
    centred), or {file: art/x.svg} — a lesson-only SVG."""
    label_attr = escape(re.sub(r'\*\*', '', str(label or '')))
    if isinstance(spec, dict) and spec.get('file'):
        path = Path(lesson_dir) / str(spec['file'])
        if not path.exists():
            return Markup('')
        svg = path.read_text(encoding='utf-8')
        svg = re.sub(r'<\?xml[^>]*\?>|<!--.*?-->|<!DOCTYPE[^>]*>', '', svg, flags=re.S).strip()
        used.update(re.findall(r'href="#([^"]+)"', svg))
        svg = re.sub(r'<svg\b', f'<svg role="img" aria-label="{label_attr}"', svg, count=1)
        return Markup(svg)
    single = isinstance(spec, str)
    items = [{'use': spec}] if single else (spec if isinstance(spec, list) else [])
    shapes, texts = [], []
    for it in items:
        if not isinstance(it, dict):
            continue
        if it.get('use'):
            sid = str(it['use'])
            used.add(sid)
            if sid in kit.tokens:
                sc = float(it.get('scale', 3 if single else 1))
                x, y = float(it.get('x', CANVAS_W / 2)), float(it.get('y', CANVAS_H * .7))
                shapes.append(f'<g fill="{_color(it.get("color"))}" transform="translate({x:.1f} {y:.1f}) '
                              f'scale({sc:g})"><use href="#{escape(sid)}"/></g>')
                continue
            vb = kit.symbols.get(sid, ((0, 0, 100, 100), None))[0]
            vw, vh = vb[2] or 100, vb[3] or 100
            if single:  # the focus of the scene: long side up to 390 units, never past 1.6× natural (art-guide.md)
                scale = min(FOCUS_MAX / max(vw, vh), SCALE_MAX)
                w, h = vw * scale, vh * scale
                x, y = (CANVAS_W - w) / 2, (CANVAS_H - h) / 2
            else:
                w = float(it.get('w', it['h'] * vw / vh if it.get('h') else vw))
                h = float(it.get('h', w * vh / vw))
                x, y = float(it.get('x', (CANVAS_W - w) / 2)), float(it.get('y', (CANVAS_H - h) / 2))
            tf = []
            if it.get('rotate'):  # degrees, around the centre of the symbol's box
                tf.append(f'rotate({float(it["rotate"]):g} {x + w / 2:.1f} {y + h / 2:.1f})')
            if it.get('flip'):
                tf.append(f'translate({2 * x + w:.1f} 0) scale(-1 1)')
            transform = f' transform="{" ".join(tf)}"' if tf else ''
            shapes.append(f'<use href="#{escape(sid)}" x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
                          f'color="{_color(it.get("color"), kit.default_color(sid))}"{transform}/>')
        elif it.get('text') is not None:
            size = float(it.get('size', 34))
            texts.append(f'<text x="{float(it.get("x", CANVAS_W / 2)):.1f}" y="{float(it.get("y", CANVAS_H / 2)):.1f}" '
                         f'font-size="{size:.0f}" text-anchor="middle" dominant-baseline="middle" '
                         f'fill="{_color(it.get("color"))}">{escape(str(it["text"]))}</text>')
    rough = f' filter="url(#{kit.rough})"' if kit.rough else ''
    return Markup(f'<svg viewBox="0 0 {CANVAS_W} {CANVAS_H}" role="img" aria-label="{label_attr}">'
                  f'<g{rough}>{"".join(shapes)}</g>{"".join(texts)}</svg>')


# ----------------------------------------------------------------------------- derive

def slide_label(nums: list[int]) -> str:
    if not nums:
        return ''
    return f'שקף {nums[0]}' if len(nums) == 1 else f'שקפים {nums[0]}–{nums[-1]}'


def tags_union(*lists) -> list:
    out = []
    for lst in lists:
        for x in lst or []:
            if x not in out:
                out.append(x)
    return out


def step_tags(step: dict, key: str) -> list:
    """A step's practices/spotlights: its own, plus those of its tracks (D45: every track has its own tags)."""
    own = list(step.get(key) or [])
    for typ, v in blocks_of(step):
        if typ == 'tracks' and isinstance(v, list):
            for tr in v:
                if isinstance(tr, dict):
                    own = tags_union(own, tr.get(key))
    return own


def derive(data: dict, kit: Kit) -> dict:
    """Everything the templates need, computed from lesson.yaml: times, slides, refs, prep lines."""
    lesson_dir = data['_dir']
    steps = [s for s in (data.get('steps') or []) if isinstance(s, dict)]
    used: set[str] = set()
    slides: list[dict] = []
    deck_url = src_url(data)

    def add_slide(step_id, *, kicker='', title='', sub='', points=None, art=None, timer=None,
                  link=None, link_label=None, cls='', h1=False, alt=None, track=None):
        n = len(slides) + 1
        slides.append({
            'n': n, 'step': step_id, 'track': track, 'cls': cls, 'h1': h1,
            'kicker': md(kicker), 'title': md(title), 'sub': md(sub),
            'points': [md(p) for p in (points or [])],
            'art': render_art(art, kit, lesson_dir, alt or title, used),
            'timer': int(timer) if timer else 0,
            'timer_label': minutes_label(timer) if timer else '',
            'link': link, 'link_label': link_label,
        })
        return n

    cover = data.get('cover') or {}
    unit_line = section_clean(data.get('section'))
    unit = data.get('unit') or ''
    kicker = ' · '.join(x for x in (unit, lesson_no(data)) if x)
    title = data.get('title', '')
    add_slide(None, kicker=kicker, title=cover_title(title), sub=cover.get('sub', ''), art=cover.get('art'),
              cls=f's-cover {cover_class(title)}'.strip(), h1=True, alt=cover.get('alt') or title)

    # timeline: content steps from 0′, extensions as +N′, closing steps anchored to the bell
    content = [s for s in steps if kind_of(s) == 'core']
    closing = [s for s in steps if kind_of(s) in ('messages', 'exit')]
    times = {}
    t = 0
    for s in content:
        m = int(s.get('minutes') or 0)
        times[id(s)] = (t, t + m)
        t += m
    end = LESSON_MINUTES
    for s in reversed(closing):
        m = int(s.get('minutes') or 0)
        times[id(s)] = (end - m, end)
        end -= m
    last_content = content[-1] if content else None

    by_id = {s.get('id'): s for s in steps}
    brain = data.get('brain_break') or {}
    brain_after = brain.get('after')
    if not brain_after and content:
        brain_after = min(content, key=lambda s: (abs(times[id(s)][1] - 20), times[id(s)][1])).get('id')

    def tagviews(practices, spotlights):
        return ([{'name': p, 'f': PRACTICES.get(p, 'think') if isinstance(p, str) else 'think'}
                 for p in practices or []], list(spotlights or []))

    def make_blocks(owner: dict, step_id, track=None) -> list[dict]:
        """The blocks of a step body or of a track body, in reading order; slides are numbered as they come."""
        first = None
        out = []
        after_tracks = False
        for typ, v in blocks_of(owner):
            b = {'type': typ, 'v': v}
            if after_tracks:
                b['both'] = True  # the first shared block after the two tracks: "בשני המסלולים"
                after_tracks = False
            if typ == 'slide' and isinstance(v, dict):
                n = add_slide(step_id, kicker=v.get('kicker', ''), title=v.get('title', ''), sub=v.get('sub', ''),
                              points=v.get('points'), art=v.get('art'), timer=v.get('timer'), alt=v.get('alt'),
                              track=track)
                b['n'], b['first'] = n, first is None
                first = first or n
                b['s'] = slides[n - 1]
                b['echo'] = bool(v.get('echo'))
                b['cue'] = md(v.get('cue', ''))
            elif typ == 'video' and isinstance(v, dict):
                link = video_link(v)
                n = add_slide(step_id, kicker='לפני שצופים', title=v.get('before', ''), art=v.get('art'),
                              link=link, cls='s-video', alt=v.get('alt'), track=track)
                b['n'], b['first'] = n, first is None
                first = first or n
                b['s'] = slides[n - 1]
                pauses = [p for p in (v.get('pauses') or []) if isinstance(p, dict)]
                b['pauses'] = [{'at': pause_label(p.get('at')), 'moment': p.get('moment', ''),
                                'ask': unquote(p.get('ask', ''))} for p in pauses]
                b['watch'] = unquote(v.get('watch', ''))
                b['link'] = link
                b['clip'] = clip_text(v, pauses)
            elif typ == 'messages' and isinstance(v, dict):
                # D42: every message verbatim in המערך; in the deck one message per slide
                items = [x for x in (v.get('items') or []) if isinstance(x, str)]
                head = v.get('title') or 'חשוב לזכור'
                nums = []
                for i, item in enumerate(items):
                    kicker = head if len(items) == 1 else f'{head} · {i + 1} מתוך {len(items)}'
                    nums.append(add_slide(step_id, kicker=kicker, title=item, art=v.get('art'),
                                          cls=f's-msg {msg_class(item)}'.strip(), alt=v.get('alt'), track=track))
                b['nums'], b['first'] = nums, first is None
                b['n'] = nums[0] if nums else None
                b['label'] = slide_label(nums)
                first = first or (nums[0] if nums else None)
                b['items'] = items
                b['head'] = head
            elif typ == 'exit' and isinstance(v, dict):
                n = add_slide(step_id, kicker='כרטיס יציאה', title=v.get('title', ''), points=v.get('prompts'),
                              art=v.get('art'), timer=v.get('timer'), cls='s-exit', alt=v.get('alt'), track=track)
                b['n'], b['first'] = n, first is None
                first = first or n
            elif typ == 'source_slide' and isinstance(v, dict):
                # an image that exists only in the original deck (a painting, game cards, a photo): the teacher
                # switches to that deck; our deck holds a placeholder slide that says where to (skill-fixes #24)
                b['label'] = source_label(source_slides(v) or [0])
                b['url'] = deck_url
                n = add_slide(step_id, kicker='מהמצגת המקורית', title='עוברים למצגת המקורית', sub=b['label'],
                              art=v.get('art') or 'laptop', link=deck_url or None, link_label='למצגת המקורית ←',
                              cls='s-source', alt=v.get('alt') or 'מחשב נייד — עוברים למצגת המקורית', track=track)
                b['n'], b['first'] = n, first is None
                first = first or n
            elif typ == 'tracks' and isinstance(v, list) and track is None:
                tracks = []
                for ti, tr in enumerate(v[:2]):
                    if not isinstance(tr, dict):
                        continue
                    key = f'{step_id}-{TRACK_IDS[ti]}'
                    tblocks = make_blocks(tr, step_id, track=key)
                    nums = [sl['n'] for sl in slides if sl.get('track') == key]
                    pr, sp = tagviews(tr.get('practices'), tr.get('spotlights'))
                    tracks.append({**tr, 'letter': TRACK_LETTERS[ti], 'id': key, 'cls': f't{ti + 1}',
                                   'blocks': tblocks, 'nums': nums, 'label': slide_label(nums),
                                   'href': f'slides.html#/{nums[0] - 1}' if nums else '',
                                   'practices': pr, 'spotlights': sp})
                b['tracks'] = tracks
                track_first = next((t['nums'][0] for t in tracks if t['nums']), None)
                first = first or track_first
                after_tracks = True
            elif typ in ('say', 'ask'):
                b['v'] = unquote(v)
            out.append(b)
        return out

    views = []
    for idx, s in enumerate(steps):
        k = kind_of(s)
        step_id = s.get('id')
        blocks = make_blocks(s, step_id)
        nums = [sl['n'] for sl in slides if sl['step'] == step_id] if step_id else []
        start, end_ = times.get(id(s), (None, None))
        if k == 'extension':
            time_label, table_time = f'+{s.get("minutes")}′', f'+{s.get("minutes")}′'
        else:
            time_label = f'{start}′–{end_}′' if start is not None else ''
            table_time = f'{start}′' if start is not None else ''
        tail = []
        if s is last_content:
            tm = data.get('time') or {}
            if tm.get('clock'):
                tail.append({'type': 'whisper', 'v': tm['clock']})
            short = tm.get('short') or {}
            if short.get('text'):
                txt = str(short['text']).strip().rstrip('.').strip()
                txt = re.sub(r'^אם חסר זמן( גם לליבה)?\s*[—–-]\s*', '', txt)
                tail.append({'type': 'whisper', 'v': f'אם חסר זמן גם לליבה — {txt}. על כרטיס היציאה לא מוותרים.'})
        if brain and step_id and step_id == brain_after:
            nxt = steps[idx + 1] if idx + 1 < len(steps) else None
            src = by_id.get(brain.get('from'))
            tail.append({'type': 'brain', 'next': (nxt or {}).get('title', ''), 'signs': brain.get('signs', ''),
                         'ideas': brain.get('ideas') or [],
                         'from': (src or {}).get('title', ''), 'from_ext': kind_of(src or {}) == 'extension'})
        track_block = next((b for b in blocks if b['type'] == 'tracks'), None)
        track_names = (' · '.join(f'מסלול {t["letter"]}: {t.get("title", "")}' for t in track_block['tracks'])
                       if track_block else '')
        pr, sp = tagviews(step_tags(s, 'practices'), step_tags(s, 'spotlights'))
        views.append({
            'id': step_id, 'kind': k, 'title': s.get('title', ''),
            'display_title': ('אם נשאר זמן: ' + str(s.get('title', ''))) if k == 'extension' else s.get('title', ''),
            'minutes': s.get('minutes'), 'start': start, 'end': end_,
            'time_label': time_label, 'table_time': table_time,
            'practices': pr, 'spotlights': sp,
            'summary': s.get('summary', ''), 'track_names': track_names, 'blocks': blocks, 'tail': tail,
            'slides': nums, 'slide_label': slide_label(nums),
            'slide_href': f'slides.html#/{nums[0] - 1}' if nums else '',
        })

    # prep: the deck first, then the author's lines, then what the steps imply
    prep = [Markup(f'<a href="slides.html">המצגת</a> ({len(slides)} שקפים), פתוחה במחשב הכיתה לפני השיעור · '
                   f'גיבוי: <a href="slides.pdf">PDF</a>')]
    prep += [md(p) for p in (data.get('prep') or [])]

    def prep_from(blocks, where, prefix=''):
        for b in blocks:
            if b['type'] == 'handout' and isinstance(b['v'], dict):
                prep.append(md(f'{prefix}{b["v"].get("title", "")} — {b["v"].get("copies", "")} ({where})'))
            elif b['type'] == 'video' and isinstance(b['v'], dict):
                vv = b['v']
                length = f' ({vv["length"]})' if vv.get('length') else ''
                marks = 'עם נקודות העצירה מסומנות' if len(b['pauses']) > 1 else 'עם נקודת העצירה מסומנת'
                span = Markup(' (מקרינים {})').format(b['clip']['span']) if b.get('clip') else ''
                prep.append(Markup(f'{escape(prefix)}הסרטון <a href="{escape(b.get("link") or vv.get("url", ""))}" '
                                   f'target="_blank" rel="noopener">״{escape(vv.get("title", ""))}״</a>{escape(length)} '
                                   f'— פתוח במחשב הכיתה, {marks}{span}'))
            elif b['type'] == 'source_slide' and isinstance(b['v'], dict):
                deck = (Markup('<a href="{}" target="_blank" rel="noopener">המצגת המקורית</a>').format(b['url'])
                        if b.get('url') else Markup('המצגת המקורית'))
                prep.append(Markup('{}{} — פתוחה במחשב הכיתה לצד המצגת שלנו; מציגים ממנה את {} ({})').format(
                    prefix, deck, b['label'], where))
            elif b['type'] == 'exit' and isinstance(b['v'], dict):
                prep.append(md({'board': 'פתקים או חצאי דפים לכרטיס היציאה, לכל הכיתה',
                                'sticky': 'פתקיות דביקות לכרטיס היציאה, לכל הכיתה',
                                'print': 'כרטיס היציאה מודפס — עותק לכל תלמיד'}.get(b['v'].get('form'), '')))
            elif b['type'] == 'tracks':
                for t in b['tracks']:
                    tp = f'במסלול ״{t.get("title", "")}״: '
                    for line in t.get('prep') or []:
                        prep.append(md(f'{tp}{line}'))
                    prep_from(t['blocks'], where, tp)

    for v_ in views:
        prep_from(v_['blocks'], f'בשלב ״{v_["display_title"]}״')

    n_core = sum(1 for v_ in views if v_['kind'] != 'extension')
    n_ext = sum(1 for v_ in views if v_['kind'] == 'extension')
    return {
        'L': data, 'slug': data['_slug'], 'steps': views, 'slides': slides, 'prep': [p for p in prep if p],
        'kit_defs': kit.subset(used), 'kit_used': used,
        'grade_label': GRADE_LABEL.get(data.get('grade'), str(data.get('grade', ''))),
        'unit_line': ' · '.join(x for x in [unit_line, unit, lesson_no(data)] if x),
        'core_minutes': sum(int(s.get('minutes') or 0) for s in steps if kind_of(s) != 'extension'),
        'ext_minutes': sum(int(s.get('minutes') or 0) for s in steps if kind_of(s) == 'extension'),
        'n_core': n_core, 'n_ext': n_ext,
    }


# ----------------------------------------------------------------------------- render

def env() -> Environment:
    e = Environment(loader=FileSystemLoader(str(SKILL / 'templates')), autoescape=True,
                    trim_blocks=True, lstrip_blocks=True)
    e.filters['md'] = md
    e.filters['paras'] = paras
    e.globals['COLORS'] = COLORS
    return e


def write_atomic(path: Path, content: str | bytes) -> bool:
    """Write via temp file + rename; returns False when the content is already there."""
    path = Path(path)
    data = content.encode('utf-8') if isinstance(content, str) else content
    if path.exists() and path.read_bytes() == data:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.' + path.name + '.')
    with os.fdopen(fd, 'wb') as f:
        f.write(data)
    os.chmod(tmp, 0o644)  # mkstemp creates 0600
    os.replace(tmp, path)
    return True


def render_lesson(data: dict, kit: Kit) -> tuple[str, str, dict]:
    ctx = derive(data, kit)
    e = env()
    return e.get_template('lesson.html.j2').render(**ctx), e.get_template('slides.html.j2').render(**ctx), ctx


# ----------------------------------------------------------------------------- shared assets

def ensure_reveal() -> None:
    dst = SHARED / 'reveal'
    version = dst / 'VERSION'
    if version.exists() and version.read_text().strip() == REVEAL_VERSION and all((dst / f).exists() for f in REVEAL_FILES):
        return
    url = f'https://registry.npmjs.org/reveal.js/-/reveal.js-{REVEAL_VERSION}.tgz'
    with urllib.request.urlopen(url, timeout=60) as r:
        blob = r.read()
    with tarfile.open(fileobj=io.BytesIO(blob), mode='r:gz') as tar:
        for name in REVEAL_FILES:
            member = f'package/{name}' if name == 'LICENSE' else f'package/dist/{name}'
            write_atomic(dst / name, tar.extractfile(member).read())
    write_atomic(version, REVEAL_VERSION + '\n')


def sync_assets() -> list[str]:
    """Copy css/js/kit into lessons/_assets (atomic, only when changed) and make sure reveal is vendored."""
    changed = []
    for name in ASSET_FILES:
        if write_atomic(SHARED / name, (SKILL / 'assets' / name).read_bytes()):
            changed.append(name)
    if write_atomic(SHARED / 'art' / 'kit.svg', kit_path().read_bytes()):
        changed.append('art/kit.svg')
    ensure_reveal()
    return changed


def lesson_dirs(root: Path = LESSONS) -> list[Path]:
    return sorted(p for p in Path(root).iterdir() if p.is_dir() and not p.name.startswith(('_', '.'))
                  and (p / 'lesson.yaml').exists())


# ----------------------------------------------------------------------------- skill version

VERSIONED = ('templates', 'scripts', 'assets')  # everything a build reads from the skill


def skill_version() -> str:
    """One line for the top of build.py / validate.py: a hash of the contents of templates/, scripts/ and assets/,
    and the newest file among them — so an agent sees that the skill changed in the middle of its run
    (skill-fixes #26)."""
    h, newest = hashlib.sha256(), (0.0, '')
    for top in VERSIONED:
        for p in sorted((SKILL / top).rglob('*')):
            rel = p.relative_to(SKILL)
            if not p.is_file() or any(part.startswith('.') or part == '__pycache__' for part in rel.parts):
                continue
            h.update(rel.as_posix().encode() + b'\0' + p.read_bytes() + b'\0')
            newest = max(newest, (p.stat().st_mtime, rel.as_posix()))
    when = time.strftime('%Y-%m-%d %H:%M', time.localtime(newest[0])) if newest[1] else '?'
    return f'סקיל lighthouse-lesson-lab · גרסה {h.hexdigest()[:8]} · שינוי אחרון {when} ({newest[1]})'
