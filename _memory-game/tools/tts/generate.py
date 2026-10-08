"""Generate a memory game's voice clips (D6 audio contract, H4/H7).

    _memory-game/tools/tts/tts.sh <game> <work> generate [options]     # the usual way
    <engines>/.venv-stt/bin/python -u _memory-game/tools/tts/generate.py --game <game> --work <work> [options]

Reads <work>/data/players.json (role starter|bench) and the club's pronunciations.json.
The voice reads each player's `speak_he`: the text inside a trailing "(...)"
of the displayed name when there is one, else the full name (HR3/H4). Every
clip is rendered with several seeds; the take whose ivrit.ai STT round-trip
matches best is kept, then trimmed / normalized / encoded to MP3, and the
final MP3 is checked again. Writes:

    <out>/audio/name/<id>.mp3     speak_he
    <out>/audio/match/<id>.mp3    "מספר <N in words>, <speak_he>!"
    <out>/audio/ui/start.mp3      "יאללה, בואי נשחק!"  (only with --ui)
    <out>/audio/ui/win.mp3        "כל הכבוד! מצאת את כל השחקנים!"  (only with --ui)
    <out>/manifest.json           [{id, kind, text, engine_input, file, duration_ms,
                                    stt_transcript, stt_ok}]
    <out>/TTS_READY               only with --ready, and only when every clip exists
    tts/qa/<run>.json             per-clip details: takes, scores, loudness, onset
    tts/listen.html               one row per player, for listening by ear

Options:
    --game DIR            the game folder; implies --pron DIR/tools/tts/pronunciations.json
    --work DIR            the work directory (data/, tts/); see config.py for the environment variables
    --tts-home DIR        work/, qa/ and out/ (default <work>/tts)
    --engines DIR         the engine install (default: config.py's lookup)
    --pron FILE           the club's pronunciations.json (when there is no --game)
    --engine blue|piper|say  acoustic model (default blue = BlueTTS 2.5; piper = Phonikud +
                          Piper, needs --phonemes-from; say = macOS Carmit, no pronunciation control)
    --voice NAME          default noa / shaul / Carmit per engine (`female` is refused, see tts.md)
    --takes N             seeds per clip (default 8)
    --speed X             pace; BlueTTS speed, Piper length_scale = 1/X (default 0.88)
    --only ID,ID          only these ids (merged into an existing manifest; ui clips: start,win)
    --stale               only the ids whose clips are missing or no longer match the roster and the
                          pronunciations (each manifest row records what it was rendered from)
    --ui                  also the start and win clips
    --phonemes-from FILE  reuse engine_input IPA from another manifest (identical pronunciation
                          across engines, for comparison samples)
    --out DIR             default tts/out
    --second-opinion      also transcribe final clips with ivrit large-v3 on faster-whisper
    --ready               write TTS_READY when every expected clip exists
    --players FILE        default <work>/data/players.json
    --run-name NAME       work/qa folder name (default <engine>-<voice>-<timestamp>)

pronunciations.json, one per club (<game>/tools/tts/), the only schema:
    {"players": {"<players.json id>": {
        "ipa": "...",           fed to BlueTTS verbatim (RenikudPlus IPA: ˈ before the stressed vowel,
                                ʁ χ ʔ ts dʒ tʃ). It spells speak_he (the text inside a trailing
                                parenthetical, else the full name), in the name clip and inside the match
                                clip, so the two always sound alike.
        "g2p": "...",           what RenikudPlus made of the bare speak_he, kept to show what changed
        "why": "...",           why the pin differs from g2p
        "stt_variants": [...],  spellings the STT check accepts as the same pronunciation; never one
                                that implies a different sound
        "stt_text": "...",      optional: the STT target when the intended pronunciation is spelled
                                differently from the card (the clip's text stays speak_he)
        "ipa_match": "...",     optional: the same pronunciation nudged for the match clip only
        "speed": 0.95,          optional: this player's pace (BlueTTS divides the duration by it)
        "listen": "..."}}}      optional: a judgement call worth a listen; listen.html highlights it
A player missing from the file is read by RenikudPlus G2P from speak_he and flagged in the QA report.
"""
from __future__ import annotations

