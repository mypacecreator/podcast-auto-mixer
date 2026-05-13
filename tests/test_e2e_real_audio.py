"""End-to-end tests with real (audible) sine-wave audio fixtures.

Unlike the synthetic-silence tests in test_cli.py, these tests use tonal WAV
files so the pipeline is exercised with actual audio content.  This catches
issues that only manifest with non-zero samples: pydub format coercion, ffmpeg
encoding, RMS-based position verification, etc.

Fixture sizes:
  voice : 30 000 ms @ 440 Hz  (simulates a full episode body)
  bgm   :  5 000 ms @ 220 Hz  (must loop → exercises loop_to_length)
  outro : 10 000 ms @ 880 Hz  (> outro_tail_ms=3000 ms, satisfies build_episode precondition)
"""

from __future__ import annotations

import array
import json
import math
import shutil
import subprocess
import sys
import wave
from pathlib import Path

import pytest

pytest.importorskip("pydub")

from podmix import audio_io
from podmix.cli import main

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).parent.parent


def _write_tone(
    path: Path,
    freq_hz: float = 440,
    duration_ms: int = 5000,
    sample_rate: int = 44100,
    amplitude: float = 0.5,
) -> None:
    """Write a mono 16-bit WAV containing a pure sine wave (single buffered write)."""
    n = int(sample_rate * duration_ms / 1000)
    buf = array.array(
        "h",
        (
            int(32767 * amplitude * math.sin(2 * math.pi * freq_hz * i / sample_rate))
            for i in range(n)
        ),
    )
    if sys.byteorder == "big":
        buf.byteswap()
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(buf.tobytes())


@pytest.fixture(scope="session")
def tone_inputs(tmp_path_factory) -> tuple[Path, Path, Path]:
    """Generate the standard tone WAV fixtures once per test session."""
    base = tmp_path_factory.mktemp("tones")
    voice = base / "voice.wav"
    bgm = base / "bgm.wav"
    outro = base / "outro.wav"
    _write_tone(voice, freq_hz=440, duration_ms=30_000)
    _write_tone(bgm, freq_hz=220, duration_ms=5_000)
    _write_tone(outro, freq_hz=880, duration_ms=10_000)
    return voice, bgm, outro


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_timing_wav(tmp_path, tone_inputs):
    """Output duration matches the formula: voice_start + voice + outro_tail."""
    voice_start_ms = 1500
    outro_tail_ms = 3000
    voice_ms = 30_000

    voice, bgm, outro = tone_inputs
    output = tmp_path / "ep.wav"

    rc = main([
        "--voice", str(voice),
        "--bgm", str(bgm),
        "--outro", str(outro),
        "--output", str(output),
        "--voice-start", str(voice_start_ms / 1000),
        "--outro-tail", str(outro_tail_ms / 1000),
        "--bgm-outro-crossfade", "2.0",
        "--bgm-gain", "-12",
    ])

    assert rc == 0
    loaded = audio_io.load_audio(output)
    expected_ms = voice_start_ms + voice_ms + outro_tail_ms
    assert abs(len(loaded) - expected_ms) < 50, (
        f"WAV duration {len(loaded)} ms, expected {expected_ms} ms"
    )


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_timing_mp3(tmp_path, tone_inputs):
    """Timing formula holds for MP3 output (wider tolerance for codec padding)."""
    voice_start_ms = 1500
    outro_tail_ms = 3000
    voice_ms = 30_000

    voice, bgm, outro = tone_inputs
    output = tmp_path / "ep.mp3"

    rc = main([
        "--voice", str(voice),
        "--bgm", str(bgm),
        "--outro", str(outro),
        "--output", str(output),
        "--voice-start", str(voice_start_ms / 1000),
        "--outro-tail", str(outro_tail_ms / 1000),
        "--bgm-outro-crossfade", "2.0",
        "--bgm-gain", "-12",
    ])

    assert rc == 0
    loaded = audio_io.load_audio(output)
    expected_ms = voice_start_ms + voice_ms + outro_tail_ms
    assert abs(len(loaded) - expected_ms) < 150, (
        f"MP3 duration {len(loaded)} ms, expected {expected_ms} ms"
    )


def test_output_format(tmp_path, tone_inputs):
    """Output has the default sample_rate (48 000 Hz) and channel count (2)."""
    voice, bgm, outro = tone_inputs
    output = tmp_path / "ep.wav"

    rc = main([
        "--voice", str(voice),
        "--bgm", str(bgm),
        "--outro", str(outro),
        "--output", str(output),
        "--voice-start", "1.5",
        "--outro-tail", "3.0",
        "--bgm-outro-crossfade", "2.0",
    ])

    assert rc == 0
    loaded = audio_io.load_audio(output)
    assert loaded.frame_rate == 48_000, f"Expected 48000 Hz, got {loaded.frame_rate}"
    assert loaded.channels == 2, f"Expected 2 channels, got {loaded.channels}"


