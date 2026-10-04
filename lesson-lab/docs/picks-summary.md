# Picks summary — lesson-lab, round 1

**Source of the picks.** `~/Downloads/picks.json` (`updated` 2026-10-03T12:09:01.417Z) is the newer of the two files. The repo copy, `lesson-lab/picker/picks.json` (`updated` 12:08:54.784Z), has the same picks, notes and per-pick timestamps. Only the top-level `updated` stamp differs, by 7 seconds (a re-save), so there is nothing to reconcile.

**Shape.** There are 28 points: 22 have a letter pick and 6 are "none" (1.2, 3.4, 4.1, 4.2, 4.3, 4.5). Four of the "none" picks carry a note (3.4, 4.1, 4.2, 4.5). No letter pick has a note. No multi-select array came back: 3.4, the only multi point, is "none".

Labels are the options' `data-label` as written in `picker/options/*.html`. Where BRIEFS.md differs from the markup, the markup wins; for example, the 4.4b brain break is 3 minutes in the markup and 2 in BRIEFS.

## Picks

| Point | Title | Pick | Users' note (verbatim) | Binding implication |
|---|---|---|---|---|
| 1.1 | כמה משנים את המקור? | **b** · עריכה מחדש | — | Each המערך keeps the source's central activities and re-edits them into one arc of 6–7 steps, shortening, merging or sending home the secondary parts, with חותם practices layered on top; it neither reproduces the whole source (a) nor rebuilds it (c). |
| 1.2 | שלד קבוע לאורך השנה? | **none** | — | This pick mandates no skeleton; see R1 (recommended: a fixed close with an exit ticket and an opening chosen per lesson). |
| 1.3 | כמה זמן תופס המערך? | **b** · ליבה של 35 + הרחבות | — | Every המערך plans a 35-minute core plus about 10 minutes of named "אם נשאר זמן" extensions (+5′, +8′), with a clock-check note at the decision point and an "אם חסר זמן — מוותרים על…" line that never cuts the exit ticket. |
| 1.4 | כשבמקור כתוב ״לבחירת המורה״ | **c** · שני מסלולים שווים | — | When the source leaves the activity to the teacher's choice, the step shows both activities side by side as equal tracks in the same time slot, each with a "מתאים כש:" criterion, and the teacher picks before the lesson. |
| 2.1 | כמה תסריט? | **b** · הנחיות וניסוחי מפתח | — | Each step is a short numbered list of teacher moves, plus a `.task` card for any task and 2–3 key phrasings in `.say`/`.say.q`; it is never a word-for-word script and never a bare skeleton. |
| 2.2 | באיזה טון המערך מדבר אליכם? | **b** · עמית חם | — | The המערך sounds like a warm colleague who also says why a moment matters ("זה הרגע שהכי קל לדלג עליו — אל תדלגי"), not like an official directive or a clipped checklist. |
| 2.3 | שפה מגדרית | **d** · רבים רגיל | — | Students are referred to and addressed in ordinary plural ("תלמידים", "כתבו", "מי מוכן לשתף?", "כל אחד מכם"), with no dot or slash forms and no forced neutral phrasing; this replaces the house style's neutral-gender rule. |
| 2.4 | איך מדברים אל התלמידים? | **b** · חם וניטרלי | — | Everything students see (`.board`, `.board.screen`, `.exit`, slides) is warm, plain and short ("שלום לכולם! מתחילים בכתיבה קצרה."), with no emoji, no slang and no test-like solemnity. |
| 2.5 | איך המערך פונה אליכם? | **d** · ״בקשי״ | — | The whole המערך addresses the teacher in second-person feminine singular ("הציגי", "שאלי", "המתיני", "את מזמינה", "כדאי לך") instead of the house style's plural, so every copied example markup must be converted. |
| 3.1 | איך מסודר המהלך? | **c** · טבלת סקירה ופירוט | — | The lesson flow opens with a `table.plan` of the whole lesson (זמן · שלב · מה עושים · פרקטיקה), followed by the detail as a `.doc` with one `h2` per step and a `<span class="t">` time range, with no `.flow.lite` minute rail. |
| 3.2 | מה פותח את המערך? | **b** · שאלת השיעור | — | Right after the hero comes a `.lesson-card` holding the lesson question in `.question-big`, "ייקחו איתם" (2–3 takeaways) and "צריך להכין", with no goals/knowledge/skills/values block up front. |
| 3.3 | איך מסמנים את חותם ואת המגדלור? | **a** · תגיות בכל שלב | — | Every step carries a `.tags` row with its `.pr` practice tag(s) and `.beam` spotlight tag(s), and there are no `.why` boxes, no card quotations and no "מפת חותם" at the end. |
| 3.4 | מה עוד נכנס למערך? (multi) | **none** | כלום, לא צריך שום דבר נוסף | The המערך gets none of the add-ons: no content background, no print appendix, no pocket card and no separate Plan B section (edge cases in R2). |
| 4.1 | איך פותחים שיעור? | **none** | כל שיעור פרקטיקה אחרת, לפי מה שמתאים. כל הדוגמאות טובות | The opening practice is chosen per lesson from קדימה ללמידה, מה הקשר? and תרגילי שליפה by what the content needs, and is expected to vary across lessons (retrieval vs. 5.4a: R3). |
| 4.2 | איך מנהלים דיון במליאה? | **none** | כל הטכניקות טובות, כל פעילות ומה שמתאים לה | Each plenary discussion uses whichever technique fits that activity (Think–Pair–Share, מהלכי שיח with think time, or כולם כותבים followed by a round) and is tagged with its `.pr` (decision guide: R4). |
| 4.3 | עבודה בקבוצות | **none** | — | No preference was given; see R5 (recommended: the source's own group design by default, otherwise chosen by fit with the lowest prep). |
| 4.4 | הפסקת מוח | **b** · רק כהצעה | — | There is no scheduled brain break; around minute 20 the המערך places an optional `.tip` ("הפסקת מוח, אם הכיתה עייפה — 3 דקות…") listing signs of fatigue, three ready ideas and the step the minutes come from. |
| 4.5 | כרטיס יציאה | **none** | שניהם טובים, לא דיגיטלי, אפשר גם פשוט על הלוח, פחות הכנה. לא משנה מה, לא דיגיטלי. | Every exit ticket is non-digital and low-prep: either a written note collected at the door (a) or sticky notes on the board (c), with the prompt simply written on the board if wished, and never a QR code or online form (R6). |
| 4.6 | דיפרנציאליות ובחירה | **a** · שאלות עזר ואתגר | — | Every task gets a `.ladder` with one שאלת עזר and one שאלת אתגר, and both are also written in a corner of the board for the whole activity. |
| 4.7 | מסרי הסיכום: מקריאים, או שהכיתה בונה? | **a** · מקריאים את המסרים | — | Near the end, the source's summary messages are projected and read aloud verbatim, followed by one short think-then-raise-hands question; the class does not compose them. |
| 5.1 | כמה לעדכן את הדוגמאות? | **a** · נאמן למקור | — | Cases and examples are reproduced as in the source (names, apps, details), with no modernizing and no `.fill` placeholders for the teacher. |
| 5.2 | נושאים רגישים | **a** · תיבה בראש המערך | — | A lesson that touches a sensitive topic gets one `.safe` "לפני השיעור" box at the top of the המערך (counselor coordination, who may be hurt, no pressure to share, what to do on a disclosure) and no `.safe` notes inside the steps. |
| 5.3 | סרטונים ומדיה | **a** · סרטון עם משימת צפייה | — | A video always comes with a viewing task (a question before, what to watch for, a marked pause with a prediction, Think–Pair–Share after) and a prep line to open it on the classroom computer, with no offline fallback. |
| 5.4 | רצף לאורך השנה | **a** · כל שיעור עצמאי | — | Every המערך stands alone, so a substitute or a student who missed the last lesson can join without a gap: no teaser for the next lesson and no class product that runs through the year. |
| 5.5 | עמדה מול הכיתה: כמה פומבית הבחירה? | **a** · כמו במקור — עומדים בחלל | — | A physical stance activity from the source stays public in the room as the source has it, preceded by "חושבים לבד חמש שניות, בלי להסתכל על אף אחד — ורק אז זזים" and followed by one speaker from each side. |
| 6.1 | באיזה כלי בונים את המצגת? | **c** · reveal.js + גיבוי PDF (מומלץ) | — | The visual aid is a reveal.js deck in the site's design language, shipped with an automatically generated PDF of the same deck as an offline backup. |
| 6.2 | מה על השקפים? | **b** · איור גדול + מעט מילים | — | Every slide is an eli5-style slide: a large illustration plus a kicker, a short headline and at most one short line. |
| 6.3 | איך המערך מפנה לשקפים? | **a** · תגית שקף בכל שלב | — | Every step names its slide(s) with a `.slide-ref` ("שקף 1", "שקפים 2–3"), with an inline `.slide-ref` wherever the slide changes mid-step. |

## Combined rules

Numbered continuously so other documents can cite "rule N". "R" numbers point to **Needs a ruling** below.

### Structure & time

1. **MUST** start from the שפ״י lesson and re-edit it (1.1b). Keep its central activities, order them into one arc and aim for 6–7 steps in 45 minutes. Shorten, merge or move home whatever is secondary: for example, three reflection questions become one asked in depth, and a personal worksheet goes home.
2. **MUST** split the time into a 35-minute core and about 10 minutes of named extensions (1.3b). Each extension is a full mini-step titled "אם נשאר זמן: …" with its length (+5′, +8′). Extensions sit after the last core content step and before the closing steps (messages, then exit ticket).
3. **MUST** end the last core content step with a clock-check `.say.whisper` that maps the remaining minutes to what to do next, and include one "אם חסר זמן גם לליבה — מוותרים על …" line naming what to cut from the core (1.3b).
4. **MUST** close every lesson with an exit ticket inside the core. It is the one step never cut (the 1.3b markup itself says "על כרטיס היציאה לא מוותרים"; also 4.5; R1).
5. **SHOULD** choose the opening for each lesson by its content, so no fixed skeleton repeats across lessons (4.1; 1.2 → R1).
6. **MUST** present a "לבחירת המורה" choice in the source as two equal tracks (1.4c): one step and one time slot, with two side-by-side boxes. Each box has a title, 1–2 lines and "מתאים כש: …", and the teacher decides before the lesson. The `table.plan` row names both tracks, and each track gets its own slide(s).
7. **MUST** keep each lesson standalone (5.4a). It has to work for a substitute and for students who missed the previous lesson. Do not include:
   - a teaser for the next lesson;
   - a class product that carries over between lessons;
   - a follow-up that the next lesson depends on.

   For retrieval openings, see R3.

### Voice & language

8. **MUST** address the teacher in second-person feminine singular throughout (2.5d): הציגי, שאלי, רשמי, המתיני, שימי לב; את, לך, לעצמך.
   - Never refer to "המורה" in third person, never write "נבקש", and never use "אתם/לכם/לעצמכם" toward the teacher.
   - What the class does stays in impersonal plural present ("כותבים לבד, 3 דקות").
   - See R7.
9. **MUST** use the warm-colleague voice (2.2b): encouraging and direct, naming in one sentence why a pivotal moment matters ("זה הרגע שהכי קל לדלג עליו — אל תדלגי"). Avoid official phrasing ("יש להקדיש", "מומלץ להמתין") and telegraph style. The length limit is set in R8.
10. **MUST** write each step as guidelines plus key phrasings (2.1b):
    - a numbered list of teacher moves;
    - a `.task` card (מה עושים? + זמן · הרכב · כללים · במליאה) for every task;
    - 2–3 `.say`/`.say.q` lines for the moments that matter (the launch, the key question, the bridge).

    No full script and no bare skeleton.
11. **MUST** refer to and address students in ordinary plural (2.3d): "תלמידים", "כתבו", "מי מוכן לשתף?", "כל אחד מכם". No "תלמידות.ים" or "מוכן/ה", and no forced neutralization or alternating example names. Verbatim source text keeps its original wording (R9).
12. **MUST** keep every student-facing text warm, neutral and short (2.4b). This covers `.board`, `.board.screen`, `.exit` and slides: no emoji, no slang, no solemn or test-like phrasing.
13. **MUST** write in Hebrew only and always call the document "המערך".

### Page layout (המערך)

14. **MUST** follow this order (R10):
    1. hero: `.lesson-unit` · `.lesson-title` · `.lesson-sub` · `.meta`;
    2. `.lesson-card` (3.2b): שאלת השיעור in `.question-big`, ייקחו איתם (2–3 bullets) and צריך להכין;
    3. in sensitive lessons only, the `.safe` "לפני השיעור" box (5.2a);
    4. `h2.sec` "השיעור במבט אחד" + `table.plan` (3.1c);
    5. the detail inside `.wrap.doc`, with one `h2` per step and `<span class="t">0′–5′</span>` (3.1c).

    The page uses `<body class="paper">`.
15. **MUST** build each detail section the same way:
    - Directly under the `h2` comes a `.tags` row with `.pr` + `.beam` (3.3a).
    - The `h2` carries a `.slide-ref` after its time span (6.3a).
    - The body uses the regular components: `.board`/`.board.screen`, `.say`/`.say.q`/`.say.whisper`, `.task`, `.ladder`, `.tip`, `.exit`.
    - Leave out the `.flow`/`.step` rail, `.why` boxes, in-step `.safe` notes and `.ctx` lines (R10).
16. **MUST** list every step in `table.plan`: the core steps, the extensions (time cell "+5′"/"+8′", title "אם נשאר זמן: …") and the exit ticket last. The פרקטיקה column holds `.pr` tags only.
17. **MUST NOT** include any of the following (3.2b, 3.3a, 3.4; edge cases in R2):
    - the שפ״י goals/knowledge/skills/values block;
    - a content-background section;
    - a print appendix;
    - a pocket card;
    - a Plan B section;
    - a "מה השתנה לעומת המקור" box;
    - a "מפת חותם".
18. **Template change (MUST).** `theme/lesson.css` line 106 labels `.say.whisper` "לעצמכם"; change it to "לעצמך" to match 2.5d.
19. **Template change (MUST).** Promote the two-track boxes into `theme/lesson.css` as a regular component, because 1.4c makes them standard wherever the source offers a choice. Today they exist only as picker CSS (`.b-ch1x-two` and `.when`, in `options/ch1x-choice.html` lines 10–14).

### Practices

20. **MUST** use only the 11 "חותם על זה" practices, each tagged with the right `.pr[data-f]` family, and only the five spotlight names for `.beam` (BRIEFS.md).
21. **Opening (4.1).** Choose קדימה ללמידה, מה הקשר? or תרגילי שליפה by what the content needs, and vary across lessons. Retrieval is allowed only in its self-sufficient form (R3).
22. **Plenary discussion (4.2).** Use one technique per discussion, chosen by the activity: Think–Pair–Share, מהלכי שיח + זמן חשיבה, or כולם כותבים + סבב (decision guide: R4).
23. **Group work (4.3).** Follow R5.
24. **Brain break (4.4b).** Never schedule one. Around minute 20, add one `.tip` "הפסקת מוח, אם הכיתה עייפה — 3 דקות לפני …" with signs of fatigue, three ready ideas and the step the 3 minutes come out of, preferably an extension (rule 2).
25. **Exit ticket (4.5).** It is non-digital and low-prep (R6):
    - a private note collected at the door (a) when the content is personal or the teacher needs to see who is struggling;
    - a sticky note on the board (c) when a visible class product fits.

    The prompt may simply be written on the board, so nothing needs printing. Never use a QR code or an online form.
26. **Differentiation (4.6a).** Every task (individual, pair or group) gets a `.ladder` (שאלת עזר · שאלת אתגר), and the step tells the teacher to write both in a corner of the board for the whole activity.
27. **Summary messages (4.7a).** Add a "חשוב לזכור" step near the end, before the exit ticket. Project the source's messages and read them aloud verbatim, then ask one think-then-raise-hands question ("איזה משפט מהשלושה הכי נכון בשבילכם היום?"). An optional one-line `.tip` can say what each message is for.

### Content & sensitivity

28. **MUST** reproduce case stories and examples as in the source (5.1a): names, apps and details stay unchanged, with no `.fill` placeholders for the teacher to complete. A text the class needs on paper (a case card, a worksheet) appears inside its step and is listed under צריך להכין (R2).
29. **MUST** open the המערך with the `.safe` "לפני השיעור" box (5.2a) when the lesson touches smoking, alcohol, harm, sexuality or a personal recall of a hard moment. Lessons without such content get no box, and steps never carry `.safe` notes. The box covers:
    - coordinating with the counselor, including asking her to be available afterwards;
    - who may be hurt and how to talk about it;
    - pressing no one to share ("מספרים רק על עצמנו"; passing is allowed; no calling on students who didn't raise a hand);
    - what to do on a disclosure of harm: stop gently, thank, continue privately, update the counselor the same day, and promise no secrecy.
30. **MUST** pair every video with a viewing task (5.3a):
    - a written question or prediction before viewing;
    - what to watch for;
    - a pause point (the exact timestamp, or `.fill` "[דקה:שנייה]" when it can't be verified) with a one-word prediction;
    - Think–Pair–Share afterwards.

    Add the prep line "open it on the classroom computer before the lesson". No offline fallback is written.
31. **MUST** keep public stance activities as the source has them (5.5a): students move in the room, there is "think alone five seconds, without looking at anyone — then move" before each situation, one speaker from each side, and a closing מהלכי שיח question (for sensitive lessons, see R11).

### Slides (visual aid)

32. **MUST** build the visual aid as a reveal.js deck using `theme/slides.css`, plus an automatically generated PDF of the same deck (6.1c). Both are listed under צריך להכין.
33. **MUST** give every slide a large illustration with few words (6.2b). The default layout is `s-pic`: kicker, short headline, at most one short sub-line, and an inline SVG in the rough eli5 style (`#rough` filter, `#kid` figure). The cover may use `s-cover` with its art. The authoring skill therefore draws one illustration per slide.
34. **MUST** keep one idea per slide. Split lists and multi-part instructions across consecutive slides or reveal them as fragments. Every `.board.screen` block in the המערך shows exactly the words of its slide (R12).
35. **MUST** give every step its `.slide-ref` and add an inline `.slide-ref` at each mid-step slide change (6.3a). Slide numbers match the deck, which follows the step order; both tracks of a 1.4c step get their own slides.

## Needs a ruling

The first six items are the "none" picks; the rest are conflicts between picks, or between a pick and the house style or a sample.

**R1 · 1.2 שלד קבוע — "none", no note.**
- *Signals from other picks.* 4.1's note rules out a fixed opening, which excludes 1.2a and the opening half of 1.2b. Two picks assume an exit ticket in every lesson: the chosen 1.3b markup ("על כרטיס היציאה לא מוותרים") and 4.5's note about its form.
- *Recommended.* No fixed skeleton, with one constant: every lesson ends with a non-digital exit ticket inside the core. The opening follows 4.1 and the middle follows the source (1.1b). In effect this is 1.2b's closing without its fixed opening.
- *Why.* It matches every preference the user did express without inventing a routine they didn't ask for.

**R2 · 3.4 מה עוד נכנס — "none" + "כלום, לא צריך שום דבר נוסף".**
- *Issue.* The four listed add-ons are clearly out, but five nearby things need a boundary.
- *Recommended:*
  - (a) The "מה השתנה לעומת המקור" card that all three 1.1 outlines end with stays out of the המערך. The authoring run logs the changes in `docs/runs/` instead.
  - (b) The formal שפ״י goals stay out. 3.2b's note ("המטרות הרשמיות והרקע נדחקים להמשך") implies they come later, but "ייקחו איתם" already carries the goals in student language.
  - (c) The "אחרי השיעור" lists under the 4.5a/4.5c exit tickets shrink to one `.say.whisper` inside the exit-ticket step (what to look for when reading the notes). Nothing carries over into the next lesson (5.4a).
  - (d) In-flow elements chosen on other points stay: 1.3b's extensions and time notes, 4.4b's brain-break tip and 5.2a's top box.
  - (e) Printable material the class needs (case cards, worksheets) appears inside its step, as 5.1a's sample shows, and is listed under צריך להכין. There is no appendix.
- *Why.* "Nothing extra" is the strongest preference in the set, and the in-flow items are explicit picks rather than extra sections.

**R3 · 4.1 note × 5.4a — retrieval openings vs. standalone lessons.**
- *Issue.* The note accepts all three openings, including תרגילי שליפה. But 5.4a requires each lesson to stand alone, and 4.1c's own note warns "מי שהחסירו את השיעור הקודם נשארים מול דף ריק".
- *Recommended.* Allow retrieval when the source itself opens with recall (as סיפור במניפה's "נזכרים" does), and only in a self-sufficient form:
  - a `.say.whisper` summarizing what the previous lesson covered (as in 4.1c, line 79);
  - absentees paired with a classmate.

  Never write a teaser, and never make the opening depend on the previous lesson's exit tickets or products.
- *Why.* It keeps 4.1's variety and 5.1a's fidelity to the source without breaking 5.4a.

**R4 · 4.2 דיון במליאה — "none" + "כל הטכניקות טובות, כל פעילות ומה שמתאים לה".**
- *Issue.* The intent is clear, but the skill needs a repeatable decision rule.
- *Recommended.* Choose by the trade-offs the options themselves state:
  - **Think–Pair–Share** when everyone should process a few short questions. It is slow, so use at most 2–3 questions.
  - **מהלכי שיח + זמן חשיבה** for one continuous discussion where the class responds to itself.
  - **כולם כותבים + סבב** when every voice must be heard, for example when opening a delicate subject.

  Use one technique per discussion, and tag it.
- *Why.* It turns "by fit" into a consistent choice without overriding it.

**R5 · 4.3 עבודה בקבוצות — "none", no note.**
- *Issue.* The point was left unanswered.
- *Recommended.*
  - **Default:** follow the source's own group design. In the anchor lesson, `sources/text/7/HashpahaHevratit1.md` slide 14 says "בקבוצות": each group reads a case card, discusses it, writes a dialogue and presents it in plenary. Which group gets which case is left open.
  - **Otherwise:** choose a/b/c by fit, as the notes on 4.1 and 4.2 do, with the lower-prep option winning ties (4.5's "פחות הכנה").
  - **Jigsaw (b):** only when every student must know every case.
- *Why.* This mirrors the user's other "none" notes and fits their low-prep, source-faithful picks (1.1b, 5.1a).

**R6 · 4.5 כרטיס יציאה — "none" + the non-digital note.**
- *Issue.* Which of a and c to use, and what "אפשר גם פשוט על הלוח, פחות הכנה" changes.
- *Recommended.* "שניהם" means a and c, the two non-digital options.
  - **Default:** the lowest-prep form. Write the prompt on the board and collect answers on any note or half-sheet at the door (a, unprinted).
  - **Use c** (sticky notes on the board) when the answer is an intention or a class product and isn't private.
  - **Markup:** render the prompt as `.board` when it is written on the board and as `.exit` when it is handed out. Never copy the picker-only sticky-note wall (`.b-ch4b-*`).
- *Why.* The note excludes only the digital form and explicitly asks for less prep.

**R7 · 2.5d "בקשי" × the plural house style — how far "את" reaches.**
- *Issue.* 2.5's gloss calls it the grammatical person "שבו כל המערך כתוב", and the 2.5d sample puts every teacher verb in the "את" form. Every other chosen sample is in the house style instead:
  - impersonal present for teacher moves ("מסבירים… בודקים… מסתובבים", 2.1b);
  - plural imperatives ("ספרו לה… שאלו… בקשו", 5.2a; "פתחו… סמנו", 5.3a);
  - "לעצמכם" in the `.say.whisper` label.
- *Recommended:*
  - The teacher's own actions and every address to her take the "את" form: הסבירי, בדקי, הסתובבי, ספרי לה, סמני לעצמך.
  - What the class does stays impersonal plural present ("קמים", "כותבים לבד").
  - Impersonal "אפשר/כדאי/חשוב" stays.
  - `.say` lines (teacher to students) stay plural, per 2.3d.
  - Rename the whisper label (rule 18).
- *Caveat.* If the המערך is ever shared beyond one teacher, revisit 2.5; its own note says "מתאים כשהמערך נכתב למורה מסוימת".
- *Why.* It follows the chosen sample literally and keeps the teacher's role and the class's role easy to tell apart.

**R8 · 2.2b × 2.1b × 3.3a — how much "why" goes into a step.**
- *Issue.* 2.2b's own note says "ארוך יותר, וחלק מהמילים משכנעות במקום להנחות". 2.1b asks for concise guidelines, and 3.3a accepted "לא כתוב למה".
- *Recommended.* Warmth comes from word choice, not length. Use at most one "why" sentence per step, in the step's prose, and only at pivotal moments: reflection, sensitive moments, and steps that are easy to skip or rush. Never use `.why` boxes or card citations.
- *Why.* It keeps all three picks true at once.

**R9 · 2.3d × 4.7a / 5.1a — verbatim source wording.**
- *Issue.* Source messages and cases use forms such as "לכל אחד ואחת יש קצב אישי".
- *Recommended.* 2.3d governs the text the skill writes. Verbatim source text (messages read aloud, case cards, quotations) keeps its original wording.
- *Why.* 4.7a and 5.1a explicitly ask for the source as it is.

**R10 · 3.1c × components shown in `.flow.lite`, and the page order.**
- *Issue.* 3.1c's detail is plain `.doc`: an `h2` + `.t`, with blockquotes and "על הלוח:" paragraphs. Every other chosen sample shows its components inside `.flow.lite` steps:
  - 1.3b marks core and extensions on the rail (`.step-min` with "ליבה" / "+5′");
  - 6.3a puts `.slide-ref` in `.step-head`;
  - 2.1b, 4.4b and 4.6a use `.task`, `.tip` and `.ladder`.
- *Recommended.* Keep 3.1c's skeleton (`h2` + `.t`, no rail) but keep the components instead of downgrading them to blockquotes:
  - `lesson.css` styles them globally, and their labels ("אומרים", "שואלים", "על הלוח", "על המסך") carry meaning.
  - Move the rail markers into the heading: an extension becomes `<h2>אם נשאר זמן: … <span class="t">+5′</span></h2>`, and `.slide-ref` follows the `.t`.
  - Page order as in rule 14, with the `.safe` box after the `.lesson-card` and before the table. 3.2's gloss reserves the first half-minute for understanding the lesson.
- *Why.* It honors the choice of no rail without losing what 2.1b, 2.4b and 4.6a picked.

**R11 · 5.5a × 5.2a — a public stance activity in a sensitive lesson.**
- *Issue.* 5.5's gloss warns that a public choice "מייצרת בדיוק את הלחץ שעליו מדברים", while the 5.2a box promises "לא לוחצים לשתף… אפשר לוותר".
- *Recommended.* Keep the activity as the source has it (the user chose a). When it appears in a sensitive lesson, the top `.safe` box gets one bullet naming it: the stance is about the hypothetical situation, only volunteers explain their side, and mocking anyone's position is stopped at once (the box already says "צחוק על מישהו בכיתה — עוצרים מיד").
- *Why.* It reconciles the two picks without changing the chosen activity.

**R12 · 6.2b × text-heavy screens.**
- *Issue.* 6.2b means few words and an illustration on every slide. But 4.7a projects the source messages verbatim (three full sentences), and several chosen samples put lists on the screen: three reflection questions, or three rounds of a task.
- *Recommended:*
  - One idea per slide: split lists across slides or reveal them as fragments, which matches "שאלו אחת אחת".
  - The messages slide is the one exception allowed for length: each message verbatim, revealed one at a time, under one illustration.
  - The `.task` details stay in the המערך for the teacher, and longer instructions go on the whiteboard (`.board`).
- *Why.* It keeps 6.2b's style without cutting verbatim text.

**R13 · The 1.1b sample outline × later picks.**
- *Issue.* The 1.1b outline (`ch1-direction.html` lines 136–212) folds the summary messages into the המשגה step and ends with the "מה השתנה" card.
- *Recommended.* Treat it as an illustration of editing depth only. Where it differs from a specific point, that point governs: the messages follow 4.7a (a "חשוב לזכור" step before the exit ticket), and the card stays out (R2a).
- *Why.* The 1.1 outlines were built to compare how far to edit, not how to lay out each step.

## Example markup

All files are under `lesson-lab/picker/`. Line numbers are those of the `<section>` tag unless stated otherwise. Before copying any snippet:

- All option markup is written in the house style: plural address to the teacher and `.flow.lite` steps. Convert it to "את" (rule 8, R7) and to the `h2`-per-step detail layout (rule 15, R10).
- Never copy `.ctx` lines ("קטע מתוך: …"); they exist only in the picker.
- Never copy `.b-ch*` classes, which exist only in the picker. The one exception is the two-track box (rule 19). The 0–45 time bar in 1.3 (`.b-time`/`.b-bar`) is a picker illustration; the המערך shows core and extensions in `table.plan`.
- Component class names: `theme/gallery.html`.

| Point | Pick | Copy from (file · `data-pt` / `data-opt`) | What to take / how to adapt |
|---|---|---|---|
| 1.1 | b | `options/ch1-direction.html` · `1.1` / `b` (line 136) | The editing depth: 7 steps, with what was kept, changed and dropped. Do not copy the "מה השתנה לעומת המקור" card (lines 204–210). |
| 1.2 | none | — | Per R1, only the closing pattern of `1.2` / `b` (line 339) applies. |
| 1.3 | b | `options/ch1-direction.html` · `1.3` / `b` (line 500) | The last core step and its "ליבה" marker (line 526), the clock-check whisper (531), the extension steps (534–549) and the "if time is short" whisper (551). Move the rail markers into `h2 .t` (R10). |
| 1.4 | c | `options/ch1x-choice.html` · `1.4` / `c` (line 59) | The two-track boxes with `.when` (line 67; CSS lines 10–14, promoted per rule 19). The step title becomes "בחרי מסלול". |
| 2.1 | b | `options/ch2-voice.html` · `2.1` / `b` (line 44) | The `<ol>` of moves (lines 54–60), the `.task` (61–69) and the 2–3 `.say` (70–72). Convert teacher verbs to "את". |
| 2.2 | b | `options/ch2-voice.html` · `2.2` / `b` (line 125) | Tone reference. Convert plural to feminine singular ("אל תדלגו" → "אל תדלגי", "שאלו… חכו" → "שאלי… חכי"). |
| 2.3 | d | `options/ch2-voice.html` · `2.3` / `d` (line 254) | How students are referred to, in prose and on the board. |
| 2.4 | b | `options/ch2-voice.html` · `2.4` / `b` (line 320) | Wording of `.board`, `.board.screen` and `.exit`. |
| 2.5 | d | `options/ch2x-address.html` · `2.5` / `d` (line 59) | The grammatical person for all teacher-facing prose, `.tip` and `.say.whisper`. |
| 3.1 | c | `options/ch3-plan.html` · `3.1` / `c` (line 88) | `h2.sec` + `table.plan` (lines 91–103) and the detail `h2` + `.t` (105–131). Keep components rather than blockquotes (R10). |
| 3.2 | b | `options/ch3-plan.html` · `3.2` / `b` (line 176) | The hero (lines 178–183) and the `.lesson-card` (185–199). |
| 3.3 | a | `options/ch3-plan.html` · `3.3` / `a` (line 228) | The `.tags` rows (lines 235 and 245). |
| 3.4 | none | — | Nothing to copy. |
| 4.1 | none | `options/ch4a-practices.html` · `4.1` / `a` (11), `b` (36), `c` (66) | All three are valid patterns. For a retrieval opening, 4.1c's recap whisper (line 79) is required (R3). |
| 4.2 | none | `options/ch4a-practices.html` · `4.2` / `a` (95), `b` (119), `c` (145) | All three are valid; choose per R4. |
| 4.3 | none | `options/ch4a-practices.html` · `4.3` / `a` (174), `b` (206), `c` (240) | Choose per R5. |
| 4.4 | b | `options/ch4b-practices.html` · `4.4` / `b` (line 74) | The `.tip` (line 92). Convert "בוחרים… לוקחים" to "בחרי… קחי". |
| 4.5 | none | `options/ch4b-practices.html` · `4.5` / `a` (143) and `c` (192) | The `.exit` (line 152) and the text of the `.board` prompt (201), without the `.b-ch4b-*` wall. Never use `b`. |
| 4.6 | a | `options/ch4b-practices.html` · `4.6` / `a` (line 229) | The `.ladder` (lines 241 and 249) and the "written in a corner of the board" line (242). |
| 4.7 | a | `options/ch4x-messages.html` · `4.7` / `a` (line 6) | The whole "חשוב לזכור" step (lines 13–20). |
| 5.1 | a | `options/ch5-content.html` · `5.1` / `a` (line 24) | The case card as `blockquote` plus its questions (lines 44–55). |
| 5.2 | a | `options/ch5-content.html` · `5.2` / `a` (line 143) | The top `.safe` box (lines 147–155). Convert "ספרו/שאלו/בקשו" to "ספרי/שאלי/בקשי". |
| 5.3 | a | `options/ch5-content.html` · `5.3` / `a` (line 272) | Both steps (lines 276–300). |
| 5.4 | a | `options/ch5-content.html` · `5.4` / `a` (line 376) | The standalone check in the `.tip` (line 404). Use it as a test to apply, not as text to print. |
| 5.5 | a | `options/ch5x-stance.html` · `5.5` / `a` (line 14) | The step (lines 21–29). |
| 6.1 | c | `options/ch6-visual.html` · `6.1` / `c` (line 99) | The deck itself is `demos/reveal-makom.html` with `theme/slides.css` and `demos/deck-init.js`. |
| 6.2 | b | `options/ch6-visual.html` · `6.2` / `b` (line 132); its frames load `demos/slides-pic.html` | `section.s-pic` (slides-pic.html lines 24, 45 and 63) and the SVG defs `#rough` / `#kid` (lines 14–22). |
| 6.3 | a | `options/ch6-visual.html` · `6.3` / `a` (line 153) | `.slide-ref` in the step head (lines 161 and 167) and inline (169). In the המערך, place it after the `h2 .t` (R10). |
