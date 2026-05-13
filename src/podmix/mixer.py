"""Core mixing logic: BGM looping and episode assembly."""

from __future__ import annotations

import warnings

from pydub import AudioSegment


def loop_to_length(
    track: AudioSegment, target_ms: int, fade_ms: int = 50
) -> AudioSegment:
    """Repeat *track* until it reaches *target_ms*, adding a tiny crossfade at each seam."""
    if target_ms <= 0:
        return AudioSegment.silent(duration=0, frame_rate=track.frame_rate)

    track_ms = len(track)
    if track_ms == 0:
        return AudioSegment.silent(duration=target_ms, frame_rate=track.frame_rate)

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

    Raises ValueError when outro is not longer than outro_tail_ms (which would
    make the overlay degenerate into a simple append).
    """
    if len(outro) <= outro_tail_ms:
        raise ValueError("outro must be longer than outro_tail_ms")

    # Step 1
    total_ms = voice_start_ms + len(voice) + outro_tail_ms
    # Step 2
    outro_start_ms = total_ms - len(outro)
    # Step 3 — guard for pathologically short voice tracks
    if outro_start_ms < voice_start_ms + bgm_outro_crossfade_ms:
        warnings.warn(
            f"voice is very short: outro_start_ms ({outro_start_ms} ms) falls inside "
            f"the BGM crossfade region (ends at {voice_start_ms + bgm_outro_crossfade_ms} ms). "
            "The mix may not sound as intended.",
            UserWarning,
            stacklevel=2,
        )
    # Step 4 — loop BGM to cover its entire region (0 → outro_start + crossfade)
    bgm_end_ms = outro_start_ms + bgm_outro_crossfade_ms
    bgm_looped = loop_to_length(bgm, bgm_end_ms)
    # Step 5 — crossfade: BGM fades out, outro fades in
    bgm_looped = bgm_looped.fade_out(bgm_outro_crossfade_ms)
    outro = outro.fade_in(bgm_outro_crossfade_ms)
    # Step 6 — composite onto a silent canvas
    canvas = AudioSegment.silent(duration=total_ms, frame_rate=voice.frame_rate)
    canvas = canvas.overlay(bgm_looped.apply_gain(bgm_gain_db), position=0)
    canvas = canvas.overlay(voice, position=voice_start_ms)
    canvas = canvas.overlay(outro, position=outro_start_ms)

    return canvas
