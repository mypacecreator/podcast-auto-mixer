"""Command-line interface for podmix.

Pipeline:

1. Parse argv with argparse.
2. Load ``MixConfig`` from ``--config`` (or defaults).
3. Overlay CLI-supplied values on top of the config (CLI > TOML > built-in).
4. Load voice / bgm / outro and normalise them to the target sample rate +
   channel count.
5. Hand off to ``mixer.build_episode`` and write the result with
   ``audio_io.export_audio``.

CLI time parameters are expressed in **seconds (float)** for human convenience
and converted to integer milliseconds here, since ``MixConfig`` and the mixer
operate strictly in ms.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import replace
from pathlib import Path
from typing import Sequence

from podmix import audio_io, mixer
from podmix.config import MixConfig, load_config


def _finite_float(value: str) -> float:
    """argparse type that rejects non-finite values (nan, inf)."""
    try:
        v = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid float: {value!r}")
    if not math.isfinite(v):
        raise argparse.ArgumentTypeError(f"must be a finite number, got {value!r}")
    return v


def _nonneg_finite_float(value: str) -> float:
    """argparse type for time parameters: finite, >= 0, and *1000-safe.

    Catches slightly-negative inputs like ``-0.0004`` that would otherwise
    round to ``0`` ms and silently violate the mixer's non-negative time
    constraint, and rejects values so large that ``v * 1000`` overflows
    (e.g. ``1e308``) before the ms conversion can crash with OverflowError.
    """
    v = _finite_float(value)
    if v < 0:
        raise argparse.ArgumentTypeError(
            f"must be a non-negative number of seconds, got {value!r}"
        )
    if not math.isfinite(v * 1000):
        raise argparse.ArgumentTypeError(
            f"value is too large to convert to milliseconds, got {value!r}"
        )
    return v


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="podmix",
        description="Mix podcast voice with BGM and an outro tail.",
    )
    p.add_argument("--voice", type=Path, required=True, help="Voice file (WAV/MP3).")
    p.add_argument(
        "--bgm",
        type=Path,
        default=None,
        help="BGM file (WAV/MP3). Defaults to config default_bgm.",
    )
    p.add_argument(
        "--outro",
        type=Path,
        default=None,
        help="Outro file (WAV/MP3). Defaults to config default_outro.",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file (WAV/MP3). Defaults to output/{voice_stem}_mixed.mp3.",
    )
    p.add_argument(
        "--voice-start",
        type=_nonneg_finite_float,
        default=None,
        help="Seconds BGM leads voice (default: config value, built-in 1.5 s).",
    )
    p.add_argument(
        "--outro-tail",
        type=_nonneg_finite_float,
        default=None,
        help="Seconds outro tails after voice ends (default: config value, built-in 3.0 s).",
    )
    p.add_argument(
        "--bgm-outro-crossfade",
        type=_nonneg_finite_float,
        default=None,
        help="Seconds of BGM↔outro crossfade (default: config value, built-in 2.0 s).",
    )
    p.add_argument(
        "--voice-gain",
        type=_finite_float,
        default=None,
        help="Voice gain in dB (default: config value, built-in 0.0 dB).",
    )
    p.add_argument(
        "--bgm-gain",
        type=_finite_float,
        default=None,
        help="BGM gain in dB (default: config value, built-in -18.0 dB).",
    )
    p.add_argument(
        "--outro-gain",
        type=_finite_float,
        default=None,
        help="Outro gain in dB (default: config value, built-in -6.0 dB).",
    )
    p.add_argument(
        "--bitrate",
        type=str,
        default=None,
        help='MP3 output bitrate string, e.g. "192k" (default: config value, built-in "192k").',
    )
    p.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Optional TOML config file path.",
    )
    return p


def _apply_overrides(cfg: MixConfig, args: argparse.Namespace) -> MixConfig:
    """Overlay CLI-supplied values on top of *cfg*.

    Only attributes the user explicitly passed are propagated, so unspecified
    CLI flags do not stomp on values that came from a TOML config file.
    """
    overrides: dict[str, object] = {}
    if args.voice_start is not None:
        overrides["voice_start_ms"] = int(round(args.voice_start * 1000))
    if args.outro_tail is not None:
        overrides["outro_tail_ms"] = int(round(args.outro_tail * 1000))
    if args.bgm_outro_crossfade is not None:
        overrides["bgm_outro_crossfade_ms"] = int(
            round(args.bgm_outro_crossfade * 1000)
        )
    if args.voice_gain is not None:
        overrides["voice_gain_db"] = float(args.voice_gain)
    if args.bgm_gain is not None:
        overrides["bgm_gain_db"] = float(args.bgm_gain)
    if args.outro_gain is not None:
        overrides["outro_gain_db"] = float(args.outro_gain)
    if args.bitrate is not None:
        overrides["output_bitrate"] = args.bitrate
    return replace(cfg, **overrides) if overrides else cfg


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    cfg = _apply_overrides(load_config(args.config), args)

    # Resolve file paths: use config defaults if not specified
    voice_path = args.voice
    bgm_path = args.bgm if args.bgm is not None else Path(cfg.default_bgm)
    outro_path = args.outro if args.outro is not None else Path(cfg.default_outro)
    output_path = (
        args.output
        if args.output is not None
        else Path("output") / f"{voice_path.stem}_mixed.mp3"
    )

    voice = audio_io.normalize_format(
        audio_io.load_audio(voice_path), cfg.sample_rate, cfg.channels
    )
    bgm = audio_io.normalize_format(
        audio_io.load_audio(bgm_path), cfg.sample_rate, cfg.channels
    )
    outro = audio_io.normalize_format(
        audio_io.load_audio(outro_path), cfg.sample_rate, cfg.channels
    )

    mixed = mixer.build_episode(
        voice,
        bgm,
        outro,
        voice_start_ms=cfg.voice_start_ms,
        outro_tail_ms=cfg.outro_tail_ms,
        bgm_outro_crossfade_ms=cfg.bgm_outro_crossfade_ms,
        voice_gain_db=cfg.voice_gain_db,
        bgm_gain_db=cfg.bgm_gain_db,
        outro_gain_db=cfg.outro_gain_db,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    audio_io.export_audio(
        mixed,
        output_path,
        bitrate=cfg.output_bitrate,
        sample_rate=cfg.sample_rate,
    )
    return 0
