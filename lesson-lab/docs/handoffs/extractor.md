# Handoff — source extractor (SmartArt, layout titles, video links) — DONE 2026-10-03

There is nothing left to resume.
- **Result:** `lesson-lab/docs/smartart-recheck.md` — what changed, the verification, the recheck list, and the changed-decks table.
- **Tool:** `lesson-lab/tools/extract_pptx.py` now extracts:
  - SmartArt and charts;
  - text boxes from the slide layout and master, such as "מה למדנו היום?" or "מה המסר שלנו?";
  - online video links.
- **Applied** to `sources/text` (72 decks) and `sources/index.json`. Writes were atomic, and only changed files were written.
- **Re-run:** `cd lesson-lab && uv run --with python-pptx python3 tools/extract_pptx.py`. Use `--out DIR` for a dry run.
- **Scratch:** the probes and the original-text snapshot are in `scratchpad/smartart/` (session `d2208d73…`).
