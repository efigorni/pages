#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "jinja2"]
# ///
"""validate.py — the rules of lighthouse-lesson-lab (D8–D45, the picks' Combined rules) for lesson.yaml files.

    uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/validate.py lesson-lab/lessons/<slug> [...]

Errors (✗) break the contract and must be fixed; warnings (!) are fixed or kept on purpose.
Exit code 1 when any lesson has an error. build.py runs the same checks.
"""
from __future__ import annotations

import difflib
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lessonlib as LL  # noqa: E402

FORBIDDEN = ('דוסי', 'dossier')  # the retired name of the document; it is always "המערך"
LATIN_OK = {'Think', 'Pair', 'Share', 'Jigsaw', 'PDF', 'YouTube', 'TikTok', 'WhatsApp', 'Instagram', 'Facebook',
            'Snapchat', 'Google', 'Zoom', 'Discord', 'Roblox', 'Minecraft', 'Fortnite', 'Netflix', 'Spotify',
            'iPhone', 'Android', 'Wi', 'Fi'}
GENDER_RE = re.compile(r'[א-ת]\.(?:ים|ות|ה|ת)(?![א-ת])|[א-ת]/(?:ה|ת|ים|ות|יות)(?![א-ת])')
EMOJI_RE = re.compile('[\U0001F000-\U0001FAFF☀-➿️]')
URL_RE = re.compile(r'https?://\S+')
QUOTED_RE = re.compile(r'(?:(?<=[\s(—–-])|^)[״"„“][^״"„“”\n]*?[״"”](?=[\s.,;:!?)—–-]|$)')
ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')
TIME_RE = re.compile(r'^\d{1,2}:\d{2}$')
# D45: a public stance activity (D27) — the validator asks for `stance: true` when the text looks like one
STANCE_HINT = re.compile(r'מסכימומטר|לאורך הקו|נעמדים על|נעמדים ליד|חוצים את הקו|ליד השלט|עמדה בחלל')
SLIDE_VERBATIM_FIELDS = ('title', 'sub', 'points')


def _words(words):
    return re.compile(r'(?<![א-ת])[ובלכמשה]?(?:' + '|'.join(words) + r')(?![א-ת])')


# Teacher prose must address her in feminine singular (rule 8, R7). Only forms that unvocalised Hebrew
# does not share with a common past tense or noun (כתבו, אמרו, נאמר, נציג… are left out on purpose).
VOICE = [
    (_words(['שימו', 'הציגו', 'בקשו', 'המתינו', 'חכו', 'הסבירו', 'הסתובבו', 'חלקו', 'הקריאו', 'הקרינו',
             'הזמינו', 'הדפיסו', 'הכינו', 'סמנו', 'תנו', 'דלגו', 'תדלגו', 'תוכלו', 'תרצו']), 'ציווי ברבים'),
    (_words(['אתם', 'לכם', 'אתכם', 'שלכם', 'לעצמכם', 'אצלכם', 'עליכם', 'בשבילכם']), 'פנייה ברבים'),
    (_words(['נבקש', 'נרשום', 'נחלק', 'נקריא', 'נסביר', 'נזמין', 'נציין']), 'גוף ראשון רבים'),
    (_words(['המורה']), 'גוף שלישי ("המורה")'),
]

TOP = {  # key: (type, required)
    'slug': (str, False), 'title': (str, True), 'sub': (str, True), 'grade': (int, True), 'grades_served': (list, False),
    'month': (str, True), 'section': (str, True), 'unit': (str, True), 'unit_order': (int, False),
    'unit_size': (int, False), 'src_text': (str, True), 'src_url': (str, False), 'sensitivity': (str, True),
    'src_fixes': (list, False),
    'format': (str, True), 'question': (str, True), 'takeaways': (list, True), 'prep': (list, True),
    'safe': (list, False), 'time': (dict, True), 'brain_break': (dict, True), 'cover': (dict, True),
    'steps': (list, True),
}
# practices/spotlights: required per step, but a step with tracks may leave them to its tracks (D45)
STEP = {'id': (str, True), 'title': (str, True), 'kind': (str, False), 'minutes': (int, True),
        'practices': (list, False), 'spotlights': (list, False), 'summary': (str, True), 'body': (list, True),
        'stance': (bool, False)}
SLIDE = {'kicker': (str, False), 'title': (str, True), 'sub': (str, False), 'points': (list, False),
         'art': (object, True), 'alt': (str, False), 'timer': (int, False), 'echo': (bool, False), 'cue': (str, False),
         'verbatim': (object, False)}
PAUSE = {'at': (str, True), 'moment': (str, False), 'ask': (str, True)}
CLIP = {'start': (str, False), 'end': (str, False)}
TIME_FIELDS = ('at', 'start', 'end')  # "m:ss" — unquoted, YAML may read 1:05 as the number 65
BLOCKS = {  # dict blocks: field → (type, required); str/list blocks by name
    'task': {'what': (str, True), 'time': (str, True), 'group': (str, True), 'rules': (str, True),
             'plenary': (str, True), 'help': (str, True), 'challenge': (str, True)},
    'ladder': {'help': (str, True), 'challenge': (str, True)},
    'slide': SLIDE,
    'timer': {'sec': (int, True), 'label': (str, True)},
    'video': {'title': (str, True), 'url': (str, True), 'length': (str, False), 'before': (str, True),
              'watch': (str, True), 'pauses': (list, True), 'art': (object, True), 'alt': (str, False),
              'clip': (dict, False)},
    'quote': {'title': (str, False), 'text': (str, True)},
    'handout': {'title': (str, True), 'copies': (str, True), 'items': (list, False), 'text': (str, False),
                'verbatim': (bool, False), 'lines': (bool, False)},
    'messages': {'title': (str, False), 'items': (list, True), 'ask': (str, True), 'tip': (str, False),
                 'art': (object, True), 'alt': (str, False)},
    'exit': {'form': (str, True), 'title': (str, True), 'prompts': (list, True), 'look_for': (str, True),
             'art': (object, True), 'alt': (str, False), 'timer': (int, False)},
}
TEXT_BLOCKS = {'p': str, 'say': str, 'ask': str, 'whisper': str, 'tip': str, 'moves': list, 'list': list,
               'board': (str, list), 'tracks': list}
TRACK = {'title': (str, True), 'text': (str, True), 'when': (str, True), 'practices': (list, True),
         'spotlights': (list, True), 'body': (list, True), 'prep': (list, False)}
HINTS = {  # retired fields → how to write them now
    ('video', 'pause'): 'השדות pause/predict הוחלפו ב-pauses: רשימה של {at, moment, ask} (D44, schema.md)',
    ('video', 'predict'): 'השדות pause/predict הוחלפו ב-pauses: רשימה של {at, moment, ask} (D44, schema.md)',
    ('track', 'slides'): 'מסלול הוא תת־שלב מלא (D45): body עם בלוקים משלו — השקפים הם בלוקי slide בתוך body',
    ('clip', 'from'): 'הקטע נכתב clip: {start, end} — "דקה:שנייה" במירכאות (schema.md, "סרטון")',
    ('clip', 'to'): 'הקטע נכתב clip: {start, end} — "דקה:שנייה" במירכאות (schema.md, "סרטון")',
}
# A list item that YAML read as a mapping: "- ולחש לכם באוזן:" or "- סבב מהיר: כל אחד אומר…" (skill-fixes #3)
COLON_HINT = ('YAML קרא את השורה כמילון, בגלל ": " (נקודתיים ורווח) או נקודתיים בסוף השורה — עטפי אותה במירכאות, '
              'או כתבי אותה כבלוק: "- >-" ובשורה הבאה הטקסט '
              '(YAML read this line as a key: value mapping — quote it, or write it as a >- block)')
