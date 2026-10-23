# Credits

דפי צביעה: אותיות ומילים are printable A4 coloring pages: a big hollow Hebrew letter, and around it line
drawings of words that start with it.

## Words

Each letter's words are in [`src/words.json`](src/words.json), each with the sources it appears in. The
Israeli Ministry of Education publishes no list of words per letter, so the words follow its 2026
curriculum's rules for teaching a letter, and are taken from its documents where they give examples:

- **משרד החינוך, המזכירות הפדגוגית, אגף שפות: תוכנית הלימודים להוראת השפה והאוריינות בגן ובכיתות א–ב,
  רכישת הקריאה והכתיבה** (2026), by Prof. Amalia Bar-On, Prof. Michal Shany, Prof. Dorit Aram, Dr. Shani
  Levy-Shimon and Dr. Limor Kolan
  (<https://meyda.education.gov.il/files/Pop/0files/ivrit_hinuch_leshoni/Yesodi/acquisition-reading-writing.pdf>).
  Its rules, which the word lists keep:
  - a letter is learned "also through exposure to different words (shown in pictures) that start with the
    same consonant but with different vowels" (its example: שעון, שמש, שיר, שולחן), so each letter's
    default words start with as many different vowels as it has good words for;
  - finding the first consonant is easiest in words that open with a cluster (its examples: גלידה, כביש,
    שריקה), so each letter has one where it can (for ב: בְּרוֹקוֹלִי);
  - example words of its own (`moe-acq`): בית, בלון, בובה, among others.
- **משרד החינוך: איגרת המפמ"ר, הוראת השפה העברית בכיתה א, תשפ"ו**
  (<https://meyda.education.gov.il/files/Pop/0files/ivrit_hinuch_leshoni/Yesodi/horaa.pdf>): example words
  (`moe-horaa`), such as בננה.
- **משרד החינוך, האגף לחינוך קדם יסודי: טעימות בעברית**
  (<https://meyda.education.gov.il/files/PreSchool/teimot-be-ivrit.pdf>): its "מילים מהלב" basic-word lists
  for kindergarten (`moe-teimot`), such as בית and בובה.
- **The words of מילים באנגלית** ([`../english-words/`](../english-words/CREDITS.md)), picked from the
  Ministry's English curriculum word lists (Pre-Band I, Band I) and Cambridge's Young Learners list, with
  their Hebrew and niqqud (`en-roster`).

The niqqud follows the english-words game: full spelling with vowels (כתיב מלא מנוקד), as in בּוּבָּה.

## Drawings

Every drawing is an **OpenMoji** emoji, from its black line set, version 17.0.0
(<https://openmoji.org/>, <https://github.com/hfg-gmuend/openmoji>): "All emojis designed by OpenMoji –
the open-source emoji and icon project. License: CC BY-SA 4.0"
(<https://creativecommons.org/licenses/by-sa/4.0/>). Changes: the shapes are flattened into one group,
every line is drawn in one printed weight, and the drawings are scaled, turned and placed on the page. The
changed drawings in [`art/`](art/) are shared under the same license, CC BY-SA 4.0. Each printed page says
"Drawings: OpenMoji, CC BY-SA 4.0".

## Fonts

- **Fredoka**: Copyright 2016 The Fredoka Project Authors (<https://github.com/hafontia/Fredoka-One>). SIL
  Open Font License 1.1; see [`fonts/OFL-Fredoka.txt`](fonts/OFL-Fredoka.txt). Its Hebrew subset is inlined
  in the page; the big letters are its Bold outlines.
- The controls use **Assistant** and **Secular One** from Google Fonts, as the rest of the site does.
