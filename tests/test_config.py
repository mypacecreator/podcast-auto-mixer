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


def test_load_config_rejects_fractional_ms(tmp_path):
    toml = tmp_path / "frac.toml"
    toml.write_text("voice_start_ms = 2.5\n")

    import pytest
    with pytest.raises(ValueError, match="voice_start_ms"):
        load_config(toml)


def test_load_config_coerces_whole_float_to_int(tmp_path):
    toml = tmp_path / "whole.toml"
    toml.write_text("voice_start_ms = 2000.0\n")

    cfg = load_config(toml)

    assert cfg.voice_start_ms == 2000
    assert isinstance(cfg.voice_start_ms, int)


def test_load_config_rejects_wrong_type(tmp_path):
    toml = tmp_path / "wrong.toml"
    toml.write_text('voice_start_ms = "notanint"\n')

    import pytest
    with pytest.raises(ValueError, match="voice_start_ms"):
        load_config(toml)


def test_load_config_rejects_nan_for_float_field(tmp_path):
    # TOML does allow nan/inf literals; _coerce should reject them.
    toml = tmp_path / "nan.toml"
    toml.write_text("bgm_gain_db = nan\n")

    import pytest
    with pytest.raises(ValueError, match="bgm_gain_db"):
        load_config(toml)


def test_load_config_rejects_inf_for_int_field(tmp_path):
    toml = tmp_path / "inf.toml"
    toml.write_text("voice_start_ms = inf\n")

    import pytest
    with pytest.raises(ValueError, match="voice_start_ms"):
        load_config(toml)


def test_load_config_rejects_negative_ms(tmp_path):
    toml = tmp_path / "neg.toml"
    toml.write_text("voice_start_ms = -100\n")

    import pytest
    with pytest.raises(ValueError, match="voice_start_ms"):
        load_config(toml)


def test_load_config_rejects_nonpositive_sample_rate(tmp_path):
    toml = tmp_path / "sr.toml"
    toml.write_text("sample_rate = 0\n")

    import pytest
    with pytest.raises(ValueError, match="sample_rate"):
        load_config(toml)


def test_load_config_rejects_invalid_channels(tmp_path):
    toml = tmp_path / "ch.toml"
    toml.write_text("channels = 3\n")

    import pytest
    with pytest.raises(ValueError, match="channels"):
        load_config(toml)
