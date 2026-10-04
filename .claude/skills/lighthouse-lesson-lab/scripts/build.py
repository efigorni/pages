#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml", "jinja2"]
# ///
"""build.py — one lesson folder → index.html (המערך) + slides.html (the deck), then the validator.

    uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/build.py lesson-lab/lessons/<slug> [...]

Also syncs lesson-lab/lessons/_assets/ (css, js, the art kit, reveal.js 5.2.1). Never touches the hub
(lessons/index.html — build_all.py rebuilds it in the control wave, D34) and never makes the PDF
(export_pdf.py, D36). Exit code 1 when any lesson has a validation error.
The first line is the skill version (lessonlib.skill_version): when it changes mid-run, the skill was updated.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.dont_write_bytecode = True  # keep the skill folder free of __pycache__
sys.path.insert(0, str(Path(__file__).resolve().parent))
import lessonlib as LL  # noqa: E402
import validate as V  # noqa: E402


def build_one(lesson_dir: Path, kit: LL.Kit) -> tuple[V.Report, dict | None]:
    """Render one lesson and validate it; returns the report and the template context (None if unrenderable)."""
    lesson_dir = Path(lesson_dir).resolve()
    rep = V.validate_dir(lesson_dir, kit)
    if any(code in ('yaml',) for code, _ in rep.errors):
        return rep, None
    data = LL.load_lesson(lesson_dir)
    try:
        lesson_html, slides_html, ctx = LL.render_lesson(data, kit)
    except Exception as e:  # a schema error the renderer cannot get past
        rep.err('render', f'הבנייה נכשלה: {type(e).__name__}: {e} — תקני קודם את שגיאות הסכמה')
        return rep, None
    for name, html in (('index.html', lesson_html), ('slides.html', slides_html)):
        for w in V.FORBIDDEN:
            if w in html:
                rep.err('forbidden', f'{name}: המילה "{w}…" אסורה')
        LL.write_atomic(lesson_dir / name, html)
    return rep, ctx


def main(argv: list[str]) -> int:
    dirs = [Path(a) for a in argv if not a.startswith('-')]
    if not dirs:
        print(__doc__)
        return 2
    print(LL.skill_version())
    LL.sync_assets()
    kit = LL.Kit()
    bad = 0
    for d in dirs:
        rep, ctx = build_one(d, kit)
        if ctx:
            print(f'→ {Path(d) / "index.html"} · {Path(d) / "slides.html"} ({len(ctx["slides"])} שקפים)')
        rep.print()
        bad += bool(rep.errors)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
