# lighthouse-lesson-lab — build spec

Binding sources: `decisions.md` (D1–D45) and `picks-summary.md` (rules 1–35). This spec turns them into one data format, two renderers, a validator, a visual check and a recipe. The field-level reference for lesson writers is the skill's `references/schema.md`. Updated after the pilot review (`review-pilots.md`) for D42–D45.

## 1. Layout

| Path | What |
|---|---|
| `.claude/skills/lighthouse-lesson-lab/` | `SKILL.md` (Hebrew, bilingual description, D35) · `references/` (verbatim `hotam-al-ze.md`, `migdalor.md` · `style-guide.md` · `schema.md` · `checklist.md`) · `templates/` (`lesson.html.j2`, `slides.html.j2`, `hub.html.j2`) · `assets/` (`lesson.css`, `slides.css`, `lesson.js`, `deck.js`; `art/` = the illustrator's kit) · `scripts/` (`lessonlib.py`, `build.py`, `validate.py`, `shoot.py`, `export_pdf.py`, `build_all.py`) |
| `lesson-lab/lessons/<slug>/` | `lesson.yaml` (source of truth) · `art/` (lesson-only SVGs) · built `index.html`, `slides.html`, `slides.pdf` · `.shots/` (screenshots, git-ignored via `lesson-lab/.gitignore`) |
| `lesson-lab/lessons/_assets/` | css/js and `art/kit.svg` copies; `reveal/` = reveal.js **5.2.1** dist, vendored |
| `lesson-lab/lessons/index.html` | hub, rebuilt only by `build_all.py` (D34) |

`build.py` syncs `_assets/` atomically and only on change, so parallel agents never tear a file. It re-fetches the pinned reveal tarball if `reveal/` is missing.

## 2. `lesson.yaml`

Hebrew values with English keys. Prose goes in block scalars. The only inline markup is `**bold**` and line breaks. Hebrew never goes inside flow `[…]`/`{…}` (PyYAML breaks on "?").

- **Lesson fields.** `slug, title, grade, month, section, unit, unit_order, unit_size, src_text, src_url, sensitivity` are copied from `docs/lessons.json`. Authored fields:
  - `sub`, `format`, `question`, `takeaways` (2–3), `prep`;
  - `safe` (`[{head, text}]`: required at `med`+ and whenever a step has `stance: true` — then with a "עמידה מול הכיתה" item, even at `low`; absent at `low` without a stance, D45);
  - `src_fixes` (`[{from, to}]`: silent corrections applied to the source before the verbatim check, D23);
  - `time.clock` and `time.short: {steps, text}`;
  - `brain_break: {after?, signs, ideas ×2–3, from}`;
  - `cover: {art, alt?, sub?}`;
  - `steps`.
- **Step fields.** `id, title, kind` (`core`·`extension`·`messages`·`exit`), `minutes`, `practices` (≥1 of 11), `spotlights` (≥1 of 5) — in a tracks step they may live in the tracks (the union is shown), `stance?`, `summary`, `body`.
- **Blocks** (one-key mappings):
  - text: `p`, `moves`, `list`, `say`, `ask`, `whisper`, `board`, `tip`, `timer`;
  - tasks: `task {what, time, group, rules, plenary, help, challenge}`, and `ladder {help, challenge}` for short writing prompts and Think–Pair–Share questions;
  - slides: `slide {kicker?, title, sub?, points?, art, alt?, timer?, echo?, cue?, verbatim?}` (`verbatim`: true or a list of title/sub/points — exempt from the gender-form check, checked against the source, D45);
  - material: `video {title, url, length?, before, watch, pauses: [{at, moment?, ask}], art}` (D44), `quote` (verbatim), `handout {title, copies, items|text, verbatim?, lines?}`;
  - structure: `tracks` (2 × `{title, text, when, practices, spotlights, prep?, body}` — each track a full sub-step, D45), `messages {items, ask, tip?, art}`, `exit {form: board|sticky|print, title, prompts, look_for, art}`.
- **Art** (620×540, kit units, per `assets/art/art-guide.md`) takes one of three forms:
  - a symbol id, drawn as the focus (≤390 units, ≤1.6× natural size);
  - placements `{use, x, y, w?, color?, flip?, rotate?}` (top-left, natural size by default; a missing `color` gets the symbol's `data-color`), `#kid` tokens, or `{text, x, y, size}`;
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

Horizontal slides only, at 1440×810, RTL. The cover is slide 1; every step's slides follow in body order (tracks A then B; track slides carry `data-track`). `video` and `exit` generate their own slide; `messages` generates one slide per message (D42), with a smaller type tier for longer messages (`MSG_TIERS`; a single message over 300 characters gets a warning).

In המערך a tracks step shows the two chooser boxes, then each track as a framed sub-section (`section.track`: h3, its own tags, its blocks); blocks after the tracks open with "בשני המסלולים". A video shows the prep line with every pause time, the `before` screen, `watch` as a say, and per pause the time, the teacher-only `moment` and the `ask`.

Every slide is `s-pic`: a kicker, a short title, ≤1 sub line, `points` as fragments, a scene and an optional timer (`T` toggles it). Layout lives in an inner `.frame`, because reveal's print mode strips section padding and display. Each deck inlines the kit subset it uses, so it works offline (fonts excepted).

`.slide-ref` links point to `slides.html#/N-1`.

## 5. Validation

**Errors:**
- schema and YAML errors (with a Hebrew hint; retired fields — `video.pause/predict`, `tracks[].slides` — say what replaced them);
- a core that is not exactly 35′; core + extensions > 45′;
- step order: content → extensions → messages → exit (exactly one exit, last, never cut);
- per step: ≥1 practice, ≥1 spotlight (own or via its tracks), ≥1 slide; per track: its own ≥1 practice, ≥1 spotlight, ≥1 slide; no tracks/messages/exit inside a track;
- `task` without `help`+`challenge`;
- `safe` that does not match the sensitivity or a `stance` step (D45), and no "עמידה" item when a stance step exists;
- `video` without a pause, a pause time that is not "m:ss" or "?", a "?" pause without `moment`;
- missing clock, short or brain-break fields; tracks ≠ 2;
- art: missing, an unknown symbol, a missing file or `#ref`;
- a retrieval opening without a recap whisper;
- Latin outside the allow-list, emoji, the forbidden word (YAML and HTML), dot/slash gender forms outside verbatim fields;
- verbatim fields (incl. marked slide fields) not found in `src_text` after `src_fixes` (compared as words); a `src_fixes.from` not in the source.

**Warnings:**
- teacher voice not "את" (unambiguous patterns, outside quotes); a step or track with no say/ask, or more than 5;
- practices used against their cards: קדימה ללמידה outside the first step or > 10′; "כרטיס יציאה" outside the exit step (or missing on it); a step tagged הפסקת מוח;
- a core outside 6–7 steps;
- slide word budget exceeded; a single message over 300 characters;
- an exit ticket > 5′ or > 3 prompts;
- a thin `safe` box (at med+);
- a step that reads like a stance activity without `stance: true`; a stance step without the five-seconds line;
- near-verbatim text;
- a missing `task`/`ladder` (writing practices, Think–Pair–Share, Jigsaw);
- a brain break outside 15′–25′;
- a mismatch with `lessons.json`;
- art-guide composition: > 5 symbols, scale outside 0.6–1.6 (0.4 inside a container), minimum sizes, ratio, the 16-unit margin, palette, ≤3 words at ≥30 — also words, `<use>` width and color in scene files (`data-diagram` exempts a source diagram's labels).

## 5a. Visual check (`shoot.py`, D43)

Playwright drives the installed Chrome headless (`uv run --with playwright`, `channel="chrome"`), no MCP:
1. every slide at 1440×810, scale 1, `?fragments=false` (all points visible) — single PNGs plus 2×3 contact sheets at 900px per slide;
2. המערך inside a 420px-wide iframe as tall as the page (a true 420 layout, no inner scrollbar), captured one 1500px viewport at a time by scrolling the wrapper — single captures stay under Chrome's 16384px limit, which otherwise tiles long pages into repeats; three strips per sheet;
3. המערך at 1280px, the 960px reading column, 1500px tiles.

Checks (✗, exit 1): horizontal scroll at 420/1280 with the elements that stick out or whose text is wider than their box; slide text taller than the text area or leaving it; a picture leaving the slide. Warning: fonts not loaded (offline). Output goes to `<lesson>/.shots/`, emptied on every run.

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

1. Read `SKILL.md`, `style-guide.md`, `schema.md`, `art-guide.md` and the three pilots' YAML. For each lesson, read the source, its digest card and its `lessons.json` row.
2. Plan the arc: central activities; 6–7 core steps; a 35′ core; extensions; all the messages; the exit ticket; tracks; ≥1 slide per step.
3. Write `lesson.yaml`.
4. Run `build.py <dir>` until it reports `0 שגיאות`, then fix or log every warning.
5. Run `shoot.py <dir>` until it reports no ✗, and look at every image it lists.
6. Run `checklist.md` against the built text, and log the changes in `docs/runs/<package>.md`.