BLOCK_KEY_RE = re.compile(r'[a-z_]+')


class Report:
    def __init__(self, slug: str):
        self.slug, self.errors, self.warnings = slug, [], []

    def err(self, code: str, msg: str):
        self.errors.append((code, msg))

    def warn(self, code: str, msg: str):
        self.warnings.append((code, msg))

    def print(self, verbose: bool = True):
        mark = '✓' if not self.errors else '✗'
        print(f'{mark} {self.slug}: {len(self.errors)} שגיאות, {len(self.warnings)} אזהרות')
        if verbose:
            for code, msg in self.errors:
                print(f'   ✗ [{code}] {msg}')
            for code, msg in self.warnings:
                print(f'   ! [{code}] {msg}')


def _typecheck(r: Report, where: str, d: dict, schema: dict, kind: str = ''):
    for k in d:
        if k not in schema and not k.startswith('_'):
            hint = HINTS.get((kind, k))
            r.err('schema', f'{where}: שדה לא מוכר "{k}"' + (f' — {hint}' if hint else f' (מותר: {", ".join(schema)})'))
    for k, (typ, req) in schema.items():
        if k not in d or d[k] is None:
            if req:
                r.err('schema', f'{where}: חסר השדה "{k}"')
            continue
        if typ is object:
            continue
        ok = isinstance(d[k], typ) and not (typ is int and isinstance(d[k], bool))
        if typ is str and isinstance(d[k], (int, float)) and k in TIME_FIELDS:
            r.err('schema', f'{where}.{k}: YAML קרא את הזמן כמספר ({d[k]}) — כתבי אותו במירכאות, למשל "1:05"')
        elif not ok:
            r.err('schema', f'{where}.{k}: צריך להיות {typ.__name__}, יש {type(d[k]).__name__}')


def _line(x: dict) -> str:
    """The line as it was written, from the mapping YAML made of it (for the error message)."""
    s = '; '.join(f'{k}: {v}' if v is not None else f'{k}:' for k, v in x.items())
    return s if len(s) <= 60 else s[:59] + '…'


def text_items(r: Report, where: str, items) -> None:
    """Every item of a list that must be text is a string. YAML turns "- ולחש לכם באוזן:" into a mapping, which
    המערך prints raw ({'…': '…'}) and the deck drops — an error, not a warning (skill-fixes #3)."""
    if not isinstance(items, list):
        return
    for i, x in enumerate(items):
        if isinstance(x, str):
            continue
        w = f'{where}[{i}]'
        if isinstance(x, dict):
            r.err('yaml-item', f'{w}: "{_line(x)}" — {COLON_HINT}')
        elif x is None:
            r.err('yaml-item', f'{w}: פריט ריק ("-" בלי טקסט) — מחקי את השורה, או כתבי בה טקסט')
        elif isinstance(x, bool):
            r.err('yaml-item', f'{w}: YAML קרא את הפריט כ-{x} — עטפי אותו במירכאות')
        elif isinstance(x, (int, float)):
            r.err('yaml-item', f'{w}: YAML קרא את הפריט כמספר ({x}) — עטפי אותו במירכאות (למשל "1:05")')
        else:
            r.err('yaml-item', f'{w}: רשימה בתוך רשימה — כל פריט הוא שורת טקסט אחת ("- ערך")')


def slide_verbatim(v: dict) -> set:
    """The fields of a slide marked as verbatim source text (D45): `verbatim: true` = title, sub, points;
    or a list of field names."""
    mark = v.get('verbatim')
    if mark is True:
        return set(SLIDE_VERBATIM_FIELDS)
    if isinstance(mark, list):
        return {str(x) for x in mark}
    if isinstance(mark, str):
        return {mark}
    return set()


# ----------------------------------------------------------------------------- text roles

def iter_text(data: dict):
    """(where, text, role) for every content string; role ∈ teacher · student · neutral · verbatim."""
    def s(where, v, role):
        if isinstance(v, str):
            yield where, v, role
        elif isinstance(v, list):
            for i, x in enumerate(v):
                if isinstance(x, str):
                    yield f'{where}[{i}]', x, role

    for k in ('title', 'sub', 'format', 'question', 'section', 'unit'):
        yield from s(k, data.get(k), 'neutral')
    yield from s('takeaways', data.get('takeaways'), 'neutral')
    yield from s('prep', data.get('prep'), 'teacher')
    for i, x in enumerate(data.get('safe') or []):
        if isinstance(x, dict):
            yield from s(f'safe[{i}].head', x.get('head'), 'teacher')
            yield from s(f'safe[{i}].text', x.get('text'), 'teacher')
    tm = data.get('time') or {}
    yield from s('time.clock', tm.get('clock'), 'teacher')
    yield from s('time.short.text', (tm.get('short') or {}).get('text'), 'teacher')
    bb = data.get('brain_break') or {}
    yield from s('brain_break.signs', bb.get('signs'), 'teacher')
    for i, x in enumerate(bb.get('ideas') or []):
        if isinstance(x, dict):
            yield from s(f'brain_break.ideas[{i}].name', x.get('name'), 'neutral')
            yield from s(f'brain_break.ideas[{i}].text', x.get('text'), 'neutral')
    cover = data.get('cover') or {}
    yield from s('cover.sub', cover.get('sub'), 'student')
    yield from art_text('cover.art', cover.get('art'))
    for si, st in enumerate(data.get('steps') or []):
        if not isinstance(st, dict):
            continue
        w = f'steps[{si}:{st.get("id")}]'
        yield from s(f'{w}.title', st.get('title'), 'neutral')
        yield from s(f'{w}.summary', st.get('summary'), 'neutral')
        yield from body_text(w, st)


def body_text(w, owner):
    for bi, (typ, v) in enumerate(LL.blocks_of(owner)):
        yield from block_text(f'{w}.body[{bi}].{typ}', typ, v)


def art_text(where, art):
    if isinstance(art, list):
        for i, it in enumerate(art):
            if isinstance(it, dict) and isinstance(it.get('text'), str):
                yield f'{where}[{i}].text', it['text'], 'student'


def slide_text(where, v):
    vb = slide_verbatim(v)
    for k in ('kicker', 'title', 'sub'):
        if isinstance(v.get(k), str):
            yield f'{where}.{k}', v[k], 'verbatim' if k in vb else 'student'
    for i, p in enumerate(v.get('points') or []):
        if isinstance(p, str):
            yield f'{where}.points[{i}]', p, 'verbatim' if 'points' in vb else 'student'
    if isinstance(v.get('cue'), str):
        yield f'{where}.cue', v['cue'], 'teacher'
    yield from art_text(f'{where}.art', v.get('art'))


