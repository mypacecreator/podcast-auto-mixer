"""Tests for podmix.audio_io."""

from __future__ import annotations

import pytest

pytest.importorskip("pydub")

from pydub import AudioSegment

from podmix.audio_io import export_audio, load_audio, normalize_format


def _silence(duration_ms: int = 200, frame_rate: int = 44100) -> AudioSegment:
    return AudioSegment.silent(duration=duration_ms, frame_rate=frame_rate)


def test_load_audio_wav_roundtrip(tmp_path):
    src = _silence()
    path = tmp_path / "sample.wav"
    export_audio(src, path, sample_rate=src.frame_rate)

    loaded = load_audio(path)

    assert loaded.frame_rate == src.frame_rate
    assert loaded.channels == src.channels
    assert len(loaded) == len(src)


def test_load_audio_mp3_roundtrip(tmp_path):
    src = _silence()
    path = tmp_path / "sample.mp3"
    export_audio(src, path, sample_rate=src.frame_rate)

    loaded = load_audio(path)

    assert loaded.frame_rate == src.frame_rate
    # MP3 encoding adds a small amount of padding; allow ~100ms tolerance.
    assert abs(len(loaded) - len(src)) < 100


def test_load_audio_rejects_unsupported_extension(tmp_path):
    bogus = tmp_path / "sample.flac"
    bogus.write_bytes(b"")
    with pytest.raises(ValueError):
        load_audio(bogus)


def test_load_audio_handles_uppercase_extension(tmp_path):
    src = _silence()
    # Write directly to an uppercase-suffix path so the test is portable on
    # case-insensitive filesystems (macOS/Windows), where renaming only the
    # case of the extension can be a no-op.
    upper_path = tmp_path / "sample.WAV"
    export_audio(src, upper_path, sample_rate=src.frame_rate)

    loaded = load_audio(upper_path)
    assert loaded.frame_rate == src.frame_rate


def test_export_audio_applies_sample_rate(tmp_path):
    src = _silence(frame_rate=44100)
    path = tmp_path / "sample.wav"
    export_audio(src, path, sample_rate=22050)

    loaded = load_audio(path)
    assert loaded.frame_rate == 22050


def test_export_audio_mp3_with_bitrate(tmp_path):
    src = _silence(duration_ms=1000)
    low_path = tmp_path / "low.mp3"
    high_path = tmp_path / "high.mp3"

    export_audio(src, low_path, bitrate="64k", sample_rate=src.frame_rate)
    export_audio(src, high_path, bitrate="256k", sample_rate=src.frame_rate)

    assert low_path.stat().st_size < high_path.stat().st_size


def test_export_audio_rejects_unsupported_extension(tmp_path):
    src = _silence()
    path = tmp_path / "sample.flac"
    with pytest.raises(ValueError):
        export_audio(src, path)


def test_normalize_format():
    src = AudioSegment.silent(duration=100, frame_rate=44100).set_channels(1)
    out = normalize_format(src, sample_rate=48000, channels=2)

    assert out.frame_rate == 48000
    assert out.channels == 2
    assert out.sample_width == 2
