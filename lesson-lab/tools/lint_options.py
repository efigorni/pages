"""Lint the picker option bundles.

    uv run --with beautifulsoup4 python3 tools/lint_options.py

Checks every picker/options/*.html listed in picker/bundles.json:
  - each point has 2-4 options, point-level attributes once, per-option attributes always
  - tags are balanced (html.parser) and only known component classes are used
  - no Latin text outside an allow-list, no dot/slash gender forms outside point 2.3
  - every .why quote appears verbatim in the "חותם על זה" transcript
  - no forbidden terminology (the document is always called "המערך")
"""
import html.parser
import json
import os
import re
import sys
from collections import defaultdict

from bs4 import BeautifulSoup

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PICKER = os.path.join(ROOT, 'picker')
HOTAM = os.path.expanduser('~/.claude/skills/migdalor-scorecard/references/hotam-al-ze.md')

LATIN_OK = {'Think', 'Pair', 'Share', 'Jigsaw', 'reveal', 'js', 'PDF', 'PowerPoint', 'Google', 'Slides', 'GitHub',
            'Pages', 'QR', 'PPTX', 'pptx', 'eli5', 'S', 'makom', 'pdf', 'lessons', 'YouTube', 'Enter', 'Esc', 'TikTok',
            'WhatsApp', 'Instagram', 'Forms'}
GENDER_RE = re.compile(r'[א-ת]\.(?:ים|ות|ה|ת)\b|[א-ת]/(?:ה|ת|ים|ות|יות)\b')
GENDER_POINTS = {'2.3'}
FORBIDDEN = ['\u05d3\u05d5\u05e1\u05d9']  # retired term for the lesson-plan document; always "המערך"


def norm(t):
    t = re.sub(r'^\s*>\s?', '', t, flags=re.M)
    t = t.replace('**', '')
    return re.sub(r'\s+', ' ', t).strip()


class Balance(html.parser.HTMLParser):
    VOID = {'meta', 'link', 'br', 'img', 'input', 'hr', 'source', 'col', 'area', 'base', 'wbr', 'circle', 'path',
            'line', 'rect', 'use', 'stop', 'feTurbulence', 'feDisplacementMap', 'ellipse', 'polygon', 'polyline'}

    def __init__(self):
        super().__init__()
        self.stack, self.errors = [], []

    def handle_starttag(self, tag, attrs):
        if tag not in self.VOID and tag.lower() not in {v.lower() for v in self.VOID}:
            self.stack.append((tag, self.getpos()))

    def handle_startendtag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        if tag.lower() in {v.lower() for v in self.VOID}:
            return
        if self.stack and self.stack[-1][0] == tag:
            self.stack.pop()
            return
        self.errors.append(f'unexpected </{tag}> at line {self.getpos()[0]} (open: {self.stack[-1] if self.stack else None})')
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break


def main():
    hotam = norm(open(HOTAM, encoding='utf-8').read())
    css = open(os.path.join(ROOT, 'theme', 'lesson.css'), encoding='utf-8').read()
    known = set(re.findall(r'\.([a-zA-Z][\w-]*)', css)) | {'wrap', 'doc', 'paper', 'lite'}
    cfg = json.load(open(os.path.join(PICKER, 'bundles.json'), encoding='utf-8'))
    problems = 0
    total_points = 0
    for b in cfg['bundles']:
        path = os.path.join(PICKER, 'options', b['file'])
        if not os.path.exists(path):
            print(f'· {b["file"]}: missing (not written yet)')
            continue
        raw = open(path, encoding='utf-8').read()
        bal = Balance()
        bal.feed(raw)
        errs = list(bal.errors) + [f'unclosed <{t}> from line {p[0]}' for t, p in bal.stack if t not in ('html', 'body', 'head')]
        for w in FORBIDDEN:
            for m in re.finditer(w, raw):
                errs.append(f'forbidden word "{w}" at line {raw.count(chr(10), 0, m.start()) + 1}')
        soup = BeautifulSoup(raw, 'html.parser')
        bundle_css = ' '.join(s.get_text() for s in soup.select('style[data-bundle-style]'))
        known_here = known | set(re.findall(r'\.([a-zA-Z][\w-]*)', bundle_css))
        pts = defaultdict(list)
        for sec in soup.select('section[data-pt]'):
            pts[sec['data-pt']].append(sec)
        for pt, secs in pts.items():
            total_points += 1
            opts = [s.get('data-opt') for s in secs]
            if not 2 <= len(secs) <= 4:
                errs.append(f'{pt}: {len(secs)} options')
            if len(set(opts)) != len(opts):
                errs.append(f'{pt}: duplicate data-opt {opts}')
            for k in ('data-title', 'data-gloss'):
                if not any(s.get(k) for s in secs):
                    errs.append(f'{pt}: no {k}')
            for s in secs:
                o = s.get('data-opt')
                for k in ('data-label', 'data-note'):
                    if not s.get(k):
                        errs.append(f'{pt}{o}: no {k}')
                for el in s.find_all(class_=True):
                    for c in el['class']:
                        if c not in known_here and not c.startswith('b-'):
                            errs.append(f'{pt}{o}: unknown class .{c}')
                why_texts = []
                for w in s.select('.why'):
                    cite = w.find('cite')
                    ctext = cite.get_text() if cite else ''
                    if cite:
                        cite.extract()
                    q = norm(w.get_text())
                    why_texts.append(q)
                    if q and q not in hotam:
                        errs.append(f'{pt}{o}: .why not verbatim: «{q[:70]}…» ({ctext})')
                for st in s.find_all(['style', 'script']):
                    st.extract()
                text = s.get_text(' ')
                visible = text
                for q in why_texts:
                    visible = visible.replace(q, '')
                latin = {w for w in re.findall(r'[A-Za-z][A-Za-z0-9]*', visible)} - LATIN_OK
                if latin:
                    errs.append(f'{pt}{o}: latin text {sorted(latin)[:8]}')
                if pt not in GENDER_POINTS:
                    g = GENDER_RE.findall(re.sub(r'\s+', ' ', visible))
                    if g:
                        errs.append(f'{pt}{o}: gender forms {g[:6]}')
        status = 'ok' if not errs else f'{len(errs)} problem(s)'
        print(f'{"✓" if not errs else "✗"} {b["file"]}: {len(pts)} points — {status}')
        for e in errs:
            print('    ' + e)
        problems += len(errs)
    print(f'\n{total_points} points, {problems} problem(s)')
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
