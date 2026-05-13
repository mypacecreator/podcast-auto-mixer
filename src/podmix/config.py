"""Configuration dataclass and TOML loader for podmix.

``MixConfig`` holds the small set of mixing parameters that ``mixer.build_episode``
and ``audio_io.export_audio`` consume. Defaults match the values documented in
``CLAUDE.md``; ``load_config`` reads a TOML file and overlays its keys onto the
defaults.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, fields
from pathlib import Path


@dataclass(frozen=True)
class MixConfig:
    voice_start_ms: int = 1500
    outro_tail_ms: int = 3000
    bgm_outro_crossfade_ms: int = 2000
    bgm_gain_db: float = -12.0
    sample_rate: int = 48000
    channels: int = 2
    output_bitrate: str = "192k"


def load_config(path: Path | None) -> MixConfig:
    """Load mixing parameters from a TOML file.

    Returns the built-in defaults when *path* is ``None``. Unknown keys in the
    TOML file are silently ignored so that newer config files remain
    backward-compatible with older versions of podmix.
    """
    if path is None:
        return MixConfig()
    with Path(path).open("rb") as fp:
        data = tomllib.load(fp)
    allowed = {f.name for f in fields(MixConfig)}
    filtered = {k: v for k, v in data.items() if k in allowed}
    return MixConfig(**filtered)
