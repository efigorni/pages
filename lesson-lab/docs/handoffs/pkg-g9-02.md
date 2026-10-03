# Handoff — pkg-g9-02 (g9-osher-1, g9-osher-2)

**DONE — superseded.**
- Both lessons are built: 0 errors and 0 warnings. `shoot.py` shows 0 display errors, and every image was reviewed.
- Report: `lesson-lab/docs/runs/pkg-g9-02.md`. The rest of this file is the paused state, kept for the record.

Paused by the coordinator. Brief: `lesson-lab/docs/lesson-agent-brief.md`. All required reading has been done: the skill, `decisions.md` up to D58, the pilots, sources and digests (`sources/digests/9a.md:52`, `:74`).

## Status

| Lesson | Written | Built/validated | Screenshotted | Notes |
|---|---|---|---|---|
| `g9-osher-1` | ✓ full draft: `lesson-lab/lessons/g9-osher-1/lesson.yaml` | ✗ not yet | ✗ | All art comes from kit symbols, so no `art/` folder is needed |
| `g9-osher-2` | ✗ only the empty folder `lesson-lab/lessons/g9-osher-2/art/` exists | ✗ | ✗ | Plan below |
| Report `lesson-lab/docs/runs/pkg-g9-02.md` | ✗ | | | |

## Verified facts (don't redo)
- Videos are alive (oEmbed 200). Lengths come from the watch page (`lengthSeconds`):
  - `NIi29Qeqlis` = עידן רייכל, "אבן על אבן (רגע של אושר)", **3:17**. The lyrics are in the YouTube description.
  - `7YIUyrtRBOo` = "שמחות קטנות", עמיר בניון ומיכה שטרית, **4:20**. Micha Shitrit wrote it *inspired by* Desi's text, so the lyrics are not the text itself. Do not quote the lyrics.
- Pause times can't be verified (the captions API needs a token), so use `at: "?"` with a `moment`.
- Validator traps:
  - ☺ (U+263A) fails the emoji check. Write "פרצוף מחייך" instead.
  - ` #` inside a plain YAML scalar starts a comment. Put text that has the $ / # marks in `>-` blocks.
  - Never start a `say` with ״, because `unquote` strips it.

## g9-osher-1: next steps
1. Build it: `uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/build.py lesson-lab/lessons/g9-osher-1`, then fix until 0 errors.
2. Decisions already in the YAML (log them in the report):
   - **Opening:** "מה הקשר?" with the song, then Think–Pair–Share on the 3 questions of slide 10.
   - **Group work:** 4 group cards from slides 12–13, rephrased. Card 3 is a drawing instead of an internet image search (D46).
   - **Definition:** slide 16 is quoted verbatim in "מה גילינו?".
   - **Practice:** slides 17–18 are content ("זה בידנו" quote + "נתרגל"), D50.
   - **Messages:** slides 19 + 20, the closing summary (D51), 2 items.
   - **Extensions:** remaining groups present (slide 14 note), and "למדנו, מיישמים" (slide 21).
   - **Out:** "מסכמים שיעור" (slide 22) becomes the optional line in the exit card.
   - **D58:** the info-sheet lines 50%/40%/10% ("happiness pie", not supported) were dropped from the verbatim handout. g6-mahu-osher kept them, so flag the inconsistency.
   - **src_fixes (3, each unique):**
     - ובחומי → ובתחומי
     - "רוצים, לא כשאנחנו" → "אלא"
     - ובניהם → וביניהם

## g9-osher-2: plan (sensitivity `med`, flag `unit-summary-inside`)
- **Core (35′):**
  - `list` 5′: קדימה ללמידה — "write ten things that make you happy" (slide 10). Ladder.
  - `sort` 6′: mark ל/ח/מ plus $, #, "פרצוף מחייך", then count. The 4 board lines are written before class (add a `prep` line). Task card. Second slide = slide 13 verbatim.
  - `groups` 6′: slide 14 as a task card. Plenary question from slide 15: "איזה תחום הייתם רוצים להרחיב?" The bridge `say` paraphrases slide 16.
  - `circles` 6′:
    - Whisper about Desi, from the slide 9 note.
    - Quote Desi's text verbatim (source lines 147–162, without the attribution line).
    - Slide 17 title/sub verbatim ("ביכולתנו לגרום לאחרים תחושת אושר"), plus a quote of slide 17 up to "ועצב" (leave out "(volf,2015)").
  - `drops` 4′:
    - Slide 19, `verbatim: [sub]`.
    - Quote of slide 18.
    - Ladder.
    - Tip with the 3 ideas from slide 23.
  - `remember` 3′: slide 20, 3 items verbatim.
  - `exit` 5′: "משהו שלמדתי על עצמי מהמיון" / "משהו שאני לוקח על עצמי לעשות אחרת, בעקבות השיעור" (slide 22 adapted) / optional "משהו שרציתי לומר לך".
- **Extensions:**
  - `song` 6′: video `7YIUyrtRBOo`, `length: "4:20"`.
  - `unit` 4′: D49. Whisper about the unit; slide 21 title verbatim "מה למדתם מההתבוננות על עצמכם?".
- **Clock:**
  - 18+ minutes left — both extensions.
  - 14–17 — only the song.
  - 12–13 — only `unit`.
  - Less — straight to messages.
- **brain_break:** `after: groups`, `from: unit`.
- **Out:** "נזכרים" (slide 8), per D26 / §3.
- **safe box, 4 items:**
  - Desi had cancer and died at 19. Give one sentence about her, no details.
  - The family column may be empty, and that is an answer.
  - No comparing $ marks.
  - "Ten is a direction, not a quota."
  - The source's risk-taking note (slide 11 notes) goes in the box, not in the steps.
  - Rule "לספר רק על עצמי".
  - Counselor.
- **Art files to draw in `art/`:**
  - `cover.svg`: two drops (teal = personal, orange = class) + kit sun.
  - `circles.svg`: kit heart + orange circle inside + small orange circles around.
  - `drops.svg`: big teal drop + kit board with small orange drops.
  - `song.svg`: kit laptop + heart on the screen + ink music notes.
  - Drop path: `M75 0 C90 40 150 85 150 145 A75 75 0 0 1 0 145 C0 85 60 40 75 0 Z`. Add a shading crescent in ink at 13% opacity. Don't define any `id`s.

## Then
1. Rebuild both lessons right before the last screenshot run.
2. Run `uv run --with playwright python3 .claude/skills/lighthouse-lesson-lab/scripts/shoot.py lesson-lab/lessons/g9-osher-1 lesson-lab/lessons/g9-osher-2`.
3. Read every image and fix what looks broken.
4. Go through the checklist.
5. Write `docs/runs/pkg-g9-02.md`. Its חיכוך section should cover:
   - style-guide §10: a multi-slide closing summary (cf. pkg-g6-01 friction 3).
   - The ☺ emoji trap and the ` #` YAML trap.
   - The happiness-pie inconsistency (D58).
   - Suggested kit symbols: `drop`, `music`.
