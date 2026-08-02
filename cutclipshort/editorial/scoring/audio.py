"""Audio scorer — genre-aware energy, speech presence, music, ambient."""

from __future__ import annotations

from cutclipshort.editorial.genre_profiles import GenreProfile
from cutclipshort.types import AudioSegment, TimeRange


def score_audio(
    time_range: TimeRange,
    audio_segments: list[AudioSegment],
    profile: GenreProfile,
) -> float:
    """Score audio quality with genre-specific logic.

    Speech genres: reward consistent energy + penalize music.
    Action: reward energy spikes (bursts of intensity).
    Nature: reward ambient sound, penalize excessive speech.
    Kids Music: reward continuous audio + music presence.
    """
    relevant = [
        seg for seg in audio_segments if seg.time_range.overlaps(time_range)
    ]
    if not relevant:
        return 0.5

    genre = profile.name
    scores = []

    # ── Genre-specific audio scoring ──

    if genre == "action":
        # Action: reward HIGH energy + energy spikes
        energies = [seg.energy_avg for seg in relevant]
        avg_e = sum(energies) / len(energies)
        # High average energy = good for action
        scores.append(min(1.0, avg_e / 0.35))
        # Energy spikes = exciting moments
        if len(energies) >= 2:
            spike_count = sum(
                1 for i in range(1, len(energies))
                if energies[i] > energies[i - 1] * 1.5
            )
            scores.append(min(1.0, 0.4 + spike_count * 0.2))
        else:
            scores.append(0.5)
        # Music/SFX OK for action
        scores.append(0.8)

    elif genre == "nature":
        # Nature: reward ambient sound, calm energy, penalize excessive speech
        speech_segs = [s for s in relevant if s.has_speech]
        speech_ratio = len(speech_segs) / len(relevant)
        # Low-moderate speech is ideal for nature
        if speech_ratio <= 0.3:
            scores.append(0.9)  # Mostly ambient — great
        elif speech_ratio <= 0.5:
            scores.append(0.8)  # Some narration — good
        else:
            scores.append(0.5)  # Too talky for nature
        # Calm energy consistency
        energies = [seg.energy_avg for seg in relevant]
        if len(energies) >= 2:
            mean_e = sum(energies) / len(energies)
            variance = sum((e - mean_e) ** 2 for e in energies) / len(energies)
            # Low variance = calm = good for nature
            scores.append(max(0.3, 1.0 - variance * 8))
        else:
            scores.append(0.6)
        # Ambient audio presence
        scores.append(0.8)

    elif genre == "kids_music":
        # Kids Music: reward continuous audio, music presence, rhythm
        silence_segs = [s for s in relevant if s.has_silence]
        silence_ratio = len(silence_segs) / len(relevant)
        music_count = sum(1 for seg in relevant if getattr(seg, 'has_music', False))
        music_ratio = music_count / len(relevant)

        # All-silence check: distinguish "silent failure" from "pure music"
        if silence_ratio >= 0.95 and music_ratio < 0.1:
            # Likely data issue — no real audio detected
            scores.append(0.2)
            scores.append(0.2)
        else:
            # Low silence = continuous music
            scores.append(max(0.3, 1.0 - silence_ratio * 2.0))
            # Music presence = good
            scores.append(0.5 + music_ratio * 0.5)
        # Energy consistency (rhythm)
        energies = [seg.energy_avg for seg in relevant]
        if len(energies) >= 2:
            mean_e = sum(energies) / len(energies)
            variance = sum((e - mean_e) ** 2 for e in energies) / len(energies)
            scores.append(max(0.3, 1.0 - variance * 10))
        else:
            scores.append(0.6)

    else:
        # ── Default: speech genres (talking_head, podcast, interview, etc.) ──

        # Energy consistency (smooth delivery = good)
        energies = [seg.energy_avg for seg in relevant if seg.has_speech]
        if len(energies) >= 2:
            mean_e = sum(energies) / len(energies)
            variance = sum((e - mean_e) ** 2 for e in energies) / len(energies)
            scores.append(max(0.0, 1.0 - variance * 10))
        else:
            scores.append(0.6)

        # Has speech
        has_any_speech = any(seg.has_speech for seg in relevant)
        if profile.require_speech:
            scores.append(1.0 if has_any_speech else 0.1)
        else:
            scores.append(0.8)

        # Music contamination (bad for speech genres)
        music_count = sum(1 for seg in relevant if getattr(seg, 'has_music', False))
        music_ratio = music_count / len(relevant)
        if music_ratio > 0.5 and profile.require_speech:
            scores.append(0.5)
        else:
            scores.append(0.9)

    return sum(scores) / len(scores) if scores else 0.5
