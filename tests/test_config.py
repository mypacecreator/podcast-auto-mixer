"""Tests for podmix.config."""

from __future__ import annotations

from podmix.config import MixConfig, load_config


def test_load_config_none_returns_defaults():
    cfg = load_config(None)
    assert cfg == MixConfig()


def test_load_config_reads_all_fields(tmp_path):
    toml = tmp_path / "custom.toml"
    toml.write_text(
        """
voice_start_ms = 2000
outro_tail_ms = 4500
bgm_outro_crossfade_ms = 1500
bgm_gain_db = -9.5
sample_rate = 44100
channels = 1
output_bitrate = "128k"
"""
    )

    cfg = load_config(toml)

    assert cfg.voice_start_ms == 2000
    assert cfg.outro_tail_ms == 4500
    assert cfg.bgm_outro_crossfade_ms == 1500
    assert cfg.bgm_gain_db == -9.5
    assert cfg.sample_rate == 44100
    assert cfg.channels == 1
    assert cfg.output_bitrate == "128k"


def test_load_config_ignores_unknown_keys(tmp_path):
    toml = tmp_path / "extra.toml"
    toml.write_text(
        """
voice_start_ms = 750
unknown_field = "ignored"
future_option = 42
"""
    )

    cfg = load_config(toml)

    assert cfg.voice_start_ms == 750
    # Untouched fields fall back to defaults
    assert cfg.outro_tail_ms == MixConfig().outro_tail_ms


def test_load_config_partial_keeps_defaults_for_rest(tmp_path):
    toml = tmp_path / "partial.toml"
    toml.write_text('output_bitrate = "256k"\n')

    cfg = load_config(toml)

    defaults = MixConfig()
    assert cfg.output_bitrate == "256k"
    assert cfg.voice_start_ms == defaults.voice_start_ms
    assert cfg.bgm_gain_db == defaults.bgm_gain_db
    assert cfg.sample_rate == defaults.sample_rate


def test_mix_config_is_frozen():
    cfg = MixConfig()
    try:
        cfg.voice_start_ms = 999  # type: ignore[misc]
    except Exception as exc:
        assert isinstance(exc, (AttributeError, TypeError))
    else:
        raise AssertionError("MixConfig should be immutable (frozen dataclass)")
