# Teaching-quality audit — 57 new grade 4–5 lessons

2026-11-15. Baseline `017b82e` (published PR17). Worktree `lesson-content-audit`, branch `fix/ENG-00-lesson-teaching-quality`.

## Scope and method

Read the repository instructions, local lighthouse lesson skill/README, terminology/project memories, binding followup-decisions.md and workflow/grade4/grade5b/integration/review reports. The newer published state supersedes the old memory saying the hub was unpublished. Original decks were read only from the retained grade4, grade5b and integration worktrees.

All57 lessons received a teaching-stage audit: age-appropriate framing, task/action clarity, grouping and privacy, preparation, 35-minute core plus at most10 optional minutes, exit assessment and correspondence to the original activity sequence. Original activity maps were compared with the new stages and the explicit adaptations in `docs/runs/grade4.md`, `grade5b.md` and `pkg-g5-c.md`. Every original PPTX was independently re-extracted with the repository extractor: all slide text and speaker notes match the committed extraction exactly. Counts and raw paths are in `content-audit-extractions.json` beside the external report.

Coverage is deliberately not described as a second line-by-line translation review of every source slide. Activity maps and retained/omitted choices were checked across all57; deeper source-note inspection covered Bead Azmi's characters/86-slide compression, Shachar's relationships/branching narrative, consent and touch safeguards, online image/scan metaphors, bystander role definitions and the group-game/film timing findings. Image-only cards and comics were not independently re-rendered in this audit; prior source-image inspection is recorded in the author reports. No new image transcription was introduced. Exact source quotations are checked by the existing validator.

## Findings and repairs

**F1 — P2, missing narrative setup (2 lessons).** `g4-bead-azmi` asks pupils to use three characters' strengths, but supplies neither species nor strengths before the task. Source slides4–7 provide those facts. Added a short teacher-readable retelling. `g4-shachar-kaduregel` names Dan, Nadav and Yossi without their relationships; source10 and notes13/16/18/22 explain that they are the familiar instructor, older brother and adult coach. Added the relationships so the trust/help-seeking dilemma works without an unexplained cast. No source story copied in full.

**F2 — P2, missing central role definitions (2 lessons).** `g5-omdim-lezad` and `g5-tafkid-lekol-tafkid` tell the teacher to explain and pupils to classify six roles but only list their names. In particular, מסייע can easily be mistaken for helping the victim. Source Omdim11/13 notes and Tafkid11 notes define assistance to the aggressor. Added concise definitions for all six roles, retaining the distinction between action in an event and a child's identity; the source's victim stereotype and numerical claims remain omitted.

**F3 — P2, undefined tool in a standalone lesson (1 lesson).** `g5-meniat-afazat-tmunot-poganiyot` asks pupils to activate סרוק without explaining it. Source18–20 introduces facial/body cues and inner thoughts. Added an actionable explanation of observing cues, treating feelings as hypotheses and asking; inner voice means a thought. This is an explicit adaptation of the source's literal mind-reading metaphor, consistent with the already-adapted introductory remote-control lesson.

**F4 — P2, contradictory private-work instructions (6 lessons).** `g4-yad-alalev/s4` and `g4-shachar-kaduregel/s5` promise private personal writing yet specify pair work and sharing two answers. Their task group and plenary now preserve privacy. `g5-gizanut-shayachut-3/map`, `g5-meishirim-mabat/continuum` and `g5-visut-3-hamelech-amar/ruler` promise privacy but append a generic pair-comparison instruction: replaced it with discussion of a fictional example and no comparison of personal maps/ratings. `g5-zoom/part-3` promises that the cloud need not be shared but assigns pair work and a group-owned output: changed to individual writing and optional process-only discussion. Existing source adaptations toward optional disclosure remain intact; these edits make their execution consistent.

