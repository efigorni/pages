# Credits

זיכרון הפועל תל אביב is a private family game. It is not affiliated with or endorsed by
Hapoel Tel Aviv FC.

## Player photos

Player photos © Hapoel Tel Aviv FC, from the club's team and players page at
<https://www.htafc.co.il/צוות-ושחקנים/>. They are cropped and resized for use in this
private family game.

## Design

The cards follow the look of the club's team and players page: its reds and wines, the
big shirt number beside each player and the name in wine under the picture. The dark red
wall paint on the cards and the start screen is our own render after the wine panel of
the page's banner (`tools/look/paint.py`); no club files are included. The club's
typefaces, RagSans and RAG Marom Poster, are commercial, so the game uses Rubik for the
names and Karantina for the numbers and the title.

## Fonts

- **Rubik**: Copyright 2015 The Rubik Project Authors
  (<https://github.com/googlefonts/rubik>). SIL Open Font License 1.1; see
  [`fonts/OFL-Rubik.txt`](fonts/OFL-Rubik.txt).
- **Karantina**: Copyright 2020 The Karantina Project Authors
  (<https://github.com/ronykoch/Karantina>). SIL Open Font License 1.1; see
  [`fonts/OFL-Karantina.txt`](fonts/OFL-Karantina.txt).

## Voice

Voice: BlueTTS (MIT) with LibriTTS-R speaker 1088 (CC BY 4.0).

- **BlueTTS 2.5** (<https://github.com/maxmelichov/BlueTTS>, MIT License)
  synthesized every clip in [`audio/`](audio/) locally from the player names.
- The `noa` voice is speaker 1088 of the **LibriTTS-R** corpus
  (<https://www.openslr.org/141/>), licensed under CC BY 4.0
  (<https://creativecommons.org/licenses/by/4.0/>). The clips are new synthetic
  speech in that speaker's voice; no audio from the corpus is included here.
- LibriTTS-R asks that its paper be cited: Yuma Koizumi, Heiga Zen, Shigeki Karita,
  Yifan Ding, Kohei Yatabe, Nobuyuki Morioka, Michiel Bacchiani, Yu Zhang, Wei Han,
  and Ankur Bapna, "LibriTTS-R: A Restored Multi-Speaker Text-to-Speech Corpus,"
  arXiv, 2023.
