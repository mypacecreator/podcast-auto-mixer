"""Tests for podmix.mixer."""

from __future__ import annotations

import pytest

pytest.importorskip("pydub")

from pydub import AudioSegment

from podmix.mixer import build_episode, loop_to_length

FRAME_RATE = 8000  # low sample rate keeps tests fast


def _silence(duration_ms: int) -> AudioSegment:
    return AudioSegment.silent(duration=duration_ms, frame_rate=FRAME_RATE)


def _tone(duration_ms: int) -> AudioSegment:
    """Constant non-zero PCM so rms > 0 after overlay."""
    n_samples = FRAME_RATE * duration_ms // 1000
    raw = b"\x40\x00" * n_samples  # 16-bit LE, value = 64
    return AudioSegment(data=raw, sample_width=2, frame_rate=FRAME_RATE, channels=1)


# ---------------------------------------------------------------------------
# loop_to_length
# ---------------------------------------------------------------------------


class TestLoopToLength:
    def test_output_length_equals_target(self):
        result = loop_to_length(_silence(1000), target_ms=3500)
        assert len(result) == 3500

    def test_exact_multiple(self):
        result = loop_to_length(_silence(1000), target_ms=3000)
        assert len(result) == 3000

    def test_track_longer_than_target_is_trimmed(self):
        result = loop_to_length(_silence(2000), target_ms=500)
        assert len(result) == 500

    def test_zero_target_returns_empty(self):
        result = loop_to_length(_silence(1000), target_ms=0)
        assert len(result) == 0

    def test_non_multiple_remainder(self):
        result = loop_to_length(_silence(700), target_ms=2000)
        assert len(result) == 2000

    def test_single_ms_track(self):
        result = loop_to_length(_silence(1), target_ms=100)
        assert len(result) == 100


# ---------------------------------------------------------------------------
# build_episode
# ---------------------------------------------------------------------------


class TestBuildEpisodeLength:
    def test_output_length_matches_formula(self):
        voice = _silence(10_000)
        bgm = _silence(5_000)
        outro = _silence(8_000)
        voice_start_ms = 1500
        outro_tail_ms = 3000

        result = build_episode(
            voice, bgm, outro,
            voice_start_ms=voice_start_ms,
            outro_tail_ms=outro_tail_ms,
            bgm_outro_crossfade_ms=2000,
            bgm_gain_db=-12.0,
        )

        expected = voice_start_ms + len(voice) + outro_tail_ms
        assert len(result) == expected

    def test_custom_voice_start(self):
        voice = _silence(5_000)
        bgm = _silence(3_000)
        outro = _silence(6_000)
        voice_start_ms = 2000
        outro_tail_ms = 2000

        result = build_episode(
            voice, bgm, outro,
            voice_start_ms=voice_start_ms,
            outro_tail_ms=outro_tail_ms,
            bgm_outro_crossfade_ms=1000,
        )

        assert len(result) == voice_start_ms + len(voice) + outro_tail_ms


class TestBuildEpisodePrecondition:
    def test_raises_when_outro_equals_tail(self):
        with pytest.raises(ValueError, match="outro must be longer than outro_tail_ms"):
            build_episode(
                _silence(5000), _silence(3000), _silence(2000), outro_tail_ms=2000
            )

    def test_raises_when_outro_shorter_than_tail(self):
        with pytest.raises(ValueError):
            build_episode(
                _silence(5000), _silence(3000), _silence(1000), outro_tail_ms=3000
            )

    def test_warns_for_very_short_voice(self):
        # outro_start_ms < voice_start_ms + bgm_outro_crossfade_ms triggers warning
        # With voice=500ms, outro=4000ms, outro_tail=3000ms, voice_start=1500ms:
        #   total = 1500 + 500 + 3000 = 5000
        #   outro_start = 5000 - 4000 = 1000
        #   threshold   = 1500 + 2000 = 3500  → 1000 < 3500 → warns
        with pytest.warns(UserWarning):
            build_episode(
                _silence(500), _silence(1000), _silence(4000),
                voice_start_ms=1500,
                outro_tail_ms=3000,
                bgm_outro_crossfade_ms=2000,
            )


class TestBuildEpisodeOverlayPositions:
    """Verify that each track is placed at the correct time offset."""

    def test_voice_is_audible_after_voice_start(self):
        voice_start_ms = 1500
        voice = _tone(10_000)
        bgm = _silence(5_000)   # silent so it doesn't bleed into the check
        outro = _silence(8_000)

        result = build_episode(
            voice, bgm, outro,
            voice_start_ms=voice_start_ms,
            outro_tail_ms=3000,
            bgm_outro_crossfade_ms=2000,
            bgm_gain_db=0.0,
        )

        # Only BGM (silent) before voice_start — output should be silent
        assert result[:voice_start_ms - 100].rms == 0
        # Voice (tone) is present after voice_start — output should be non-silent
        assert result[voice_start_ms + 100 : voice_start_ms + 500].rms > 0

    def test_outro_is_audible_after_outro_start(self):
        voice_start_ms = 1500
        outro_tail_ms = 3000
        bgm_outro_crossfade_ms = 2000

        voice = _silence(10_000)
        bgm = _silence(5_000)
        outro = _tone(8_000)

        total_ms = voice_start_ms + len(voice) + outro_tail_ms
        outro_start_ms = total_ms - len(outro)

        result = build_episode(
            voice, bgm, outro,
            voice_start_ms=voice_start_ms,
            outro_tail_ms=outro_tail_ms,
            bgm_outro_crossfade_ms=bgm_outro_crossfade_ms,
            bgm_gain_db=0.0,
        )

        # Well past the fade_in region: outro should be fully audible
        check_start = outro_start_ms + bgm_outro_crossfade_ms + 100
        assert result[check_start : check_start + 500].rms > 0

        # In the voice-only region (voice is silent here, BGM is silent):
        # output should be silent
        mid_ms = voice_start_ms + 100
        if mid_ms < outro_start_ms - 200:
            assert result[mid_ms : mid_ms + 200].rms == 0
