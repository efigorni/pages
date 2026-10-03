# Handoff — SmartArt extractor fix (paused 2026-10-03 ~20:10)

## State
- **`lesson-lab/tools/extract_pptx.py` is changed and finished. It has only been dry-run.**
  - Each SmartArt diagram (`ppt/diagrams/dataN.xml`) is emitted after the slide's text as a `(SmartArt)` block, one paragraph per top-level item.
  - Each chart is emitted the same way as a `(תרשים)` block.
  - Notes, links, flags and the shape walker are unchanged.
  - `מילים בשקפים` / `words_slides` now include the added words.
  - Writes are atomic (dot-temp file + `os.replace`), and a file is written only when its content changed.
  - `--out DIR` sends the output to another directory, for a dry run.
- **The real `sources/text/**` and `sources/index.json` are NOT touched yet.** They are still the 13:47 originals.
- **Scratchpad:** `/private/tmp/claude-501/-Users-adamer-dev-efigorni-pages/d2208d73-3cb9-4d07-bfe5-294aaa6667cd/scratchpad/smartart/`
  - `old/` — snapshot of the original `text/`, `index.json` and extractor. The old extractor reproduces it byte-for-byte.
  - `new/` — dry-run output of the new extractor.
  - `survey.py`, `coverage.py`, `dump_dgm.py` — probes.
- **Dry-run result:**
  - 125 decks extracted, 10 changed, 115 byte-identical.
  - Every diff is additive. The only line changed in place is the header word count (line 7).
- **Coverage:** in all 125 decks, the old walker misses no slide-XML text. The only skipped containers were:
  - 16 SmartArt diagrams in 9 decks.
  - 5 charts in `6/Sheela_Tshuva`.
  - No `mc:AlternateContent` text and no OLE objects. 3D models and slide zooms have no text.
- **Reading order:**
  - SmartArt text follows the data model (text-pane) order.
  - Exception: a left-to-right row grid is mirrored to right-to-left reading order. This applies to `7/Tofsim_Kivun_Bareshet` 18–19 and `9/Ani_Meshatef_Ani_Kayam` 20.
  - Cycles, pyramids, lists and right-to-left grids keep text-pane order.
  - `Tiru_Oty` 20–21 come out in exactly the order of the pkg-g6-09 `src_fixes`.

## Next steps (exact)
1. Run the real extraction:
   `cd /Users/adamer/dev/efigorni-pages/lesson-lab && uv run --with python-pptx python3 -u tools/extract_pptx.py`
   Expect `125 decks extracted, 10 updated, 128 index rows`, with `index.json` rewritten.
2. Verify that the real output equals the dry run:
   `diff -r <scratch>/smartart/new/text sources/text && cmp <scratch>/smartart/new/index.json sources/index.json`
3. Compatibility check on the 7 built lessons below. Run it with `PYTHONDONTWRITEBYTECODE=1` so nothing is written into the skill.
   - Import the skill's `scripts/validate.py` and use `iter_text`, `norm` and `fixed_source`.
   - Every `src_fixes.from` must still be found.
   - The set of failing verbatim quotes must be the same or smaller, comparing old text against new.
   - Expected result: no breakage. Slide headers are unchanged, so the `"## שקף N"` anchors still match.
4. For the recheck list, grep each built lesson's `lesson.yaml` for the added text, to see whether it already covers it:
   - g6-lizmoach-hoze slides 6–7.
   - g7-tofsim-kivun-bareshet 18–19.
   - g8-karov-rachok-reshet 29.
5. Write `lesson-lab/docs/smartart-recheck.md`. Use the table below, and add a recheck list.
6. Return ≤120 words to the coordinator.

## Partial findings (dry run)
| deck | slug | built? (pkg · queue) | slides | added | words |
|---|---|---|---|---|---|
| 6/Tiru_Oty | g6-tiru-oty | yes (g6-09 · הושלם) | 20, 21 | messages (6) | 110 |
| 6/Maavarim_Bareshet | g6-maavarim-bareshet | yes (g6-09 · הושלם) | 30, 31, 32 | messages (30) + checklists (31–32), which the lesson used as messages 5–6 | 127 |
| 6/Lizmoach_Hoze | g6-lizmoach-hoze | yes (g6-04 · הושלם) | 6, 7 | activity content: 5 opening questions and 3 example answers | 52 |
| 6/Sheela_Tshuva | g6-sheela-tshuva | yes (g6-08 · הושלם) | 19, 27, 28 | other: pie-chart data, which the slide text and notes already state | 55 |
| 7/Omdim_Lezad_6 | g7-omdim-lezad-6 | yes (g7-09 · הושלם) | 9, 12 (hidden) | other: teacher rationale and lesson goals — not messages | 107 |
| 7/Tofsim_Kivun_Bareshet | g7-tofsim-kivun-bareshet | yes (g7-07 · הושלם) | 18, 19 | messages (5) | 91 |
| 8/Karov_Rachok_Reshet | g8-karov-rachok-reshet | yes (g8-04 · רץ) | 29 | messages (5, "מה למדנו היום?") | 70 |
| 9/Ani_Meshatef_Ani_Kayam | g9-ani-meshatef-ani-kayam | no (g9-06 · ממתין) | 20 | messages (4) | 77 |
| 9/Netya_Minit | g9-netya-minit | no (g9-07 · ממתין) | 31 | activity content: 4 closing prompts | 13 |
| 9/Shaar_Laatid | g9-shaar-laatid | no (g9-08 · ממתין) | 14 | activity content: 3 individual-work questions | 33 |

Total: 735 words.

**Recheck list (built, and the added text is messages or activity content):**
- **g7-tofsim-kivun-bareshet** — 5 messages were missing from its source.
- **g8-karov-rachok-reshet** — 5 messages. Its package is still running, so tell that agent.
- **g6-lizmoach-hoze** — the opening questions and the examples.
- **g6-tiru-oty** and **g6-maavarim-bareshet** — the messages were already injected through `src_fixes`. Those entries still apply but are now redundant, and can be removed.

**No recheck needed:**
- g6-sheela-tshuva — the chart data is redundant.
- g7-omdim-lezad-6 — the SmartArt is the hidden teacher rationale and goals, not messages. This contradicts the guess in pkg-g6-09.
- The three g9 lessons are not built yet. They get the text once step 1 runs.
