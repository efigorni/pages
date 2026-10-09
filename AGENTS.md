# Guidelines for AI Agents Working on this Repository

## Repository Overview
This repository (`efigorni/pages`) hosts standalone, single-file HTML web applications, educational tools, games, and activity hubs deployed automatically via **GitHub Pages**:
🔗 **Live Base URL**: `https://efigorni.github.io/pages/`

---

## 🚨 MANDATORY INSTRUCTIONS

### 1. Always Update `index.html` When Adding / Modifying Pages
Whenever you create, import, rename, or delete an HTML page:
- **YOU MUST update `index.html`** to add or update a card linking to the new page.
- Every page in this repository **must** have a corresponding card in the `index.html` directory grid, except the unlisted pages below.

#### Unlisted pages
Kept private on purpose, at the owner's request: each stays out of `index.html` and the catalog below, and carries `<meta name="robots" content="noindex, nofollow">`.
- **Every memory game** is unlisted: any folder at the root with a `club/club.json` (`python3 -I _memory-game/tools/page/build_page.py list` names them): a football club's memory game for a young child, at `/pages/<folder>/`. Never add one to `index.html` or the catalog, never remove its `noindex`, and never delete one, or `_memory-game/`, as an orphan. A new club needs no edit here.

Every memory game is built from `_memory-game/`, which is not a page. A game's `index.html` and `sw.js` are generated whole from its `club/` sources and `_memory-game/`: edit those (or refresh the roster) and run `python3 -I _memory-game/tools/page/build_page.py assemble`, never the generated files. A shared change changes every game, so commit and verify all of them. Adding or refreshing a club: see `_memory-game/README.md`.

Testing the memory games (`_memory-game/tools/verify/verify.sh`, details in `_memory-game/README.md`):
- **`verify.sh sanity` is the default gate** for every commit and PR: every game in parallel in about a minute (it includes `assemble --check`). After a merge, `verify.sh live`.
- **`verify.sh full`** (about an hour) only when the engine's behaviour is deliberately refactored across every game, or when asked.

### 2. Card Design Standard in `index.html`
Each card in `index.html` must follow the aesthetic established by `gibush.html`:
- **Direction / Language**: Hebrew RTL (`dir="rtl"`, `lang="he"`).
- **Fonts**: `Secular One` (display / titles), `Assistant` (body).
- **Card Structure**:
  - `motif`: Decorative colored abstract SVG in top corner.
  - `card-cat`: Category tag with colored indicator dot (e.g., חינוך והוראה, פעילויות חברתיות, מוגנות ברשת, כלי עזר).
  - `card-t`: Bold, clear Hebrew title in Secular One.
  - `card-s`: 1-2 sentences explaining what the page does.
  - `card-f`: Footer with tag / badges and a "פתח אפליקציה &larr;" button/arrow link.
  - Choose a unique theme color per card (e.g., `--teal`, `--purple`, `--orange`, `--moss`, `--blue`, `--rose`).

### 3. File Architecture & Best Practices
- **Standalone Files**: All web applications should preferably be standalone, self-contained HTML files containing all their inline CSS and JavaScript (or using standard reliable CDNs) so they work seamlessly on GitHub Pages.
- **RTL & Mobile Responsive**: Ensure all pages work well on mobile, tablet, and desktop screens with proper Hebrew RTL support (`<html lang="he" dir="rtl">`).
- **Clean Naming**: Use clean, descriptive lowercase filenames (e.g., `waze.html`, `safesurf.html`, `gibush.html`).

---

## Current Pages Catalog

| File | URL | Description | Category |
| :--- | :--- | :--- | :--- |
| `gibush.html` | `/pages/gibush.html` | 101 פעילויות גיבוש והיכרות | פעילויות וגיבוש |
| `safesurf.html` | `/pages/safesurf.html` | רולטת מוגנות וגלישה בטוחה ברשת | מוגנות ורשת |
| `waze.html` | `/pages/waze.html` | Class Waze - ניווט וניהול חכם בכיתה | חינוך והוראה |
| `schedule.html` | `/pages/schedule.html` | מחולל לו״ז יומי מעוצב | חינוך והוראה |
| `massa_z.html` | `/pages/massa_z.html` | הכ״חות שבדרך - רולטת מסע כיתה ז׳ | פעילויות וגיבוש |
| `lesson-lab/lessons/index.html` | `/pages/lesson-lab/lessons/index.html` | הכ״חות שבדרך - 116 מערכי שיעור לכישורי חיים, כיתות ו׳–ט׳ (המערך + מצגת לכל שיעור) | חינוך והוראה |

