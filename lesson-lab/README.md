# lesson-lab — מעבדת מערכי שיעור

כאן מכיילים סגנון של מערכי שיעור לכישורי חיים (כיתה ז׳), שנבנים מחומרי שפ״י
("הכ״חות שבדרך") לפי עקרונות "המגדלור" ופרקטיקות "חותם על זה". המטרה הסופית:
סקיל שמקבל מצגת בסגנון שפ״י ומוציא מערך שיעור מובנה כדף HTML בסגנון האתר.

התיקייה הזו לא מקושרת מ-`index.html` ולא מוצגת באתר הציבורי, עד שנחליט אחרת.

## מבנה

```
lesson-lab/
├── sources/
│   ├── manifest.json     ← כל שיעורי ו׳–ט׳ באתר שפ״י, עם קישורים
│   ├── index.json        ← אותו דבר + סטטיסטיקות חילוץ
│   ├── raw/              ← המצגות המקוריות (לא בגיט, ~1GB)
│   ├── text/<שכבה>/      ← טקסט השקפים + הערות המנחה, קובץ לכל שיעור
│   └── digests/          ← תקצירי שיעורים (כרטיס לכל שיעור + סיכום אצווה)
├── theme/
│   ├── lesson.css        ← שפת העיצוב של דפי המערך (המשך של gibush.html)
│   ├── lesson.js         ← עיגולי המסילה, אמנות ה-hero, טיימרים
│   └── gallery.html      ← כל הרכיבים עם שמות המחלקות
├── picker/
│   ├── index.html        ← הפיקר: נקודה בכל פעם, 2–4 גרסאות לכל נקודה
│   ├── preview.html      ← מציג גרסה אחת בתוך iframe
│   ├── bundles.json      ← רשימת הפרקים
│   ├── options/*.html    ← הגרסאות: <section data-pt data-opt …>
│   └── picks.json        ← הבחירות שלכם (נכתב על ידי השרת)
└── tools/
    ├── extract_pptx.py   ← מצגות → טקסט
    └── serve.py          ← שרת סטטי + שמירת בחירות
```

## הרצה

```bash
cd lesson-lab
python3 tools/serve.py          # http://localhost:8765/picker/
```

הבחירות נשמרות ל-`picker/picks.json` (ול-localStorage). הבריפים לכל נקודה: `picker/BRIEFS.md`.
דמואים של העזר החזותי (reveal.js): `picker/demos/` — `?thumb=1&slide=N` לתמונה ממוזערת של שקף.

בדיקת קבצי הגרסאות (מאפיינים, HTML, אנגלית, צורות מגדריות, ציטוטים מילוליים מ"חותם על זה"):

```bash
uv run --with beautifulsoup4 python3 tools/lint_options.py
```

## הורדה וחילוץ מחדש

```bash
uv run --with python-pptx python3 tools/extract_pptx.py
```
(ההורדה עצמה: לולאת curl על `sources/manifest.json`; הקבצים נשמרים ב-`sources/raw/<שכבה>/`.)
