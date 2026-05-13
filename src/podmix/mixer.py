"""Core mixing logic: BGM looping and episode assembly."""

from __future__ import annotations

import warnings

from pydub import AudioSegment


def _silent_like(track: AudioSegment, duration_ms: int) -> AudioSegment:
    """Return silence that matches *track*'s frame rate, channels, and sample width."""
    return (
        AudioSegment.silent(duration=duration_ms, frame_rate=track.frame_rate)
        .set_channels(track.channels)
        .set_sample_width(track.sample_width)
    )


def loop_to_length(
    track: AudioSegment, target_ms: int, fade_ms: int = 50
) -> AudioSegment:
    """Repeat *track* until it reaches *target_ms*, adding a tiny crossfade at each seam."""
    if fade_ms < 0:
        raise ValueError(f"fade_ms must be >= 0, got {fade_ms}")
    if target_ms < 0:
        raise ValueError(f"target_ms must be >= 0, got {target_ms}")
    if target_ms == 0:
        return _silent_like(track, 0)

    track_ms = len(track)
    if track_ms == 0:
        return _silent_like(track, target_ms)

    # Cap so each append always makes forward progress
    effective_fade = min(fade_ms, track_ms // 2)

    result = track
    while len(result) < target_ms:
        result = result.append(track, crossfade=effective_fade)

    return result[:target_ms]


def build_episode(
    voice: AudioSegment,
    bgm: AudioSegment,
    outro: AudioSegment,
    *,
    voice_start_ms: int = 1500,
    outro_tail_ms: int = 3000,
    bgm_outro_crossfade_ms: int = 2000,
    bgm_gain_db: float = -12.0,
) -> AudioSegment:
    """Assemble a podcast episode from voice, BGM loop, and outro.

    Raises ValueError when:
    - any time parameter (voice_start_ms, outro_tail_ms, bgm_outro_crossfade_ms) is negative
    - outro is not longer than outro_tail_ms (overlay would degenerate into append)
    - outro is longer than the total episode length (outro_start_ms would be negative)
    - bgm_outro_crossfade_ms exceeds len(outro) (crossfade would extend past outro end)
    """
    if voice_start_ms < 0 or outro_tail_ms < 0 or bgm_outro_crossfade_ms < 0:
        raise ValueError(
            "voice_start_ms, outro_tail_ms, and bgm_outro_crossfade_ms must all be >= 0"
        )
    if len(outro) <= outro_tail_ms:
        raise ValueError("outro must be longer than outro_tail_ms")
    if bgm_outro_crossfade_ms > len(outro):
        raise ValueError(
            f"bgm_outro_crossfade_ms ({bgm_outro_crossfade_ms} ms) exceeds "
            f"outro length ({len(outro)} ms)"
        )

    # Step 1
    total_ms = voice_start_ms + len(voice) + outro_tail_ms
    # Step 2
    outro_start_ms = total_ms - len(outro)
    if outro_start_ms < 0:
        raise ValueError(
            f"outro ({len(outro)} ms) is longer than the total episode length "
            f"({total_ms} ms); reduce outro length or increase voice/voice_start_ms"
        )
    # Step 3 — guard for pathologically short voice tracks
    if outro_start_ms < voice_start_ms + bgm_outro_crossfade_ms:
        warnings.warn(
            f"voice is very short: outro_start_ms ({outro_start_ms} ms) falls inside "
            f"the BGM crossfade region (ends at {voice_start_ms + bgm_outro_crossfade_ms} ms). "
            "The mix may not sound as intended.",
            UserWarning,
            stacklevel=2,
        )
    # Sync bgm/outro format with voice to prevent implicit pydub conversions during overlay
    def _match_fmt(seg: AudioSegment) -> AudioSegment:
        return (
            seg.set_frame_rate(voice.frame_rate)
            .set_channels(voice.channels)
            .set_sample_width(voice.sample_width)
        )

    bgm = _match_fmt(bgm)
    outro = _match_fmt(outro)

    # Step 4 — loop BGM to cover its entire region (0 → outro_start + crossfade)
    bgm_end_ms = outro_start_ms + bgm_outro_crossfade_ms
    bgm_looped = loop_to_length(bgm, bgm_end_ms)
    # Step 5 — crossfade: BGM fades out, outro fades in
    bgm_looped = bgm_looped.fade_out(bgm_outro_crossfade_ms)
    outro = outro.fade_in(bgm_outro_crossfade_ms)
    # Step 6 — composite onto a silent canvas
    canvas = (
        AudioSegment.silent(duration=total_ms, frame_rate=voice.frame_rate)
        .set_channels(voice.channels)
        .set_sample_width(voice.sample_width)
    )
    canvas = canvas.overlay(bgm_looped.apply_gain(bgm_gain_db), position=0)
    canvas = canvas.overlay(voice, position=voice_start_ms)
    canvas = canvas.overlay(outro, position=outro_start_ms)

    return canvas
