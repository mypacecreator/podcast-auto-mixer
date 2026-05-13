"""Configuration dataclass and TOML loader for podmix.

``MixConfig`` holds the small set of mixing parameters that ``mixer.build_episode``
and ``audio_io.export_audio`` consume. Defaults match the values documented in
``CLAUDE.md``; ``load_config`` reads a TOML file and overlays its keys onto the
defaults.
"""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
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


_FIELD_TYPES: dict[str, type] = {
    "voice_start_ms": int,
    "outro_tail_ms": int,
    "bgm_outro_crossfade_ms": int,
    "bgm_gain_db": float,
    "sample_rate": int,
    "channels": int,
    "output_bitrate": str,
}

_NONNEG_MS_FIELDS = frozenset(
    {"voice_start_ms", "outro_tail_ms", "bgm_outro_crossfade_ms"}
)
_ALLOWED_CHANNELS = frozenset({1, 2})


def _check_int_range(key: str, iv: int) -> None:
    """Apply per-field range constraints so errors name the offending key."""
    if key in _NONNEG_MS_FIELDS and iv < 0:
        raise ValueError(f"config key {key!r}: must be >= 0, got {iv}")
    if key == "sample_rate" and iv <= 0:
        raise ValueError(f"config key {key!r}: must be > 0, got {iv}")
    if key == "channels" and iv not in _ALLOWED_CHANNELS:
        raise ValueError(f"config key {key!r}: must be 1 or 2, got {iv}")


def _coerce(key: str, value: object) -> object:
    """Validate and coerce a single TOML value to its expected Python type.

    Raises ValueError with the offending key name when the value cannot be
    coerced (e.g. fractional float for an int field, wrong type entirely) or
    when an integer field violates its documented range constraint.
    """
    target = _FIELD_TYPES[key]
    if target is int:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"config key {key!r}: expected integer, got {type(value).__name__!r}"
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError(
                f"config key {key!r}: expected finite integer value, got {value!r}"
            )
        iv = int(value)
        if iv != value:
            raise ValueError(
                f"config key {key!r}: expected integer value, got {value!r}"
            )
        _check_int_range(key, iv)
        return iv
    if target is float:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"config key {key!r}: expected number, got {type(value).__name__!r}"
            )
        fv = float(value)
        if not math.isfinite(fv):
            raise ValueError(
                f"config key {key!r}: must be a finite number, got {value!r}"
            )
        return fv
    if target is str:
        if not isinstance(value, str):
            raise ValueError(
                f"config key {key!r}: expected string, got {type(value).__name__!r}"
            )
        return value
    return target(value)


def load_config(path: Path | None) -> MixConfig:
    """Load mixing parameters from a TOML file.

    Returns the built-in defaults when *path* is ``None``. Unknown keys in the
    TOML file are silently ignored so that newer config files remain
    backward-compatible with older versions of podmix. Known keys are
    type-validated and coerced; a ``ValueError`` is raised for any key whose
    value cannot be interpreted as the expected type.
    """
    if path is None:
        return MixConfig()
    with Path(path).open("rb") as fp:
        data = tomllib.load(fp)
    filtered = {k: _coerce(k, v) for k, v in data.items() if k in _FIELD_TYPES}
    return MixConfig(**filtered)