def block_text(where, typ, v):
    roles = {'p': 'teacher', 'moves': 'teacher', 'list': 'teacher', 'whisper': 'teacher', 'tip': 'teacher',
             'say': 'student', 'ask': 'student', 'board': 'student'}
    if typ in roles:
        if isinstance(v, str):
            yield where, v, roles[typ]
        elif isinstance(v, list):
            for i, x in enumerate(v):
                if isinstance(x, str):
                    yield f'{where}[{i}]', x, roles[typ]
        return
    if not isinstance(v, (dict, list)):
        return
    if typ == 'task':
        for k in ('what', 'time', 'group', 'rules', 'plenary'):
            if isinstance(v.get(k), str):
                yield f'{where}.{k}', v[k], 'neutral'
        for k in ('help', 'challenge'):
            if isinstance(v.get(k), str):
                yield f'{where}.{k}', v[k], 'student'
    elif typ == 'ladder':
        for k in ('help', 'challenge'):
            if isinstance(v.get(k), str):
                yield f'{where}.{k}', v[k], 'student'
    elif typ == 'timer':
        if isinstance(v.get('label'), str):
            yield f'{where}.label', v['label'], 'teacher'
    elif typ == 'slide':
        yield from slide_text(where, v)
    elif typ == 'video':
        if isinstance(v.get('title'), str):
            yield f'{where}.title', v['title'], 'neutral'
        for k in ('before', 'watch'):
            if isinstance(v.get(k), str):
                yield f'{where}.{k}', v[k], 'student'
        for i, p in enumerate(v.get('pauses') or []):
            if isinstance(p, dict):
                if isinstance(p.get('moment'), str):
                    yield f'{where}.pauses[{i}].moment', p['moment'], 'teacher'
                if isinstance(p.get('ask'), str):
                    yield f'{where}.pauses[{i}].ask', p['ask'], 'student'
        yield from art_text(f'{where}.art', v.get('art'))
    elif typ == 'quote':
        if isinstance(v.get('title'), str):
            yield f'{where}.title', v['title'], 'neutral'
        if isinstance(v.get('text'), str):
            yield f'{where}.text', v['text'], 'verbatim'
    elif typ == 'handout':
        role = 'verbatim' if v.get('verbatim') else 'student'
        if isinstance(v.get('title'), str):
            yield f'{where}.title', v['title'], 'student'
        if isinstance(v.get('copies'), str):
            yield f'{where}.copies', v['copies'], 'teacher'
        if isinstance(v.get('text'), str):
            yield f'{where}.text', v['text'], role
        for i, x in enumerate(v.get('items') or []):
            if isinstance(x, str):
                yield f'{where}.items[{i}]', x, role
    elif typ == 'tracks':
        for ti, tr in enumerate(v):
            if not isinstance(tr, dict):
                continue
            tw = f'{where}[{ti}]'
            if isinstance(tr.get('title'), str):
                yield f'{tw}.title', tr['title'], 'neutral'
            for k in ('text', 'when'):
                if isinstance(tr.get(k), str):
                    yield f'{tw}.{k}', tr[k], 'teacher'
            for i, x in enumerate(tr.get('prep') or []):
                if isinstance(x, str):
                    yield f'{tw}.prep[{i}]', x, 'teacher'
            yield from body_text(tw, tr)
    elif typ == 'messages':
        for i, x in enumerate(v.get('items') or []):
            if isinstance(x, str):
                yield f'{where}.items[{i}]', x, 'verbatim'
        for k, role in (('title', 'student'), ('ask', 'student'), ('tip', 'teacher')):
            if isinstance(v.get(k), str):
                yield f'{where}.{k}', v[k], role
        yield from art_text(f'{where}.art', v.get('art'))
    elif typ == 'exit':
        if isinstance(v.get('title'), str):
            yield f'{where}.title', v['title'], 'student'
        for i, x in enumerate(v.get('prompts') or []):
            if isinstance(x, str):
                yield f'{where}.prompts[{i}]', x, 'student'
        if isinstance(v.get('look_for'), str):
            yield f'{where}.look_for', v['look_for'], 'teacher'
        yield from art_text(f'{where}.art', v.get('art'))


# ----------------------------------------------------------------------------- verbatim

def norm(t: str) -> str:
    """Words only: punctuation, quote marks and spacing never decide whether a quote is verbatim (D23)."""
    t = re.sub(r'[^\w/]+', ' ', str(t).replace('**', ''))
    return re.sub(r'\s+', ' ', t).strip()


