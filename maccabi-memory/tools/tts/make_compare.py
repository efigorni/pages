"""Build <work>/tts/compare.html: one row per phrase, one column per engine/voice.

    MACCABI_WORK=<work> python3 make_compare.py      (default: the current directory)

Scans <work>/tts/samples/<engine>/manifest.json (written by generate.py --out ...).
Relative paths only, so the page works straight from file://.
"""
from __future__ import annotations

import html
import json
import os
from pathlib import Path

TTS = Path(os.environ.get("MACCABI_WORK", ".")).resolve() / "tts"
SAMPLES = TTS / "samples"

# Column order and the one-line description shown in each header.
ENGINES = {
    "bluetts-noa": ("BlueTTS 2.5 · noa", "chosen — what the game ships"),
    "bluetts-adam": ("BlueTTS 2.5 · adam", "same engine, male voice"),
    "bluetts-female": ("BlueTTS 2.5 · female", "same engine, in-house Hebrew voice (rights unclear)"),
    "piper-shaul": ("Phonikud + Piper · shaul", "runner-up engine, same IPA input"),
    "piper-michael": ("Phonikud + Piper · michael", "runner-up engine, same IPA input"),
    "macos-carmit": ("macOS say · Carmit", "baseline, no pronunciation control"),
}
KIND_LABEL = {"name": "name", "match": "match", "ui": "ui"}


def main() -> None:
    cols = [e for e in ENGINES if (SAMPLES / e / "manifest.json").exists()]
    cols += sorted(p.name for p in SAMPLES.iterdir()
                   if p.is_dir() and p.name not in ENGINES and (p / "manifest.json").exists())
    data = {e: {(m["id"], m["kind"]): m for m in json.load(open(SAMPLES / e / "manifest.json", encoding="utf-8"))}
            for e in cols}
    keys = []
    for e in cols:
        for k in data[e]:
            if k not in keys:
                keys.append(k)
    order = {"name": 0, "match": 1, "ui": 2}
    keys.sort(key=lambda k: (order[k[1]], k[0]))

    head = "".join(
        f"<th><div class=eng>{html.escape(ENGINES.get(e, (e, ''))[0])}</div>"
        f"<div class=sub>{html.escape(ENGINES.get(e, ('', ''))[1])}</div></th>" for e in cols)
    rows = []
    for k in keys:
        text = next(data[e][k]["text"] for e in cols if k in data[e])
        cells = []
        for e in cols:
            m = data[e].get(k)
            if not m:
                cells.append("<td class=na>—</td>")
                continue
            ok = "pass" if m["stt_ok"] else "fail"
            cells.append(
                f"<td><audio controls preload=none src=\"samples/{e}/{m['file']}\"></audio>"
                f"<div class='stt {ok}' dir=rtl title='what ivrit.ai Whisper heard'>"
                f"{html.escape(m['stt_transcript'])}</div></td>")
        rows.append(
            f"<tr><th class=phrase><span class=kind>{KIND_LABEL[k[1]]}</span>"
            f"<span dir=rtl lang=he>{html.escape(text)}</span>"
            f"<button class=all title='play this row left to right'>▶ row</button></th>"
            + "".join(cells) + "</tr>")

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Voice Comparison</title>
<style>
:root {{ --bg:#f7f7f4; --fg:#1d1f24; --muted:#5f6675; --line:#dddcd5; --card:#fff;
        --ok:#1f7a3f; --bad:#b3261e; --accent:#12305c; --hl:#ffd43b; }}
@media (prefers-color-scheme: dark) {{
  :root {{ --bg:#14161b; --fg:#e8e8e3; --muted:#a3a8b4; --line:#2c2f37; --card:#1c1f26;
          --ok:#6fd38f; --bad:#ff8a80; --accent:#9ab8ff; --hl:#ffd43b; }} }}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:24px 16px 48px; background:var(--bg); color:var(--fg);
       font:15px/1.45 system-ui, -apple-system, "Segoe UI", Arial, sans-serif; }}
h1 {{ font-size:22px; margin:0 0 4px; }}
p.lead {{ margin:0 0 16px; color:var(--muted); max-width:860px; }}
.wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:10px; background:var(--card); }}
table {{ border-collapse:collapse; min-width:100%; }}
th, td {{ border-bottom:1px solid var(--line); padding:10px; vertical-align:top; text-align:left; }}
thead th {{ position:sticky; top:0; background:var(--card); z-index:1; min-width:230px; }}
thead th:first-child {{ min-width:220px; }}
.eng {{ font-weight:650; color:var(--accent); }}
.sub {{ font-weight:400; font-size:12.5px; color:var(--muted); }}
th.phrase {{ font-weight:600; }}
th.phrase span[lang=he] {{ display:block; font-size:17px; margin:2px 0 6px; }}
.kind {{ font-size:11px; letter-spacing:.06em; text-transform:uppercase; color:var(--muted); }}
audio {{ width:220px; height:34px; display:block; }}
.stt {{ font-size:12.5px; margin-top:4px; }}
.stt.pass {{ color:var(--ok); }} .stt.fail {{ color:var(--bad); }}
.stt::before {{ content:"STT: "; color:var(--muted); }}
td.na {{ color:var(--muted); }}
button.all {{ font:inherit; font-size:12.5px; padding:3px 10px; border-radius:6px; cursor:pointer;
             border:1px solid var(--line); background:var(--bg); color:var(--fg); }}
tr.playing th.phrase {{ box-shadow: inset 4px 0 0 var(--hl); }}
</style>
</head>
<body>
<h1>Voice comparison — Maccabi memory game</h1>
<p class="lead">Every clip went through the same trim / loudness (−16 LUFS) / MP3 chain as the game's
audio. "STT" is what a local ivrit.ai Whisper heard (green = matches the intended text).
Listen for: an Israeli accent, the names said the way fans say them, warmth for a 6-year-old,
and speech that starts the instant the clip starts. "▶ row" plays one phrase across all voices.</p>
<div class="wrap"><table>
<thead><tr><th>phrase</th>{head}</tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table></div>
<script>
document.addEventListener('play', e => {{
  document.querySelectorAll('audio').forEach(a => {{ if (a !== e.target) a.pause(); }});
}}, true);
document.querySelectorAll('button.all').forEach(btn => btn.addEventListener('click', () => {{
  const tr = btn.closest('tr');
  const list = [...tr.querySelectorAll('audio')];
  document.querySelectorAll('tr.playing').forEach(r => r.classList.remove('playing'));
  tr.classList.add('playing');
  let i = 0;
  const next = () => {{
    if (i >= list.length) {{ tr.classList.remove('playing'); return; }}
    const a = list[i++];
    a.currentTime = 0;
    a.onended = () => setTimeout(next, 450);
    a.play().catch(next);
  }};
  next();
}}));
</script>
</body>
</html>
"""
    (TTS / "compare.html").write_text(page, encoding="utf-8")
    print(f"wrote {TTS / 'compare.html'}: {len(keys)} phrases x {len(cols)} engines")


if __name__ == "__main__":
    main()
