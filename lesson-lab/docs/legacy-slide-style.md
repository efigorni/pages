# Existing lesson slide cleanup — 2026-11-15

D87 extends Efrat's label removal to the 116 existing grade 6–9 lessons. It follows the separately published grade 4–5 addition; its original no-touch and UI-waiver reports remain historical.

## Preservation before rebuilding

Baseline: `017b82e` (PR 17 merged). Compared all 232 existing HTML outputs with fresh in-memory rendering before editing. Only `g7-makom-baolam/slides.html` differed: Efrat had removed exactly 15 kicker elements in `be80dc0594e7f1a53f8b186fce9b0c2d75a5fe1b`. No other authored/manual drift was found.

Each legacy YAML receives only `slide_kickers: false`; its existing bytes follow that added line unchanged. Original authored kicker values remain as historical metadata. The existing renderer suppresses them and generated cover/video/message/exit/source labels centrally, so no renderer, template, stylesheet or script asset change was needed. Outputs were rendered per lesson without syncing assets or rebuilding the hub.

## Exact checks

- All 232 HTML outputs match both fresh rendering and the baseline with only the appropriate label elements removed: 1,838 presentation `div.kicker` elements and 1,165 teacher echo `span.k` elements immediately before `p.h`. Teacher practice tags and the messages-block heading remain.
- All 1,855 derived slides match their previous slide objects with only `kicker` cleared. Titles, instructions, messages, images, numbering, ordering, timers and links therefore remain identical.
- Efrat's Makom Baolam presentation remains byte-identical, SHA-256 `90d2473217acffff2ead1f8cc83fbdaef7ea8310ac235cad697ac0a7e090e6c5`.
- All 398 other tracked lesson-directory files remain identical, including the 57 new lessons, the hub, source artwork and shared assets.
- HTML link lists and IDs are identical before/after. 7,609 local references resolve, with no broken anchors or new broken links. The 116 inherited `slides.pdf` links remain unavailable without local PDF generation (D81/D82); this cleanup does not change them.
- All 116 lessons validate with zero errors. Their 49 existing warnings remain exactly unchanged: 26 `messages`, 20 `src-fix`, two `slide-words`, one `video`. There are also 1,171 expected `hidden-kicker` warnings because D87 deliberately retains historical label metadata without displaying it. No other warning was introduced, and no warning was suppressed.
- Seven generator regression tests pass; the existing opt-in test now explicitly sets `slide_kickers: true` before exercising the old behavior. `git diff --check` passes.

## Scope and limits

This proves a mechanical label-only migration, not a new editorial review of the legacy lessons. The root portal card and authoring documentation describe the updated style. No PDFs were regenerated. Targeted visual verification is coordinated separately by the single browser owner; these static checks alone make no browser or visual-quality claim. Unrelated memory-game browser tests are outside this follow-up's targeted checks.
