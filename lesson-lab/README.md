# lesson-lab — מערכי שיעור לכישורי חיים

כל שיעורי "הכ״חות שבדרך" (שפ״י) לכיתות ו׳–ט׳, בעריכה מחדש לפי הפרקטיקות של "חותם על זה" והזרקורים של "המגדלור". לכל שיעור יש **המערך** — מסמך HTML שאפשר להעביר ממנו את השיעור — ו**מצגת** (reveal.js) שמלווה אותו, עם גיבוי PDF.

- **116 שיעורים** — ו׳ 41 · ז׳ 35 · ח׳ 13 · ט׳ 27, בסך הכול 1,855 שקפים. 18 שיעורים לא הופקו; הרשימה ב-`docs/inventory.md`, בסעיף "פערים".
- **דף המרכז** — `lessons/index.html`: כרטיס לכל שיעור, עם סינון לפי כיתה, חודש ויחידה, וחיפוש. בכל כרטיס קישורים למערך, למצגת ול-PDF. הדף מקושר מהפורטל (`index.html` בשורש הריפו).
- **הסקיל** — `.claude/skills/lighthouse-lesson-lab/`. לכל שיעור כותבים `lesson.yaml` אחד, והבנייה מפיקה ממנו את המערך, את המצגת ואת ה-PDF. המתכון, הפקודות והטעויות הנפוצות — ב-`SKILL.md`.
- **ההחלטות המחייבות** — `docs/decisions.md`: דרישות המשתמשים (R) והפסיקות (D). כל מי שבונה, כותב או בודק שיעור פועל לפיהן; החלטה חדשה נוספת בסוף הקובץ, עם תאריך.

## מבנה

```
lesson-lab/
├── lessons/
│   ├── index.html          ← דף המרכז (נבנה ב-build_all.py)
│   ├── _assets/            ← css, js, ערכת האיורים ו-reveal.js — עותק של assets/ מהסקיל
│   └── <slug>/             ← למשל g7-makom-baolam
│       ├── lesson.yaml     ← מקור האמת: הקובץ היחיד שכותבים ביד (ואיורים ב-art/)
│       ├── index.html      ← המערך (נבנה)
│       ├── slides.html     ← המצגת (נבנית)
│       └── slides.pdf      ← גיבוי המצגת (נוצר מקומית, לא בגיט)
├── docs/
│   ├── decisions.md        ← ההחלטות המחייבות
│   ├── lessons.json        ← רשומה לכל שיעור: מקור, יחידה, רגישות ודגלים
│   ├── inventory.md        ← המלאי והפערים
│   ├── helplines.md        ← מרשם קווי העזרה המאומתים (D75)
│   ├── final-report.md     ← דוח האיחוד הסופי
│   └── runs/ · qa/         ← יומני ההפקה ודוחות הבקרה
├── sources/                ← מצגות המקור: manifest, טקסט ותקצירים (raw/ — לא בגיט, ~1GB)
├── theme/ · picker/        ← שלב הכיול: שפת העיצוב הראשונה, והפיקר שבו נבחר הסגנון
└── tools/                  ← חילוץ טקסט מהמצגות, שרת מקומי ובדיקת גרסאות הפיקר
```

## בנייה

מתיקיית הריפו. את `index.html` ו-`slides.html` של שיעור לא עורכים ביד — הבנייה כותבת אותם מחדש מ-`lesson.yaml`.

```bash
# שיעור אחד: בנייה + בדיקה
uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/build.py lesson-lab/lessons/<slug>

# כל השיעורים + דף המרכז
uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/build_all.py
```

צילום ובדיקה חזותית (`shoot.py`) ושאר הפקודות — בטבלה ב-`SKILL.md`. לצפייה מקומית פותחים את `lesson-lab/lessons/index.html` בדפדפן.

## יצירת קובצי PDF

קובצי `slides.pdf` **לא נמצאים בגיט** (D81): יחד הם כ־129MB, וכל ייצוא מחדש היה מוסיף עוד 129MB להיסטוריה. `lesson-lab/.gitignore` מתעלם מהם, ומייצרים אותם מקומית.

צריך `uv` ו-Google Chrome מותקן: Playwright מדפיס דרכו את המצגת, עמוד לכל שקף. אין Chrome? מריצים פעם אחת `uv run --with playwright playwright install chromium`, ומוסיפים `--bundled` לפקודה.

מתיקיית הריפו:

```bash
# כל המצגות. נוצר רק PDF שחסר או ישן מהמצגת; --force מייצר את כולם מחדש
uv run --with playwright python3 .claude/skills/lighthouse-lesson-lab/scripts/export_pdf.py lesson-lab/lessons/g*/

# שיעור אחד
uv run --with playwright python3 .claude/skills/lighthouse-lesson-lab/scripts/export_pdf.py lesson-lab/lessons/<slug>

# הכול מחדש: המערכים, המצגות, דף המרכז וה-PDF (--force-pdf: כל ה-PDF מחדש)
uv run --with pyyaml --with jinja2 python3 .claude/skills/lighthouse-lesson-lab/scripts/build_all.py --pdf
```

לכל שיעור מודפסת שורה כמו `✓ g7-makom-baolam: slides.pdf — 15 עמודים / 15 שקפים`. ✗ — מספר העמודים שונה ממספר השקפים.

דף המרכז מקשר ל-`slides.pdf` של כל שיעור. כל עוד ה-PDF מחוץ לגיט, הקישורים האלה עובדים רק בעותק מקומי, לא באתר.

### אריזה ב-zip

```bash
(cd lesson-lab/lessons && zip -q ~/Downloads/lesson-pdfs.zip g*/slides.pdf)         # כל 116 הקבצים, ~114MB
(cd lesson-lab/lessons && zip -q ~/Downloads/lesson-pdfs-g7.zip g7-*/slides.pdf)    # שכבה אחת: g6 / g7 / g8 / g9
```

לכל הקבצים אותו שם, ולכן ב-zip כל קובץ נשמר בתיקייה של השיעור שלו (`g7-makom-baolam/slides.pdf`). את ה-zip שומרים מחוץ לריפו.

## שלב הכיול (היסטוריה)

הסגנון נבחר בפיקר: נקודה בכל פעם, 2–4 גרסאות לכל נקודה. הבחירות נשמרו ב-`picker/picks.json`, והתקציר שלהן ב-`docs/picks-summary.md`.

```bash
python3 lesson-lab/tools/serve.py                                       # http://localhost:8765/picker/
uv run --with beautifulsoup4 python3 lesson-lab/tools/lint_options.py   # בדיקת קבצי הגרסאות
uv run --with python-pptx python3 lesson-lab/tools/extract_pptx.py      # מצגות המקור ← טקסט
```

ההורדה עצמה: לולאת curl על `sources/manifest.json`; הקבצים נשמרים ב-`sources/raw/<שכבה>/`.