@pytest.mark.skipif(shutil.which("ffprobe") is None, reason="ffprobe not installed")
def test_ffprobe_metadata(tmp_path, tone_inputs):
    """ffprobe confirms MP3 metadata: sample_rate, channels, duration."""
    voice_start_ms = 1500
    outro_tail_ms = 3000
    voice_ms = 30_000

    voice, bgm, outro = tone_inputs
    output = tmp_path / "ep.mp3"

    rc = main([
        "--voice", str(voice),
        "--bgm", str(bgm),
        "--outro", str(outro),
        "--output", str(output),
        "--voice-start", str(voice_start_ms / 1000),
        "--outro-tail", str(outro_tail_ms / 1000),
        "--bgm-outro-crossfade", "2.0",
        "--bgm-gain", "-12",
    ])
    assert rc == 0

    result = subprocess.run(
        [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_streams", "-show_format", str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(result.stdout)
    audio = next(s for s in data["streams"] if s["codec_type"] == "audio")

    assert int(audio["sample_rate"]) == 48_000
    assert int(audio["channels"]) == 2

    # MP3 stream-level duration is often absent; use format.duration instead.
    expected_s = (voice_start_ms + voice_ms + outro_tail_ms) / 1000
    actual_s = float(data["format"]["duration"])
    assert abs(actual_s - expected_s) < 0.2, (
        f"ffprobe duration {actual_s:.3f} s, expected {expected_s:.3f} s"
    )


def test_bgm_audible_at_lead_in(tmp_path, tone_inputs):
    """BGM is present (non-silent) during the lead-in before voice starts."""
    voice_start_ms = 1500

    voice, bgm, outro = tone_inputs
    output = tmp_path / "ep.wav"

    rc = main([
        "--voice", str(voice),
        "--bgm", str(bgm),
        "--outro", str(outro),
        "--output", str(output),
        "--voice-start", str(voice_start_ms / 1000),
        "--outro-tail", "3.0",
        "--bgm-outro-crossfade", "2.0",
        "--bgm-gain", "-12",
    ])
    assert rc == 0

    loaded = audio_io.load_audio(output)
    # Slice to a window well inside the BGM-only lead-in (avoid fade edges)
    lead_in_slice = loaded[100 : voice_start_ms - 100]
    assert lead_in_slice.rms > 0, "BGM should be audible during the lead-in window"


def test_outro_present_at_tail(tmp_path, tone_inputs):
    """Outro audio is present (non-silent) during the tail after voice ends."""
    voice_start_ms = 1500
    outro_tail_ms = 3000
    voice_ms = 30_000

    voice, bgm, outro = tone_inputs
    output = tmp_path / "ep.wav"

    rc = main([
        "--voice", str(voice),
        "--bgm", str(bgm),
        "--outro", str(outro),
        "--output", str(output),
        "--voice-start", str(voice_start_ms / 1000),
        "--outro-tail", str(outro_tail_ms / 1000),
        "--bgm-outro-crossfade", "2.0",
        "--bgm-gain", "-12",
    ])
    assert rc == 0

    loaded = audio_io.load_audio(output)
    total_ms = len(loaded)
    # Slice to a window inside the outro-only tail (after voice ends, before end)
    tail_slice = loaded[total_ms - outro_tail_ms + 200 : total_ms - 200]
    assert tail_slice.rms > 0, "Outro should be audible during the tail window"


def test_default_config_toml_integration(tmp_path, tone_inputs):
    """CLI with --config config/default.toml produces correct duration."""
    import tomllib

    default_toml = _REPO_ROOT / "config" / "default.toml"
    if not default_toml.exists():
        pytest.skip("config/default.toml not found")

    with default_toml.open("rb") as f:
        cfg = tomllib.load(f)
    voice_start_ms = cfg["voice_start_ms"]
    outro_tail_ms = cfg["outro_tail_ms"]
    voice_ms = 30_000

    voice, bgm, outro = tone_inputs
    output = tmp_path / "ep_default.wav"

    rc = main([
        "--voice", str(voice),
        "--bgm", str(bgm),
        "--outro", str(outro),
        "--output", str(output),
        "--config", str(default_toml),
    ])

    assert rc == 0
    loaded = audio_io.load_audio(output)
    expected_ms = voice_start_ms + voice_ms + outro_tail_ms
    assert abs(len(loaded) - expected_ms) < 50, (
        f"Duration {len(loaded)} ms, expected {expected_ms} ms with default config"
    )
