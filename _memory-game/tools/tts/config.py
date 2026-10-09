"""Where the voice tools find a game, the work directory and the engine install.

Flags come first, then MEMORY_GAME_* environment variables; the older MACCABI_* names still work.
  game     --game <folder>: implies its tools/tts/pronunciations.json and audio/ (tts.sh passes it)
  work     --work, MEMORY_GAME_ROOT: the scratch directory outside the repo with data/players.json and tts/
  tts      --tts-home, MEMORY_GAME_TTS_HOME (default <work>/tts): work/, qa/, out/, listen.html
  engines  --engines, MEMORY_GAME_TTS_ENGINES (default ${XDG_CACHE_HOME:-~/.cache}/memory-game-tts): .venv-blue,
           .venv-stt and _engines/BlueTTS. The default belongs to no club; `setup.sh --install` makes it.
The engine install is only ever run: no bytecode, no model downloads (generate.py sets both).
"""
from __future__ import annotations

import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]


def env(name: str) -> str | None:
    return os.environ.get(f"MEMORY_GAME_{name}") or os.environ.get(f"MACCABI_{name}") or None


def default_engines() -> Path:
    return Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache") / "memory-game-tts"


def work_dir(flag: str | None = None) -> Path:
    work = flag or env("ROOT")
    if not work:
        raise SystemExit("pass --work <dir> (or set MEMORY_GAME_ROOT): the scratch directory outside the repo "
                         "that holds data/players.json and tts/")
    return Path(work).expanduser().resolve()


def tts_home(work: Path, flag: str | None = None) -> Path:
    return Path(flag or env("TTS_HOME") or work / "tts").expanduser().resolve()


def engines_home(flag: str | None = None, tts: Path | None = None) -> Path:
    """The first install that has a BlueTTS venv: the flag, the variable, the default home, then <tts>
    (where installs used to go)."""
    asked = flag or env("TTS_ENGINES")
    if asked:
        if not (Path(asked) / ".venv-blue/bin/python").exists():
            raise SystemExit(f"no BlueTTS install in {asked}: see _memory-game/tools/tts/setup.sh")
        return Path(asked).expanduser().resolve()
    for home in (default_engines(), tts):
        if home and (home / ".venv-blue/bin/python").exists():
            return home.resolve()
    raise SystemExit(f"no BlueTTS install in {default_engines()}: run _memory-game/tools/tts/setup.sh --install "
                     "(or pass --engines)")


def game_dir(name: str) -> Path:
    path = Path(name)
    if not path.is_dir():
        path = REPO / name
    if not (path / "manifest.webmanifest").is_file():
        raise SystemExit(f"{name} is not a game folder (no manifest.webmanifest)")
    return path.resolve()
