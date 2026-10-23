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
    שריקה), so each letter has one where it can (for ג: גְּלִידָה);
  - example words of its own (`moe-acq`): בית, בלון, בובה, among others.

  ב's ten default words are the exception: they were chosen by hand, and its cluster words (בְּרֵיכָה,
  בְּרוֹקוֹלִי) are among its other words.
- **משרד החינוך: איגרת המפמ"ר, הוראת השפה העברית בכיתה א, תשפ"ו**
  (<https://meyda.education.gov.il/files/Pop/0files/ivrit_hinuch_leshoni/Yesodi/horaa.pdf>): example words
  (`moe-horaa`), such as בננה.
- **משרד החינוך, האגף לחינוך קדם יסודי: טעימות בעברית**
  (<https://meyda.education.gov.il/files/PreSchool/teimot-be-ivrit.pdf>): its activities, songs and "מילים
  מהלב" basic-word lists for kindergarten (`moe-teimot`), such as בית and בובה.
- **The words of מילים באנגלית** ([`../english-words/`](../english-words/CREDITS.md)), picked from the
  Ministry's English curriculum word lists (Pre-Band I, Band I) and Cambridge's Young Learners list, with
  their Hebrew and niqqud (`en-roster`).

A word's Ministry sources say where it appears, as an example or as a plain mention of the thing. Every
word was checked against the full text of the three documents: a source is listed when the word appears in
it as a whole word, alone, in the plural or after one prefix letter (ה ו ב ל מ ש כ), and in its own sense.
Another word with the same letters (מצב is not צב, כלב is not לב), another sense (לשון as language) or a
name doesn't count.

The niqqud follows the english-words game: full spelling with vowels (כתיב מלא מנוקד), as in בּוּבָּה.

## Drawings

Most drawings are **OpenMoji** emoji, from its black line set, version 17.0.0
(<https://openmoji.org/>, <https://github.com/hfg-gmuend/openmoji>): "All emojis designed by OpenMoji –
the open-source emoji and icon project. License: CC BY-SA 4.0"
(<https://creativecommons.org/licenses/by-sa/4.0/>). Changes: the shapes are flattened into one group,
every line is drawn in one printed weight, and the drawings are scaled, turned and placed on the page. The
changed drawings in [`art/`](art/) are shared under the same license, CC BY-SA 4.0.

### Own drawings

For 25 words OpenMoji has no drawing that reads as the word in black lines alone, so we drew them, in
OpenMoji's line style: 72×72, lines of 2 with round caps and joins, no fills but small eye dots. They are in
[`art-src/`](art-src/) and are shared under the same license, CC BY-SA 4.0.

| File | Word | Why not OpenMoji |
|---|---|---|
| `bet-doll.svg` | בּוּבָּה | its dolls are a nesting doll (1FA86), a בַּבּוּשְׁקָה, and two Japanese festival dolls (1F38E) |
| `bet-faucet.svg` | בֶּרֶז | its only tap is the potable-water sign (1F6B0), which prints inside a square frame |
| `bet-pool.svg` | בְּרֵיכָה | OpenMoji has no swimming pool |
| `bet-screw.svg` | בּוֹרֶג | a plain screw reads better than its nut and bolt (1F529) |
| `bet-acorn.svg` | בַּלּוּט | OpenMoji has no acorn |
| `bet-biscuit.svg` | בִּיסְקְווִיט | its cookie (1F36A) is round with chocolate chips and reads as עוּגִייָּה |
| `dalet-scarecrow.svg` | דַּחְלִיל | OpenMoji has no scarecrow |
| `he-steering-wheel.svg` | הֶגֶה | OpenMoji has only a car wheel (1F6DE) |
| `vav-curtain.svg` | וִילוֹן | OpenMoji has no curtain; its window (1FA9F) has none |
| `vav-hook.svg` | וָו | its hook (1FA9D) is a fishing hook, a קֶרֶס |
| `vav-vest.svg` | וֶסְט | its safety vest (1F9BA) reads as two panels in black lines |
| `vav-vase.svg` | וָאזָה | OpenMoji has no vase; its amphora (1F3FA) reads as a כַּד |
| `zayin-olives.svg` | זֵיתִים | its olive (1FAD2) is a bare oval that reads as an egg |
| `zayin-chameleon.svg` | זִיקִּית | OpenMoji has no chameleon; its lizard (1F98E) is a לְטָאָה |
| `zayin-fireworks.svg` | זִיקּוּקִים | its fireworks and sparkler (1F386, 1F387) have a solid stick and read as a wand |
| `tet-ring.svg` | טַבַּעַת | its ring (1F48D) is a one-line circle with a tiny stone, with nothing to color |
| `tet-marker.svg` | טוּשׁ | OpenMoji has no marker; its crayon and pen read as צֶבַע and עֵט |
| `tet-television.svg` | טֶלֶווִיזְיָה | its television (1F4FA) reads as a computer monitor |
| `yod-dove.svg` | יוֹנָה | its dove (1F54A) alone reads as a צִיפּוֹר; the olive branch makes it a dove |
| `lamed-lizard.svg` | לְטָאָה | its lizard (1F98E) is a thin sliver that could pass for a crocodile |
| `lamed-whale.svg` | לִווְייָתָן | its spouting whale (1F433) is less clear in print and is drawn as filled shapes, not lines; its whale (1F40B) doesn't read |
| `mem-king.svg` | מֶלֶךְ | OpenMoji has no king; its person with a crown and prince (1FAC5, 1F934) read as a princess and a prince |
| `nun-swing.svg` | נַדְנֵדָה | OpenMoji has no swing |
| `tsadi-submarine.svg` | צוֹלֶלֶת | OpenMoji has no submarine |
| `shin-table.svg` | שׁוּלְחָן | OpenMoji has no table |

Each printed page says "Drawings: OpenMoji, CC BY-SA 4.0", or "Drawings: OpenMoji and own, CC BY-SA 4.0"
when one of these is on it.

## Fonts

- **Fredoka**: Copyright 2016 The Fredoka Project Authors (<https://github.com/hafontia/Fredoka-One>). SIL
  Open Font License 1.1; see [`fonts/OFL-Fredoka.txt`](fonts/OFL-Fredoka.txt). Its Hebrew subset is inlined
  in the page; the big letters are its Bold outlines.
- The controls use **Assistant** and **Secular One** from Google Fonts, as the rest of the site does.
