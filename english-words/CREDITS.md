# Credits

מילים באנגלית is a private family game for learning first English words.

## Words

The 347 words, their order and their Hebrew come from two published lists (where they were made is in
`tools/README.md`):

- **Israel Ministry of Education, Inspectorate for English Language Education**: English Curriculum
  2020, *Lexical Pre-Band I & Band I, Elementary School*
  (<https://meyda.education.gov.il/files/Mazkirut_Pedagogit/English/CurriculumFilesAugust21/LexicalBand1.xlsx>).
  219 of the words are on its Pre-Band I, Band I Core I or Core II sheets.
- **Cambridge Assessment English**: *Pre A1 Starters, A1 Movers and A2 Flyers word list*, for exams
  from 2018 (<https://www.cambridgeenglish.org/pl/Images/149681-yle-flyers-word-list.pdf>). The other
  128 words, the concrete early words a picture game needs, come from it.

Only the words are used; the Hebrew, the niqqud and the teaching order are our own.

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
