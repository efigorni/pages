# בדיקת סרטונים — כל השיעורים

בדיקה לקריאה בלבד, 2026-10-04 00:08. לא שיניתי אף שיעור. שיעורי ט׳ עוד נכתבים — ראו בסוף טבלת ט׳ מה לא נבדק.

**איך נבדק (בלי דפדפן):**
- **יוטיוב:** oEmbed — 200 חי, 401 הטמעה חסומה, 404 ירד. בנוסף, עמוד הצפייה: `playabilityStatus`, `playableInEmbed`, `lengthSeconds`. לסרטונים החדשים של ט׳ שעמוד הצפייה לא החזיר להם נתונים, האורך והזמינות נלקחו מ־yt-dlp.
- **קישורים אחרים:** GET עם הפניות, ובדיקה שאין דף הרשמה. mako ושירונט חוסמים בקשות של סקריפט (דף Radware), ולכן נבדקו ב־curl עם כותרות של דפדפן.
- **אורך אמיתי:**
  - Drive — yt-dlp.
  - קובץ ה־mp4 של מט״ח והסרטון שמוטמע ב־pptx — ffprobe.
  - mako — שדה `duration` בדף.
- **השוואה למקור:** קישורי הווידאו ב־`src_text` של כל שיעור מול הקישורים בשיעור. כך אומתו כל הסרטונים שירדו (D53). כל שאר הסרטונים שבמקור ולא נכנסו לשיעור — חיים.

## בקצרה
- **64 בלוקי `video`** ב־47 שיעורים. 58 סרטונים שונים, ועוד 1 קישור מדיה בטקסט (מילות שיר בשירונט).
- **קישורים מתים:** 0.
- **הטמעה חסומה:** 1 — `g6-sheela-tshuva`. ביוטיוב עצמו הסרטון נצפה, והשיעור מקשר לעמוד הצפייה, כך שאין מה לתקן.
- **אורך:** 0 אי־התאמות מתוך 56 אורכים מוצהרים. ב־8 בלוקים אין `length`, אף שהאורך ידוע עכשיו.
- **קטעים:** 0 מתוך 9 יוצאים מאורך הסרטון. עצירות עם זמן מפורש: 0 מחוץ לטווח.
- **עצירות ״?״ (לא אומתו):** 59 מתוך 65 עצירות, ב־44 שיעורים.
- **D53:** 7 שיעורים שסרטון המקור שלהם ירד (5 בו׳, 2 בז׳). כולם עדיין מתים. ב־`g6-lizmoach-sikum` רשימת ההשמעה עצמה חיה — ראו למטה.
- **לתקן:** 6 בלוקים שבהם הקטע כתוב רק בכותרת, בקישור (`t=`) או בטקסט. המערך שנבנה מהם כותב ״ממשיכים עד הסוף.״, בניגוד לטקסט (ו׳: 2, ז׳: 4). **כדאי לתקן:** 5 (ו׳: 2, ז׳: 1, ט׳: 2). **לבדוק:** 1 בט׳, בשיעור שעוד בכתיבה.

## מה לתקן

### כיתה ו׳ — 2 לתקן, 2 כדאי
1. **`g6-lomdim-leyazeg`:**
   - בשלב `guy` להוסיף `clip: {end: "1:21"}`. עכשיו המערך כותב ״ממשיכים עד הסוף.״, והטקסט אומר שהחלק נגמר ב־1:21.
   - בשלב `guy2` להחליף את `&t=82s` ב־`clip: {start: "1:22"}`.
   - בשניהם להוסיף `length: "6:06"` (אומת: 366 שניות).
2. **`g6-model-patarti`** (שלב `maor`): להוסיף `clip: {end: "5:24"}` ו־`length: "13:28"` (ffprobe). עכשיו המערך כותב ״ממשיכים עד הסוף.״ על סרט של 13 דקות. אפשר להשאיר את `#t=0,324` בקישור.
3. *כדאי:* **`g6-megalim-achrayut-1`:** כפתור ״לסרטון״ מוריד את המצגת המקורית כולה (121MB). הסרטון מוטמע בשקף 11 ואורכו 26:32, והקטע עד 8:08 תקין. כדאי להוסיף `length: "26:32"` ושורת הכנה: ״להוריד את המצגת לפני השיעור״. אפשר גם לחכות להצעה של pkg-g8-03 — `source_slide` לסרטון שמוטמע רק במצגת.
4. *כדאי:* **`g6-mekorot-haosher`** (שלב `song`): להוסיף `length: "3:24"`.

