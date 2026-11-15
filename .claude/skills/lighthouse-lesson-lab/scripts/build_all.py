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

import argparse
import heapq
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))
import build as B  # noqa: E402
import lessonlib as LL  # noqa: E402

GRADE_COLOR = {4: '#ad5876', 5: '#4c78a8', 6: '#3f8f8d', 7: '#e08f36', 8: '#6c60b0', 9: '#4a8571'}


def teaching_order(cards: list[dict], sequences: dict) -> list[dict]:
    """Keep shared lessons in each grade's teaching order, preferring the existing card order."""
    by_slug = {c['slug']: c for c in cards}
    following = {slug: set() for slug in by_slug}
    pending = dict.fromkeys(by_slug, 0)
    for sequence in sequences.values():
        present = list(dict.fromkeys(slug for slug in sequence if slug in by_slug))
        for before, after in zip(present, present[1:]):
            if after not in following[before]:
                following[before].add(after)
                pending[after] += 1
    ready = [(by_slug[slug]['key'], slug) for slug, count in pending.items() if not count]
    heapq.heapify(ready)
    ordered = []
    while ready:
        _, slug = heapq.heappop(ready)
        ordered.append(by_slug[slug])
        for after in following[slug]:
            pending[after] -= 1
            if not pending[after]:
                heapq.heappush(ready, (by_slug[after]['key'], after))
    if len(ordered) != len(cards):
        raise ValueError('Curriculum sequences disagree on the order of shared lessons')
    return ordered


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
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument('--grades', nargs='+', type=int, choices=LL.GRADE_LABEL,
                       help='Build only these grades; keep every lesson in the hub.')
    scope.add_argument('--hub-only', action='store_true', help='Update only the hub from lesson metadata.')
    parser.add_argument('--no-sync-assets', action='store_true', help='Preserve the published shared assets.')
    parser.add_argument('--pdf', action='store_true')
    parser.add_argument('--force-pdf', action='store_true')
    parser.add_argument('-q', action='store_true')
    args = parser.parse_args(argv)
    if args.hub_only and (args.pdf or args.force_pdf):
        parser.error('--hub-only cannot export PDFs')
    print(LL.skill_version())
    inv = LL.inventory()
    order = {slug: i for i, slug in enumerate(inv)}
    dirs = LL.lesson_dirs()
    lessons = {d: LL.load_lesson(d) for d in dirs}
    selected = [] if args.hub_only else [d for d in dirs if not args.grades or lessons[d].get('grade') in args.grades]
    if args.grades and not selected:
        parser.error('No lesson folders match the selected grades')
    if not args.hub_only and not args.no_sync_assets:
        LL.sync_assets()
    kit = LL.Kit() if selected else None
    cards, totals, bad = [], [0, 0], 0
    for d in dirs:
        if d in selected:
            rep, ctx = B.build_one(d, kit)
            rep.print(verbose=not args.q)
            totals[0] += len(rep.errors)
            totals[1] += len(rep.warnings)
            bad += bool(rep.errors)
            if not ctx:
                continue
        L = lessons[d]
        grades = inv.get(d.name, {}).get('grades_served') or L.get('grades_served') or [L.get('grade')]
        cards.append({
            'slug': d.name, 'title': L.get('title', d.name), 'question': L.get('question', ''),
            'grade': L.get('grade'), 'grades': grades,
            'grade_label': ', '.join(LL.GRADE_LABEL[g] for g in grades if g in LL.GRADE_LABEL),
            'month': L.get('month', ''), 'months': LL.months_of(L.get('month', '')),
            'unit': L.get('unit', ''), 'unit_order': L.get('unit_order'), 'unit_size': L.get('unit_size'),
            'lesson_no': LL.lesson_no(L),
            'color': GRADE_COLOR.get(L.get('grade'), '#3f8f8d'), 'has_pdf': (d / 'slides.pdf').exists(),
            'key': (order.get(d.name, 10_000), L.get('grade') or 0, d.name),
        })
    sequences = json.loads(LL.INVENTORY.read_text(encoding='utf-8')).get('sequence', {})
    cards = teaching_order(cards, sequences)
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

    if (args.pdf or args.force_pdf) and selected:
        uv = shutil.which('uv')
        if not uv:
            print('✗ uv לא נמצא — התקיני uv כדי לייצא PDF')
            return 1
        cmd = [uv, 'run', '--with', 'playwright', 'python3', str(Path(__file__).with_name('export_pdf.py'))]
        cmd += [str(d) for d in selected] + (['--force'] if args.force_pdf else [])
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
