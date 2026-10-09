"""Check a game's voice clips against its roster, then copy them into the game.

    _memory-game/tools/tts/tts.sh <game> <work> check
    _memory-game/tools/tts/tts.sh <game> <work> sync

check: every starter/bench/quiz player has a name and a match clip in <tts>/out with a manifest row that
passed the STT round-trip, and each clip is in the format spec (MP3, mono, 24 kHz, 64 kbps; -16 LUFS
±0.4; true peak <= -1.5 dBTP; <= 30 ms of silence before and 120 ms after). Loudness, peak and silence
come from the QA row the clip was made in (re-measured when none matches); a second model's "no"
fails too. Exits 1 on any problem.
sync: check, then copy the roster's clips into <game>/audio/{name,match}/ and delete the clips of
players who are no longer in it. The start and win clips are the engine's (_memory-game/audio/ui/).
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

KINDS = ("name", "match")
FORMAT = ("mp3", 24000, 1, 64000)


def roster_ids(players_path: Path) -> list[str]:
    return [p["id"] for p in json.load(open(players_path, encoding="utf-8"))["players"]
            if p.get("role") in ("starter", "bench", "quiz")]


def qa_rows(tts: Path, rows: dict) -> dict:
    """(id, kind) -> the newest QA row made of exactly the clip the manifest names."""
    found = {}
    for qf in sorted((tts / "qa").glob("*.json"), key=lambda p: p.stat().st_mtime):
        for q in json.load(open(qf, encoding="utf-8")):
            m = rows.get((q.get("id"), q.get("kind")))
            if m and (q["engine_input"], q["duration_ms"], q["stt_transcript"]) == \
                    (m["engine_input"], m["duration_ms"], m["stt_transcript"]):
                found[(q["id"], q["kind"])] = q
    return found


def check(ids: list[str], tts: Path) -> list[str]:
    out = tts / "out"
    man_path = out / "manifest.json"
    if not man_path.exists():
        return [f"no {man_path}: run `tts.sh <game> <work> generate` first"]
    rows = {(m["id"], m["kind"]): m for m in json.load(open(man_path, encoding="utf-8"))}
    qa = qa_rows(tts, rows)
    problems = []
    for pid in ids:
        for kind in KINDS:
            m = rows.get((pid, kind))
            if m is None:
                problems.append(f"{kind} {pid}: no clip")
                continue
            f = out / m["file"]
            if not f.exists():
                problems.append(f"{kind} {pid}: {f} is missing")
                continue
            if not m["stt_ok"]:
                problems.append(f"{kind} {pid}: STT heard «{m['stt_transcript']}»")
            q = qa.get((pid, kind))
            if q is not None and q.get("stt2_ok") is False:
                problems.append(f"{kind} {pid}: the second model heard «{q.get('stt2_transcript')}»")
            if q is None:
                import audio_metrics
                q = audio_metrics.measure(str(f))
            if not -16.4 <= q["lufs"] <= -15.6:
                problems.append(f"{kind} {pid}: loudness {q['lufs']} LUFS")
            if q["tp_db"] > -1.5:
                problems.append(f"{kind} {pid}: true peak {q['tp_db']} dBTP")
            if q["lead_ms"] > 30 or q["trail_ms"] > 120:
                problems.append(f"{kind} {pid}: silence {q['lead_ms']} ms before, {q['trail_ms']} ms after")
            probe = json.loads(subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "stream=codec_name,sample_rate,channels,bit_rate",
                 "-of", "json", str(f)], capture_output=True, text=True, check=True).stdout)["streams"][0]
            got = (probe["codec_name"], int(probe["sample_rate"]), int(probe["channels"]), int(probe["bit_rate"]))
            if got != FORMAT:
                problems.append(f"{kind} {pid}: format {got}")
    return problems


def sync(ids: list[str], tts: Path, game: Path) -> None:
    copied = same = removed = 0
    for kind in KINDS:
        dest = game / "audio" / kind
        dest.mkdir(parents=True, exist_ok=True)
        for pid in ids:
            src, dst = tts / "out/audio" / kind / f"{pid}.mp3", dest / f"{pid}.mp3"
            if dst.exists() and dst.read_bytes() == src.read_bytes():
                same += 1
                continue
            shutil.copyfile(src, dst)
            copied += 1
        for old in sorted(dest.glob("*.mp3")):
            if old.stem not in ids:
                old.unlink()
                removed += 1
                print(f"[sync] removed {old.relative_to(game.parent)}", flush=True)
    print(f"[sync] {game.name}: {copied} clips copied, {same} unchanged, {removed} removed", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=("check", "sync"))
    ap.add_argument("--game", required=True)
    ap.add_argument("--work")
    ap.add_argument("--tts-home")
    a = ap.parse_args()
    game, work = config.game_dir(a.game), config.work_dir(a.work)
    tts = config.tts_home(work, a.tts_home)
    ids = roster_ids(work / "data/players.json")
    problems = check(ids, tts)
    for p in problems:
        print(f"[check] {p}", flush=True)
    print(f"[check] {game.name}: {len(ids)} players, {2 * len(ids)} clips: "
          f"{'OK' if not problems else f'{len(problems)} problems'}", flush=True)
    if problems:
        return 1
    if a.cmd == "sync":
        sync(ids, tts, game)
    return 0


if __name__ == "__main__":
    sys.exit(main())
