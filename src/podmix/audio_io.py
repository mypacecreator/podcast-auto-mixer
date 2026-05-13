"""Audio file loading, exporting, and format normalization."""

from __future__ import annotations

from pathlib import Path

from pydub import AudioSegment

_EXTENSION_TO_FORMAT = {".wav": "wav", ".mp3": "mp3"}


def _format_for_path(path: Path) -> str:
    fmt = _EXTENSION_TO_FORMAT.get(path.suffix.lower())
    if fmt is None:
        raise ValueError(f"Unsupported audio extension: {path.suffix!r}")
    return fmt


def load_audio(path: Path) -> AudioSegment:
    fmt = _format_for_path(path)
    return AudioSegment.from_file(path, format=fmt)


def export_audio(
    seg: AudioSegment,
    path: Path,
    *,
    bitrate: str = "192k",
    sample_rate: int = 48000,
) -> None:
    fmt = _format_for_path(path)
    seg = seg.set_frame_rate(sample_rate)
    if fmt == "mp3":
        seg.export(path, format=fmt, bitrate=bitrate)
    else:
        seg.export(path, format=fmt)


def normalize_format(
    seg: AudioSegment, sample_rate: int, channels: int
) -> AudioSegment:
    return seg.set_frame_rate(sample_rate).set_channels(channels).set_sample_width(2)