### כיתה ז׳ — 4 לתקן, 1 כדאי
1. **`g7-golshim-leshinuy`** (שלב `open`, מסלול ״משפחה בהסעה״): להחליף את `&t=85s` ב־`clip: {start: "1:25", end: "2:10"}` ולהוסיף `length: "27:31"`. עכשיו המערך כותב ״ממשיכים עד הסוף.״ על פרק של 27 דקות.
2. **`g7-sulam-mishpachti`** (שלב `movie`): להחליף את `&t=12s` ב־`clip: {start: "0:12", end: "0:40"}`. עכשיו כתוב ״ממשיכים עד הסוף.״, והטקסט אומר לעצור ב־0:40.
3. **`g7-mitchapsim-veshomrim-al-azmenu`** (שלב `laugh`): להוסיף `clip: {end: "1:20"}` ו־`length: "4:06"`.
4. **`g7-mudaut-migdarit`** (הרחבה `shelly`):
   - להוסיף `clip: {start: "3:29"}` ו־`length: "23:46"`. עכשיו הקישור נפתח בתחילת הפרק.
   - את סוף הקטע צריך לקבוע בצפייה, וכשייקבע — להוסיף גם `end`.
5. *כדאי:* **`g7-hitbagrut-banot`** (שלב `body`): להוריד מהקישור את `&list=…&index=10`. בלעדיהם הסרטון לא נפתח בתוך רשימת השמעה, ויוטיוב לא עובר לבד לסרטון הבא.

### כיתה ח׳ — אין
כל הקישורים חיים, וכל האורכים והקטעים תואמים. נשארו רק עצירות ״?״.

### כיתה ט׳ — 0 לתקן, 2 כדאי, 1 לבדוק (מתוך השיעורים שכבר נכתבו)
1. *כדאי:* **`g9-eich-lesaper-5`** (שלב `video`): להחליף את `/shorts/q7b48xccsvw` ב־`https://www.youtube.com/watch?v=q7b48xccsvw`. נגן ה־Shorts חוזר בלולאה ואין בו פס זמן רגיל, והסכמה מצפה לקישור `watch` או `youtu.be`.
2. *כדאי:* **`g9-ani-meshatef-ani-kayam`** (בכתיבה): הקישור ל״מאסטר יוטיוב״ מפנה לכתובת חדשה, `mako.co.il/mako-vod-keshet/eretz_nehederet-s-16/shorts/Video-91c6afab48c0961006.htm`, וכדאי לעדכן אליה. בשני הקישורים של mako יש פרסומת לפני הסרטון.
3. *לבדוק:* **`g9-bead-azmi-masa-ishi-yofi`** (בכתיבה): ב־`before` של הסרטון כתוב ״להיכנס היום? באיזו דלת תבחרו״. זה הסדר של טקסט המקור (שקף 27), כנראה שארית חילוץ. על השקף ״לפני שצופים״ צריך לכתוב ״באיזו דלת תבחרו להיכנס היום?״ (D23).
- ב־11 שיעורי ט׳ שעוד לא היה להם `lesson.yaml` ב־00:02 בדקתי מראש את קישורי המדיה שבמקור: 22 קישורים, כולם חיים. לא צפוי שם D53.

### עצירות ״?״ — לאמת בצפייה
לפי הסכמה, `at: "?"` הוא ערך מותר: המורה מסמנת את הזמן לפני השיעור. אפשר לקבוע את הזמנים מראש בצפייה, ובסרטון שיש לו כתוביות ביוטיוב — מהכתוביות, כמו שנעשה ב־`g8-haverut-veachrayut`. בטבלאות למטה הסרטונים האלה מסומנים ״יש כתוביות״. השיעורים, לפי שכבה:
- **ו׳ (10):** `g6-empathy-bamasachim`, `g6-hitmodedut-hachlatot`, `g6-lokchim-laderech`, `g6-lomdim-leyazeg`, `g6-megalim-achrayut-1`, `g6-mekorot-haosher`, `g6-model-patarti`, `g6-sheela-tshuva`, `g6-signonot-hachlatot`, `g6-sium-shana`.
- **ז׳ (17):** `g7-alkohol-4`, `g7-gizanut-ani-veacher-4`, `g7-gizanut-siyum-5`, `g7-gizanut-streotipim-2`, `g7-golshim-leshinuy`, `g7-hashpaha-hevratit-1`, `g7-hitbagrut-banim`, `g7-hitbagrut-banot`, `g7-lemida-sheli-1`, `g7-miniyut-vepratiyut-bareshet-4`, `g7-mitchapsim-veshomrim-al-azmenu`, `g7-mudaut-migdarit`, `g7-omdim-lezad-6`, `g7-shana-tova`, `g7-sulam-mishpachti`, `g7-tabak-vemuzarav-3`, `g7-yom-zikaron`.
- **ח׳ (6):** `g8-alkohol-vemitbagrim-2`, `g8-haverut-veachrayut`, `g8-mashmaut-erech`, `g8-miniyut-hizur-8`, `g8-pituy-pogesh-gvul`, `g8-sigaria-he-sigaria`.
- **ט׳ (11):** `g9-akartis-amatin-sheli-6`, `g9-ani-meshatef-ani-kayam`, `g9-bead-azmi-masa-ishi-yofi`, `g9-eich-lesaper-5`, `g9-empathy-masachim-1`, `g9-leachnis-et-atov-1`, `g9-mashabey-hitmodedut-sheli-2`, `g9-osher-1`, `g9-osher-2`, `g9-samim-kabalat-hachlatot`, `g9-samim-lishmor`.

