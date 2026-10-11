from __future__ import annotations

import math
import wave
from pathlib import Path

from platform_sdk.follow_read_acoustic_fallback import (
    AcousticFallbackError,
    analyze_follow_read_audio_signal,
)


def _write_tone(path: Path, *, frequency: float = 440.0, seconds: float = 1.0, amplitude: int = 10000) -> None:
    sample_rate = 16000
    sample_count = int(sample_rate * seconds)
    with wave.open(str(path), 'wb') as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        frames = []
        for index in range(sample_count):
            sample = int(amplitude * math.sin(2 * math.pi * frequency * index / sample_rate))
            frames.append(sample.to_bytes(2, 'little', signed=True))
        writer.writeframes(b''.join(frames))


def test_follow_read_audio_signal_detects_voiced_recording(tmp_path):
    audio_path = tmp_path / 'user.wav'
    _write_tone(audio_path)

    signal = analyze_follow_read_audio_signal(str(audio_path))

    assert signal['duration_seconds'] >= 1
    assert signal['voiced_seconds'] >= 0.9
    assert signal['peak'] > 0.1
    assert signal['rms'] > 0.05
    assert signal['feature_count'] > 0


def test_follow_read_audio_signal_rejects_empty_file(tmp_path):
    audio_path = tmp_path / 'empty.wav'
    audio_path.write_bytes(b'')

    try:
        analyze_follow_read_audio_signal(str(audio_path))
    except AcousticFallbackError:
        pass
    else:
        raise AssertionError('expected empty audio to fail decoding')
