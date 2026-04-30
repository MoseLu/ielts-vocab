from __future__ import annotations

import math
import wave
from pathlib import Path

from platform_sdk.follow_read_acoustic_fallback import score_follow_read_acoustic_fallback


def _write_tone(path: Path, *, frequency: float, seconds: float = 1.0) -> None:
    sample_rate = 16000
    sample_count = int(sample_rate * seconds)
    with wave.open(str(path), 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        frames = []
        for index in range(sample_count):
            sample = int(10000 * math.sin(2 * math.pi * frequency * index / sample_rate))
            frames.append(sample.to_bytes(2, 'little', signed=True))
        writer.writeframes(b''.join(frames))


def test_acoustic_fallback_scores_similar_audio_higher_than_mismatched_audio(tmp_path):
    reference_path = tmp_path / 'reference.wav'
    matching_path = tmp_path / 'matching.wav'
    mismatched_path = tmp_path / 'mismatched.wav'
    _write_tone(reference_path, frequency=440, seconds=1.0)
    _write_tone(matching_path, frequency=440, seconds=1.0)
    _write_tone(mismatched_path, frequency=880, seconds=0.35)

    matching = score_follow_read_acoustic_fallback(
        audio_path=str(matching_path),
        reference_audio_path=str(reference_path),
        word='demonstrate',
        phonetic='/demo/',
    )
    mismatched = score_follow_read_acoustic_fallback(
        audio_path=str(mismatched_path),
        reference_audio_path=str(reference_path),
        word='demonstrate',
        phonetic='/demo/',
    )

    assert matching['provider'] == 'fallback-acoustic'
    assert matching['score'] >= 75
    assert matching['score'] > mismatched['score']
    assert mismatched['score'] < 70


def test_acoustic_fallback_without_reference_returns_basic_recording_score(tmp_path):
    audio_path = tmp_path / 'user.wav'
    _write_tone(audio_path, frequency=440, seconds=1.0)

    result = score_follow_read_acoustic_fallback(
        audio_path=str(audio_path),
        reference_audio_path=None,
        word='demonstrate',
        phonetic='/demo/',
    )

    assert result['provider'] == 'fallback-acoustic'
    assert result['score'] == 60
    assert result['confidence'] == 'low'
    assert '参考音频' in result['feedback']['summary']
