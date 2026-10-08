"""Generate the Maccabi memory-game voice clips (D6 audio contract).

    <work>/tts/.venv-stt/bin/python generate.py --work <work> [options]

<work> is the work directory (from --work, else $MACCABI_WORK, else the current
directory): it holds data/players.json from the scrape and tts/ from setup.sh.
Reads <work>/data/players.json (role starter|bench) and pronunciations.json,
renders every clip with several seeds, keeps the take whose ivrit.ai STT
round-trip matches best, then trims / normalizes / encodes to MP3 and verifies
the final MP3 again. Writes:

    <out>/audio/name/<id>.mp3     the player's name
    <out>/audio/match/<id>.mp3    "מספר <N in words>, <name>!"
    <out>/audio/ui/start.mp3      "יאללה, בואי נשחק!"
    <out>/audio/ui/win.mp3        "כל הכבוד! מצאת את כל השחקנים!"
    <out>/manifest.json           [{id, kind, text, engine_input, file, duration_ms,
                                    stt_transcript, stt_ok}]
    <out>/TTS_READY               when every clip exists (even if some fail STT)
    tts/qa/<run>.json             per-clip details: takes, scores, loudness, onset

Options:
    --engine blue|piper|say  acoustic model (default blue = BlueTTS 2.5; say = macOS Carmit)
    --voice NAME          BlueTTS: noa lily adam daniel female libri_*; Piper: shaul michael model
    --takes N             seeds per clip (default 4)
    --speed X             pace; BlueTTS speed, Piper length_scale = 1/X (default 0.88)
    --only ID,ID          only these player ids (ui clips are skipped unless listed: start,win)
    --work DIR            work directory (default $MACCABI_WORK or the current directory)
    --out DIR             default <work>/tts/out
    --phonemes-from FILE  reuse engine_input IPA from another manifest (identical pronunciation
                          across engines, for the comparison samples)
    --second-opinion      also transcribe final clips with ivrit large-v3 on faster-whisper
    --no-ready            do not write TTS_READY
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(1, str(HERE.parents[2] / "_memory-game/tools/tts"))  # stt, stt_fw, audio_metrics
import audio_metrics  # noqa: E402
import hebrew  # noqa: E402
import stt  # noqa: E402

ROOT = TTS = Path()
VENV: dict[str, Path] = {}


def set_work(work: str) -> None:
    """Point every path at <work>; renderer subprocesses inherit it via $MACCABI_WORK."""
    global ROOT, TTS, VENV
    ROOT = Path(work).resolve()
    TTS = ROOT / "tts"
    VENV = {"blue": TTS / ".venv-blue/bin/python", "piper": TTS / ".venv-phonikud/bin/python",
            "say": Path(sys.executable)}
    os.environ["MACCABI_WORK"] = str(ROOT)


RENDER = {"blue": HERE / "render_blue.py", "piper": HERE / "render_piper.py",
          "say": HERE / "render_say.py"}
DEFAULT_VOICE = {"blue": "noa", "piper": "shaul", "say": "Carmit"}

# BlueTTS starts at sample 0 and squeezes the first phoneme ("סגיב" came back
# "תגיב" on every voice). A leading comma gives it a beat to start on; the
# silence it adds is trimmed away below. Measured: noa 12/27 → 18/27 names.
LEAD_IN = ","
LEAD_KEEP_S = 0.015      # silence kept before the first speech frame (≤ 30 ms spec)
TAIL_KEEP_S = 0.090      # kept after the last speech frame (≤ 120 ms spec)
TARGET_LUFS = -16.0
LIMIT_DBTP = -1.8        # limiter ceiling; leaves margin for the -1.5 dBTP spec after MP3
OUT_SR = 24000


def log(*a):
    print(*a, flush=True)


def build_items(players: list[dict], pron: dict, only: set[str] | None) -> list[dict]:
    items = []
    for p in players:
        if p.get("role") not in ("starter", "bench"):
            continue
        if only and p["id"] not in only:
            continue
        e = pron["players"].get(p["id"], {})
        ipa = e.get("ipa")
        var = e.get("stt_variants", [])
        words = hebrew.number_words_fem(p["number"]) if p.get("number") is not None else None
        name = [{"ipa": ipa + "."}] if ipa else [{"text": p["name_he"] + "."}]
        name_job = {"parts": [{"ipa": LEAD_IN}] + name}
        lead = [{"text": f"מספר {words},"}] if words else []
        match_job = {"parts": [{"ipa": LEAD_IN}] + lead +
                     ([{"ipa": ipa + "!"}] if ipa else [{"text": p["name_he"] + "!"}])}
        items.append({"id": p["id"], "kind": "name", "text": p["name_he"], "variants": var,
                      "job": name_job, "pinned": bool(ipa), "speed": e.get("speed")})
        items.append({"id": p["id"], "kind": "match", "text": hebrew.match_text(p.get("number"), p["name_he"]),
                      "variants": [hebrew.match_text(p.get("number"), v) for v in var],
                      "job": match_job, "pinned": bool(ipa), "speed": e.get("speed")})
    for uid, text in (("start", hebrew.START_TEXT), ("win", hebrew.WIN_TEXT)):
        if only and uid not in only:
            continue
        items.append({"id": uid, "kind": "ui", "text": text, "variants": [],
                      "job": {"parts": [{"ipa": LEAD_IN}, {"text": text}], "target_speaker": 2},
                      "pinned": True})
    return items


def rel_file(it: dict) -> str:
    sub = "ui" if it["kind"] == "ui" else it["kind"]
    return f"audio/{sub}/{it['id']}.mp3"


def render(engine: str, voice: str, items: list[dict], takes: int, speed: float, work: Path,
           phonemes_from: dict | None) -> None:
    jobs = []
    for it in items:
        for s in range(1, takes + 1):
            j = {"key": f"{it['kind']}__{it['id']}__s{s}", "seed": s, "voice": voice}
            src = dict(it["job"])
            if phonemes_from and (it["id"], it["kind"]) in phonemes_from:
                src = {"phonemes": phonemes_from[(it["id"], it["kind"])]}
            sp = it.get("speed") or speed  # pronunciations.json may pace a long name faster
            if engine == "blue":
                j.update(src, speed=sp, steps=24, cfg=4.0)
            elif engine == "say":
                j.update(text=it["text"], rate=round(175 * sp))
            else:
                if "parts" in src or "phonemes" not in src:
                    raise SystemExit("piper runs need --phonemes-from (shared IPA) in this pipeline")
                j.update(src, length_scale=round(1.0 / sp, 3), noise_scale=0.6, noise_w=0.7)
            jobs.append(j)
    spec = work / "jobs.json"
    json.dump({"out_dir": str(work / "raw"), "jobs": jobs}, open(spec, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    log(f"[gen] rendering {len(jobs)} takes with {engine}/{voice}...")
    p = subprocess.run([str(VENV[engine]), "-u", str(RENDER[engine]), str(spec)],
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines = [ln for ln in p.stdout.splitlines() if ln.startswith("[")]
    for ln in lines[-3:]:
        log("   ", ln)
    if p.returncode:
        log(p.stdout[-3000:])
        raise SystemExit(f"renderer failed ({p.returncode})")


def pick_takes(items: list[dict], takes: int, work: Path) -> None:
    paths = [str(work / "raw" / f"{it['kind']}__{it['id']}__s{s}.wav")
             for it in items for s in range(1, takes + 1)]
    log(f"[gen] STT on {len(paths)} raw takes...")
    res = {r["file"]: r for r in stt.transcribe(paths)}
    for it in items:
        cands = []
        for s in range(1, takes + 1):
            f = str(work / "raw" / f"{it['kind']}__{it['id']}__s{s}.wav")
            r = res[f]
            ok, how = hebrew.compare(it["text"], r["text"], it["variants"])
            meta = json.load(open(f[:-4] + ".json", encoding="utf-8"))
            dur = audio_metrics.measure(f)["speech_ms"]
            cands.append({"seed": s, "file": f, "heard": r["text"], "ok": ok, "how": how,
                          "mean_p": r["mean_p"], "min_p": r["min_p"], "speech_ms": dur,
                          "sim": round(hebrew.similarity(it["text"], r["text"]), 3),
                          "engine_input": meta.get("phonemes_used") or meta.get("phonemes")})
        # Prefer a clean round-trip, then the model's confidence, then the weakest syllable.
        best = max(cands, key=lambda c: (c["ok"], round(c["mean_p"], 2), c["min_p"], c["sim"]))
        it["takes"], it["best"] = cands, best


LEAD_MIN_S = 0.010       # BlueTTS starts at sample 0; a few ms keep a plosive onset intact
TAIL_MIN_S = 0.060       # and it stops right after the last phoneme; let the release ring


def finalize(src: str, dst: Path) -> dict:
    """Trim/pad to the speech region, normalize, limit, encode MP3 (mono 24 kHz, 64 kbps CBR)."""
    sr = 48000
    x = audio_metrics.load_mono(src, sr)
    s, e = audio_metrics.speech_bounds(x, sr, rel_db=45.0, floor_db=-60.0, win_ms=5.0)
    a, b = max(0, s - int(LEAD_KEEP_S * sr)), min(len(x), e + int(TAIL_KEEP_S * sr))
    pre = np.zeros(max(0, int(LEAD_MIN_S * sr) - (s - a)), np.float32)
    post = np.zeros(max(0, int(TAIL_MIN_S * sr) - (b - e)), np.float32)
    y = np.concatenate([pre, x[a:b], post])
    fi, fo = len(pre) + int(0.003 * sr), len(post) + int(0.012 * sr)
    y[:fi] *= np.linspace(0, 1, fi, dtype=np.float32)
    y[-fo:] *= np.linspace(1, 0, fo, dtype=np.float32)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        raw, comp = os.path.join(td, "y.f32"), os.path.join(td, "c.wav")
        y.astype(np.float32).tofile(raw)
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
             "-f", "f32le", "-ar", str(sr), "-ac", "1", "-i", raw,
             "-af", "acompressor=threshold=0.1:ratio=2.5:attack=3:release=60:makeup=1",
             "-c:a", "pcm_f32le", comp], check=True)
        lufs, _ = audio_metrics.loudness(comp)
        gain = TARGET_LUFS - lufs
        lim = 10 ** (LIMIT_DBTP / 20)
        for _ in range(3):  # the limiter eats a little loudness; correct and re-encode
            subprocess.run(
                ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", comp, "-af",
                 f"volume={gain:.2f}dB,aresample=96000,"
                 f"alimiter=limit={lim:.4f}:attack=0.5:release=40:level=false,"
                 f"aresample={OUT_SR}",
                 "-ac", "1", "-ar", str(OUT_SR), "-c:a", "libmp3lame", "-b:a", "64k",
                 str(dst)], check=True)
            got, _ = audio_metrics.loudness(str(dst))
            if abs(got - TARGET_LUFS) <= 0.3:
                break
            gain += TARGET_LUFS - got
    return audio_metrics.measure(str(dst))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", default="blue", choices=["blue", "piper", "say"])
    ap.add_argument("--voice")
    ap.add_argument("--takes", type=int, default=4)
    ap.add_argument("--speed", type=float, default=0.88)
    ap.add_argument("--only")
    ap.add_argument("--work", default=os.environ.get("MACCABI_WORK", "."))
    ap.add_argument("--out")
    ap.add_argument("--phonemes-from")
    ap.add_argument("--second-opinion", action="store_true")
    ap.add_argument("--no-ready", action="store_true")
    ap.add_argument("--run-name")
    args = ap.parse_args()
    set_work(args.work)
    voice = args.voice or DEFAULT_VOICE[args.engine]
    only = set(args.only.split(",")) if args.only else None
    out = Path(args.out) if args.out else TTS / "out"
    run = args.run_name or f"{args.engine}-{voice}-{time.strftime('%Y%m%d-%H%M%S')}"
    work = TTS / "work" / run
    (work / "raw").mkdir(parents=True, exist_ok=True)

    roster = json.load(open(ROOT / "data/players.json", encoding="utf-8"))["players"]
    pron = json.load(open(HERE / "pronunciations.json", encoding="utf-8"))
    items = build_items(roster, pron, only)
    log(f"[gen] {len(items)} clips -> {out} (run {run})")
    phon = None
    if args.phonemes_from:
        phon = {(m["id"], m["kind"]): m["engine_input"]
                for m in json.load(open(args.phonemes_from, encoding="utf-8"))}

    t0 = time.time()
    render(args.engine, voice, items, args.takes, args.speed, work, phon)
    pick_takes(items, args.takes, work)

    log("[gen] finalizing MP3s...")
    for it in items:
        it["final"] = finalize(it["best"]["file"], out / rel_file(it))
    finals = [str(out / rel_file(it)) for it in items]
    log("[gen] STT on final MP3s...")
    fin = {r["file"]: r for r in stt.transcribe(finals)}
    fw = {}
    if args.second_opinion:
        import stt_fw
        log("[gen] second opinion (ivrit large-v3, faster-whisper)...")
        model = stt_fw.load()
        for f in finals:
            fw[f] = stt_fw.transcribe([f], model)[0]

    man_path = out / "manifest.json"
    manifest = json.load(open(man_path, encoding="utf-8")) if man_path.exists() else []
    index = {(m["id"], m["kind"]): m for m in manifest}
    qa = []
    for it, f in zip(items, finals):
        r = fin[f]
        ok, how = hebrew.compare(it["text"], r["text"], it["variants"])
        row = {"id": it["id"], "kind": it["kind"], "text": it["text"],
               "engine_input": it["best"]["engine_input"], "file": rel_file(it),
               "duration_ms": it["final"]["duration_ms"], "stt_transcript": r["text"], "stt_ok": ok}
        index[(it["id"], it["kind"])] = row
        q = {**row, "match_how": how, "mean_p": r["mean_p"], "min_p": r["min_p"],
             "engine": args.engine, "voice": voice, "seed": it["best"]["seed"],
             "pinned_ipa": it["pinned"], "lead_ms": it["final"]["lead_ms"],
             "trail_ms": it["final"]["trail_ms"], "lufs": it["final"]["lufs"],
             "tp_db": it["final"]["tp_db"], "f0_med": it["final"]["f0_med"],
             "f0_st": it["final"]["f0_st"],
             "takes": [{k: c[k] for k in ("seed", "heard", "ok", "mean_p", "min_p", "speech_ms")}
                       for c in it["takes"]]}
        if f in fw:
            ok2, _ = hebrew.compare(it["text"], fw[f]["text"], it["variants"])
            q.update(stt2_transcript=fw[f]["text"], stt2_ok=ok2, stt2_mean_p=fw[f]["mean_p"])
        qa.append(q)

    order = {"name": 0, "match": 1, "ui": 2}
    roster_ids = [p["id"] for p in roster]
    manifest = sorted(index.values(), key=lambda m: (
        order[m["kind"]], roster_ids.index(m["id"]) if m["id"] in roster_ids else 99))
    out.mkdir(parents=True, exist_ok=True)
    json.dump(manifest, open(man_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    (TTS / "qa").mkdir(exist_ok=True)
    json.dump(qa, open(TTS / "qa" / f"{run}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    n_ok = sum(q["stt_ok"] for q in qa)
    log(f"\n[gen] {n_ok}/{len(qa)} clips pass the STT round-trip ({time.time() - t0:.0f}s)")
    for q in qa:
        flag = "ok " if q["stt_ok"] else "XX "
        extra = f" | fw «{q['stt2_transcript']}»" if "stt2_transcript" in q else ""
        log(f"  {flag}{q['kind']:5s} {q['id']:20s} {q['duration_ms']:5d}ms lead {q['lead_ms']:3d} "
            f"tail {q['trail_ms']:3d} {q['lufs']:6.1f}LUFS tp {q['tp_db']:5.1f} p={q['mean_p']:.2f} "
            f"«{q['stt_transcript']}»{extra}")
    expected = {(it["id"], it["kind"]) for it in build_items(roster, pron, None)}
    have = {(m["id"], m["kind"]) for m in manifest if (out / m["file"]).exists()}
    if not args.no_ready and expected <= have:
        (out / "TTS_READY").write_text(time.strftime("%Y-%m-%d %H:%M:%S\n"))
        log(f"[gen] wrote {out / 'TTS_READY'}")


if __name__ == "__main__":
    main()
