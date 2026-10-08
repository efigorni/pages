"""BlueTTS 2.5 (ONNX) renderer — run with <engines>/.venv-blue/bin/python.

<engines> is $MEMORY_GAME_TTS_ENGINES (generate.py sets it), else config.py's
default; see setup.sh. The engine install is only read, never written.

    render_blue.py jobs.json

jobs.json: {"out_dir": str, "jobs": [{key, text? | phonemes? | parts?, voice, speed,
            steps, cfg, seed, speaker?, target_speaker?}]}

`parts` is a list of {"text": ...} (run through G2P) and {"ipa": ...} (used
verbatim), joined with spaces — so a match clip can say the G2P'd number words
and then the exact hand-fixed IPA of the name.

    render_blue.py --g2p "טקסט" [target_speaker]   # print RenikudPlus IPA only
    render_blue.py --g2p-roster players.json [pronunciations.json]
                                                   # every starter/bench name: G2P next to its pin

Hebrew G2P is RenikudPlus. Each job writes <key>.wav (44.1 kHz float→PCM16) and
<key>.json with the exact IPA spoken, so a mispronounced name can be fixed by
editing phonemes instead of guessing at spellings.
"""
from __future__ import annotations

import os
import sys

# The engine install may be shared with another project: write no bytecode into it
# and keep the Hugging Face client on the cached model revisions.
sys.dont_write_bytecode = True
os.environ.update(PYTHONDONTWRITEBYTECODE="1", HF_HUB_OFFLINE="1")

import json  # noqa: E402
import re  # noqa: E402
import time  # noqa: E402
from pathlib import Path  # noqa: E402

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config  # noqa: E402

ROOT = config.engines_home() / "_engines/BlueTTS"
sys.path.insert(0, str(ROOT / "src"))
from blue_onnx import limit_peak, load_text_to_speech, load_voice_style  # noqa: E402

TAG = re.compile(r"</?[a-z]{2}>")


def voice_path(name: str) -> str:
    for p in (ROOT / "voices" / f"{name}.json", ROOT / "onnx_models/voices" / f"{name}.json"):
        if p.exists():
            return str(p)
    raise SystemExit(f"unknown BlueTTS voice: {name}")


def g2p(tts, text: str) -> str:
    return TAG.sub("", tts.g2p.phonemize(text, lang="he")).strip()


def main(spec_path: str) -> None:
    spec = json.load(open(spec_path, encoding="utf-8"))
    out = Path(spec["out_dir"])
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    tts = load_text_to_speech(str(ROOT / "onnx_models"), config_path=str(ROOT / "config/tts.json"))
    styles: dict[str, object] = {}
    jobs = spec["jobs"]
    print(f"[blue] loaded in {time.time() - t0:.1f}s, {len(jobs)} jobs, sr={tts.sample_rate}", flush=True)
    for i, j in enumerate(jobs, 1):
        voice = j.get("voice", "noa")
        if voice not in styles:
            styles[voice] = load_voice_style([voice_path(voice)])
        tts.g2p.speaker = int(j.get("speaker", 0))
        tts.g2p.target_speaker = int(j.get("target_speaker", 0))
        ph = j.get("phonemes")
        if not ph and j.get("parts"):
            ph = " ".join(
                p["ipa"] if "ipa" in p else g2p(tts, p["text"]) for p in j["parts"]
            )
        if not ph:
            ph = g2p(tts, j["text"])
        np.random.seed(int(j.get("seed", 0)))
        t1 = time.time()
        wav, _ = tts(
            ph, lang="he", style=styles[voice],
            total_step=int(j.get("steps", 16)),
            speed=float(j.get("speed", 1.0)),
            cfg_scale=float(j.get("cfg", 4.0)),
            text_is_phonemes=True,
            silence_duration=float(j.get("gap", 0.15)),
        )
        wav = np.asarray(wav, dtype=np.float32)
        if wav.ndim == 2:
            wav = wav[0]
        wav = limit_peak(wav)
        sf.write(out / f"{j['key']}.wav", wav, tts.sample_rate, subtype="PCM_16")
        meta = {**j, "engine": "bluetts-2.5", "phonemes_used": ph,
                "sr": tts.sample_rate, "render_s": round(time.time() - t1, 2)}
        json.dump(meta, open(out / f"{j['key']}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"[blue] {i}/{len(jobs)} {j['key']} {voice} {len(wav) / tts.sample_rate:.2f}s "
              f"({time.time() - t1:.1f}s) {ph}", flush=True)


def g2p_roster(players_path: str, pron_path: str | None) -> None:
    """One process for a whole roster (a new club's first look): id, the spoken text, G2P, and the pin."""
    import hebrew
    from blue_onnx import TextProcessor

    tp = TextProcessor(target_speaker=0)
    pins = json.load(open(pron_path, encoding="utf-8"))["players"] if pron_path else {}
    for p in json.load(open(players_path, encoding="utf-8"))["players"]:
        if p.get("role") not in ("starter", "bench"):
            continue
        say = (p.get("speak_he") or hebrew.speak_text(p.get("name_he") or p["name"])).strip()
        ipa = TAG.sub("", tp.phonemize(say, lang="he")).strip()
        pin = pins.get(p["id"], {}).get("ipa")
        mark = "no pin" if pin is None else ("pin = g2p" if pin == ipa else f"pin {pin}")
        print(f"{p['id']:26s} {say:22s} {ipa:32s} {mark}", flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "--g2p":
        from blue_onnx import TextProcessor
        tp = TextProcessor(target_speaker=int(sys.argv[3]) if len(sys.argv) > 3 else 0)
        print(TAG.sub("", tp.phonemize(sys.argv[2], lang="he")).strip())
    elif sys.argv[1] == "--g2p-roster":
        g2p_roster(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
    else:
        main(sys.argv[1])
