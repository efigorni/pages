# Credits

מילים באנגלית is a private family game for learning English words, from grade 1 to grade 7.

## Words

The 384 words, their school grade (א׳ to ז׳), their order and their Hebrew come from the formal English
lists below (where they were made is in `tools/README.md`). 241 of the words are on a Ministry of
Education list; the other 143 are on Cambridge's.

- **Israel Ministry of Education, Inspectorate for English Language Education**:
  - *English Curriculum 2020* (<https://meyda.education.gov.il/files/Mazkirut_Pedagogit/English/Curriculum2020.pdf>):
    its Table 2 gives each lexical band's grades (Pre-Band I grade 3; Band I Core I grade 4 to mid 5;
    Core II mid 5 to the end of 6; Band II Core I grade 7 to mid 8), and its Table 1 their CEFR levels.
  - *Lexical Pre-Band I & Band I, Elementary School*
    (<https://meyda.education.gov.il/files/Mazkirut_Pedagogit/English/CurriculumFilesAugust21/LexicalBand1.xlsx>).
  - *Lexical Band II, Junior High*
    (<https://meyda.education.gov.il/files/Mazkirut_Pedagogit/English/CurriculumFilesAugust21/LexicalBand2.xlsx>).
- **Cambridge University Press & Assessment**:
  - *Pre A1 Starters, A1 Movers and A2 Flyers Wordlists* (2025)
    (<https://www.cambridgeenglish.org/Images/739104-starters-movers-flyers-word-list-2025.pdf>).
  - *A2 Key and A2 Key for Schools Vocabulary List* (August 2025)
    (<https://www.cambridgeenglish.org/images/506886-a2-key-2020-vocabulary-list.pdf>), A2, the level the
    curriculum's Table 1 gives Band II Core I.

A word's grade is the **lowest grade any of these sources gives it**: its Ministry band's grades (split
by its Cambridge young learners' level), Starters grade 3, Movers grade 5, Flyers grade 6, A2 Key grade 7.
The Ministry has no word list for grades 1–2, where English starts with the *Enjoy English* programme
(<https://pop.education.gov.il/kindergarten/topics/english/teaching-materials/enrichment/>). A Starters word
in one of the programme's themes (colours, numbers, animals, family, the body, clothes, food, feelings,
transport, weather, actions) is grade 2, and grade 1 when it is also in the grades 1–2 word bank of
*English Playbox* (<https://english-playbox.netlify.app/>, linked from the programme's site) or on Pre-Band
I. A few early words no list places that low sit with their theme's siblings. Grade 7 holds only words
added for it; no word is placed above the grade a source gives it.

Only the words and their levels are used; the Hebrew, the niqqud and the teaching order are our own.

## Pictures

Every picture in [`img/`](img/) is a **Fluent Emoji** by Microsoft in its 3D style
(<https://github.com/microsoft/fluentui-emoji>, commit `1ffb34c752ecf5d402f04cfb4b392c77f57c54bc`).
People and body parts use the default (yellow) skin tone. Changes: trimmed to the drawing's edges,
centred, resized to 200×200 px and converted to WebP with a transparent background. They are used under
the MIT License:

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
