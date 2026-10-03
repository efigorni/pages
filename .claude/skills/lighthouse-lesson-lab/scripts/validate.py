#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "jinja2"]
# ///
"""validate.py — the rules of lighthouse-lesson-lab (D8–D30, the picks' Combined rules) for lesson.yaml files.

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

FORBIDDEN = ('\u05d3\u05d5\u05e1\u05d9', 'dossier')  # the retired name of the document; it is always "המערך"
LATIN_OK = {'Think', 'Pair', 'Share', 'Jigsaw', 'PDF', 'YouTube', 'TikTok', 'WhatsApp', 'Instagram', 'Facebook',
            'Snapchat', 'Google', 'Zoom', 'Discord', 'Roblox', 'Minecraft', 'Fortnite', 'Netflix', 'Spotify',
            'iPhone', 'Android', 'Wi', 'Fi'}
GENDER_RE = re.compile(r'[א-ת]\.(?:ים|ות|ה|ת)(?![א-ת])|[א-ת]/(?:ה|ת|ים|ות|יות)(?![א-ת])')
EMOJI_RE = re.compile('[\U0001F000-\U0001FAFF☀-➿️]')
URL_RE = re.compile(r'https?://\S+')
QUOTED_RE = re.compile(r'(?:(?<=[\s(—–-])|^)[״"„“][^״"„“”\n]*?[״"”](?=[\s.,;:!?)—–-]|$)')
ID_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')


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
    'format': (str, True), 'question': (str, True), 'takeaways': (list, True), 'prep': (list, True),
    'safe': (list, False), 'time': (dict, True), 'brain_break': (dict, True), 'cover': (dict, True),
    'steps': (list, True),
}
STEP = {'id': (str, True), 'title': (str, True), 'kind': (str, False), 'minutes': (int, True),
        'practices': (list, True), 'spotlights': (list, True), 'summary': (str, True), 'body': (list, True)}
SLIDE = {'kicker': (str, False), 'title': (str, True), 'sub': (str, False), 'points': (list, False),
         'art': (object, True), 'alt': (str, False), 'timer': (int, False), 'echo': (bool, False), 'cue': (str, False)}
BLOCKS = {  # dict blocks: field → (type, required); str/list blocks by name
    'task': {'what': (str, True), 'time': (str, True), 'group': (str, True), 'rules': (str, True),
             'plenary': (str, True), 'help': (str, True), 'challenge': (str, True)},
    'ladder': {'help': (str, True), 'challenge': (str, True)},
    'slide': SLIDE,
    'timer': {'sec': (int, True), 'label': (str, True)},
    'video': {'title': (str, True), 'url': (str, True), 'length': (str, False), 'before': (str, True),
              'watch': (str, True), 'pause': (str, True), 'predict': (str, True), 'art': (object, True),
              'alt': (str, False)},
    'quote': {'title': (str, False), 'text': (str, True)},
    'handout': {'title': (str, True), 'copies': (str, True), 'items': (list, False), 'text': (str, False),
                'verbatim': (bool, False)},
    'messages': {'title': (str, False), 'items': (list, True), 'ask': (str, True), 'tip': (str, False),
                 'art': (object, True), 'alt': (str, False)},
    'exit': {'form': (str, True), 'title': (str, True), 'prompts': (list, True), 'look_for': (str, True),
             'art': (object, True), 'alt': (str, False), 'timer': (int, False)},
}
TEXT_BLOCKS = {'p': str, 'say': str, 'ask': str, 'whisper': str, 'tip': str, 'moves': list, 'list': list,
               'board': (str, list), 'tracks': list}
TRACK = {'title': (str, True), 'text': (str, True), 'when': (str, True), 'slides': (list, True)}


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


def _typecheck(r: Report, where: str, d: dict, schema: dict):
    for k in d:
        if k not in schema and not k.startswith('_'):
            r.err('schema', f'{where}: שדה לא מוכר "{k}" (מותר: {", ".join(schema)})')
    for k, (typ, req) in schema.items():
        if k not in d or d[k] is None:
            if req:
                r.err('schema', f'{where}: חסר השדה "{k}"')
            continue
        if typ is object:
            continue
        ok = isinstance(d[k], typ) and not (typ is int and isinstance(d[k], bool))
        if typ is str and isinstance(d[k], (int, float)) and k == 'pause':
            r.err('schema', f'{where}.pause: YAML קרא את הזמן כמספר ({d[k]}) — כתבי אותו במירכאות, למשל "1:05"')
        elif not ok:
            r.err('schema', f'{where}.{k}: צריך להיות {typ.__name__}, יש {type(d[k]).__name__}')


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
        for bi, (typ, v) in enumerate(LL.blocks_of(st)):
            yield from block_text(f'{w}.body[{bi}].{typ}', typ, v)


def art_text(where, art):
    if isinstance(art, list):
        for i, it in enumerate(art):
            if isinstance(it, dict) and isinstance(it.get('text'), str):
                yield f'{where}[{i}].text', it['text'], 'student'


def slide_text(where, v):
    for k in ('kicker', 'title', 'sub'):
        if isinstance(v.get(k), str):
            yield f'{where}.{k}', v[k], 'student'
    for i, p in enumerate(v.get('points') or []):
        if isinstance(p, str):
            yield f'{where}.points[{i}]', p, 'student'
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
        for k in ('before', 'watch', 'predict'):
            if isinstance(v.get(k), str):
                yield f'{where}.{k}', v[k], 'student'
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
            if isinstance(tr.get('title'), str):
                yield f'{where}[{ti}].title', tr['title'], 'neutral'
            for k in ('text', 'when'):
                if isinstance(tr.get(k), str):
                    yield f'{where}[{ti}].{k}', tr[k], 'teacher'
            for i, sl in enumerate(tr.get('slides') or []):
                if isinstance(sl, dict):
                    yield from slide_text(f'{where}[{ti}].slides[{i}]', sl)
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


# ----------------------------------------------------------------------------- the checks

def check(data: dict, kit: LL.Kit | None = None) -> Report:
    r = Report(data.get('_slug', '?'))
    kit = kit or LL.Kit()
    _typecheck(r, 'lesson', data, TOP)
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
        for p in s.get('practices') or []:
            if p not in LL.PRACTICES:
                guess = difflib.get_close_matches(str(p).replace('-', '–'), list(LL.PRACTICES), n=1, cutoff=.6)
                r.err('tags', f'{where}: "{p}" אינה אחת מ-11 הפרקטיקות' + (f' (אולי "{guess[0]}"?)' if guess else ''))
        for b in s.get('spotlights') or []:
            if b not in LL.SPOTLIGHTS:
                guess = difflib.get_close_matches(str(b), list(LL.SPOTLIGHTS), n=1, cutoff=.5)
                r.err('tags', f'{where}: "{b}" אינו אחד מ-5 הזרקורים' + (f' (אולי "{guess[0]}"?)' if guess else ''))
        if isinstance(s.get('practices'), list) and not s['practices']:
            r.err('tags', f'{where}: צריך לפחות פרקטיקה אחת')
        if isinstance(s.get('spotlights'), list) and not s['spotlights']:
            r.err('tags', f'{where}: צריך לפחות זרקור אחד')
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
        r.warn('messages', 'אין שלב "חשוב לזכור" (kind: messages) — אם במקור יש מסרים, מקריאים אותם לפני כרטיס היציאה')
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
            for sid in short['steps']:
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

    # --- sensitivity
    safe = data.get('safe')
    if sens in LL.SAFE_REQUIRED and not safe:
        r.err('safe', f'sensitivity: {sens} — צריך תיבת safe ("לפני השיעור") בראש המערך')
    if sens == 'low' and safe:
        r.err('safe', 'sensitivity: low — בלי תיבת safe')
    if safe:
        for i, x in enumerate(safe if isinstance(safe, list) else []):
            if not isinstance(x, dict) or not x.get('head') or not x.get('text'):
                r.err('safe', f'safe[{i}]: צריך {{head, text}}')
        if isinstance(safe, list) and len(safe) < 4:
            r.warn('safe', f'safe: {len(safe)} סעיפים — בדרך כלל ארבעה (יועצת · מי עלול להיפגע · לא לוחצים לשתף · אם מישהו משתף פגיעה)')
        if 'יועצ' not in str(safe):
            r.warn('safe', 'safe: לא מוזכרת היועצת')

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
    if first and 'תרגילי שליפה' in (first.get('practices') or []):
        if not any(t == 'whisper' for t, _ in LL.blocks_of(first)):
            r.err('retrieval', 'פתיחה בתרגילי שליפה: צריך whisper שמסכם מה היה בשיעור הקודם (R3)')

    # --- text: language, gender forms, voice, verbatim
    src_norm = norm(src_path.read_text(encoding='utf-8')) if src_path and src_path.exists() else ''
    for where, text, role in iter_text(data):
        clean = URL_RE.sub(' ', text)
        if role != 'verbatim':
            latin = sorted({w for w in re.findall(r'[A-Za-z][A-Za-z0-9]*', clean)} - LATIN_OK)
            if latin:
                r.err('hebrew', f'{where}: טקסט לטיני {latin[:6]} — עברית בלבד')
            g = GENDER_RE.findall(clean)
            if g:
                r.err('gender', f'{where}: צורות עם נקודה/לוכסן {g[:4]} — רבים רגיל ("תלמידים", "מוכן")')
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
                    r.warn('verbatim', f'{where}: כמעט מילה במילה ({ratio:.0%}) — תיקון שקט (D23)? אחרת העתיקי מהמקור')
                else:
                    r.err('verbatim', f'{where}: לא נמצא במקור ({ratio:.0%}) — ציטוט מהמקור נשאר כמו שהוא')
    for w in FORBIDDEN:
        if w in data.get('_raw', ''):
            r.err('forbidden', f'המילה "{w}…" אסורה — המסמך נקרא "המערך"')
    return r


def check_art(r: Report, where: str, art, kit: LL.Kit, lesson_dir: Path):
    if isinstance(art, dict):
        f = art.get('file')
        if not f:
            r.err('art', f'{where}: צריך {{file: art/…svg}}, מזהה סמל, או רשימת מיקומים')
        elif not (Path(lesson_dir) / str(f)).exists():
            r.err('art', f'{where}: הקובץ {f} לא קיים בתיקיית השיעור')
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
        return
    if not isinstance(art, list):
        return
    uses = [it for it in art if isinstance(it, dict) and it.get('use')]
    if len(uses) > LL.MAX_USES:
        r.warn('art', f'{where}: {len(uses)} סמלים — מוקד אחד ועד 3 תומכים, לכל היותר {LL.MAX_USES}')
    for i, it in enumerate(uses):
        sid, w_ = str(it['use']), f'{where}[{i}] ({it["use"]})'
        c = it.get('color')
        if c and LL.COLORS.get(str(c), str(c)).lower() not in LL.PALETTE:
            r.warn('art', f'{w_}: הצבע {c} לא מהפלטה של הערכה')
        if sid not in kit.symbols:
            continue
        vw, vh = kit.symbols[sid][0][2] or 100, kit.symbols[sid][0][3] or 100
        w, h = it.get('w'), it.get('h')
        if w and h and abs((float(w) / float(h)) / (vw / vh) - 1) > .05:
            r.warn('art', f'{w_}: w/h לא ביחס של הסמל ({vw:g}×{vh:g}) — תני רק w')
        w = float(w or (float(h) * vw / vh if h else vw))
        h = float(h or w * vh / vw)
        if not LL.SCALE_MIN - .005 <= w / vw <= LL.SCALE_MAX + .005:
            r.warn('art', f'{w_}: פי {w / vw:.2f} מהגודל הטבעי — טווח העבודה {LL.SCALE_MIN}–{LL.SCALE_MAX} '
                          f'(רוחב {vw * LL.SCALE_MIN:.0f}–{vw * LL.SCALE_MAX:.0f})')
        least = LL.MIN_SIZE.get(sid, 100 if sid.startswith('face-') else 0)
        if w < least:
            r.warn('art', f'{w_}: רוחב {w:.0f} — הסמל המפורט הזה צריך לפחות {least}')
        x = float(it.get('x', (LL.CANVAS_W - w) / 2))
        y = float(it.get('y', (LL.CANVAS_H - h) / 2))
        m = LL.MARGIN
        if x < m - .5 or y < m - .5 or x + w > LL.CANVAS_W - m + .5 or y + h > LL.CANVAS_H - m + .5:
            r.warn('art', f'{w_}: יוצא משולי הסצנה (x {x:.0f}…{x + w:.0f}, y {y:.0f}…{y + h:.0f}; '
                          f'המסגרת {m}…{LL.CANVAS_W - m} × {m}…{LL.CANVAS_H - m})')
    texts = [it for it in art if isinstance(it, dict) and it.get('text') is not None]
    words = sum(len(str(t['text']).split()) for t in texts)
    if words > 3:
        r.warn('art', f'{where}: {words} מילים בתוך התמונה — עד 3, והמשפט עצמו בטקסט של השקף')
    for t in texts:
        if float(t.get('size', 34)) < 30:
            r.warn('art', f'{where}: תווית "{t["text"]}" בגודל {t.get("size")} — 30 ומעלה')


def check_slide(r: Report, where: str, v: dict, kit: LL.Kit, lesson_dir: Path, budget: bool = True):
    _typecheck(r, where, v, SLIDE)
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


def check_blocks(r: Report, where: str, step: dict, kit: LL.Kit, lesson_dir: Path):
    kind = LL.kind_of(step)
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
            if typ == 'tracks':
                if len(v) != 2:
                    r.err('tracks', f'{w}: בדיוק שני מסלולים, יש {len(v)}')
                for ti, tr in enumerate(v):
                    if not isinstance(tr, dict):
                        r.err('tracks', f'{w}[{ti}]: מסלול הוא מילון')
                        continue
                    _typecheck(r, f'{w}[{ti}]', tr, TRACK)
                    sl = tr.get('slides') or []
                    if not sl:
                        r.err('tracks', f'{w}[{ti}]: לכל מסלול שקף משלו')
                    for i, spec in enumerate(sl):
                        if isinstance(spec, dict):
                            check_slide(r, f'{w}[{ti}].slides[{i}]', spec, kit, lesson_dir)
                            n_slides += 1
            continue
        if typ not in BLOCKS:
            r.err('schema', f'{w}: סוג בלוק לא מוכר (מותר: {", ".join(list(TEXT_BLOCKS) + list(BLOCKS))})')
            continue
        if not isinstance(v, dict):
            r.err('schema', f'{w}: צריך מילון של שדות')
            continue
        if typ == 'slide':
            check_slide(r, w, v, kit, lesson_dir)
            n_slides += 1
            continue
        _typecheck(r, w, v, BLOCKS[typ])
        if typ in ('video', 'messages', 'exit'):
            n_slides += 1
            if v.get('art'):
                check_art(r, f'{w}.art', v['art'], kit, lesson_dir)
        if typ == 'handout' and not (v.get('items') or v.get('text')):
            r.err('schema', f'{w}: צריך items או text')
        if typ == 'exit':
            if v.get('form') not in ('board', 'sticky', 'print'):
                r.err('exit', f'{w}.form: board · sticky · print (לא דיגיטלי)')
            pr = v.get('prompts') or []
            if isinstance(pr, list) and not pr:
                r.err('exit', f'{w}.prompts: לפחות שאלה אחת')
            elif isinstance(pr, list) and len(pr) > 3:
                r.warn('exit', f'{w}.prompts: {len(pr)} שאלות — 2–3 שאלות קצרות')
        if typ == 'messages':
            items = v.get('items') or []
            if isinstance(items, list) and not items:
                r.err('messages', f'{w}.items: לפחות מסר אחד')
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
    if 'הוצאה למשימה' in (step.get('practices') or []) and 'task' not in types and 'tracks' not in types:
        r.warn('task', f'{where}: מתויג "הוצאה למשימה" בלי בלוק task (מה עושים + זמן · הרכב · כללים · במליאה)')
    writing = {'קדימה ללמידה', 'כולם כותבים'} & set(step.get('practices') or [])
    if writing and kind not in ('exit', 'messages') and not {'task', 'ladder'} & set(types):
        r.warn('ladder', f'{where}: משימת כתיבה ({", ".join(sorted(writing))}) בלי שאלת עזר ושאלת אתגר — בלוק ladder')


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
