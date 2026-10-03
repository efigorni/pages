---
name: lighthouse-lesson-lab
description: Lesson plans from the Ministry of Education life-skills decks ("הכ״חות שבדרך", שפ״י, grades 6–9) — write a lesson.yaml that re-edits a source lesson around the חותם "חותם על זה" practices and the "המגדלור" spotlights, then build it into המערך (HTML lesson plan) and a reveal.js deck with a PDF backup; also validating, rebuilding or exporting lessons under lesson-lab/lessons. מערך שיעור מתוך מצגת שפ״י · בנייה, בדיקה וייצוא של שיעורי lesson-lab.
---

# lighthouse-lesson-lab — מערך שיעור ממצגת שפ״י

הסקיל הופך שיעור "הכ״חות שבדרך" למערך שיעור חדש בעברית: עריכה מחדש של המקור, מבוססת על 11 הפרקטיקות של "חותם על זה" ו-5 הזרקורים של "המגדלור". לכל שיעור כותבים **קובץ אחד** — `lesson-lab/lessons/<slug>/lesson.yaml` — והבנייה מפיקה ממנו את **המערך** (`index.html`, מסמך שאפשר להעביר ממנו שיעור), את **המצגת** (`slides.html`, reveal.js) ואת **הגיבוי** (`slides.pdf`). הטבלה, הזמנים, מספור השקפים וההפניות אליהם — נגזרים מהקובץ, לא נכתבים ביד.

## כללי ברזל

1. **רק `lesson.yaml`** (ואיורים ייעודיים ב-`art/` של השיעור). את `index.html` ו-`slides.html` כותבת רק הבנייה; תיקון שם יימחק בבנייה הבאה.
2. **כותבים רק בתיקיות השיעורים שלך** וביומן החבילה (`lesson-lab/docs/runs/<חבילה>.md`). לא נוגעים ב-`_assets/`, בדף המרכז (`lessons/index.html`), בסקיל או בשיעורים של חבילות אחרות (D34).
3. **אין git** — הרועה עושה commit (D2). **אין דפדפן** — לא Chrome DevTools ולא PDF; הבדיקה החזותית וה-PDF נעשים בגל הבקרה (D36).
4. עקרונות חותם והמגדלור — **רק** מתוך `references/hotam-al-ze.md` ו-`references/migdalor.md` (תעתיק מילולי), לא מהזיכרון ולא מספרי Teach Like a Champion.
5. המסמך נקרא **"המערך"**. המילה הישנה אסורה בכל מקום, גם בהערות.

## המתכון — לכל שיעור בחבילה

1. **קוראים.** פעם אחת לחבילה: `references/style-guide.md`, `references/schema.md`, `assets/art/art-guide.md`. לכל שיעור: טקסט המקור (`src_text`), כרטיס התקציר שלו (`digest_ref` ב-`lesson-lab/docs/lessons.json`) ושורת המלאי שלו. *גמור כש*אפשר למנות את הפעילויות המרכזיות של המקור, את המסרים שלו (מילה במילה) ואת רמת הרגישות.
2. **מתכננים את הקשת** (לפני שכותבים YAML): מה נשאר, מה מתקצר, מה יוצא; סדר השלבים; דקות לכל שלב (ליבה 35′ בדיוק, הרחבות עד 10′); פרקטיקת הפתיחה; טכניקת הדיון לכל דיון; צורת כרטיס היציאה; שקף אחד או יותר לכל שלב והאיור שלו. *גמור כש*סכום הליבה 35 ויש 6–7 שלבי ליבה.
3. **כותבים** את `lesson.yaml` לפי `schema.md` (מטא־דאטה מועתקת מ-`lessons.json`).
4. **בונים** — הבנייה מריצה גם את הבדיקה:
   ```bash
   uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/build.py lesson-lab/lessons/<slug>
   ```
   מתקנים כל ✗ ומריצים שוב. כל ! (אזהרה) — מתקנים, או רושמים ביומן החבילה למה היא נשארת. *גמור כש*השורה האחרונה היא `✓ <slug>: 0 שגיאות`.
5. **עוברים על `references/checklist.md`** מול הטקסט של `index.html` שנבנה. *גמור כש*כל שורה מסומנת.
6. **רושמים ביומן החבילה**: לכל שיעור — מה נשאר, מה השתנה, מה יצא (ולמה), ואילו אזהרות נשארו.

## פקודות

כולן מתיקיית הריפו (`/Users/adamer/dev/efigorni-pages`):

| מה | פקודה |
|---|---|
| בנייה + בדיקה של שיעור | `uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/build.py lesson-lab/lessons/<slug>` |
| בדיקה בלבד | `… scripts/validate.py lesson-lab/lessons/<slug>` (אותן תלויות) |
| PDF (גל הבקרה) | `uv run --with playwright python3 .claude/skills/lighthouse-lesson-lab/scripts/export_pdf.py lesson-lab/lessons/<slug>` |
| כל השיעורים + דף המרכז (גל הבקרה) | `uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/build_all.py --pdf` |

## טעויות נפוצות

| טעות | תיקון |
|---|---|
| YAML נשבר על "מה הקשר?" או על שאלה בתוך `[ … ]` | טקסט עברי רק בסגנון בלוק — רשימה בשורות, `- ערך` |
| הליבה יוצאת 37′ | הליבה = תוכן + "חשוב לזכור" + כרטיס יציאה = 35′; ההרחבות מחוץ לה |
| "שימו לב", "הציגו", "נבקש", "המורה תשאל" | "שימי לב", "הציגי", "שאלי" — פונים למורה ב"את" |
| "כל אחד.ת", "מוכן/ה" בטקסט שכתבת | רבים רגיל: "כל אחד", "מוכן" (ציטוט מילולי מהמקור — נשאר) |
| `.board.screen` שנכתב ביד | `echo: true` על השקף — המסך והמערך תמיד אותן מילים |
| כותבים "שקף 4" בטקסט | ההפניות נגזרות; למעבר באמצע שלב — `slide` עם `cue` |
| שקף עם שלוש שאלות ופסקה | שקף לכל רעיון, או `points` שנחשפות אחת־אחת |
| מסר "משופר" | המסרים מילה במילה מהמקור; הבדיקה משווה ל-`src_text` |
| סמל שלא קיים בערכה | שמות הסמלים ב-`assets/art/art-guide.md` / `gallery.html`; המאמת מציע שמות קרובים |
| סמל מתוח, ענק או צמוד לקצה | `art-guide.md` §קומפוזיציה: מוקד עד 390, פי 0.6–1.6 מהגודל הטבעי, שוליים 16 |
| תיבת "לפני השיעור" כללית | ארבעה סעיפים שמדברים על השיעור הזה (מדריך הסגנון, סעיף 12) |

## הפניות

- `references/style-guide.md` — כל כללי הכתיבה (D8–D30 והכללים המשולבים), עם דוגמאות.
- `references/schema.md` — שדות `lesson.yaml`, הבלוקים, האיורים, ומה נגזר לבד.
- `references/checklist.md` — בדיקה עצמית לפני סיום.
- `references/hotam-al-ze.md` · `references/migdalor.md` — הכרטיסיות, מילה במילה.
- `assets/art/` — ערכת האיורים (`kit.svg`), הקטלוג (`art-guide.md`) והתצוגה (`gallery.html`).
- דוגמה מלאה: `lesson-lab/lessons/g7-makom-baolam/lesson.yaml`.