import os
import sys

# The venvs may belong to another project (setup.sh can reuse an existing
# install): never write bytecode into them, and never let the Hugging Face client
# fetch a newer model revision mid-project. Set before anything else is imported.
sys.dont_write_bytecode = True
os.environ.update(PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1")

import argparse  # noqa: E402
import json  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audio_metrics  # noqa: E402
import config  # noqa: E402
import hebrew  # noqa: E402
import stt  # noqa: E402

RENDER = {"blue": HERE / "render_blue.py", "piper": HERE / "render_piper.py", "say": HERE / "render_say.py"}
DEFAULT_VOICE = {"blue": "noa", "piper": "shaul", "say": "Carmit"}
# Set by configure(): the work directory, the tts home (work/, qa/, out/) and the engine install.
ROOT = TTS = ENGINES = None
VENV: dict = {}
CHILD_ENV: dict = {}


def configure(work: str | None = None, tts_home: str | None = None, engines: str | None = None) -> None:
    global ROOT, TTS, ENGINES, VENV, CHILD_ENV
    ROOT = config.work_dir(work)
    TTS = config.tts_home(ROOT, tts_home)
    ENGINES = config.engines_home(engines, TTS)
    VENV = {"blue": ENGINES / ".venv-blue/bin/python", "piper": ENGINES / ".venv-phonikud/bin/python",
            "say": Path(sys.executable)}
    CHILD_ENV = {**os.environ, "MEMORY_GAME_TTS_ENGINES": str(ENGINES)}

# BlueTTS starts at sample 0 and squeezes the first phoneme ("סגיב" came back
# "תגיב" on every voice). A leading comma gives it a beat to start on; the
# silence it adds is trimmed away below. Measured: noa 12/27 → 18/27 names.
LEAD_IN = ","
LEAD_KEEP_S = 0.015      # silence kept before the first speech frame (≤ 30 ms spec)
TAIL_KEEP_S = 0.090      # kept after the last speech frame (≤ 120 ms spec)
TARGET_LUFS = -16.0
LIMIT_DBTP = -1.8        # limiter ceiling; leaves margin for the -1.5 dBTP spec after MP3
OUT_SR = 24000
STT_BATCH = 48           # raw takes per whisper-cli process (progress granularity)


def log(*a):
    print(*a, flush=True)


def display_name(p: dict) -> str:
    return p.get("name_he") or p["name"]


def speak_he(p: dict) -> str:
    """players.json's `speak_he` when present, else the H4 rule applied to the name."""
    return (p.get("speak_he") or hebrew.speak_text(display_name(p))).strip()


def check_speak(players: list[dict]) -> None:
    for p in players:
        if p.get("role") not in ("starter", "bench"):
            continue
        rule = hebrew.speak_text(display_name(p))
        if p.get("speak_he") and p["speak_he"].strip() != rule:
            log(f"[gen] WARNING {p['id']}: players.json speak_he «{p['speak_he']}» "
                f"differs from the parentheses rule «{rule}»; using players.json")
        if p.get("number") is None:
            log(f"[gen] WARNING {p['id']}: no shirt number, the match clip will say the name only")


def build_items(players: list[dict], pron: dict, only: set[str] | None, ui: bool = False) -> list[dict]:
    items = []
    for p in players:
        if p.get("role") not in ("starter", "bench"):
            continue
        if only and p["id"] not in only:
            continue
        e = pron["players"].get(p["id"], {})
        say = speak_he(p)
        # stt_text: how the STT should spell the intended pronunciation when it
        # deliberately differs from the card's spelling (e.g. the club's חורה said
        # as the media's גורה). The clip's `text` stays speak_he.
        expect = e.get("stt_text", say)
        ipa = e.get("ipa")
        # ipa_match: the same pronunciation nudged for the match context (e.g. a vowel
        # length that one clip needs); the name clip, heard on every flip, uses `ipa`.
        ipa_m = e.get("ipa_match", ipa)
        var = e.get("stt_variants", [])
        num = p.get("number")
        words = hebrew.number_words_fem(num) if num is not None else None
        name = [{"ipa": ipa + "."}] if ipa else [{"text": say + "."}]
        name_job = {"parts": [{"ipa": LEAD_IN}] + name}
        lead = [{"text": f"מספר {words},"}] if words else []
        match_job = {"parts": [{"ipa": LEAD_IN}] + lead +
                     ([{"ipa": ipa_m + "!"}] if ipa_m else [{"text": say + "!"}])}
        common = {"id": p["id"], "display": display_name(p), "speak": say, "number": num,
                  "pinned": bool(ipa), "speed": e.get("speed")}
        items.append({**common, "kind": "name", "text": say, "expect": expect, "variants": var,
                      "job": name_job})
        items.append({**common, "kind": "match", "text": hebrew.match_text(num, say),
                      "expect": hebrew.match_text(num, expect),
                      "variants": [hebrew.match_text(num, v) for v in var], "job": match_job})
    for uid, text in (("start", hebrew.START_TEXT), ("win", hebrew.WIN_TEXT)) if ui else ():
        if only and uid not in only:
            continue
        # target_speaker 2: the G2P's female-listener forms (בואי, מָצָאת).
        items.append({"id": uid, "kind": "ui", "display": text, "speak": text, "number": None, "pinned": True,
                      "speed": None, "text": text, "expect": text, "variants": [],
                      "job": {"parts": [{"ipa": LEAD_IN}, {"text": text}], "target_speaker": 2}})
    return items


def rel_file(it: dict) -> str:
    return f"audio/{it['kind']}/{it['id']}.mp3"


def render(engine: str, voice: str, items: list[dict], takes: int, speed: float, work: Path,
           phonemes_from: dict | None = None) -> None:
    jobs = []
    for it in items:
        for s in range(1, takes + 1):
            sp = it.get("speed") or speed  # pronunciations.json may pace a long name faster
            j = {"key": f"{it['kind']}__{it['id']}__s{s}", "seed": s, "voice": voice}
            src = dict(it["job"])
            if phonemes_from and (it["id"], it["kind"]) in phonemes_from:
                src = {"phonemes": phonemes_from[(it["id"], it["kind"])]}
            if engine == "blue":
                j.update(src, speed=sp, steps=24, cfg=4.0)
            elif engine == "say":
                j.update(text=it["text"], rate=round(175 * sp))
            else:
                if "phonemes" not in src:
                    raise SystemExit("piper runs need --phonemes-from (shared IPA) in this pipeline")
                j.update(src, length_scale=round(1.0 / sp, 3), noise_scale=0.6, noise_w=0.7)
            jobs.append(j)
    spec = work / "jobs.json"
    json.dump({"out_dir": str(work / "raw"), "jobs": jobs}, open(spec, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    log(f"[gen] rendering {len(jobs)} takes with {engine}/{voice} ({ENGINES})...")
    p = subprocess.Popen([str(VENV[engine]), "-u", str(RENDER[engine]), str(spec)],
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=CHILD_ENV)
    tail, done = [], 0
    for ln in p.stdout:
        tail = (tail + [ln.rstrip()])[-40:]
        if ln.startswith(f"[{engine}] loaded"):
            log("   ", ln.rstrip())
        elif ln.startswith(f"[{engine}] "):
            done += 1
            if done % 25 == 0 or done == len(jobs):
                log(f"    rendered {done}/{len(jobs)}")
    if p.wait():
        log("\n".join(tail))
        raise SystemExit(f"renderer failed ({p.returncode})")


def transcribe(paths: list[str], label: str) -> dict[str, dict]:
    res = {}
    for i in range(0, len(paths), STT_BATCH):
        for r in stt.transcribe(paths[i:i + STT_BATCH]):
            res[r["file"]] = r
        log(f"    {label} STT {min(i + STT_BATCH, len(paths))}/{len(paths)}")
    return res


def pick_takes(items: list[dict], takes: int, work: Path) -> None:
    paths = [str(work / "raw" / f"{it['kind']}__{it['id']}__s{s}.wav")
             for it in items for s in range(1, takes + 1)]
    log(f"[gen] STT on {len(paths)} raw takes...")
    res = transcribe(paths, "raw")
    for it in items:
        cands = []
        for s in range(1, takes + 1):
            f = str(work / "raw" / f"{it['kind']}__{it['id']}__s{s}.wav")
            r = res[f]
            ok, how = hebrew.compare(it["expect"], r["text"], it["variants"])
            meta = json.load(open(f[:-4] + ".json", encoding="utf-8"))
            dur = audio_metrics.measure(f)["speech_ms"]
            cands.append({"seed": s, "file": f, "heard": r["text"], "ok": ok, "how": how,
                          "mean_p": r["mean_p"], "min_p": r["min_p"], "speech_ms": dur,
                          "sim": round(hebrew.similarity(it["expect"], r["text"]), 3),
                          "engine_input": meta.get("phonemes_used") or meta.get("phonemes")})
        best = max(cands, key=take_rank)
        it["takes"], it["best"] = cands, best


def take_rank(c: dict) -> tuple:
    """Prefer a clean round-trip, then the model's confidence, then the weakest syllable."""
    return (c["ok"], round(c["mean_p"], 2), c["min_p"], c["sim"])


def passes(it: dict, r: dict) -> bool:
    return hebrew.compare(it["expect"], r["text"], it["variants"])[0]


def settle(it: dict, dst: Path, fw_model, cur_ok1: bool) -> tuple[dict, dict | None] | None:
    """The chosen take's final MP3 fails the primary STT, or the second model disagrees.

    Trimming and encoding can tip a borderline take (Silva Kani: "סילבא קאני" as a raw
    WAV, "סילבקני" as the MP3), so the decision is made on final MP3s. The other takes
    that passed raw are tried best first; the first whose MP3 passes both models (or the
    primary alone, without --second-opinion) is left in place and its (primary, second)
    results returned. When none passes both, a primary-only pass replaces a primary
    failure; otherwise the original take is restored and None returned.
    """
    orig, fallback = it["best"], None
    for c in sorted((c for c in it["takes"] if c["ok"] and c is not orig), key=take_rank, reverse=True):
        final = finalize(c["file"], dst)
        r1 = stt.transcribe([str(dst)])[0]
        if not passes(it, r1):
            continue
        r2 = None
        if fw_model is not None:
            import stt_fw
            r2 = stt_fw.transcribe([str(dst)], fw_model)[0]
        if r2 is None or passes(it, r2):
            log(f"    {it['kind']} {it['id']}: seed {orig['seed']} -> seed {c['seed']}, "
                f"final MP3 heard «{r1['text']}»" + (f" / «{r2['text']}»" if r2 else ""))
            it["best"], it["final"] = c, final
            return r1, r2
        if fallback is None:
            fallback = (c, r1, r2)
    if not cur_ok1 and fallback:
        c, r1, r2 = fallback
        it["best"], it["final"] = c, finalize(c["file"], dst)
        log(f"    {it['kind']} {it['id']}: seed {orig['seed']} -> seed {c['seed']} (primary passes; "
            f"second model still hears «{r2['text']}»)")
        return r1, r2
    it["final"] = finalize(orig["file"], dst)
    log(f"    {it['kind']} {it['id']}: kept seed {orig['seed']}; no other take "
        + ("passes both models" if cur_ok1 else "passes once encoded"))
    return None


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


def source(it: dict, engine: str, voice: str, speed: float) -> dict:
    """What a clip is rendered from; a manifest row whose source differs is stale."""
    return {"job": it["job"], "engine": engine, "voice": voice, "speed": it.get("speed") or speed}


def stale_ids(items: list[dict], manifest: list[dict], out: Path, engine: str, voice: str, speed: float) -> list[str]:
    """Ids with a clip that is missing, or whose manifest row was made from other text or input. A row
    from before rows recorded their source is judged by its text and, for a pinned name, its IPA."""
    rows = {(m["id"], m["kind"]): m for m in manifest}
    stale = []
    for it in items:
        m = rows.get((it["id"], it["kind"]))
        if m is None or not (out / m["file"]).exists() or m["text"] != it["text"]:
            fresh = False
        elif "source" in m:
            fresh = m["source"] == source(it, engine, voice, speed)
        else:
            pin = it["job"]["parts"][-1].get("ipa")
            fresh = pin is None or m["engine_input"].endswith(pin)
        if not fresh and it["id"] not in stale:
            stale.append(it["id"])
    return stale


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--game")
    ap.add_argument("--work")
    ap.add_argument("--tts-home")
    ap.add_argument("--engines")
    ap.add_argument("--pron")
    ap.add_argument("--engine", default="blue", choices=["blue", "piper", "say"])
    ap.add_argument("--voice")
    ap.add_argument("--takes", type=int, default=8)
    ap.add_argument("--speed", type=float, default=0.88)
    ap.add_argument("--only")
    ap.add_argument("--stale", action="store_true")
    ap.add_argument("--ui", action="store_true")
    ap.add_argument("--phonemes-from")
    ap.add_argument("--out")
    ap.add_argument("--second-opinion", action="store_true")
    ap.add_argument("--ready", action="store_true")
    ap.add_argument("--run-name")
    ap.add_argument("--players")
    args = ap.parse_args()
    configure(args.work, args.tts_home, args.engines)
    if args.game:
        args.pron = args.pron or str(config.game_dir(args.game) / "tools/tts/pronunciations.json")
    if not args.pron:
        ap.error("pass --game <folder> (or --pron <pronunciations.json>)")
    args.players = args.players or str(ROOT / "data/players.json")
    voice = args.voice or DEFAULT_VOICE[args.engine]
    if args.engine == "blue" and voice == "female":
        raise SystemExit("BlueTTS's `female` voice is not to be shipped (its model card: check rights first)")
    only = set(args.only.split(",")) if args.only else None
    out = Path(args.out) if args.out else TTS / "out"

    roster = json.load(open(args.players, encoding="utf-8"))["players"]
    pron = json.load(open(args.pron, encoding="utf-8"))
    if args.stale:
        man_path = out / "manifest.json"
        current = json.load(open(man_path, encoding="utf-8")) if man_path.exists() else []
        ids = stale_ids(build_items(roster, pron, only, args.ui), current, out, args.engine, voice, args.speed)
        if not ids:
            log(f"[gen] nothing stale in {out}")
            return
        log(f"[gen] stale: {', '.join(ids)}")
        only = set(ids)
    run = args.run_name or f"{args.engine}-{voice}-{time.strftime('%Y%m%d-%H%M%S')}"
    work = TTS / "work" / run
    (work / "raw").mkdir(parents=True, exist_ok=True)
    check_speak(roster)
    items = build_items(roster, pron, only, args.ui)
    if not items:
        raise SystemExit("nothing to render (no starter/bench players matched)")
    log(f"[gen] {len(items)} clips -> {out} (run {run})")
    for it in items:
        if it["kind"] == "name" and not it["pinned"]:
            log(f"[gen] note: {it['id']} has no pinned IPA; RenikudPlus G2P reads «{it['speak']}»")
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
    fin = transcribe(finals, "final")
    fw, fw_model = {}, None
    if args.second_opinion:
        import stt_fw
        log("[gen] second opinion (ivrit large-v3, faster-whisper)...")
        fw_model = stt_fw.load()
    for i, (it, f) in enumerate(zip(items, finals), 1):
        r2 = None
        if fw_model is not None:
            r2 = stt_fw.transcribe([f], fw_model)[0]
        ok1 = passes(it, fin[f])
        if not ok1 or (r2 is not None and not passes(it, r2)):
            got = settle(it, Path(f), fw_model, ok1)
            if got:
                fin[f], r2 = got
        if r2 is not None:
            fw[f] = r2
        if fw_model is not None and (i % 10 == 0 or i == len(finals)):
            log(f"    second opinion {i}/{len(finals)}")

    man_path = out / "manifest.json"
    manifest = json.load(open(man_path, encoding="utf-8")) if man_path.exists() else []
    index = {(m["id"], m["kind"]): m for m in manifest}
    qa = []
    for it, f in zip(items, finals):
        r = fin[f]
        ok, how = hebrew.compare(it["expect"], r["text"], it["variants"])
        row = {"id": it["id"], "kind": it["kind"], "text": it["text"],
               "engine_input": it["best"]["engine_input"], "file": rel_file(it),
               "duration_ms": it["final"]["duration_ms"], "stt_transcript": r["text"], "stt_ok": ok,
               "source": source(it, args.engine, voice, args.speed)}
        index[(it["id"], it["kind"])] = row
        q = {**row, "display_name": it["display"], "speak_he": it["speak"], "number": it["number"],
             "stt_expected": it["expect"], "match_how": how, "mean_p": r["mean_p"], "min_p": r["min_p"],
             "engine": args.engine, "voice": voice, "seed": it["best"]["seed"],
             "speed": it.get("speed") or args.speed,
             "pinned_ipa": it["pinned"], "lead_ms": it["final"]["lead_ms"],
             "trail_ms": it["final"]["trail_ms"], "lufs": it["final"]["lufs"],
             "tp_db": it["final"]["tp_db"], "f0_med": it["final"]["f0_med"],
             "f0_st": it["final"]["f0_st"],
             "takes": [{k: c[k] for k in ("seed", "heard", "ok", "mean_p", "min_p", "speech_ms")}
                       for c in it["takes"]]}
        if f in fw:
            ok2, _ = hebrew.compare(it["expect"], fw[f]["text"], it["variants"])
            q.update(stt2_transcript=fw[f]["text"], stt2_ok=ok2, stt2_mean_p=fw[f]["mean_p"])
        qa.append(q)

    # Keep only rows for the current roster (a re-scrape can drop players); ui rows aren't tied to it.
    expected = {(it["id"], it["kind"]) for it in build_items(roster, pron, None, args.ui)}
    keep = expected | {k for k in index if k[1] == "ui"}
    order = {"name": 0, "match": 1, "ui": 2}
    roster_ids = [p["id"] for p in roster]
    manifest = sorted((m for k, m in index.items() if k in keep), key=lambda m: (
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
        log(f"  {flag}{q['kind']:5s} {q['id']:24s} {q['duration_ms']:5d}ms lead {q['lead_ms']:3d} "
            f"tail {q['trail_ms']:3d} {q['lufs']:6.1f}LUFS tp {q['tp_db']:5.1f} p={q['mean_p']:.2f} "
            f"«{q['stt_transcript']}»{extra}")
    if out.resolve() == (TTS / "out").resolve():
        import make_listen
        make_listen.main(players_path=args.players, pron_path=args.pron, tts=TTS)
    have = {(m["id"], m["kind"]) for m in manifest if (out / m["file"]).exists()}
    if args.ready:
        if expected <= have:
            (out / "TTS_READY").write_text(time.strftime("%Y-%m-%d %H:%M:%S\n"))
            log(f"[gen] wrote {out / 'TTS_READY'}")
        else:
            log(f"[gen] NOT writing TTS_READY: missing {sorted(expected - have)}")


if __name__ == "__main__":
    main()