def best_ratio(q: str, src: str) -> float:
    n = len(q)
    if not n or not src:
        return 0.0
    sm = difflib.SequenceMatcher(None, autojunk=False)
    sm.set_seq2(q)
    best, step = 0.0, max(1, n // 12)
    for i in range(0, max(1, len(src) - n + 1), step):
        sm.set_seq1(src[i:i + n])
        if sm.real_quick_ratio() <= best or sm.quick_ratio() <= best:
            continue
        best = max(best, sm.ratio())
    return best


def fixed_source(r: Report, raw: str, fixes) -> str:
    """The source text with the lesson's silent corrections applied (D23): `src_fixes: [{from, to}]`.
    A fix whose `from` is not in the source is an error, so a stale fix can't hide a real change."""
    for i, fx in enumerate(fixes if isinstance(fixes, list) else []):
        if not isinstance(fx, dict) or not isinstance(fx.get('from'), str) or not isinstance(fx.get('to'), str):
            r.err('src-fix', f'src_fixes[{i}]: צריך {{from, to}} — המילים במקור, והתיקון השקט')
            continue
        if fx['from'] not in raw:
            r.err('src-fix', f'src_fixes[{i}]: "{fx["from"]}" לא נמצא במקור (העתיקי את הקטע כמו שהוא, כולל רווחים)')
            continue
        raw = raw.replace(fx['from'], fx['to'])
    return raw


# ----------------------------------------------------------------------------- the checks

def check(data: dict, kit: LL.Kit | None = None) -> Report:
    r = Report(data.get('_slug', '?'))
    kit = kit or LL.Kit()
    _typecheck(r, 'lesson', data, TOP)
    for k in ('takeaways', 'prep'):
        text_items(r, k, data.get(k))
    steps = [s for s in (data.get('steps') or []) if isinstance(s, dict)]

    # --- metadata
    if data.get('slug') and data['slug'] != data.get('_slug'):
        r.err('meta', f'slug "{data["slug"]}" שונה משם התיקייה "{data.get("_slug")}"')
    if isinstance(data.get('grade'), int) and data['grade'] not in LL.GRADE_LABEL:
        r.err('meta', f'grade צריך להיות 6–9, יש {data["grade"]}')
    if isinstance(data.get('month'), str):
        bad = [p for p in re.split(r'\s*[–-]\s*', data['month']) if p not in LL.MONTHS]
        if bad:
            r.err('meta', f'month: חודש לא מוכר {bad} (חודש אחד, או טווח עם מקף: ינואר–פברואר)')
    sens = data.get('sensitivity')
    if isinstance(sens, str) and sens not in LL.SENSITIVITY:
        r.err('meta', f'sensitivity צריך להיות אחד מ-{", ".join(LL.SENSITIVITY)}')
    src_text = data.get('src_text')
    src_path = LL.LAB / src_text if isinstance(src_text, str) else None
    if src_path and not src_path.exists():
        r.err('meta', f'src_text לא נמצא: lesson-lab/{src_text}')
    tk = data.get('takeaways')
    if isinstance(tk, list) and not 2 <= len(tk) <= 3:
        r.err('card', f'takeaways: 2–3 שורות, יש {len(tk)}')
    inv = LL.inventory().get(data.get('_slug'))
    if inv:
        for k in ('title', 'grade', 'month', 'section', 'unit', 'unit_order', 'src_text', 'sensitivity'):
            if k in inv and data.get(k) is not None and data.get(k) != inv[k]:
                r.warn('inventory', f'{k}: "{data.get(k)}" ושונה מ-docs/lessons.json ("{inv[k]}")')

    # --- steps: fields, kinds, ids, order
    ids, kinds = set(), []
    for i, s in enumerate(steps):
        where = f'steps[{i}:{s.get("id")}]'
        _typecheck(r, where, s, STEP)
        sid = s.get('id')
        if isinstance(sid, str):
            if not ID_RE.match(sid):
                r.err('schema', f'{where}: id באותיות לטיניות קטנות, ספרות ומקפים בלבד')
            if sid in ids:
                r.err('schema', f'{where}: id כפול')
            ids.add(sid)
        k = LL.kind_of(s)
        if k not in LL.KINDS:
            r.err('schema', f'{where}: kind "{k}" — מותר {", ".join(LL.KINDS)}')
        kinds.append(k)
        if k == 'extension' and str(s.get('title', '')).startswith('אם נשאר זמן'):
            r.err('schema', f'{where}: כותרת הרחבה בלי "אם נשאר זמן:" — הבנייה מוסיפה אותו')
        for key in ('practices', 'spotlights'):
            text_items(r, f'{where}.{key}', s.get(key))
        check_tags(r, where, s.get('practices'), s.get('spotlights'))
        if not LL.step_tags(s, 'practices'):
            r.err('tags', f'{where}: צריך לפחות פרקטיקה אחת (לשלב, או לכל אחד מהמסלולים שלו)')
        if not LL.step_tags(s, 'spotlights'):
            r.err('tags', f'{where}: צריך לפחות זרקור אחד (לשלב, או לכל אחד מהמסלולים שלו)')
        check_blocks(r, where, s, kit, data['_dir'])

    rank = {'core': 0, 'extension': 1, 'messages': 2, 'exit': 3}
    seq = [rank.get(k, 0) for k in kinds]
    if seq != sorted(seq):
        r.err('order', 'סדר השלבים: כל שלבי התוכן, אחריהם ההרחבות, אחריהן "חשוב לזכור", ובסוף כרטיס היציאה')
    if kinds.count('exit') != 1:
        r.err('exit', f'צריך בדיוק שלב אחד עם kind: exit (יש {kinds.count("exit")})')
    elif kinds[-1] != 'exit':
        r.err('exit', 'כרטיס היציאה הוא השלב האחרון')
    if kinds.count('messages') > 1:
        r.err('order', 'לכל היותר שלב "חשוב לזכור" אחד')
    if kinds.count('messages') == 0:
        r.warn('messages', 'אין שלב "חשוב לזכור" (kind: messages). מסרים (D50–D51, מדריך הסגנון §10): שקף מסרים מפורש '
                           'במקור, ואם אין — שקף הסיכום שסוגר את השיעור, כשהוא מנוסח כמסר לתלמידים. אין גם כזה — '
                           'האזהרה נשארת, ורושמים ביומן')
    if 'core' not in kinds:
        r.err('order', 'אין שלבי תוכן (kind: core)')

    # --- time
    mins = lambda ks: sum(int(s.get('minutes') or 0) for s in steps if LL.kind_of(s) in ks)  # noqa: E731
    core, ext = mins({'core', 'messages', 'exit'}), mins({'extension'})
    if core != LL.CORE_MINUTES:
        r.err('time', f'הליבה (תוכן + חשוב לזכור + כרטיס יציאה) היא {core}′ — צריך בדיוק {LL.CORE_MINUTES}′')
    if core + ext > LL.LESSON_MINUTES:
        r.err('time', f'ליבה + הרחבות = {core + ext}′ — לכל היותר {LL.LESSON_MINUTES}′')
    n_core = sum(1 for k in kinds if k != 'extension')
    if not 6 <= n_core <= 7:
        r.warn('arc', f'{n_core} שלבי ליבה — הכיוון הוא 6–7 (כולל חשוב לזכור וכרטיס יציאה)')
    for s in steps:
        if LL.kind_of(s) == 'exit' and int(s.get('minutes') or 0) > 5:
            r.warn('exit', f'כרטיס היציאה לוקח {s.get("minutes")}′ — עד 5 דקות')
    tm = data.get('time') or {}
    if isinstance(tm, dict):
        if not isinstance(tm.get('clock'), str) or not tm.get('clock', '').strip():
            r.err('time', 'time.clock: חסרה הלחישה "כאן מסתכלים בשעון" לסוף שלב התוכן האחרון')
        short = tm.get('short')
        if not isinstance(short, dict) or not isinstance(short.get('text'), str) or not isinstance(short.get('steps'), list):
            r.err('time', 'time.short: צריך {steps: [ids], text: …} — על מה מוותרים כשחסר זמן גם לליבה')
        else:
            exit_ids = {s.get('id') for s in steps if LL.kind_of(s) == 'exit'}
            text_items(r, 'time.short.steps', short['steps'])
            for sid in [x for x in short['steps'] if isinstance(x, str)]:
                if sid not in ids:
                    r.err('time', f'time.short.steps: אין שלב "{sid}"')
                elif sid in exit_ids:
                    r.err('exit', 'time.short: על כרטיס היציאה לא מוותרים')
                elif LL.kind_of(next(s for s in steps if s.get('id') == sid)) == 'extension':
                    r.warn('time', f'time.short.steps: "{sid}" הוא הרחבה — הרחבות ממילא לא בליבה')
            if re.search('כרטיס( ה)?יציאה', short['text']):
                r.err('exit', 'time.short.text מזכיר את כרטיס היציאה — עליו לא מוותרים (הבנייה מוסיפה את המשפט הזה בעצמה)')

    # --- brain break
    bb = data.get('brain_break')
    if isinstance(bb, dict):
        _typecheck(r, 'brain_break', bb, {'after': (str, False), 'signs': (str, True), 'ideas': (list, True),
                                          'from': (str, True)})
        ideas = bb.get('ideas') or []
        if isinstance(ideas, list) and not 2 <= len(ideas) <= 3:
            r.err('brain', f'brain_break.ideas: 2–3 רעיונות, יש {len(ideas)}')
        for i, it in enumerate(ideas if isinstance(ideas, list) else []):
            if not isinstance(it, dict) or not it.get('name') or not it.get('text'):
                r.err('brain', f'brain_break.ideas[{i}]: צריך {{name, text}}')
        if bb.get('from') and bb['from'] not in ids:
            r.err('brain', f'brain_break.from: אין שלב "{bb["from"]}"')
        elif bb.get('from') and 'extension' in kinds:
            src = next(s for s in steps if s.get('id') == bb['from'])
            if LL.kind_of(src) != 'extension':
                r.warn('brain', 'brain_break.from: עדיף לקחת את 3 הדקות מהרחבה')
        if bb.get('after'):
            if bb['after'] not in ids:
                r.err('brain', f'brain_break.after: אין שלב "{bb["after"]}"')
            else:
                t, end = 0, None
                for s in steps:
                    if LL.kind_of(s) != 'core':
                        continue
                    t += int(s.get('minutes') or 0)
                    if s.get('id') == bb['after']:
                        end = t
                if end is None:
                    r.err('brain', 'brain_break.after: צריך להיות שלב תוכן (kind: core)')
                elif not 15 <= end <= 25:
                    r.warn('brain', f'הפסקת המוח אחרי דקה {end} — הכיוון הוא סביב דקה 20')

    # --- sensitivity (D24, D45): the box at med+ — or whenever a public stance activity is in the lesson
    safe = data.get('safe')
    stance_steps = [s.get('id') for s in steps if s.get('stance') is True]
    if sens in LL.SAFE_REQUIRED and not safe:
        r.err('safe', f'sensitivity: {sens} — צריך תיבת safe ("לפני השיעור") בראש המערך')
    if stance_steps and not safe:
        r.err('safe', f'עמידה פומבית ({", ".join(stance_steps)}) — צריך תיבת safe גם ברגישות {sens}, '
                      'עם סעיף "עמידה מול הכיתה" (D45)')
    if sens == 'low' and safe and not stance_steps:
        r.err('safe', 'sensitivity: low בלי עמידה פומבית — בלי תיבת safe')
    if safe:
        for i, x in enumerate(safe if isinstance(safe, list) else []):
            if not isinstance(x, dict) or not x.get('head') or not x.get('text'):
                r.err('safe', f'safe[{i}]: צריך {{head, text}}')
        heads = ' '.join(str(x.get('head', '')) for x in safe if isinstance(x, dict))
        if stance_steps and 'עמידה' not in heads:
            r.err('safe', 'יש עמידה פומבית — סעיף safe שהכותרת שלו "עמידה מול הכיתה" (D45, מדריך הסגנון §12)')
        if sens in LL.SAFE_REQUIRED:
            if isinstance(safe, list) and len(safe) < 4:
                r.warn('safe', f'safe: {len(safe)} סעיפים — בדרך כלל ארבעה (יועצת · מי עלול להיפגע · לא לוחצים לשתף · אם מישהו משתף פגיעה)')
            if 'יועצ' not in str(safe):
                r.warn('safe', 'safe: לא מוזכרת היועצת')
    for i, s in enumerate(steps):
        if s.get('stance') is True:
            text = ' '.join(t for _, t, _ in body_text('', s))
            if 'חמש שניות' not in text:
                r.warn('stance', f'steps[{i}:{s.get("id")}]: עמידה פומבית בלי "חושבים לבד חמש שניות, בלי להסתכל על אף אחד — '
                                 'ורק אז זזים" (מדריך הסגנון §12)')
        elif STANCE_HINT.search(' '.join(t for _, t, _ in body_text('', s))):
            r.warn('stance', f'steps[{i}:{s.get("id")}]: נראה כמו עמידה פומבית (D27) — אם כן, stance: true בשלב '
                             'וסעיף "עמידה מול הכיתה" בתיבת safe')

    # --- cover
    cover = data.get('cover')
    if isinstance(cover, dict):
        _typecheck(r, 'cover', cover, {'art': (object, True), 'alt': (str, False), 'sub': (str, False)})
        if not cover.get('art'):
            r.err('art', 'cover.art: לשקף השער צריך איור')
        else:
            check_art(r, 'cover.art', cover['art'], kit, data['_dir'])

    # --- opening by retrieval needs a self-sufficient recap (R3)
    first = next((s for s in steps if LL.kind_of(s) == 'core'), None)
    if first and 'תרגילי שליפה' in LL.step_tags(first, 'practices'):
        if 'whisper' not in [t for t, _, _ in walk_blocks(first)]:
            r.err('retrieval', 'פתיחה בתרגילי שליפה: צריך whisper שמסכם מה היה בשיעור הקודם (R3)')

    # --- practices used as their cards define them (references/hotam-al-ze.md)
    for i, s in enumerate(steps):
        w, tags, k = f'steps[{i}:{s.get("id")}]', LL.step_tags(s, 'practices'), LL.kind_of(s)
        if 'קדימה ללמידה' in tags and s is not first:
            r.warn('practice', f'{w}: קדימה ללמידה היא משימת הפתיחה — בדקות הראשונות של השיעור, לא באמצע')
        if 'קדימה ללמידה' in tags and s is first and int(s.get('minutes') or 0) > 10:
            r.warn('practice', f'{w}: קדימה ללמידה — משימה של 3–5 דקות (ועוד אותו זמן לשמוע תשובות); השלב {s.get("minutes")}′')
        if 'כרטיס יציאה' in tags and k != 'exit':
            r.warn('practice', f'{w}: "כרטיס יציאה" רק בשלב כרטיס היציאה — המשימה האחרונה בשיעור')
        if k == 'exit' and 'כרטיס יציאה' not in tags:
            r.warn('practice', f'{w}: שלב כרטיס היציאה מתויג "כרטיס יציאה"')
        if 'הפסקת מוח' in tags:
            r.warn('practice', f'{w}: הפסקת מוח לא מתוזמנת (D19) — היא נכנסת רק כהצעה, דרך brain_break')
        if k in ('core', 'extension'):
            owners = [('', s)] + [(f' · מסלול {LL.TRACK_LETTERS[ti]}', tr) for typ, v in LL.blocks_of(s)
                                  if typ == 'tracks' and isinstance(v, list)
                                  for ti, tr in enumerate(v[:2]) if isinstance(tr, dict)]
            for label, owner in owners:
                if owner is s and any(t == 'tracks' for t, _ in LL.blocks_of(s)):
                    continue  # a tracks step: counted per track (its shared bridge counts in each)
                said = sum(1 for t, v in LL.blocks_of(owner) if t in ('say', 'ask'))
                said += sum(1 + len(v.get('pauses') or []) for t, v in LL.blocks_of(owner)
                            if t == 'video' and isinstance(v, dict))
                if owner is not s:
                    said += sum(1 for t, _ in LL.blocks_of(s) if t in ('say', 'ask'))
                if said == 0:
                    r.warn('voice', f'{w}{label}: אין אף ניסוח מפתח (say/ask) — 2–3 לרגעים החשובים')
                elif said > 5:
                    r.warn('voice', f'{w}{label}: {said} ניסוחי מפתח — 2–3 לרגעים החשובים, לא תסריט מלא')

    # --- text: language, gender forms, voice, verbatim
    raw_src = src_path.read_text(encoding='utf-8') if src_path and src_path.exists() else ''
    src_norm = norm(fixed_source(r, raw_src, data.get('src_fixes'))) if raw_src else ''
    for where, text, role in iter_text(data):
        clean = URL_RE.sub(' ', text)
        if role != 'verbatim':
            latin = sorted({w for w in re.findall(r'[A-Za-z][A-Za-z0-9]*', clean)} - LATIN_OK)
            if latin:
                r.err('hebrew', f'{where}: טקסט לטיני {latin[:6]} — עברית בלבד')
            g = GENDER_RE.findall(clean)
            if g:
                r.err('gender', f'{where}: צורות עם נקודה/לוכסן {g[:4]} — רבים רגיל ("תלמידים", "מוכן"); '
                                'ציטוט מילולי מהמקור — סמני אותו כ-verbatim')
        if EMOJI_RE.search(clean):
            r.err('emoji', f'{where}: בלי אימוג׳י וסמלים')
        if role == 'teacher':
            prose = QUOTED_RE.sub(' ', clean)
            for rx, what in VOICE:
                m = rx.search(prose)
                if m:
                    r.warn('voice', f'{where}: "{m.group(0)}" — {what}; למורה פונים ב"את" ("הציגי", "שאלי", "לך")')
                    break
        if role == 'verbatim' and src_norm:
            q = norm(text)
            if q and f' {q} ' not in f' {src_norm} ':
                ratio = best_ratio(q, src_norm)
                if ratio >= .9:
                    r.warn('verbatim', f'{where}: כמעט מילה במילה ({ratio:.0%}) — תיקון שקט? רשמי אותו ב-src_fixes; '
                                       'אחרת העתיקי מהמקור')
                else:
                    r.err('verbatim', f'{where}: לא נמצא במקור ({ratio:.0%}) — ציטוט מהמקור נשאר כמו שהוא')
    for w in FORBIDDEN:
        if w in data.get('_raw', ''):
            r.err('forbidden', f'המילה "{w}…" אסורה — המסמך נקרא "המערך"')
    return r


def walk_blocks(owner: dict, where: str = ''):
    """(type, value, where) for every block of a step, including the blocks inside its tracks."""
    for bi, (typ, v) in enumerate(LL.blocks_of(owner)):
        w = f'{where}.body[{bi}].{typ}'
        yield typ, v, w
        if typ == 'tracks' and isinstance(v, list):
            for ti, tr in enumerate(v):
                if isinstance(tr, dict):
                    yield from walk_blocks(tr, f'{w}[{ti}]')


def check_tags(r: Report, where: str, practices, spotlights):
    """Tag names; an item that is not text is reported by text_items."""
    for p in practices or []:
        if isinstance(p, str) and p not in LL.PRACTICES:
            guess = difflib.get_close_matches(str(p).replace('-', '–'), list(LL.PRACTICES), n=1, cutoff=.6)
            r.err('tags', f'{where}: "{p}" אינה אחת מ-11 הפרקטיקות' + (f' (אולי "{guess[0]}"?)' if guess else ''))
    for b in spotlights or []:
        if isinstance(b, str) and b not in LL.SPOTLIGHTS:
            guess = difflib.get_close_matches(str(b), list(LL.SPOTLIGHTS), n=1, cutoff=.5)
            r.err('tags', f'{where}: "{b}" אינו אחד מ-5 הזרקורים' + (f' (אולי "{guess[0]}"?)' if guess else ''))


def check_art(r: Report, where: str, art, kit: LL.Kit, lesson_dir: Path):
    if isinstance(art, dict):
        f = art.get('file')
        if not f:
            r.err('art', f'{where}: צריך {{file: art/…svg}}, מזהה סמל, או רשימת מיקומים')
        elif not (Path(lesson_dir) / str(f)).exists():
            r.err('art', f'{where}: הקובץ {f} לא קיים בתיקיית השיעור')
        else:
            check_scene(r, where, art, kit, lesson_dir)
        return
    if isinstance(art, list):
        for i, it in enumerate(art):
            if not isinstance(it, dict) or not ('use' in it or 'text' in it):
                r.err('art', f'{where}[{i}]: כל פריט הוא {{use: מזהה, x, y, w, color}} או {{text, x, y, size}}')
    elif not isinstance(art, str):
        r.err('art', f'{where}: סוג לא מוכר')
    for sid in LL.art_symbols(art):
        if not kit.has(sid):
            guess = difflib.get_close_matches(sid, list(kit.symbols) + sorted(kit.tokens), n=3, cutoff=.4)
            r.err('art', f'{where}: אין סמל "{sid}" בערכה (assets/art/kit.svg)' + (f' — אולי {guess}?' if guess else ''))
    check_scene(r, where, art, kit, lesson_dir)


def _box(it: dict, kit: LL.Kit):
    sid = str(it['use'])
    vw, vh = kit.symbols[sid][0][2] or 100, kit.symbols[sid][0][3] or 100
    w, h = it.get('w'), it.get('h')
    w = float(w or (float(h) * vw / vh if h else vw))
    h = float(h or w * vh / vw)
    x = float(it.get('x', (LL.CANVAS_W - w) / 2))
    y = float(it.get('y', (LL.CANVAS_H - h) / 2))
    return x, y, w, h


def check_scene(r: Report, where: str, art, kit: LL.Kit, lesson_dir: Path):
    """The composition rules of assets/art/art-guide.md, as warnings."""
    if isinstance(art, dict) and art.get('file'):
        path = Path(lesson_dir) / str(art['file'])
        if not path.exists():
            return
        svg = path.read_text(encoding='utf-8')
        if not re.search(r'viewBox="0 0 620 540"', svg):
            r.warn('art', f'{where}: {art["file"]} — viewBox="0 0 620 540" (מסגרת הסצנה)')
        own = set(re.findall(r'\bid="([^"]+)"', svg))
        for ref in sorted(set(re.findall(r'href="#([^"]+)"', svg)) - own):
            if not kit.has(ref):
                r.err('art', f'{where}: {art["file"]} מפנה ל-#{ref}, שאין בערכה')
        for m in re.finditer(r'<use\b[^>]*href="#([^"]+)"[^>]*>', svg):
            tag, ref = m.group(0), m.group(1)
            if ref in kit.symbols and not re.search(r'\bwidth=', tag):
                r.warn('art', f'{where}: {art["file"]} — <use href="#{ref}"> בלי width/height ממלא את כל המסגרת')
            if ref in kit.symbols and kit.default_color(ref) and 'color=' not in tag:
                r.warn('art', f'{where}: {art["file"]} — <use href="#{ref}"> בלי color (בקובץ אין צבע ברירת מחדל)')
        words = sum(len(t.split()) for t in re.findall(r'<text\b[^>]*>([^<]*)</text>', svg))
        if words > 3 and 'data-diagram' not in svg:
            r.warn('art', f'{where}: {art["file"]} — {words} מילים בתמונה (עד 3). תרשים שמשחזר תרשים מהמקור '
                          '(מילה לכל חלק) — data-diagram="true" על ה-<svg>')
        return
    if not isinstance(art, list):
        return
    uses = [it for it in art if isinstance(it, dict) and it.get('use')]
    if len(uses) > LL.MAX_USES:
        r.warn('art', f'{where}: {len(uses)} סמלים — מוקד אחד ועד 3 תומכים, לכל היותר {LL.MAX_USES}')
    boxes = {i: _box(it, kit) for i, it in enumerate(uses) if str(it['use']) in kit.symbols}
    for i, it in enumerate(uses):
        sid, w_ = str(it['use']), f'{where}[{i}] ({it["use"]})'
        c = it.get('color')
        if c and LL.COLORS.get(str(c), str(c)).lower() not in LL.PALETTE:
            r.warn('art', f'{w_}: הצבע {c} לא מהפלטה של הערכה')
        if sid not in kit.symbols:
            continue
        vw, vh = kit.symbols[sid][0][2] or 100, kit.symbols[sid][0][3] or 100
        if it.get('w') and it.get('h') and abs((float(it['w']) / float(it['h'])) / (vw / vh) - 1) > .05:
            r.warn('art', f'{w_}: w/h לא ביחס של הסמל ({vw:g}×{vh:g}) — תני רק w')
        x, y, w, h = boxes[i]
        # a detail inside a container (a bulb in a speech bubble, a phone in a thought) may go down to DETAIL_MIN
        inside = any(j != i and str(uses[j]['use']) in LL.CONTAINERS and
                     bx - 1 <= x and by - 1 <= y and x + w <= bx + bw + 1 and y + h <= by + bh + 1
                     for j, (bx, by, bw, bh) in boxes.items())
        lo = LL.DETAIL_MIN if inside else LL.SCALE_MIN
        if not lo - .005 <= w / vw <= LL.SCALE_MAX + .005:
            r.warn('art', f'{w_}: פי {w / vw:.2f} מהגודל הטבעי — טווח העבודה {lo}–{LL.SCALE_MAX} '
                          f'(רוחב {vw * lo:.0f}–{vw * LL.SCALE_MAX:.0f})')
        least = LL.MIN_SIZE.get(sid, 100 if sid.startswith('face-') else 0)
        if w < least:
            r.warn('art', f'{w_}: רוחב {w:.0f} — הסמל המפורט הזה צריך לפחות {least}')
        m = LL.MARGIN
        if not it.get('rotate') and (x < m - .5 or y < m - .5 or x + w > LL.CANVAS_W - m + .5
                                      or y + h > LL.CANVAS_H - m + .5):
            r.warn('art', f'{w_}: יוצא משולי הסצנה (x {x:.0f}…{x + w:.0f}, y {y:.0f}…{y + h:.0f}; '
                          f'המסגרת {m}…{LL.CANVAS_W - m} × {m}…{LL.CANVAS_H - m})')
    texts = [it for it in art if isinstance(it, dict) and it.get('text') is not None]
    words = sum(len(str(t['text']).split()) for t in texts)
    if words > 3:
        r.warn('art', f'{where}: {words} מילים בתוך התמונה — עד 3, והמשפט עצמו בטקסט של השקף')
    for t in texts:
        if float(t.get('size', 34)) < 30:
            r.warn('art', f'{where}: תווית "{t["text"]}" בגודל {t.get("size")} — 30 ומעלה')


def check_clip(r: Report, where: str, v: dict):
    """video.clip (skill-fixes #7): the part of the video the class watches — times of the whole video, "m:ss"."""
    clip = v['clip']
    _typecheck(r, where, clip, CLIP, kind='clip')
    t = {}
    for k in ('start', 'end'):
        if isinstance(clip.get(k), str):
            secs = LL.clock_secs(clip[k])
            if secs is None:
                r.err('video', f'{where}.{k}: "{clip[k]}" — דקה:שנייה במירכאות, כמו בנגן ("0:12")')
            else:
                t[k] = secs
    if clip.get('start') is None and clip.get('end') is None:
        r.err('video', f'{where}: צריך start, end או שניהם — "דקה:שנייה" במירכאות; סרטון שלם — בלי clip')
    elif t.get('start') == 0 and clip.get('end') is None:
        r.err('video', f'{where}: start "{clip["start"]}" בלי end הוא הסרטון כולו — מחקי את clip')
    if 'start' in t and 'end' in t and t['start'] >= t['end']:
        r.err('video', f'{where}: start ({clip["start"]}) צריך להיות לפני end ({clip["end"]})')
    length = LL.clock_secs(v.get('length'))
    if length is not None:
        for k, secs in t.items():
            if secs > length:
                r.err('video', f'{where}.{k}: {clip[k]} — אחרי סוף הסרטון ({v["length"]})')
    lo, hi = t.get('start', 0), t.get('end')
    for pi, p in enumerate(v.get('pauses') or []):
        at = LL.clock_secs(p.get('at')) if isinstance(p, dict) else None
        if at is not None and (at < lo or (hi is not None and at > hi)):
            r.warn('video', f'{where}: העצירה pauses[{pi}] ב־{p["at"]} מחוץ לקטע — הזמנים הם של הסרטון כולו, '
                            'כמו בנגן')
    if t.get('start') and not LL.youtube_id(v.get('url')):
        r.warn('video', f'{where}: הקישור אינו של יוטיוב, ולכן לא ייפתח בתחילת הקטע — המערך יבקש מהמורה לקדם את '
                        f'הסרטון ל־{clip["start"]}')


def check_slide(r: Report, where: str, v: dict, kit: LL.Kit, lesson_dir: Path, budget: bool = True):
    _typecheck(r, where, v, SLIDE)
    text_items(r, f'{where}.points', v.get('points'))
    if isinstance(v.get('verbatim'), list):
        text_items(r, f'{where}.verbatim', v['verbatim'])
    mark = v.get('verbatim')
    if mark is not None and not isinstance(mark, (bool, list, str)):
        r.err('schema', f'{where}.verbatim: true, או רשימת שדות מתוך title · sub · points')
    bad = slide_verbatim(v) - set(SLIDE_VERBATIM_FIELDS)
    if bad:
        r.err('schema', f'{where}.verbatim: {sorted(bad)} — רק title · sub · points יכולים להיות ציטוט מהמקור')
    if v.get('art'):
        check_art(r, f'{where}.art', v['art'], kit, lesson_dir)
    if not budget:
        return
    for k, limit in (('kicker', 45), ('title', 60), ('sub', 90)):
        if isinstance(v.get(k), str) and len(v[k]) > limit:
            r.warn('slide-words', f'{where}.{k}: {len(v[k])} תווים — מעט מילים על השקף (עד {limit})')
    pts = v.get('points') or []
    if isinstance(pts, list):
        if len(pts) > 4:
            r.warn('slide-words', f'{where}.points: {len(pts)} נקודות — רעיון אחד לשקף; פצלי לשקפים')
        for i, p in enumerate(pts):
            if isinstance(p, str) and len(p) > 80:
                r.warn('slide-words', f'{where}.points[{i}]: {len(p)} תווים (עד 80)')


def unknown_block(w: str, typ, v) -> tuple[str, str]:
    """(code, message) for a body item that is not a block — often a line of text that YAML read as a mapping."""
    if typ == '?' and v is None:
        return 'yaml-item', f'{w}: פריט ריק ("-" בלי טקסט) — מחקי את השורה, או כתבי בה טקסט'
    if typ == '?' and isinstance(v, dict):
        msg = f'{w}: כמה מפתחות בפריט אחד ({", ".join(map(str, list(v)[:4]))}) — כל בלוק הוא פריט משלו, בשורת "- " משלו'
        if any(not BLOCK_KEY_RE.fullmatch(str(k)) for k in v):
            return 'yaml-item', f'{msg}. ואם זו שורת טקסט — {COLON_HINT}'
        return 'schema', msg
    if typ != '?' and not BLOCK_KEY_RE.fullmatch(str(typ)):
        return 'yaml-item', f'{w}: "{_line({typ: v})}" — {COLON_HINT}'
    return 'schema', f'{w}.{typ}: סוג בלוק לא מוכר (מותר: {", ".join(list(TEXT_BLOCKS) + list(BLOCKS))})'


def check_blocks(r: Report, where: str, step: dict, kit: LL.Kit, lesson_dir: Path, track: bool = False) -> int:
    """The blocks of a step body — or of a track body (track=True). Returns the number of slides they make."""
    kind = 'core' if track else LL.kind_of(step)
    blocks = LL.blocks_of(step)
    n_slides = 0
    types = [t for t, _ in blocks]
    for bi, (typ, v) in enumerate(blocks):
        w = f'{where}.body[{bi}].{typ}'
        if typ in TEXT_BLOCKS:
            want = TEXT_BLOCKS[typ]
            if not isinstance(v, want):
                r.err('schema', f'{w}: סוג לא נכון ({type(v).__name__})')
                continue
            if typ in ('moves', 'list', 'board') and isinstance(v, list):
                text_items(r, w, v)
            if typ == 'tracks':
                if track:
                    r.err('tracks', f'{w}: מסלולים בתוך מסלול — לא; נקודת בחירה נוספת היא שלב נפרד')
                    continue
                if len(v) != 2:
                    r.err('tracks', f'{w}: בדיוק שני מסלולים, יש {len(v)}')
                for ti, tr in enumerate(v):
                    tw = f'{w}[{ti}]'
                    if not isinstance(tr, dict):
                        r.err('tracks', f'{tw}: מסלול הוא מילון')
                        continue
                    _typecheck(r, tw, tr, TRACK, kind='track')
                    for key in ('practices', 'spotlights', 'prep'):
                        text_items(r, f'{tw}.{key}', tr.get(key))
                    check_tags(r, tw, tr.get('practices'), tr.get('spotlights'))
                    if isinstance(tr.get('practices'), list) and not tr['practices']:
                        r.err('tags', f'{tw}: לכל מסלול לפחות פרקטיקה אחת משלו (D45)')
                    if isinstance(tr.get('spotlights'), list) and not tr['spotlights']:
                        r.err('tags', f'{tw}: לכל מסלול לפחות זרקור אחד משלו (D45)')
                    if isinstance(tr.get('body'), list):
                        n = check_blocks(r, tw, tr, kit, lesson_dir, track=True)
                        n_slides += n
                        if not n:
                            r.err('tracks', f'{tw}: לכל מסלול שקף משלו — בלוק slide בתוך body')
            continue
        if typ not in BLOCKS:
            r.err(*unknown_block(f'{where}.body[{bi}]', typ, v))
            continue
        if not isinstance(v, dict):
            r.err('schema', f'{w}: צריך מילון של שדות')
            continue
        if typ == 'slide':
            check_slide(r, w, v, kit, lesson_dir)
            n_slides += 1
            continue
        _typecheck(r, w, v, BLOCKS[typ], kind=typ)
        if track and typ in ('messages', 'exit'):
            r.err('tracks', f'{w}: {typ} רק בשלב משלו, לא בתוך מסלול')
        if typ in ('video', 'exit'):
            n_slides += 1
            if v.get('art'):
                check_art(r, f'{w}.art', v['art'], kit, lesson_dir)
        if typ == 'messages':
            items = v.get('items') or []
            n_slides += len(items) if isinstance(items, list) else 0
            if v.get('art'):
                check_art(r, f'{w}.art', v['art'], kit, lesson_dir)
            if isinstance(items, list) and not items:
                r.err('messages', f'{w}.items: לפחות מסר אחד')
            text_items(r, f'{w}.items', items)
            for i, x in enumerate(items if isinstance(items, list) else []):
                if isinstance(x, str) and len(x.strip()) > LL.MSG_MAX:
                    r.warn('messages', f'{w}.items[{i}]: {len(x.strip())} תווים — מסר אחד ארוך מכדי להיכנס לשקף '
                                       f'(עד {LL.MSG_MAX}). בדקי את השקף בצילום (shoot.py)')
        if typ == 'video':
            pauses = v.get('pauses') or []
            if isinstance(pauses, list) and not pauses:
                r.err('video', f'{w}.pauses: לפחות נקודת עצירה אחת עם שאלה (D25, D44)')
            for pi, p in enumerate(pauses if isinstance(pauses, list) else []):
                pw = f'{w}.pauses[{pi}]'
                if not isinstance(p, dict):
                    r.err('video', f'{pw}: צריך {{at, moment, ask}}')
                    continue
                _typecheck(r, pw, p, PAUSE)
                at = p.get('at')
                if isinstance(at, str) and at.strip() != '?' and not TIME_RE.match(at.strip()):
                    r.err('video', f'{pw}.at: "{at}" — דקה:שנייה במירכאות ("1:05"), או "?" כשאי אפשר לאמת')
                if isinstance(at, str) and at.strip() == '?' and not p.get('moment'):
                    r.err('video', f'{pw}: at: "?" — צריך moment: איזה רגע בסרטון, כדי שהמורה תמצא ותסמן אותו')
            if isinstance(v.get('length'), (int, float)):
                r.err('schema', f'{w}.length: במירכאות ("2:16") — ורק אם אומת')
            if isinstance(v.get('clip'), dict):
                check_clip(r, f'{w}.clip', v)
        if typ == 'handout':
            if not (v.get('items') or v.get('text')):
                r.err('schema', f'{w}: צריך items או text')
            text_items(r, f'{w}.items', v.get('items'))
        if typ == 'exit':
            if v.get('form') not in ('board', 'sticky', 'print'):
                r.err('exit', f'{w}.form: board · sticky · print (לא דיגיטלי)')
            pr = v.get('prompts') or []
            text_items(r, f'{w}.prompts', pr)
            if isinstance(pr, list) and not pr:
                r.err('exit', f'{w}.prompts: לפחות שאלה אחת')
            elif isinstance(pr, list) and len(pr) > 3:
                r.warn('exit', f'{w}.prompts: {len(pr)} שאלות — 2–3 שאלות קצרות')
    if not track:
        if kind == 'messages' and types.count('messages') != 1:
            r.err('messages', f'{where}: שלב "חשוב לזכור" מכיל בדיוק בלוק messages אחד')
        if kind != 'messages' and 'messages' in types:
            r.err('messages', f'{where}: בלוק messages רק בשלב עם kind: messages')
        if kind == 'exit' and types.count('exit') != 1:
            r.err('exit', f'{where}: שלב כרטיס היציאה מכיל בדיוק בלוק exit אחד')
        if kind != 'exit' and 'exit' in types:
            r.err('exit', f'{where}: בלוק exit רק בשלב עם kind: exit')
        if n_slides == 0:
            r.err('slides', f'{where}: אין שקף — לכל שלב לפחות שקף אחד (slide, video, messages, exit או tracks)')
    # task/ladder checks run on the owner's own tags: the step's for shared blocks, each track's for its body
    if 'הוצאה למשימה' in (step.get('practices') or []) and 'task' not in types and 'tracks' not in types:
        r.warn('task', f'{where}: מתויג "הוצאה למשימה" בלי בלוק task (מה עושים + זמן · הרכב · כללים · במליאה)')
    tasky = {'קדימה ללמידה', 'כולם כותבים', 'Think–Pair–Share', 'Jigsaw'} & {
        p for p in step.get('practices') or [] if isinstance(p, str)}
    if tasky and kind not in ('exit', 'messages') and not {'task', 'ladder'} & set(types):
        r.warn('ladder', f'{where}: משימה ({", ".join(sorted(tasky))}) בלי שאלת עזר ושאלת אתגר — בלוק ladder (כלל 26)')
    return n_slides


def validate_dir(lesson_dir: Path, kit: LL.Kit | None = None) -> Report:
    try:
        data = LL.load_lesson(lesson_dir)
    except LL.LessonError as e:
        r = Report(Path(lesson_dir).name)
        r.err('yaml', str(e))
        return r
    return check(data, kit)


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv if not a.startswith('-')] or LL.lesson_dirs()
    kit = LL.Kit()
    bad = 0
    for d in dirs:
        rep = validate_dir(d, kit)
        rep.print()
        bad += bool(rep.errors)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