**F5 — P3, preparation/group-material mismatches (10 lessons).** Eight preparation lists omitted required advance work: large person outline and attachment materials (`g4-adam-ichpati-2`, source14–16); two-color notes (`g4-maskim-lo-maskim`, source12); note container (`g4-simcha-lakita-3`, source13–14); board tool (`g4-zvita-balev-3`, source21); source-case printouts already required in the activities (`g4-achraim-bareshet`,22/24/25; `g4-keshet-pratyut`,17–25; `g4-samim-filter`,12–14; `g4-zvita-balev-2`,12–14). Added concrete quantities/preparation. `g4-zvita-balev-1/s4` gives pairs a repair task but prepares one large heart: returned to source15's volunteer demonstration, followed by pair reflection. The pupil prompt now says to observe the repair. `g5-mitnaschim-misrey-ani/part-3` specifies pairs despite only one six-card pack per quartet: corrected grouping to quartets, matching source10–11 and the preceding preparation/build stage.

**F6 — P2, film stage overpacked (1 lesson).** `g5-sium-shana/part-2` allocates7 minutes to the complete film, a pause and4 minutes of pupil work plus sharing. The sole browser verifier checked the actual source video `YYb4h8U7Ljw`: duration128.741seconds (`PT2M9S`), leaving only51seconds for the pause, explanation, sharing and transition. Reallocated this stage to9 minutes, and the existing three-round carousel to8 (three2-minute conversations, one minute transition and one minute closing insight). Core stays35; no activity or source message removed.

There are21 affected lessons because Shachar has two findings. No high-severity issue found; no speculative redesign or blanket rewrite applied. The other36 lessons have no material finding from this audit's coverage depth.

## Timing and age assessment

The shortened sources remain suitable as introductions/practice for grades4–5 rather than promises to deliver entire multimeeting programs. Fictional characters, optional personal disclosure, no compulsory touch, adult responsibility, accessible materials and practical help-seeking remain in place. All57 cores total35 minutes with6–7 core stages; only Bead Azmi has an optional5-minute extension. Classroom timing is an informed desk assessment, not a live classroom trial. Teachers still choose whether a sensitive topic fits their current class.

## Per-lesson matrix

Every row includes age/task/preparation/timing/source-activity/adaptation review. Source numbers are PPTX slide numbers, including notes. “Pass” means no material defect found at the stated review depth; “Fixed” names the concrete repair above. All cores remain35 minutes.

