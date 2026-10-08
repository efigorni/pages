"""Build tts/listen.html: one row per player, the name clip and the match clip.

    MACCABI_ROOT=<work> python3 _memory-game/tools/tts/make_listen.py --pron <game>/tools/tts/pronunciations.json

Reads tts/out/manifest.json, data/players.json, the club's pronunciations.json and
the QA files in tts/qa/ (for the second-opinion transcript). Paths in the page are
relative, so it opens straight from file://. generate.py runs this after every
run that writes tts/out.

Alternative pronunciations for a judgement call go in tts/alternatives/<id>--<label>/
(a generate.py --out folder); they are shown next to that player's note, labelled
<label> with dashes as spaces.
"""
from __future__ import annotations

import argparse
import html
import json
import os
from pathlib import Path

if not os.environ.get("MACCABI_ROOT"):
    raise SystemExit("set MACCABI_ROOT to the work directory (outside the repo) that holds data/ and tts/")
ROOT = Path(os.environ["MACCABI_ROOT"])
TTS = Path(os.environ.get("MACCABI_TTS_HOME", ROOT / "tts"))


def _second_opinions(manifest: list[dict]) -> dict:
    """(id, kind) -> large-v3 transcript, from the QA run that made the current clip."""
    want = {(m["id"], m["kind"]): (m["engine_input"], m["duration_ms"], m["stt_transcript"])
            for m in manifest}
    got = {}
    for qf in sorted((TTS / "qa").glob("*.json"), key=lambda p: p.stat().st_mtime):
        for q in json.load(open(qf, encoding="utf-8")):
            k = (q.get("id"), q.get("kind"))
            if k in want and "stt2_transcript" in q and \
                    (q["engine_input"], q["duration_ms"], q["stt_transcript"]) == want[k]:
                got[k] = (q["stt2_transcript"], q.get("stt2_ok"))
    return got


def main(players_path: str | None = None, pron_path: str | None = None) -> None:
    man = json.load(open(TTS / "out/manifest.json", encoding="utf-8"))
    roster = json.load(open(players_path or ROOT / "data/players.json", encoding="utf-8"))["players"]
    pron = json.load(open(pron_path, encoding="utf-8"))["players"]
    rows_by = {(m["id"], m["kind"]): m for m in man}
    fw = _second_opinions(man)
    alts: dict[str, list[tuple[str, str, dict]]] = {}
    for d in sorted((TTS / "alternatives").glob("*--*/manifest.json")):
        pid, label = d.parent.name.split("--", 1)
        for m in json.load(open(d, encoding="utf-8")):
            if m["id"] == pid:
                alts.setdefault(pid, []).append((label.replace("-", " "), d.parent.name, m))

    def alt_cell(pid):
        out = []
        for label, folder, m in alts.get(pid, []):
            out.append(f"<div class=alt><span class=sub>alternative, {html.escape(label)} — {m['kind']}:</span>"
                       f"<audio controls preload=none src=\"alternatives/{html.escape(folder)}/{html.escape(m['file'])}\">"
                       f"</audio></div>")
        return "".join(out)

    def stt_cell(k):
        m = rows_by.get(k)
        if not m:
            return "<span class=bad>missing</span>"
        s = f"<span class={'ok' if m['stt_ok'] else 'bad'}>{html.escape(m['stt_transcript'])}</span>"
        if k in fw:
            t, ok = fw[k]
            s += f"<br><span class='{'ok' if ok else 'bad'} sub' title='second model (large-v3)'>{html.escape(t)}</span>"
        return s

    def audio(k):
        m = rows_by.get(k)
        return (f"<audio controls preload=none src=\"out/{html.escape(m['file'])}\"></audio>"
                if m else "<span class=bad>—</span>")

    rows, n = [], 0
    for p in roster:
        if p.get("role") not in ("starter", "bench"):
            continue
        n += 1
        e = pron.get(p["id"], {})
        name = rows_by.get((p["id"], "name"), {})
        speak = name.get("text", "")
        shown = p.get("name_he") or p.get("name", "")
        note = e.get("listen", "")
        rows.append(
            f"<tr{' class=flag' if note else ''}>"
            f"<td class=num>{p.get('number', '')}</td>"
            f"<td><div class=shown lang=he>{html.escape(shown)}</div>"
            + (f"<div class=sub lang=he>voice: {html.escape(speak)}</div>" if speak != shown else "")
            + f"<div class=sub>{html.escape(p.get('role', ''))} · <code>{html.escape(p['id'])}</code></div></td>"
            f"<td>{audio((p['id'], 'name'))}<div class=stt lang=he>{stt_cell((p['id'], 'name'))}</div></td>"
            f"<td>{audio((p['id'], 'match'))}<div class=stt lang=he>{stt_cell((p['id'], 'match'))}</div></td>"
            f"<td class=note>{html.escape(note)}{alt_cell(p['id'])}</td></tr>")
    n_ok = sum(m["stt_ok"] for m in man)

    page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex, nofollow">
