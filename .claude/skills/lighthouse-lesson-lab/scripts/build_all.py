#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "jinja2"]
# ///
"""build_all.py — the control wave: every lesson, the hub (lessons/index.html) and a validation summary.

    uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/build_all.py [--pdf] [--force-pdf] [-q]

--pdf        also export slides.pdf for every lesson whose deck changed (runs export_pdf.py through uv).
--force-pdf  re-export every PDF.
-q           summary only (no per-rule lines).
Exit code 1 when any lesson has a validation error or a PDF fails.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402
import lessonlib as LL  # noqa: E402

GRADE_COLOR = {6: '#3f8f8d', 7: '#e08f36', 8: '#6c60b0', 9: '#4a8571'}


def motif(i: int, c: str) -> str:
    v = i % 4
    if v == 0:
        return (f'<svg viewBox="0 0 100 100"><circle cx="60" cy="42" r="30" fill="{c}" fill-opacity=".9"/>'
                f'<circle cx="36" cy="60" r="25" fill="#f7ae4d" fill-opacity=".78"/></svg>')
    if v == 1:
        return (f'<svg viewBox="0 0 100 100"><defs><pattern id="p{i}" width="8" height="8" patternTransform="rotate(45)" '
                f'patternUnits="userSpaceOnUse"><line x1="0" y1="0" x2="0" y2="8" stroke="#f7ae4d" stroke-width="3.6"/>'
                f'</pattern></defs><circle cx="42" cy="55" r="30" fill="url(#p{i})"/>'
                f'<circle cx="66" cy="36" r="20" fill="{c}" fill-opacity=".88"/></svg>')
    if v == 2:
        rings = ''.join(f'<circle cx="50" cy="50" r="{r}"/>' for r in (8, 16, 24, 32, 40))
        return f'<svg viewBox="0 0 100 100"><g fill="none" stroke="{c}" stroke-width="2.6">{rings}</g></svg>'
    return (f'<svg viewBox="0 0 100 100"><circle cx="52" cy="48" r="31" fill="{c}"/><path d="M52 26a22 20 0 1 0 -12 36 '
            f'l-6 12 l14 -8 a22 20 0 0 0 4 -40 z" fill="none" stroke="#fff" stroke-width="2.6" stroke-linejoin="round"/></svg>')


def main(argv: list[str]) -> int:
    quiet = '-q' in argv
    print(LL.skill_version())
    LL.sync_assets()
    kit = LL.Kit()
    inv = LL.inventory()
    order = {slug: i for i, slug in enumerate(inv)}
    dirs = LL.lesson_dirs()
    cards, totals, bad = [], [0, 0], 0
    for d in dirs:
        rep, ctx = B.build_one(d, kit)
        rep.print(verbose=not quiet)
        totals[0] += len(rep.errors)
        totals[1] += len(rep.warnings)
        bad += bool(rep.errors)
        if not ctx:
            continue
        L = ctx['L']
        grades = L.get('grades_served') or [L.get('grade')]
        cards.append({
            'slug': d.name, 'title': L.get('title', d.name), 'question': L.get('question', ''),
            'grade': L.get('grade'), 'grades': grades, 'grade_label': ctx['grade_label'],
            'month': L.get('month', ''), 'months': LL.months_of(L.get('month', '')),
            'unit': L.get('unit', ''), 'unit_order': L.get('unit_order'), 'unit_size': L.get('unit_size'),
            'lesson_no': LL.lesson_no(L),
            'color': GRADE_COLOR.get(L.get('grade'), '#3f8f8d'), 'has_pdf': (d / 'slides.pdf').exists(),
            'key': (order.get(d.name, 10_000), L.get('grade') or 0, d.name),
        })
    cards.sort(key=lambda c: c['key'])
    for i, c in enumerate(cards):
        c['motif'] = LL.Markup(motif(i, c['color']))
    grades = sorted({g for c in cards for g in c['grades'] if g in LL.GRADE_LABEL})
    months = [m for m in LL.MONTHS if any(m in c['months'] for c in cards)]
    units = list(dict.fromkeys(c['unit'] for c in cards if c['unit']))
    hub = LL.env().get_template('hub.html.j2').render(
        lessons=cards, months=months, units=units,
        grades=[{'v': str(g), 'label': LL.GRADE_LABEL[g], 'c': GRADE_COLOR[g]} for g in grades])
    LL.write_atomic(LL.LESSONS / 'index.html', hub)
    print(f'\n→ {LL.LESSONS / "index.html"}: {len(cards)} שיעורים · {totals[0]} שגיאות · {totals[1]} אזהרות · '
          f'{bad} שיעורים עם שגיאות')

    if '--pdf' in argv or '--force-pdf' in argv:
        uv = shutil.which('uv')
        cmd = [uv, 'run', '--with', 'playwright', 'python3', str(Path(__file__).with_name('export_pdf.py'))]
        cmd += [str(d) for d in dirs] + (['--force'] if '--force-pdf' in argv else [])
        if not uv:
            print('✗ uv לא נמצא — הריצי ידנית: ' + ' '.join(cmd[1:]))
            return 1
        rc = subprocess.call(cmd)
        if rc:
            bad += 1
        else:  # the hub links PDFs that now exist
            for c in cards:
                c['has_pdf'] = (LL.LESSONS / c['slug'] / 'slides.pdf').exists()
            LL.write_atomic(LL.LESSONS / 'index.html', LL.env().get_template('hub.html.j2').render(
                lessons=cards, months=months, units=units,
                grades=[{'v': str(g), 'label': LL.GRADE_LABEL[g], 'c': GRADE_COLOR[g]} for g in grades]))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
