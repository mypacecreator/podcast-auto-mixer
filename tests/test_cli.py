"""End-to-end tests for podmix.cli.

Drives ``cli.main`` directly with synthetic silent WAVs so the full pipeline
(``load_audio`` → ``normalize_format`` → ``mixer.build_episode`` →
``export_audio``) is exercised without depending on real audio fixtures.
"""

from __future__ import annotations

import pytest

pytest.importorskip("pydub")

from pydub import AudioSegment

from podmix import audio_io
from podmix.cli import main


def _write_silence(path, duration_ms: int, frame_rate: int = 44100) -> None:
    AudioSegment.silent(duration=duration_ms, frame_rate=frame_rate).export(
        path, format="wav"
    )


def _make_inputs(tmp_path, *, voice_ms=2000, bgm_ms=500, outro_ms=1500):
    voice = tmp_path / "voice.wav"
    bgm = tmp_path / "bgm.wav"
    outro = tmp_path / "outro.wav"
    _write_silence(voice, voice_ms)
    _write_silence(bgm, bgm_ms)
    _write_silence(outro, outro_ms)
    return voice, bgm, outro


def test_main_end_to_end_wav(tmp_path):
    voice, bgm, outro = _make_inputs(tmp_path)
    output = tmp_path / "out" / "episode.wav"

    rc = main(
        [
            "--voice", str(voice),
            "--bgm", str(bgm),
            "--outro", str(outro),
            "--output", str(output),
            "--voice-start", "0.1",
            "--outro-tail", "0.5",
            "--bgm-outro-crossfade", "0.2",
            "--bgm-gain", "-15",
        ]
    )

    assert rc == 0
    assert output.exists()

    loaded = audio_io.load_audio(output)
    # default cfg.sample_rate is 48000; CLI didn't override it
    assert loaded.frame_rate == 48000
    assert loaded.channels == 2
    # voice_start (100ms) + voice (2000ms) + outro_tail (500ms) = 2600ms total
    assert abs(len(loaded) - 2600) < 50


def test_main_reads_config_and_cli_overrides(tmp_path):
    voice, bgm, outro = _make_inputs(tmp_path)
    output = tmp_path / "ep.wav"
    cfg = tmp_path / "podmix.toml"
    cfg.write_text(
        """
voice_start_ms = 100
outro_tail_ms = 500
bgm_outro_crossfade_ms = 200
bgm_gain_db = -10.0
sample_rate = 22050
channels = 1
output_bitrate = "128k"
"""
    )

    rc = main(
        [
            "--voice", str(voice),
            "--bgm", str(bgm),
            "--outro", str(outro),
            "--output", str(output),
            "--config", str(cfg),
            "--bgm-gain", "-20",  # CLI override wins over TOML's -10
        ]
    )

    assert rc == 0
    loaded = audio_io.load_audio(output)
    assert loaded.frame_rate == 22050
    assert loaded.channels == 1


def test_main_creates_output_directory(tmp_path):
    voice, bgm, outro = _make_inputs(tmp_path)
    nested = tmp_path / "a" / "b" / "c" / "episode.wav"

    rc = main(
        [
            "--voice", str(voice),
            "--bgm", str(bgm),
            "--outro", str(outro),
            "--output", str(nested),
            "--voice-start", "0.1",
            "--outro-tail", "0.5",
            "--bgm-outro-crossfade", "0.2",
        ]
    )

    assert rc == 0
    assert nested.exists()


def test_main_without_voice_enters_batch_mode(tmp_path, monkeypatch):
    # No audio/voice/ directory under tmp_path → batch mode exits with code 1.
    monkeypatch.chdir(tmp_path)
    _, bgm, outro = _make_inputs(tmp_path)
    output = tmp_path / "ep.wav"

    with pytest.raises(SystemExit) as exc_info:
        main(["--bgm", str(bgm), "--outro", str(outro), "--output", str(output)])
    assert exc_info.value.code == 1


def test_batch_mode_empty_voice_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "audio" / "voice").mkdir(parents=True)
    _, bgm, outro = _make_inputs(tmp_path)

    with pytest.raises(SystemExit) as exc_info:
        main(["--bgm", str(bgm), "--outro", str(outro)])
    assert exc_info.value.code == 1


def test_batch_mode_processes_all_voice_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    voice_dir = tmp_path / "audio" / "voice"
    voice_dir.mkdir(parents=True)
    bgm = tmp_path / "bgm.wav"
    outro = tmp_path / "outro.wav"
    _write_silence(bgm, 500)
    _write_silence(outro, 1500)
    _write_silence(voice_dir / "ep001.wav", 2000)
    _write_silence(voice_dir / "ep002.wav", 2000)

    rc = main([
        "--bgm", str(bgm),
        "--outro", str(outro),
        "--voice-start", "0.1",
        "--outro-tail", "0.5",
        "--bgm-outro-crossfade", "0.2",
    ])

    assert rc == 0
    assert (tmp_path / "output" / "ep001_mixed.mp3").exists()
    assert (tmp_path / "output" / "ep002_mixed.mp3").exists()


def test_batch_mode_continues_after_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    voice_dir = tmp_path / "audio" / "voice"
    voice_dir.mkdir(parents=True)
    bgm = tmp_path / "bgm.wav"
    _write_silence(bgm, 500)
    # outro shorter than outro_tail_ms → build_episode raises ValueError for every file
    outro = tmp_path / "outro.wav"
    _write_silence(outro, 200)
    _write_silence(voice_dir / "ep001.wav", 2000)
    _write_silence(voice_dir / "ep002.wav", 2000)

    rc = main([
        "--bgm", str(bgm),
        "--outro", str(outro),
        "--voice-start", "0.1",
        "--outro-tail", "0.5",
        "--bgm-outro-crossfade", "0.1",
    ])

    assert rc == 1
    assert not (tmp_path / "output" / "ep001_mixed.mp3").exists()
    assert not (tmp_path / "output" / "ep002_mixed.mp3").exists()


