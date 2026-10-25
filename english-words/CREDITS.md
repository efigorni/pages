# Credits

מילים באנגלית is a private family game for learning English words, from grade 1 to grade 12.

## Words

The 966 words, their school grade (א׳ to י״ב), their order and their Hebrew come from the formal English
lists below (where they were made is in `tools/README.md`). 634 of the words are on a Ministry of
Education list; of the other 332, 234 are on Cambridge's and 98 only on the CEFR-levelled lists (CEFR-J
92, Oxford 6).

- **Israel Ministry of Education, Inspectorate for English Language Education**:
  - *English Curriculum 2020* (<https://meyda.education.gov.il/files/Mazkirut_Pedagogit/English/Curriculum2020.pdf>):
    its Table 2 gives each lexical band's grades (Pre-Band I grade 3; Band I Core I grade 4 to mid 5;
    Core II mid 5 to the end of 6; Band II Core I grade 7 to mid 8; Band II Core II mid 8 to 9; Band III
    grades 10 to 12), and its Table 1 their CEFR levels.
  - *Lexical Pre-Band I & Band I, Elementary School*
    (<https://meyda.education.gov.il/files/Mazkirut_Pedagogit/English/CurriculumFilesAugust21/LexicalBand1.xlsx>).
  - *Lexical Band II, Junior High*
    (<https://meyda.education.gov.il/files/Mazkirut_Pedagogit/English/CurriculumFilesAugust21/LexicalBand2.xlsx>).
  - *Lexical Band III, High School*
    (<https://meyda.education.gov.il/files/Mazkirut_Pedagogit/English/CurriculumFilesAugust21/LexicalBand3.pdf>).
- **Cambridge University Press & Assessment**:
  - *Pre A1 Starters, A1 Movers and A2 Flyers Wordlists* (2025)
    (<https://www.cambridgeenglish.org/Images/739104-starters-movers-flyers-word-list-2025.pdf>).
  - *A2 Key and A2 Key for Schools Vocabulary List* (August 2025)
    (<https://www.cambridgeenglish.org/images/506886-a2-key-2020-vocabulary-list.pdf>), A2, the level the
    curriculum's Table 1 gives Band II Core I.
  - *B1 Preliminary and B1 Preliminary for Schools Vocabulary List* (August 2025)
    (<https://www.cambridgeenglish.org/images/506887-b1-preliminary-vocabulary-list.pdf>), B1, Band III's
    level.
- **Oxford University Press**: *The Oxford 3000 and The Oxford 5000 by CEFR level*, American and British
  editions (<https://www.oxfordlearnersdictionaries.com/external/pdf/wordlists/oxford-3000-5000/American_Oxford_3000_by_CEFR_level.pdf>,
  <https://www.oxfordlearnersdictionaries.com/external/pdf/wordlists/oxford-3000-5000/American_Oxford_5000_by_CEFR_level.pdf>,
  and the `The_Oxford_3000_by_CEFR_level.pdf` and `The_Oxford_5000_by_CEFR_level.pdf` beside them).
- **CEFR-J Wordlist Version 1.6** (『CEFR-J Wordlist Version 1.6』 東京外国語大学投野由紀夫研究室, Tono Laboratory,
  Tokyo University of Foreign Studies; <https://www.cefr-j.org/data/CEFRJ_wordlist_ver1.6.zip>, downloaded
  October 2026).

A CEFR level gives the grade the curriculum's Table 1 matches it with: Pre-A1 grade 3, A1 grade 5, A2
grade 7, B1 grade 10, B2 and above grade 12.

A word's grade is the **lowest grade any of these sources gives it**: its Ministry band's grades (split
by its Cambridge young learners' level; Band II Core II grade 8, Band III grade 10), Starters grade 3,
Movers grade 5, Flyers grade 6, A2 Key grade 7, B1 Preliminary grade 10, and the CEFR levels above.
The Ministry has no word list for grades 1–2, where English starts with the *Enjoy English* programme
(<https://pop.education.gov.il/kindergarten/topics/english/teaching-materials/enrichment/>). A Starters word
in one of the programme's themes (colours, numbers, animals, family, the body, clothes, food, feelings,
transport, weather, actions) is grade 2, and grade 1 when it is also in the grades 1–2 word bank of
*English Playbox* (<https://english-playbox.netlify.app/>, linked from the programme's site) or on Pre-Band
I. A few early words no list places that low sit with their theme's siblings. No word is placed above
the grade a source gives it, and no source gives grades 9 or 11 a word of their own (the picker joins
them to the grade before).

Only the words and their levels are used; the Hebrew, the niqqud and the teaching order are our own.

## Pictures

Each picture's source is listed per word in [`club/pictures.json`](club/pictures.json) (`source`, `ref`),
which `build_page.py data` writes from the word list: 496 Fluent Emoji, 469 original drawings and 1
ARASAAC pictogram. A picture is admitted only when someone who is not
told the word names it from the card alone.

### Fluent Emoji (`fluent`)

496 pictures in [`img/`](img/) are **Fluent Emoji** by Microsoft in its 3D style
(<https://github.com/microsoft/fluentui-emoji>, commit `1ffb34c752ecf5d402f04cfb4b392c77f57c54bc`); `ref`
is the emoji's name. People and body parts use the default (yellow) skin tone. Changes: trimmed to the
drawing's edges, centred, resized to 200×200 px and converted to WebP with a transparent background. They
are used under the MIT License:

> MIT License
>
> Copyright (c) Microsoft Corporation.
>
> Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
> associated documentation files (the "Software"), to deal in the Software without restriction,
> including without limitation the rights to use, copy, modify, merge, publish, distribute,
> sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all copies or
> substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
> NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
> NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
> DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT
> OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

### Original drawings made for this game (`svg`)

Where no emoji shows a word exactly (469 words), the picture is an original drawing made for this game in the same
rounded, softly shaded style, drawn as SVG and rendered to the same 200×200 px WebP; `ref` is the drawing's
file. These drawings are licensed under the Creative Commons Attribution 4.0 International license, CC BY
4.0 (<https://creativecommons.org/licenses/by/4.0/>): credit "מילים באנגלית, efigorni/pages".

### ARASAAC pictograms (`arasaac`)

Where neither fits, the picture is an ARASAAC colour pictogram; `ref` is its ARASAAC id
(<https://arasaac.org/pictograms/en/{ref}>). One word: **student**
([`img/student.webp`](img/student.webp)), pictogram 5900 (<https://arasaac.org/pictograms/en/5900>). Resized to 200×200 px and converted to WebP. As ARASAAC asks:

> The pictographic symbols used are the property of the Government of Aragón and have been created by
> Sergio Palao for ARASAAC (http://www.arasaac.org), that distribute them under Creative Commons License
> BY-NC-SA.

Pictograms author: Sergio Palao. Origin: ARASAAC (http://www.arasaac.org). License: CC BY-NC-SA 4.0
(<https://creativecommons.org/licenses/by-nc-sa/4.0/>). Owner: Government of Aragón (Spain). This game is
free and non-commercial; the pictograms in it, as changed, are shared under the same license.

## Design

The card back, the speech bubble, the icons and the start screen are our own drawings. The "Aa" on
the icon is Andika Bold's outline.

## Fonts

- **Andika**: Copyright (c) 2004-2022 SIL International (<http://www.sil.org/>). SIL Open Font
  License 1.1; see [`fonts/OFL-Andika.txt`](fonts/OFL-Andika.txt).
- **Fredoka**: Copyright 2016 The Fredoka Project Authors (<https://github.com/hafontia/Fredoka-One>).
  SIL Open Font License 1.1; see [`fonts/OFL-Fredoka.txt`](fonts/OFL-Fredoka.txt).

## Voice

English: Kokoro-82M (Apache-2.0), voice `am_michael`. Hebrew: BlueTTS (MIT) with LibriTTS-R speaker 1088
(CC BY 4.0).

- **English words** ([`audio/en/`](audio/en/)): synthesized locally with **Kokoro-82M**
  (<https://huggingface.co/hexgrad/Kokoro-82M>, Apache License 2.0), voice **`am_michael`** (American
  English, male), part of the same Apache-2.0 release. The model ran as ONNX through **kokoro-onnx**
  (<https://github.com/thewh1teagle/kokoro-onnx>, MIT License) with its v1.0 model files
  (`kokoro-v1.0.onnx`, `voices-v1.0.bin`). Pronunciations come from the US lexicon of **misaki**
  (<https://github.com/hexgrad/misaki>, Apache License 2.0), the G2P Kokoro was trained with, and
  **eSpeak NG** (GPL-3.0, used as a build-time tool only) for words the lexicon lacks. The clips are new
  synthetic speech; no code or data of these projects ships with the game.
- **Hebrew words** ([`audio/he/`](audio/he/)) and the start and win lines ([`audio/ui/`](audio/ui/)):
  synthesized locally with **BlueTTS 2.5** (<https://github.com/maxmelichov/BlueTTS>, MIT License).
- The `noa` voice is speaker 1088 of the **LibriTTS-R** corpus
  (<https://www.openslr.org/141/>), licensed under CC BY 4.0
  (<https://creativecommons.org/licenses/by/4.0/>). The clips are new synthetic
  speech in that speaker's voice; no audio from the corpus is included here.
- LibriTTS-R asks that its paper be cited: Yuma Koizumi, Heiga Zen, Shigeki Karita,
  Yifan Ding, Kohei Yatabe, Nobuyuki Morioka, Michiel Bacchiani, Yu Zhang, Wei Han,
  and Ankur Bapna, "LibriTTS-R: A Restored Multi-Speaker Text-to-Speech Corpus,"
  arXiv, 2023.
- Every clip was checked by a local speech-to-text round-trip: OpenAI Whisper (MIT;
  `Systran/faster-whisper-medium.en`, second opinion `large-v3-turbo`) for English, ivrit.ai's Whisper
  models (`ivrit-ai/whisper-large-v3-turbo-ggml`, second opinion `ivrit-ai/whisper-large-v3-ct2`) for
  Hebrew. Those models only listened; nothing of them ships.
- 56 English words were re-voiced in the same `am_michael` voice and picked by ear: most said inside a
  short sentence ("I see a cat.") and cut out at Whisper's word timestamps, a few spelled out as phonemes
  (`tools/tts/en_pins.json`). A wav2vec2 phoneme recognizer (`facebook/wav2vec2-lv-60-espeak-cv-ft`,
  Apache-2.0) flagged the suspects; it too only listened.
- 30 more English words, whose default renders the speech-to-text check didn't hear right, are the same
  sentence cut chosen by a script, not yet by ear (`tools/tts/en_pins.json` says so in each `by`).