| Lesson | Source slides examined for activity correspondence | Result and specific content check |
|---|---|---|
| `g4-achraim-bareshet` | 10–18, 21–30 | Fixed — F5: case printouts; four selected cases remain, omitted two recorded |
| `g4-adam-ichpati-2` | 12–22 | Fixed — F5: prepare large figure and attachable notes; behavior-to-feeling mapping intact |
| `g4-bead-azmi` | 4–7, 9–24, 44–48, 53–67, 78–83 | Fixed — F1: supply animal identities/strengths; all four stations retained as explicitly compressed introduction; 5-minute optional care circles |
| `g4-hachamim-bareshet` | 10–24, 27–30 | Pass — Diary, six warning cues, known-sender caution and adult help; no unsafe content displayed |
| `g4-havila-laderech` | 7–15 | Pass — Paired cards instead of passing parcel; explicit wishes/actions and source-only closing poem |
| `g4-keshet-pratyut` | 11–29 | Fixed — F5: nine source cards explicitly prepared in three packets; privacy rather than real profiles |
| `g4-kita-ichpatit-1` | 10–24 | Pass — Mirror and caring prompts retained; film idea retold without unverified playback |
| `g4-mabat-lemabat` | 9–27 | Pass — Three object riddles, Dana/Yamit perspective and six-question tool; drawing replaces phones |
| `g4-maskim-lo-maskim` | 10–20 | Fixed — F5: two-color notes prepared; no touch/disclosure; ambiguity is not permission |
| `g4-matchilim-shana` | 8–22 | Pass — Wishes, life-skill situations, class agreement; explicit limit to secrecy |
| `g4-mitbonenim-batmuna` | 10–26 | Pass — Runaway plot retold; facts versus interpretation; question cards replace folding |
| `g4-negiot` | 11–22 | Pass — Pleasant versus appropriate, consent and adult help; no touch or compelled personal examples |
| `g4-samim-filter` | 10–22 | Fixed — F5: case printouts prepared; truth/respect/necessity and permission; source16 remains intermediate content |
| `g4-shachar-kaduregel` | 10–24, 28–38 | Fixed — F1/F4: clarify brother/instructor/coach identities; private help map; alternate endings and repeated help-seeking intact |
| `g4-simcha-lakita-3` | 13–26 | Fixed — F5: container and notes prepared; all four שמח״ה actions retained |
| `g4-yad-alalev` | 11–26 | Fixed — F4: private self-check is individual, no plenary disclosure; fictional bystander cases retained |
| `g4-zvita-balev-1` | 11–23 | Fixed — F5: two volunteers repair the one prepared heart while peers observe; pair reflection remains |
| `g4-zvita-balev-2` | 10–19 | Fixed — F5: print selected scenario sheets; request remains while wording changes; no forced apology |
| `g4-zvita-balev-3` | 9–24 | Fixed — F5: prepare three זה״ב steps on board; fictional conversations and safe assistance |
| `g5-ashan-dak` | 8–14 | Pass — Trophy story, five-stage tool and Itamar simulation; no peer labels or reenacted violence |
| `g5-etgar-koshi` | 8–14 | Pass — Gentle fictional dog incident; fact/thought/feeling separation; optional imagined balloon |
| `g5-gizanut-dag-bamaim-2` | 9–16 | Pass — Poem in source, fish traits and contribution; no labeling classmates |
| `g5-gizanut-hachlala-4` | 10–17 | Pass — Prior corrected definitions present; observation separated from identity guesses; listening exercise |
| `g5-gizanut-hakol-beyachad-1` | 11–17 | Pass — Six-part identity puzzle; voluntary selected details; no required family disclosure |
| `g5-gizanut-shayachut-3` | 10–18 | Fixed — F4: private belonging map no longer requires pair comparison; discuss fictional map |
| `g5-gizanut-zivey-akeshet-5` | 9–15 | Pass — Color-story summary, parrot listening and class rule; no prior-lesson dependency |
| `g5-golshim-leshinuy` | 11–19, 21–22 | Pass — Photo consent and like cards linked to source; three practical class rules |
| `g5-hakshava-peila` | 8–16 | Pass — Adam diary, Gali/Neta situation and four listening stages; eye contact optional |
| `g5-isum-hemla` | 8–14 | Pass — Dan at board, compassionate action and self-compassion; source definition available |
| `g5-isum-sikum` | 8–19 | Pass — Tools reintroduced for independent recap; real bullying requires adult help, not only calming |
| `g5-lenael-machshavot` | 8–14 | Pass — Lemon imagery, unplugged game and drawn memento; no required costly home object |
| `g5-machshava-machshila` | 8–19 | Pass — Basketball diary, four steps and Dana application; fear can remain while choosing action |
| `g5-mazpen-ishi` | 9–15 | Pass — Hand/value mapping, election diary and practical compass; no promise of success |
| `g5-meishirim-mabat` | 10–19 | Fixed — F4: private bystander continuum stays private; source מב״ט fully provided |
| `g5-meniat-afazat-tmunot-poganiyot` | 9–22 | Fixed — F3: define scan and inner voice without mind-reading claim; comic remains source-only |
| `g5-milim-vemaasim` | 10–31 | Pass — Paper metaphor, anger scale and response choice; avoids traumatic recall and permanent-damage claim |
| `g5-miniyut-reshst-2` | 7–21 | Pass — Empty box, age cues and three general cases; no explicit content or forced exposure disclosure |
| `g5-misrey-ani` | 9–27 | Pass — Four components, Yahli/Agam and science-group application; conflict distinct from victim responsibility |
| `g5-mitkavnim-beregishut-1` | 11–19 | Pass — Memory opening and two independent empathy stations; external activities omitted explicitly |
| `g5-mitkavnim-beregishut-2` | 12–19 | Pass — Empathy definition, two chairs and two chosen posts; both alternative tracks complete |
| `g5-mitnaschim-misrey-ani` | 10–14, 19–23 | Fixed — F5: one six-card pack per quartet, matching preparation and source group exchange |
| `g5-omdim-lezad` | 11–22 | Fixed — F2: six roles defined, assistant explicitly assists aggressor; adult help and research caveat retained |
| `g5-ptichat-shana` | 8–18 | Pass — Identity sheet, voluntary recognition, expectations and next step; no time capsule dependency |
| `g5-ptichat-shana-tashpaz` | 8–15 | Pass — Class weather, influence, kindness notes and chosen gesture; no spending or forced contact |
| `g5-sholtim-bainyanim-1` | 9–22 | Pass — Remote metaphor, Omer and two group tasks; correction cannot erase harm or control others |
| `g5-sipuro-shel-regesh` | 8–16 | Pass — Two diary parts and emotion guessing; no imposed feeling or pressure for immediate relief |
| `g5-sipuru-shel-hagibor` | 13–25 | Pass — Starfish retelling, letters, bystander cases and strengths; safe adult support |
| `g5-sium-shana` | 8–15, 18–23 | Fixed — F6: verified 2:09 film now has9-minute stage; three2-minute carousel rounds fit8-minute stage |
| `g5-tafkid-lekol-tafkid` | 11–21, 25–26 | Fixed — F2: six role definitions supplied; Yahli case and three selected statements retained |
| `g5-tarbut-pnai` | 8–20 | Pass — Big-rock planning, traffic light, internal/external limits; accessible low-cost alternatives |
| `g5-visut-1-yazanu-laderech` | 8–16 | Pass — Adam diary, resilience definition, balance and agreement; imagined example and adult help |
| `g5-visut-2-bhira` | 8–18 | Pass — Cake choice, gentle self-only hand exercise and flexibility; no personality diagnosis |
| `g5-visut-3-hamelech-amar` | 8–17 | Fixed — F4: private stress rulers no longer require comparison; non-elimination game retained |
| `g5-visut-4-tsumet-lev` | 8–16 | Pass — Object change, thought categories, diary and noticing practice; no thought-content collection |
| `g5-visut-5-mafhid-lo-mesukan` | 9–16 | Pass — Fear/danger distinction includes uncertainty and immediate adult protection; no surprise scare |
| `g5-visut-6-linshom-leat` | 8–14 | Pass — Optional gentle breathing and own bubble equipment; discomfort permits stopping; documented faulty claim omitted |
| `g5-zoom` | 9–15 | Fixed — F4: personal thought cloud stays individual; broaden attention without ignoring harm |