## D53 — סרטוני מקור שירדו (לתיעוד)
בדקתי מחדש את כל שבעת הקישורים. כולם עדיין לא זמינים, ובאף שיעור לא הוכנס סרטון אחר במקומם.

| שיעור | הסרטון במקור | הקישור | בדיקה חוזרת | מה נעשה בשיעור | יומן |
|---|---|---|---|---|---|
| `g6-nihul-zman` | ״לה פמיליה״ | YouTube `62vMA6doHPg` | oEmbed 404 | נבנה בלי הסרטון ובלי שאלות הצפייה של שקף 10; הפתיחה משאלת הבחירה של המקור | `docs/runs/pkg-g6-02.md` |
| `g6-haoganim` | ״מוצאים את נמו״ (Amara) | `amara.org/en/videos/ifhQ0wBq6mPU/…` | מפנה לדף הרשמה | הרעיון נלמד בשלב ״מה עזר לכם?״ משאלות המקור | `docs/runs/pkg-g6-07.md` |
| `g6-lizmoach-pticha` | ״ברוכים הבאים לגיל ההתבגרות״ | Drive `1FD-2G8hx73mJBxviqp3E2qpHdXLtdj4D` | 404 | שאלת הקיר נוסחה מחדש בלי הסרטון | `docs/runs/pkg-g6-04.md` |
| `g6-lizmoach-sikum` | ״קריוקי ישראלי״ (רשימת השמעה) | YouTube `FGgrz5YyATA` + `list=PL5MV8_qxHC5…` | הסרטון: oEmbed 404. **רשימת ההשמעה עצמה חיה** (oEmbed 200, כ־317 סרטונים) | הפך להרחבה: פזמון למנגינה מוכרת | `docs/runs/pkg-g6-05.md` |
| `g6-yom-zikaron` | השיר ״קופסת צבעים״ | YouTube `Gi45Y8nDJyU` | oEmbed 404 | המורה מקריאה את המילים (שירונט, דרך שקף 13 של המקור) | `docs/runs/pkg-g6-12.md` |
| `g7-etgarim-balemida-3` | ״מה זה בעצם ׳דפוס חשיבה מתפתח׳?״ | YouTube `g0k8wIhPSBg` | oEmbed 404 | המושג נלמד משקף 11 של המקור | `docs/runs/pkg-g7-04.md` |
| `g7-mitchapsim-veshomrim-al-azmenu` | ״אלכוהול על המאזניים״ | Drive `1rFjSaHZitjJ38CBWYK9sKPwnHlZlsOGm` | 404 | הפעילות נשענת על נימוקי הכיתה; השלב קוצר מ־10′ ל־8′ | `docs/runs/pkg-g7-11.md` |

- **`g6-lizmoach-sikum`:** הקישור במקור היה `watch?v=FGgrz5YyATA&list=…`. הסרטון הראשון ירד, אבל רשימת ההשמעה ״קריוקי ישראלי״ (`playlist?list=PL5MV8_qxHC5ufNt9OV-lyMTm_WU-xUFWV`) חיה. אם רוצים להחזיר את הקריוקי, הקישור לרשימה עצמה עובד. בשיעור הוא לא בלוק צפייה (D25) אלא משאב לפעילות. ההחלטה — של הרועה.
- **`g6-model-patarti`** הוא לא D53. הנגן בעמוד מט״ח שבור, אבל הקובץ עצמו חי, והשיעור מקשר אליו.

## טבלאות לפי שכבה
- **מצב:** ✓ חי · ⚠ הטמעה חסומה · ✗ מת.
- **אורך:** ״—״ — אין `length` בשיעור.
- **עצירות ״?״:** כמה מהעצירות לא אומתו. ״יש כתוביות״ — אפשר לקבוע את הזמן מהכתוביות.
- **★** ליד שיעור בלי סרטון — סרטון המקור ירד (D53).

### כיתה ו׳ — 41 שיעורים, 13 עם סרטון, 15 בלוקי `video`