<title>Voice Check</title>
<style>
:root {{ --bg:#f6f7f5; --fg:#16201b; --muted:#5b6660; --line:#d9ddd8; --card:#fff;
        --ok:#1d7a42; --bad:#b3261e; --accent:#0b6b3a; --flag:#fff6d6; }}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{ --bg:#121614; --fg:#e6ebe7; --muted:#9fa9a3; --line:#2b322e;
          --card:#1a1f1c; --ok:#71d394; --bad:#ff8a80; --accent:#6fd39b; --flag:#2e2a17; }} }}
:root[data-theme="dark"] {{ --bg:#121614; --fg:#e6ebe7; --muted:#9fa9a3; --line:#2b322e;
          --card:#1a1f1c; --ok:#71d394; --bad:#ff8a80; --accent:#6fd39b; --flag:#2e2a17; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; padding:20px 16px 40px; background:var(--bg); color:var(--fg);
       font:15px/1.45 system-ui, -apple-system, "Segoe UI", Arial, sans-serif; }}
h1 {{ font-size:21px; margin:0 0 4px; color:var(--accent); }}
p {{ margin:0 0 14px; color:var(--muted); max-width:820px; }}
.wrap {{ overflow-x:auto; border:1px solid var(--line); border-radius:10px; background:var(--card); }}
table {{ border-collapse:collapse; width:100%; }}
th, td {{ border-bottom:1px solid var(--line); padding:9px 10px; vertical-align:top; text-align:left; }}
th {{ font-size:12px; letter-spacing:.05em; text-transform:uppercase; color:var(--muted); }}
tr.flag td {{ background:var(--flag); }}
.num {{ font-weight:700; font-size:18px; text-align:center; width:44px; }}
.shown {{ font-size:17px; font-weight:600; direction:rtl; text-align:left; unicode-bidi:plaintext; }}
.sub {{ font-size:12.5px; color:var(--muted); unicode-bidi:plaintext; }}
.stt {{ font-size:13px; margin-top:3px; direction:rtl; text-align:left; unicode-bidi:plaintext; }}
.ok {{ color:var(--ok); }} .bad {{ color:var(--bad); }}
.stt .sub.ok {{ color:var(--ok); opacity:.75; }}
audio {{ width:210px; height:34px; display:block; }}
td.note {{ font-size:13px; color:var(--fg); max-width:300px; }}
.alt {{ margin-top:6px; }} .alt audio {{ width:190px; height:30px; }}
code {{ font-size:12px; }}
</style>
</head>
<body>
<h1>Voice check</h1>
<p>{n} players, {n_ok}/{len(man)} clips understood by the local ivrit.ai Whisper (green = heard exactly
the intended words; the lighter second line is a second model). Yellow rows are judgement calls worth
a listen. A name in parentheses on the card is read alone.</p>
<div class="wrap"><table>
<thead><tr><th>#</th><th>player</th><th>name clip</th><th>match clip</th><th>listen for</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table></div>
<script>
document.addEventListener('play', e => {{
  document.querySelectorAll('audio').forEach(a => {{ if (a !== e.target) a.pause(); }});
}}, true);
</script>
</body>
</html>
"""
    (TTS / "listen.html").write_text(page, encoding="utf-8")
    print(f"[listen] wrote {TTS / 'listen.html'}: {n} players, {len(man)} clips", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pron", required=True, help="the club's pronunciations.json")
    ap.add_argument("--players", help="default <root>/data/players.json")
    a = ap.parse_args()
    main(players_path=a.players, pron_path=a.pron)
