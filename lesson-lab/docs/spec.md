# lighthouse-lesson-lab — build spec

Binding sources: `decisions.md` (D1–D38) and `picks-summary.md` (rules 1–35). This spec turns them into one data format, two renderers, a validator and a recipe. The field-level reference for lesson writers is the skill's `references/schema.md`.

## 1. Layout

| Path | What |
|---|---|
| `.claude/skills/lighthouse-lesson-lab/` | `SKILL.md` (Hebrew, bilingual description, D35) · `references/` (verbatim `hotam-al-ze.md`, `migdalor.md` · `style-guide.md` · `schema.md` · `checklist.md`) · `templates/` (`lesson.html.j2`, `slides.html.j2`, `hub.html.j2`) · `assets/` (`lesson.css`, `slides.css`, `lesson.js`, `deck.js`; `art/` = the illustrator's kit) · `scripts/` (`lessonlib.py`, `build.py`, `validate.py`, `export_pdf.py`, `build_all.py`) |
| `lesson-lab/lessons/<slug>/` | `lesson.yaml` (source of truth) · `art/` (lesson-only SVGs) · built `index.html`, `slides.html`, `slides.pdf` |
| `lesson-lab/lessons/_assets/` | css/js and `art/kit.svg` copies; `reveal/` = reveal.js **5.2.1** dist, vendored |
| `lesson-lab/lessons/index.html` | hub, rebuilt only by `build_all.py` (D34) |

`build.py` syncs `_assets/` atomically and only on change, so parallel agents never tear a file. It re-fetches the pinned reveal tarball if `reveal/` is missing.

## 2. `lesson.yaml`

Hebrew values with English keys. Prose goes in block scalars. The only inline markup is `**bold**` and line breaks. Hebrew never goes inside flow `[…]`/`{…}` (PyYAML breaks on "?").

- **Lesson fields.** `slug, title, grade, month, section, unit, unit_order, unit_size, src_text, src_url, sensitivity` are copied from `docs/lessons.json`. Authored fields:
  - `sub`, `format`, `question`, `takeaways` (2–3), `prep`;
  - `safe` (`[{head, text}]`: required at `med`+, absent at `low`);
  - `time.clock` and `time.short: {steps, text}`;
  - `brain_break: {after?, signs, ideas ×2–3, from}`;
  - `cover: {art, alt?, sub?}`;
  - `steps`.
- **Step fields.** `id, title, kind` (`core`·`extension`·`messages`·`exit`), `minutes`, `practices` (≥1 of 11), `spotlights` (≥1 of 5), `summary`, `body`.
- **Blocks** (one-key mappings):
  - text: `p`, `moves`, `list`, `say`, `ask`, `whisper`, `board`, `tip`, `timer`;
  - tasks: `task {what, time, group, rules, plenary, help, challenge}`, and `ladder {help, challenge}` for short writing prompts;
  - slides: `slide {kicker?, title, sub?, points?, art, alt?, timer?, echo?, cue?}`;
  - material: `video {title, url, length?, before, watch, pause, predict, art}`, `quote` (verbatim), `handout {title, copies, items|text, verbatim?}`;
  - structure: `tracks` (2 × `{title, text, when, slides}`), `messages {items, ask, tip?, art}`, `exit {form: board|sticky|print, title, prompts, look_for, art}`.
- **Art** (620×540, kit units, per `assets/art/art-guide.md`) takes one of three forms:
  - a symbol id, drawn as the focus (≤390 units, ≤1.6× natural size);
  - placements `{use, x, y, w?, color?, flip?}` (top-left, natural size by default; a missing `color` gets the symbol's `data-color`), `#kid` tokens, or `{text, x, y, size}`;
  - `{file: art/x.svg}`.

```yaml
- id: snowball
  title: כדור שלג מתגלגל
  minutes: 8
  practices:
    - הוצאה למשימה
  spotlights:
    - שיתופיות בלמידה
  summary: זוגות ואז רביעיות מחפשים דברים משותפים
  body:
    - slide:
        title: בזוגות — 10 משפטים ששומעים בבית
        timer: 180
        art:
          - {use: pair, x: 110, y: 226, w: 270}
    - task:
        what: מוצאים דברים משותפים בקבוצה שהולכת וגדלה.
        time: 3 דקות לכל סבב
        group: זוגות ← רביעיות
        rules: דף אחד לקבוצה
        plenary: נשארים ברביעיות
        help: מה אומרים אצלכם בבית בבוקר?
        challenge: מצאו משפט שכולכם שומעים — כל אחד במילים אחרות.
```

## 3. המערך (`index.html`, D14)

Order: hero → `.lesson-card` (question · takeaways · prep, with derived lines for the deck/PDF, handouts, videos and exit material) → `.safe` → `h2.sec` + `table.plan` (`.pr` only) → `.wrap.doc`, with one `section.st` per step (`h2` + `span.t` + `a.slide-ref`, `.tags`, blocks).

The build inserts:
- the board-corner line under each `task`/`ladder`;
- the clock-check and if-short whispers at the end of the last content step;
- the brain-break `.tip` after the content step ending nearest 20′;
- a `.slide-ref` cue at each slide change after a step's first slide.

`echo: true` is the only source of `.board.screen`, so screen and slide always match. Content steps run from 0′, extensions read `+N′` (forced LTR, as in the 1.3b sample), and the closing steps are anchored to the bell. Ranges keep native RTL bidi (the 3.1c sample). Print CSS outlines the boards and keeps boxes whole.

## 4. Deck (`slides.html`, D28–D30)

Horizontal slides only, at 1440×810, RTL. The cover is slide 1; every step's slides follow in body order (tracks A then B). `video`, `messages` and `exit` generate their own slides.

Every slide is `s-pic`: a kicker, a short title, ≤1 sub line, `points` as fragments, a scene and an optional timer (`T` toggles it). Layout lives in an inner `.frame`, because reveal's print mode strips section padding and display. Each deck inlines the kit subset it uses, so it works offline (fonts excepted).

`.slide-ref` links point to `slides.html#/N-1`.

## 5. Validation

**Errors:**
- schema and YAML errors (with a Hebrew hint);
- a core that is not exactly 35′; core + extensions > 45′;
- step order: content → extensions → messages → exit (exactly one exit, last, never cut);
- per step: ≥1 practice, ≥1 spotlight, ≥1 slide;
- `task` without `help`+`challenge`;
- `safe` that does not match the sensitivity;
- `video` missing its viewing fields;
- missing clock, short or brain-break fields; tracks ≠ 2;
- art: missing, an unknown symbol, a missing file or `#ref`;
- a retrieval opening without a recap whisper;
- Latin outside the allow-list, emoji, the forbidden word (YAML and HTML), dot/slash gender forms outside verbatim fields;
- verbatim fields not found in `src_text` (compared as words).

**Warnings:**
- teacher voice not "את" (unambiguous patterns, outside quotes);
- a core outside 6–7 steps;
- slide word budget exceeded;
- an exit ticket > 5′ or > 3 prompts;
- a thin `safe` box;
- near-verbatim text;
- a missing `task`/`ladder`;
- a brain break outside 15′–25′;
- a mismatch with `lessons.json`;
- art-guide composition: > 5 symbols, scale outside 0.6–1.6, minimum sizes, ratio, the 16-unit margin, palette, ≤3 words at ≥30.

## 6. PDF

`export_pdf.py` drives the installed Google Chrome through Playwright (`uv run --with playwright`, `channel="chrome"`; nothing is installed globally):
1. opens `slides.html?print-pdf` (reveal margin set to 0);
2. waits for reveal and the fonts;
3. prints with `prefer_css_page_size` and backgrounds, one 1440×810 page per slide, fragments shown, slide numbers on every page;
4. checks pages = slides.

Chrome's own `--print-to-pdf` ignores `@page` and prints Letter portrait. Per D36, lesson agents skip PDF export, and `build_all.py --pdf` runs it.

## 7. Hub

The hub keeps the gibush look: a hero with the lesson count, then a sticky search bar with counted chips for כיתה, then חודש (a range counts for each month it spans), then יחידה. Units are shown only after a grade is picked, since there are 39.

Cards appear in `lessons.json` order: a grade-coloured motif, grade · month, the title, the unit, the question, and links to המערך, the deck and the PDF. The hub is static HTML (it works without JS), and on phones the facets fold behind "סינון".

## 8. Recipe (lesson agent)

1. Read `SKILL.md`, `style-guide.md`, `schema.md` and `art-guide.md`. For each lesson, read the source, its digest card and its `lessons.json` row.
2. Plan the arc: central activities; 6–7 core steps; a 35′ core; extensions; messages; the exit ticket; ≥1 slide per step.
3. Write `lesson.yaml`.
4. Run `build.py <dir>` until it reports `0 שגיאות`, then fix or log every warning.
5. Run `checklist.md` against the built text, and log the changes in `docs/runs/<package>.md`.
