"""Configuration dataclass and TOML loader for podmix.

``MixConfig`` holds the parameters consumed across the mixing pipeline:

- ``paths``: default file paths (``default_bgm``, ``default_outro``)
- ``mixer.build_episode``: timing fields (``voice_start_ms``, ``outro_tail_ms``,
  ``bgm_outro_crossfade_ms``) and gain values (``voice_gain_db``, ``bgm_gain_db``,
  ``outro_gain_db``)
- ``audio_io.normalize_format``: ``sample_rate`` and ``channels``
- ``audio_io.export_audio``: ``sample_rate`` and ``output_bitrate``

Defaults match the values documented in ``CLAUDE.md``; ``load_config`` reads a
TOML file (supporting [paths], [mix], [output] sections) and overlays its keys
onto the defaults.
"""

from __future__ import annotations

import math
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MixConfig:
    # Paths
    default_bgm: str = "audio/bgm/bgm_main.wav"
    default_outro: str = "audio/outro/bgm_end.wav"
    # Mix parameters
    voice_start_ms: int = 1500
    outro_tail_ms: int = 3000
    bgm_outro_crossfade_ms: int = 2000
    voice_gain_db: float = 0.0
    bgm_gain_db: float = -18.0
    outro_gain_db: float = -6.0
    # Output parameters
    sample_rate: int = 48000
    channels: int = 2
    output_bitrate: str = "192k"


_FIELD_TYPES: dict[str, type] = {
    "default_bgm": str,
    "default_outro": str,
    "voice_start_ms": int,
    "outro_tail_ms": int,
    "bgm_outro_crossfade_ms": int,
    "voice_gain_db": float,
    "bgm_gain_db": float,
    "outro_gain_db": float,
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

    Returns the built-in defaults when *path* is ``None``. The TOML file can use
    sections ([paths], [mix], [output]) or flat structure (for backward
    compatibility). Unknown keys are silently ignored. Known keys are
    type-validated and coerced; a ``ValueError`` is raised for any key whose
    value cannot be interpreted as the expected type.
    """
    if path is None:
        return MixConfig()
    with Path(path).open("rb") as fp:
        data = tomllib.load(fp)

    # Flatten known sections into top-level dict; unknown sections are ignored
    _KNOWN_SECTIONS = frozenset({"paths", "mix", "output"})
    flat: dict[str, object] = {}
    for key, value in data.items():
        if isinstance(value, dict):
            if key in _KNOWN_SECTIONS:
                flat.update(value)
        else:
            # Top-level key (backward compatibility)
            flat[key] = value

    filtered = {k: _coerce(k, v) for k, v in flat.items() if k in _FIELD_TYPES}
    return MixConfig(**filtered)