def test_batch_mode_warns_when_output_specified(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    voice_dir = tmp_path / "audio" / "voice"
    voice_dir.mkdir(parents=True)
    bgm = tmp_path / "bgm.wav"
    outro = tmp_path / "outro.wav"
    _write_silence(bgm, 500)
    _write_silence(outro, 1500)
    _write_silence(voice_dir / "ep001.wav", 2000)

    rc = main([
        "--bgm", str(bgm),
        "--outro", str(outro),
        "--output", str(tmp_path / "ignored.wav"),
        "--voice-start", "0.1",
        "--outro-tail", "0.5",
        "--bgm-outro-crossfade", "0.2",
    ])

    assert rc == 0
    captured = capsys.readouterr()
    assert "Warning" in captured.err
    assert not (tmp_path / "ignored.wav").exists()


def test_batch_mode_sorted_order(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    voice_dir = tmp_path / "audio" / "voice"
    voice_dir.mkdir(parents=True)
    bgm = tmp_path / "bgm.wav"
    outro = tmp_path / "outro.wav"
    _write_silence(bgm, 500)
    _write_silence(outro, 1500)
    _write_silence(voice_dir / "zzz.wav", 2000)
    _write_silence(voice_dir / "aaa.wav", 2000)

    rc = main([
        "--bgm", str(bgm),
        "--outro", str(outro),
        "--voice-start", "0.1",
        "--outro-tail", "0.5",
        "--bgm-outro-crossfade", "0.2",
    ])

    assert rc == 0
    assert (tmp_path / "output" / "aaa_mixed.mp3").exists()
    assert (tmp_path / "output" / "zzz_mixed.mp3").exists()


def test_main_propagates_mixer_validation_error(tmp_path):
    # outro shorter than outro_tail_ms — mixer.build_episode should raise.
    voice, bgm, outro = _make_inputs(
        tmp_path, voice_ms=2000, bgm_ms=500, outro_ms=200
    )
    output = tmp_path / "ep.wav"

    with pytest.raises(ValueError, match="outro must be longer than outro_tail_ms"):
        main(
            [
                "--voice", str(voice),
                "--bgm", str(bgm),
                "--outro", str(outro),
                "--output", str(output),
                "--voice-start", "0.1",
                "--outro-tail", "0.5",
                "--bgm-outro-crossfade", "0.1",
            ]
        )


def test_main_rejects_nan_voice_start(tmp_path):
    voice, bgm, outro = _make_inputs(tmp_path)
    output = tmp_path / "ep.wav"

    with pytest.raises(SystemExit):
        main(
            [
                "--voice", str(voice),
                "--bgm", str(bgm),
                "--outro", str(outro),
                "--output", str(output),
                "--voice-start", "nan",
            ]
        )


def test_main_rejects_inf_outro_tail(tmp_path):
    voice, bgm, outro = _make_inputs(tmp_path)
    output = tmp_path / "ep.wav"

    with pytest.raises(SystemExit):
        main(
            [
                "--voice", str(voice),
                "--bgm", str(bgm),
                "--outro", str(outro),
                "--output", str(output),
                "--outro-tail", "inf",
            ]
        )


def test_main_rejects_negative_voice_start(tmp_path):
    # A tiny negative value would round to 0 ms and silently pass without
    # the _nonneg_finite_float guard.
    voice, bgm, outro = _make_inputs(tmp_path)
    output = tmp_path / "ep.wav"

    with pytest.raises(SystemExit):
        main(
            [
                "--voice", str(voice),
                "--bgm", str(bgm),
                "--outro", str(outro),
                "--output", str(output),
                "--voice-start", "-0.0004",
            ]
        )


def test_main_rejects_negative_bgm_outro_crossfade(tmp_path):
    voice, bgm, outro = _make_inputs(tmp_path)
    output = tmp_path / "ep.wav"

    with pytest.raises(SystemExit):
        main(
            [
                "--voice", str(voice),
                "--bgm", str(bgm),
                "--outro", str(outro),
                "--output", str(output),
                "--bgm-outro-crossfade", "-1.5",
            ]
        )


def test_main_rejects_overflow_voice_start(tmp_path):
    # 1e308 * 1000 overflows to inf; should be caught at parse time.
    voice, bgm, outro = _make_inputs(tmp_path)
    output = tmp_path / "ep.wav"

    with pytest.raises(SystemExit):
        main(
            [
                "--voice", str(voice),
                "--bgm", str(bgm),
                "--outro", str(outro),
                "--output", str(output),
                "--voice-start", "1e308",
            ]
        )


def test_main_allows_negative_bgm_gain(tmp_path):
    # --bgm-gain is in dB; negative is the *normal* case (attenuation).
    voice, bgm, outro = _make_inputs(tmp_path)
    output = tmp_path / "ep.wav"

    rc = main(
        [
            "--voice", str(voice),
            "--bgm", str(bgm),
            "--outro", str(outro),
            "--output", str(output),
            "--voice-start", "0.1",
            "--outro-tail", "0.5",
            "--bgm-outro-crossfade", "0.2",
            "--bgm-gain", "-30",
        ]
    )
    assert rc == 0
    assert output.exists()