## Verification and preservation

- Original PPTX re-extraction:57/57 match committed slide text and notes; raw files untouched.
- Scoped build of affected21 lessons with `--no-sync-assets`: zero errors; three inherited no-message warnings (Bead Azmi, Samim Filter, Meishirim Mabat), already justified in author logs. Builder fingerprint `ebc68929`.
- Full57 validation: zero errors, six inherited documented no-message warnings. All114 generated HTML files match fresh renders; 597 slides and1,901 local links/anchors pass. All57 cores have35 minutes and6–7 stages, extensions stay within10 minutes; all closing source-message items are unchanged. The574 old lesson/shared-asset files match baseline exactly. `git diff --check` passes.
- No browser used by this author. Sole verifier owns visual work and supplied runtime evidence for F6. No PDFs produced. No renderer, shared asset, hub, inventory, title or lesson-count change; the existing directory card remains accurate.
- Only source YAML and generated outputs of affected NEW lessons plus this dedicated audit log are committed. All116 older lesson folders and shared assets remain byte-identical to `017b82e`.

## Delivery

Delivery branch: `fix/ENG-00-lesson-teaching-quality`. Content-only draft PR; no merge by this author. Final SHA/PR handoff is recorded in the external `content-audit.md` beside the follow-up decisions. The independent reviewer and sole browser verifier own the subsequent review/visual checks.