| שיעור · שלב | קישור | מצב | אורך: מוצהר / אמיתי | קטע (`clip`) | עצירות ״?״ | הערה |
|---|---|---|---|---|---|---|
| `g6-empathy-bamasachim` · empathy | [`fMHEXXyCn2c`](https://www.youtube.com/watch?v=fMHEXXyCn2c) | ✓ חי | 2:29 / 2:29 ✓ | — | 1 מתוך 1 |  |
| `g6-hitmodedut-hachlatot` · video | [`_HEnohs6yYw`](https://www.youtube.com/watch?v=_HEnohs6yYw) | ✓ חי | 3:27 / 3:27 ✓ | עד 1:31 ✓ | 1 מתוך 1 |  |
| `g6-lizmoach-kolhalev` · video | [`rCV0pxlsEPA`](https://www.youtube.com/watch?v=rCV0pxlsEPA) | ✓ חי | 1:37 / 1:37 ✓ | — | 0 מתוך 1 (0:30 ✓) |  |
| `g6-lizmoach-lachaz-hevrati` · video · מסלול ״לחץ חברתי לא מנצח אותי״ | [`3Xq9UcDIyJk`](https://www.youtube.com/watch?v=3Xq9UcDIyJk) | ✓ חי | 1:16 / 1:16 ✓ | — | 0 מתוך 1 (0:35 ✓) |  |
| `g6-lizmoach-lachaz-hevrati` · video · מסלול ״המרושתים מדברים״ | [`kHaWPmDnvkw`](https://www.youtube.com/watch?v=kHaWPmDnvkw) | ✓ חי | 5:01 / 5:01 ✓ | 0:30–2:09 ✓ | 0 מתוך 1 (1:10 ✓) |  |
| `g6-lizmoach-streotypim` · video | [Drive](https://drive.google.com/file/d/1TrgtCJ6yjL_CFeoy1xSzOwoc7iECkXw3/view) | ✓ חי | 3:08 / 3:08 ✓ | — | 0 מתוך 2 (1:49, 2:25 ✓) | Drive ציבורי (stereotipim v4.mp4) |
| `g6-lokchim-laderech` · film | [`y47-gmGvZhI`](https://www.youtube.com/watch?v=y47-gmGvZhI) | ✓ חי | 4:24 / 4:24 ✓ | — | 1 מתוך 1 |  |
| `g6-lomdim-leyazeg` · guy | [`mo9M-gMTQeA`](https://www.youtube.com/watch?v=mo9M-gMTQeA) | ✓ חי | — / 6:06 | — | 1 מתוך 1 | הקטע (עד 1:21) רק בכותרת ובטקסט, בלי `clip` — המערך כותב ״ממשיכים עד הסוף.״ |
| `g6-lomdim-leyazeg` · guy2 | [`mo9M-gMTQeA`](https://www.youtube.com/watch?v=mo9M-gMTQeA&t=82s) (+t) | ✓ חי | — / 6:06 | — | 1 מתוך 1 | `&t=82s` בקישור במקום `clip.start` |
| `g6-megalim-achrayut-1` · video | [pptx · המצגת המקורית](https://meyda.education.gov.il/files/shefi/kishurey_chayim/Hakochot_Shebaderech/6Grade/Mamlachti/Megalim_Achrayut_1.pptx) | ✓ חי | — / 26:32 | עד 8:08 ✓ | 1 מתוך 1 | הקישור מוריד את המצגת המקורית כולה (121MB); הסרטון מוטמע בשקף 11 |
| `g6-mekorot-haosher` · song | [`ane7Sqv8RVQ`](https://www.youtube.com/watch?v=ane7Sqv8RVQ) | ✓ חי | — / 3:24 | — | 1 מתוך 1 · יש כתוביות | גם קישור המילים בשירונט (`prep`) חי |
| `g6-model-patarti` · maor | [mp4 · כותר](https://video.kotar.co.il/VideoContent/convertedflv/beinzilzulim/aniohevotah.mp4#t=0,324) | ✓ חי | — / 13:28 | — | 1 מתוך 1 | קובץ mp4 ישיר של מט״ח (כותר), עם `#t=0,324`; הקטע (עד 5:24) בלי `clip` — המערך כותב ״ממשיכים עד הסוף.״ |
| `g6-sheela-tshuva` · alice | [`pt9ND-wZ4W0`](https://www.youtube.com/watch?v=pt9ND-wZ4W0) | ⚠ הטמעה חסומה (oEmbed 401) | 1:37 / 1:37 ✓ | — | 1 מתוך 1 | ההטמעה חסומה; ביוטיוב עצמו הסרטון נצפה רגיל, והקישור הוא לעמוד הצפייה |
| `g6-signonot-hachlatot` · bear | [`IXNyOdMCBww`](https://www.youtube.com/watch?v=IXNyOdMCBww) | ✓ חי | 1:32 / 1:32 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g6-sium-shana` · climb | [`YYb4h8U7Ljw`](https://youtu.be/YYb4h8U7Ljw) | ✓ חי | 2:09 / 2:09 ✓ | — | 1 מתוך 1 · יש כתוביות |  |

**בלי קישור לסרטון (28):** `g6-adam-zover`, `g6-beikvot-ziurav`, `g6-hakoach-laavor`, `g6-hameroz-memitzraim`, `g6-haoganim` ★, `g6-hayozer-shel`, `g6-hitbagrut-vani`, `g6-kita-echpatit-medura-echpatit`, `g6-lizmoach-ani`, `g6-lizmoach-banim-banot`, `g6-lizmoach-hoze`, `g6-lizmoach-meida`, `g6-lizmoach-pticha` ★, `g6-lizmoach-sikum` ★, `g6-maavarim-bareshet`, `g6-mahu-osher`, `g6-marbim-besimcha`, `g6-mezahim-kishurim`, `g6-model-hachlatot`, `g6-nihul-zman` ★, `g6-orzim-vemitkadmim`, `g6-ptichat-shana-tashpaz`, `g6-reshet-haverim`, `g6-siyum-shana`, `g6-tiru-oty`, `g6-yaad-chalom`, `g6-yarid-simanim-lashana-achadasha`, `g6-yom-zikaron` ★.

### כיתה ז׳ — 35 שיעורים, 17 עם סרטון, 24 בלוקי `video`

| שיעור · שלב | קישור | מצב | אורך: מוצהר / אמיתי | קטע (`clip`) | עצירות ״?״ | הערה |
|---|---|---|---|---|---|---|
| `g7-alkohol-4` · video | [`DiNOUgm72e0`](https://www.youtube.com/watch?v=DiNOUgm72e0) | ✓ חי | 1:50 / 1:50 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g7-gizanut-ani-veacher-4` · video | [`XU4EM15Q2uo`](https://youtu.be/XU4EM15Q2uo) | ✓ חי | 1:00 / 1:00 ✓ | — | 1 מתוך 1 |  |
| `g7-gizanut-siyum-5` · song · הרחבה | [`ow8_GYK-Ksc`](https://www.youtube.com/watch?v=ow8_GYK-Ksc) | ✓ חי | 3:35 / 3:35 ✓ | — | 1 מתוך 1 · יש כתוביות | אותו שיר גם ב־g7-gizanut-streotipim-2 (אותה יחידה) |
| `g7-gizanut-streotipim-2` · song · הרחבה | [`ow8_GYK-Ksc`](https://www.youtube.com/watch?v=ow8_GYK-Ksc) | ✓ חי | 3:35 / 3:35 ✓ | — | 1 מתוך 1 · יש כתוביות | אותו שיר גם ב־g7-gizanut-siyum-5 (אותה יחידה) |
| `g7-golshim-leshinuy` · open · מסלול ״משפחה בהסעה״ | [`zIKwV5iVVio`](https://www.youtube.com/watch?v=zIKwV5iVVio&t=85s) (+t) | ✓ חי | — / 27:31 | — | 1 מתוך 1 | `&t=85s` בקישור; הקטע 1:25–2:10 רק בטקסט — המערך כותב ״ממשיכים עד הסוף.״ על פרק של 27 דקות |
| `g7-hashpaha-hevratit-1` · asch | [`l_YMx1cZX0A`](https://www.youtube.com/watch?v=l_YMx1cZX0A) | ✓ חי | 2:16 / 2:16 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g7-hitbagrut-banim` · body | [`EQ4YUZlJPVI`](https://www.youtube.com/watch?v=EQ4YUZlJPVI) | ✓ חי | 2:58 / 2:58 ✓ | — | 1 מתוך 1 |  |
| `g7-hitbagrut-banim` · feelings | [`rCV0pxlsEPA`](https://youtu.be/rCV0pxlsEPA) | ✓ חי | 1:37 / 1:37 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g7-hitbagrut-banim` · clip · הרחבה | [`5bMVXsX4Xuc`](https://youtu.be/5bMVXsX4Xuc) | ✓ חי | 1:25 / 1:25 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g7-hitbagrut-banot` · body | [`aCwd83TClUE`](https://www.youtube.com/watch?v=aCwd83TClUE&list=PLvOBUEO1Dk21XPCkXBDErH0ndO9pczsX4&index=10) (+index,list) | ✓ חי | 2:58 / 2:58 ✓ | — | 1 מתוך 1 | `&list=…&index=10` בקישור — נפתח בתוך רשימת השמעה |
| `g7-hitbagrut-banot` · period | [`FABAUJH_gqU`](https://youtu.be/FABAUJH_gqU) | ✓ חי | 1:46 / 1:46 ✓ | — | 1 מתוך 1 |  |
| `g7-hitbagrut-banot` · feelings | [`rCV0pxlsEPA`](https://youtu.be/rCV0pxlsEPA) | ✓ חי | 1:37 / 1:37 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g7-hitbagrut-banot` · clip · הרחבה | [`5bMVXsX4Xuc`](https://youtu.be/5bMVXsX4Xuc) | ✓ חי | 1:25 / 1:25 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g7-lemida-sheli-1` · race | [`YaVDJ_8PgcU`](https://www.youtube.com/watch?v=YaVDJ_8PgcU) | ✓ חי | 3:15 / 3:15 ✓ | — | 1 מתוך 1 |  |
| `g7-miniyut-vepratiyut-bareshet-4` · ai | [`DJziuYIXGL4`](https://www.youtube.com/watch?v=DJziuYIXGL4) | ✓ חי | 1:52 / 1:52 ✓ | — | 1 מתוך 1 |  |
| `g7-mitchapsim-veshomrim-al-azmenu` · laugh | [`p32OC97aNqc`](https://www.youtube.com/watch?v=p32OC97aNqc) | ✓ חי | — / 4:06 | — | 1 מתוך 1 | הקטע (עד 1:20) רק בכותרת ובטקסט — המערך כותב ״ממשיכים עד הסוף.״ |
| `g7-mudaut-migdarit` · shelly · הרחבה | [`_GWV9sDZuq0`](https://www.youtube.com/watch?v=_GWV9sDZuq0) | ✓ חי | — / 23:46 | — | 1 מתוך 1 · יש כתוביות | פרק של 23:46; ״מדקה 3:29״ רק בטקסט — הקישור נפתח ב־0:00 |
| `g7-omdim-lezad-6` · video | [`WnYNOV6pJWo`](https://www.youtube.com/watch?v=WnYNOV6pJWo) | ✓ חי | 1:08 / 1:08 ✓ | — | 1 מתוך 1 |  |
| `g7-omdim-lezad-6` · mmm | [`xk-hmxdBcqM`](https://www.youtube.com/watch?v=xk-hmxdBcqM) | ✓ חי | 1:38 / 1:38 ✓ | — | 1 מתוך 1 |  |
| `g7-shana-tova` · song · הרחבה | [`zACyHq8pY4s`](https://www.youtube.com/watch?v=zACyHq8pY4s) | ✓ חי | 3:42 / 3:42 ✓ | — | 1 מתוך 1 |  |
| `g7-sulam-mishpachti` · movie | [`cMfDJVvrW64`](https://www.youtube.com/watch?v=cMfDJVvrW64&t=12s) (+t) | ✓ חי | 1:23 / 1:23 ✓ | — | 1 מתוך 1 | `&t=12s` בקישור; הקטע 0:12–0:40 רק בטקסט — המערך כותב ״ממשיכים עד הסוף.״ |
| `g7-tabak-vemuzarav-3` · rabbit · הרחבה | [`TVPDqiDmgUQ`](https://www.youtube.com/watch?v=TVPDqiDmgUQ) | ✓ חי | 0:55 / 0:55 ✓ | — | 1 מתוך 1 |  |
| `g7-yom-zikaron` · story | [`TGMY6a_JzCQ`](https://www.youtube.com/watch?v=TGMY6a_JzCQ) | ✓ חי | 4:35 / 4:35 ✓ | — | 1 מתוך 1 |  |
| `g7-yom-zikaron` · hareut · הרחבה | [`XSRBg7OUDig`](https://youtu.be/XSRBg7OUDig) | ✓ חי | 3:54 / 3:54 ✓ | — | 1 מתוך 1 |  |

**בלי קישור לסרטון (18):** `g7-bead-azmi-aharacha-azmit`, `g7-eifo-ani-vehagvul-sheli-bamasachim`, `g7-etgarim-balemida-3` ★, `g7-gizanut-1`, `g7-gizanut-rov-vemiut-3`, `g7-hatchalot-1`, `g7-hatchalot-3`, `g7-hatchalot-hoze-2`, `g7-ktav-hida-4`, `g7-makom-baolam`, `g7-matchilim-leashen-2`, `g7-mesibat-sium`, `g7-mishpacha-hefez-lev`, `g7-ptichat-shana-1`, `g7-ptichat-shana-2`, `g7-sipur-bemenifa`, `g7-tamrurim-lemida-2`, `g7-tofsim-kivun-bareshet`.

### כיתה ח׳ — 13 שיעורים, 6 עם סרטון, 9 בלוקי `video`

| שיעור · שלב | קישור | מצב | אורך: מוצהר / אמיתי | קטע (`clip`) | עצירות ״?״ | הערה |
|---|---|---|---|---|---|---|
| `g8-alkohol-vemitbagrim-2` · egg · מסלול ״צופים בניסוי״ | [`fs2drTBbaNA`](https://youtu.be/fs2drTBbaNA) | ✓ חי | 1:52 / 1:52 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g8-haverut-veachrayut` · song | [`RT39VXfx80o`](https://www.youtube.com/watch?v=RT39VXfx80o) | ✓ חי | 4:17 / 4:17 ✓ | עד 1:28 ✓ | 0 מתוך 1 (1:28 ✓) | העצירה ב־1:28 היא סוף הקטע (נקבעה מהכתוביות) |
| `g8-haverut-veachrayut` · video | [`aFm4H1FkkwA`](https://www.youtube.com/watch?v=aFm4H1FkkwA) | ✓ חי | 4:44 / 4:44 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g8-mashmaut-erech` · video | [`u2euIog2I-I`](https://www.youtube.com/watch?v=u2euIog2I-I) | ✓ חי | 3:00 / 3:00 ✓ | מ־0:04 ✓ | 1 מתוך 1 · יש כתוביות |  |
| `g8-miniyut-hizur-8` · tools | [`s9oBDNjZlo0`](https://www.youtube.com/watch?v=s9oBDNjZlo0) | ✓ חי | 1:30 / 1:30 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g8-miniyut-hizur-8` · howto · הרחבה | [`eUsc513iFOA`](https://www.youtube.com/watch?v=eUsc513iFOA) | ✓ חי | 1:36 / 1:36 ✓ | — | 1 מתוך 1 |  |
| `g8-pituy-pogesh-gvul` · limits | [`6n1safVOdG4`](https://www.youtube.com/watch?v=6n1safVOdG4) | ✓ חי | 0:54 / 0:54 ✓ | — | 1 מתוך 1 |  |
| `g8-sigaria-he-sigaria` · video | [`JcZHbsXQnE4`](https://www.youtube.com/watch?v=JcZHbsXQnE4) | ✓ חי | 2:38 / 2:38 ✓ | — | 1 מתוך 1 |  |
| `g8-sigaria-he-sigaria` · rabbit | [`TVPDqiDmgUQ`](https://www.youtube.com/watch?v=TVPDqiDmgUQ) | ✓ חי | 0:55 / 0:55 ✓ | — | 1 מתוך 1 |  |

**בלי קישור לסרטון (7):** `g8-ani-vealkohol-1`, `g8-karov-rachok-reshet`, `g8-lachshov-tov-4-zeadim-2`, `g8-lachshov-tov-pil-veyated-1`, `g8-lachshov-tov-tirgul-model-3`, `g8-mashmaut-dvarim-hashuvim`, `g8-yachad`.

### כיתה ט׳ — 18 שיעורים (מתוך 27 במלאי), 11 עם סרטון, 16 בלוקי `video`

| שיעור · שלב | קישור | מצב | אורך: מוצהר / אמיתי | קטע (`clip`) | עצירות ״?״ | הערה |
|---|---|---|---|---|---|---|
| `g9-akartis-amatin-sheli-6` · video | [`w249hGEFhzs`](https://www.youtube.com/watch?v=w249hGEFhzs) | ✓ חי | 1:24 / 1:24 ✓ | — | 1 מתוך 1 |  |
| `g9-ani-meshatef-ani-kayam` · open · מסלול ״מאסטר יוטיוב״ | [mako](https://www.mako.co.il/tv-erez-nehederet/770e3d99ade16110?subChannelId=6ed41312207e8610VgnVCM2000002a0c10acRCRD&vcmid=91c6afab48c09610VgnVCM2000002a0c10acRCRD) | ✓ חי | 5:46 / 5:46 ✓ | — | 1 מתוך 1 | דף mako, מפנה לכתובת חדשה ב־mako-vod-keshet; פרסומת לפני הסרטון |
| `g9-ani-meshatef-ani-kayam` · open · מסלול ״החוויה או התמונה״ | [mako](https://www.mako.co.il/news-channel2/Channel-2-Newscast-q1_2019/Article-ea704db73c2e861004.htm) | ✓ חי | 46:35 / 46:35 ✓ | 34:00–42:35 ✓ | 1 מתוך 1 | מהדורת חדשות מלאה ב־mako; הקטע 34:00–42:35 (8:35) — הקישור לא קופץ לבד, והמערך אומר לקדם |
| `g9-ani-meshatef-ani-kayam` · polished | [`0EFHbruKEmw`](https://www.youtube.com/watch?v=0EFHbruKEmw) | ✓ חי | 3:12 / 3:12 ✓ | — | 1 מתוך 1 |  |
| `g9-bead-azmi-masa-ishi-yofi` · doors · הרחבה | [`rdiTP1zx_Ow`](https://www.youtube.com/watch?v=rdiTP1zx_Ow) | ✓ חי | 2:36 / 2:36 ✓ | — | 1 מתוך 1 |  |
| `g9-eich-lesaper-5` · video | [`q7b48xccsvw`](https://www.youtube.com/shorts/q7b48xccsvw) (shorts) | ✓ חי | 0:48 / 0:48 ✓ | — | 1 מתוך 1 | קישור Shorts (`/shorts/`) |
| `g9-eich-lesaper-5` · video-end · הרחבה | [`kRtiI3I1-6s`](https://youtu.be/kRtiI3I1-6s) | ✓ חי | 3:09 / 3:09 ✓ | מ־0:08 ✓ | 1 מתוך 1 |  |
| `g9-empathy-masachim-1` · empathy | [`BdEqtV8UZ7o`](https://www.youtube.com/watch?v=BdEqtV8UZ7o) | ✓ חי | 2:49 / 2:49 ✓ | — | 1 מתוך 1 |  |
| `g9-leachnis-et-atov-1` · video · הרחבה | [`rd3xW7KX06s`](https://youtu.be/rd3xW7KX06s) | ✓ חי | 1:49 / 1:49 ✓ | — | 1 מתוך 1 |  |
| `g9-mashabey-hitmodedut-sheli-2` · rafiki | [`AUkgMs8vPVE`](https://www.youtube.com/watch?v=AUkgMs8vPVE) | ✓ חי | 3:38 / 3:38 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g9-mashabey-hitmodedut-sheli-2` · nala · הרחבה | [`2EPQkq_8YIk`](https://www.youtube.com/watch?v=2EPQkq_8YIk) | ✓ חי | 4:02 / 4:02 ✓ | — | 1 מתוך 1 |  |
| `g9-osher-1` · song | [`NIi29Qeqlis`](https://www.youtube.com/watch?v=NIi29Qeqlis) | ✓ חי | 3:17 / 3:17 ✓ | — | 1 מתוך 1 · יש כתוביות |  |
| `g9-osher-2` · song · הרחבה | [`7YIUyrtRBOo`](https://www.youtube.com/watch?v=7YIUyrtRBOo) | ✓ חי | 4:20 / 4:20 ✓ | — | 1 מתוך 1 |  |
| `g9-samim-kabalat-hachlatot` · gorilla | [`vJG698U2Mvo`](https://www.youtube.com/watch?v=vJG698U2Mvo) | ✓ חי | 1:22 / 1:22 ✓ | מ־0:05 ✓ | 1 מתוך 1 |  |
| `g9-samim-kabalat-hachlatot` · blind · הרחבה | [`ckR4A069pf0`](https://www.youtube.com/watch?v=ckR4A069pf0) | ✓ חי | 2:33 / 2:33 ✓ | — | 1 מתוך 1 |  |
| `g9-samim-lishmor` · video | [`fwQZlGJo0cI`](https://www.youtube.com/watch?v=fwQZlGJo0cI) | ✓ חי | 3:09 / 3:09 ✓ | עד 1:56 ✓ | 1 מתוך 1 |  |

**בלי קישור לסרטון (7):** `g9-glida`, `g9-hide-park-shel-tovanot-7`, `g9-rega-lifney-shematchilim`, `g9-samim-ksamim`, `g9-samim-lama-ken-lama-lo`, `g9-shaar-laavar`, `g9-shaar-lahove`.

**לא נבדקו — עוד בכתיבה (6, אין `lesson.yaml` ב־00:08):** `g9-delet-makom-batuach`, `g9-samim-sipur-derech`, `g9-shaar-laatid`, `g9-sium-shana`, `g9-tfisa-migdarit-bemeziut-mekuvenet`, `g9-trufot-mirsham`. **טרם התחילו (3):** `g9-miniyut-7`, `g9-mabat-al-haskama`, `g9-netya-minit`.

## הערות
- **אותו סרטון בכמה שיעורים:**
  - ״ויקיפדיה — חנן בן ארי״ (`ow8_GYK-Ksc`) — הרחבה ב־`g7-gizanut-streotipim-2` וגם ב־`g7-gizanut-siyum-5`. שני השיעורים באותה יחידה, ולכן כיתה שעושה את היחידה תראה אותו פעמיים.
  - ״המתבגרים — שינויים״ (`rCV0pxlsEPA`) — ב־`g6-lizmoach-kolhalev` וגם ב־`g7-hitbagrut-banim`/`banot`.
  - הארנב של האגודה למלחמה בסרטן (`TVPDqiDmgUQ`) — ב־`g7-tabak-vemuzarav-3` וגם ב־`g8-sigaria-he-sigaria`.
- **סרטוני מקור שלא נכנסו לשיעור** — כולם חיים, ולכן זו לא השמטה לפי D53:
  - `g7-mudaut-migdarit` — הרצאת TED, `_203dmzJBsQ`.
  - `g7-omdim-lezad-6` — `RsoRXuIBVqs`.
  - `g9-akartis-amatin-sheli-6` — `HeJEZpF2u1I`.
  - `g9-eich-lesaper-5` — `LPy0rKdr6hk`.
  - `g9-hide-park-shel-tovanot-7` — `WJ7JZsDhL90`.
  - `g9-mashabey-hitmodedut-sheli-2` — ״אקונה מטטה״, `vSH8t5H4pJI`.
- **בשיעורים שעוד בכתיבה** יש לחזור על הבדיקה כשהם ייגמרו. הסקריפטים של הבדיקה הזו נמצאים רק בתיקיית ה־scratch של הסשן. skill-fixes #13 מציע להכניס בדיקה כזו ל־`validate.py`.
