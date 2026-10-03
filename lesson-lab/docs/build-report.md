# lighthouse-lesson-lab — build report

Builder run, 2026-10-03. The design is in `docs/spec.md`; this page covers what exists, how to run it, and what is still open.

## What exists where

| Path | Contents |
|---|---|
| `.claude/skills/lighthouse-lesson-lab/SKILL.md` | Hebrew skill with a bilingual description (D35). It holds the iron rules, the recipe with completion criteria, the commands and a common-mistakes table. |
| `…/references/` | `hotam-al-ze.md` and `migdalor.md` (byte-identical copies, sha256 checked) · `style-guide.md` (D8–D30 and rules 1–35 as instructions, with ✓/✗ examples) · `schema.md` (fields, YAML pitfalls, blocks, scene format, what is derived, a full example) · `checklist.md` (judgement checks the validator can't make) |
| `…/templates/` | `lesson.html.j2` (המערך) · `slides.html.j2` (deck) · `hub.html.j2` (hub) |
| `…/assets/` | `lesson.css` (the theme evolved: D14 sections, `.tracks`, whisper label "לעצמך", `.handout`, slide cues, phone layout with a stacked plan table, print CSS; the rail, `.why`, `.choice`, `.proj` and picker parts removed) · `slides.css` (the reveal RTL font fix kept; layout in `.frame`; print rules) · `lesson.js` (hero art and timers) · `deck.js` (reveal init, `?print-pdf`, `?thumb`, the `T` key) · `art/` (the illustrator's kit, untouched by me) |
| `…/scripts/` | `lessonlib.py` (model: load, derive, render, kit, asset sync) · `build.py` · `validate.py` · `export_pdf.py` · `build_all.py` |
| `lesson-lab/lessons/_assets/` | synced css/js and `art/kit.svg`; `reveal/` = reveal.js **5.2.1** (`reveal.js`, `reveal.css`, `reset.css`, `LICENSE`, `VERSION`), unmodified npm dist. The dist banner says 5.2.0, but `Reveal.VERSION` is 5.2.1, an upstream quirk. |
| `lesson-lab/lessons/index.html` | hub (built by `build_all.py`) |
| `lesson-lab/docs/spec.md` | design spec |
| `lesson-lab/docs/runs/pkg-g7-03.md` | the pilot's change log (also a sample of the log format) |

My stub kit was retired the moment `art/kit.svg` landed. `build.py` now requires the real kit.

## Commands (from the repo root)

```bash
# build + validate one lesson (lesson agents)
uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/build.py lesson-lab/lessons/<slug>
# validate only (any number of dirs; none = all lessons)
uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/validate.py lesson-lab/lessons/<slug>
# PDF of one or more decks (control wave; skips decks whose PDF is current; --force)
uv run --with playwright python3 .claude/skills/lighthouse-lesson-lab/scripts/export_pdf.py lesson-lab/lessons/<slug>
# control wave: every lesson + hub + summary (+ PDFs); -q = summary lines only
uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/build_all.py --pdf
```

`build.py` and `validate.py` exit 1 on any error. `build_all.py` exits 1 on any lesson error or a failed PDF.

**PDF method.** Playwright drives the installed Google Chrome (`channel="chrome"`). It loads `slides.html?print-pdf` (reveal margin 0), waits for `Reveal.isReady()` and `document.fonts.ready`, and prints with `prefer_css_page_size` and backgrounds. That gives one 1440×810 page per slide, with fragments visible and slide numbers on each page. The script checks pages = slides, and takes about 2.5 s per deck.

Two things are rejected or fallback only:
- Chrome's `--print-to-pdf` CLI ignores `@page` and prints Letter portrait, so it was rejected.
- With no Chrome, run `uv run --with playwright playwright install chromium` and pass `--bundled`.

## Validator rules

**Errors (✗) — must be fixed:**
- **Schema:** types, required fields, unknown keys, ids; YAML parse errors come with a Hebrew hint.
- **Time:** the core (content + "חשוב לזכור" + exit) is exactly **35′**, and core + extensions is **≤ 45′**.
- **Structure:**
  - Steps run content → extensions → messages → exit, with exactly one exit, last, never in `time.short`.
  - `time.clock`, `time.short` and `brain_break` (2–3 ideas, valid ids) are all present.
  - `tracks` has exactly 2 tracks, each with its own slide.
- **Tags:** every step has ≥1 of the 11 practices and ≥1 of the 5 spotlights, spelled exactly (the validator suggests the closest match).
- **Slides:** every step has ≥1 slide; every slide has art; every kit symbol exists; every lesson SVG and its `#refs` exist.
- **Blocks:**
  - every `task` has `help` and `challenge` (the ladder);
  - every `video` has `before`, `watch`, `pause` and `predict`;
  - `pause` read as a number means a YAML gotcha.
- **Sensitivity:** `safe` is present at `med|med-high|high` and absent at `low`.
- **Opening:** a retrieval opening (תרגילי שליפה) needs a recap `whisper` (R3).
- **Language:**
  - no Latin outside an allow-list (Think/Pair/Share, Jigsaw, PDF, app names; URLs and verbatim fields exempt);
  - no emoji;
  - no dot/slash gender forms outside verbatim fields;
  - the forbidden word is checked in the YAML and in the built HTML.
- **Verbatim:** `messages`, `quote` and `handout` with `verbatim: true` must appear in `src_text`. They are compared as words, so punctuation fixes pass and wording changes fail.

**Warnings (!) — fix, or log why they stay:**
- **Voice:** teacher prose not in feminine singular. This uses only forms that can't be a past tense or a noun, and checks outside quotes.
- **Arc:** a core outside 6–7 steps.
- **Slide budget:** kicker 45, title 60, sub 90, ≤4 points of ≤80.
- **Exit:** over 5′ or over 3 prompts.
- **Safe box:** fewer than 4 items, or no counsellor.
- **Verbatim:** near-verbatim (≥90%).
- **Tasks:** "הוצאה למשימה" without a `task`, or a writing step without `ladder`/`task`.
- **Brain break:** outside 15′–25′, or not taken from an extension.
- **Inventory:** metadata differs from `lessons.json`.
- **Art-guide composition:**
  - more than 5 symbols;
  - scale outside 0.6–1.6× natural size;
  - below the minimum size of `circle4`, `crowd`, `hands-help`, `school`, `red-line` or `face-*`;
  - a w/h ratio more than 5% off;
  - outside the 16-unit margin;
  - a colour off the palette;
  - more than 3 words, or a label under 30;
  - a lesson SVG whose viewBox ≠ 620×540.

All of these were exercised on a seeded fixture with every violation, and on a clean fixture covering video, tracks, handout, a printed exit card, `timer` and a lesson-file illustration.

## How a lesson agent uses the skill

1. Load the skill (`.claude/skills/lighthouse-lesson-lab/SKILL.md`).
2. Once per package, read `style-guide.md`, `schema.md` and `assets/art/art-guide.md`.
3. For each lesson, read the source text, its digest card, and its `docs/lessons.json` row.
4. Plan the arc before writing:
   - which activities stay;
   - 6–7 core steps with a 35′ core, then extensions;
   - the opening practice;
   - a discussion technique for each discussion;
   - the exit-ticket form;
   - a slide and scene for every step.
5. Write `lessons/<slug>/lesson.yaml`, copying the metadata. Hebrew goes only in block style.
6. Run `build.py`. Fix every ✗ until the report says `0 שגיאות`, then fix or log each !.
7. Read the built `index.html` against `checklist.md`.
8. Log kept, changed and dropped material, and any remaining warnings, in `docs/runs/<package>.md`.
9. No git, no browser, no PDF, and write only inside your own lesson folders (D2, D34, D36).

## Pilot

- Source: `lesson-lab/lessons/g7-makom-baolam/lesson.yaml`, plus `art/sun-circles.svg` and `art/venn.svg`.
- Built:
  - `lesson-lab/lessons/g7-makom-baolam/index.html` (המערך);
  - `slides.html` (13 slides);
  - `slides.pdf` (13 pages, about 1 MB).
- Validation: **0 errors, 0 warnings**.
- Arc: 7 core steps (27′ content + 3′ messages + 5′ exit), 2 × +5′ extensions, a brain break after the sun step taken from the personal-sheet extension, and the `safe` box (med-high).
- Checked in Chrome:
  - המערך at 1280px and at 420px (no horizontal scroll; the plan table stacks);
  - the deck at 1440px and 420px (`T` timer, `#/N` links, fragments);
  - the PDF contact sheet;
  - an A4 print of המערך (8 pages);
  - the hub with 1 lesson and with a synthetic 116-lesson render.

Fixes found while checking:
- reveal's print view collapsed the slides.
- An `exit` class collided with the step `kind`.
- Bidi of time labels: the approved samples use native RTL ranges, with only `+N′` forced LTR.
- Box widths were uneven.
- The unit facet was too large at scale.
- The art was off the guide's scale and margins.
- Build files were written 0600.
- PDF staleness ignored shared assets.

## Known gaps

- **Lesson agents can't see their slides.** The validator measures word budgets, not rendered overflow. Visual checks happen in the control wave (D36).
- **Hand-drawn lesson SVGs** (`art/*.svg`) are checked only for viewBox and `#refs`, not for composition.
- **PDF scenes are raster images** (the rough filter can't stay vector), at about 2.5× slide resolution, about 1 MB per lesson. That is ~120 MB for 116 lessons, and every re-export adds history.
- **Fonts load from Google Fonts** (allowed by D28). Offline, pages fall back to Arial Hebrew.
- **Video and tracks were tested only in a scratch fixture.** The pilot source has neither; the first real use is in packages flagged `alt-track` (7 lessons) and lessons with videos.
- **The skill and `lesson-lab/theme/` overlap.** `theme/` still serves the picker, and `assets/` holds the evolved copies. Retire `theme/` when the picker is done.
- **Kit subset per deck.** The art guide says to paste the whole kit per page; the build inlines only the symbols, defs and `#rough` a deck uses. The ids are the same and pages are smaller.
- **Language of these docs.** `spec.md` and this report are in English, like `picks-summary.md`. Everything user-facing, and the skill itself, is in Hebrew.
