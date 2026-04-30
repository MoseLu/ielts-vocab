from __future__ import annotations

import math
import subprocess
import wave
from array import array
from pathlib import Path

import imageio_ffmpeg


FALLBACK_PROVIDER = 'fallback-acoustic'
FALLBACK_MODEL = 'local-acoustic-v1'
_SAMPLE_RATE = 16000
_FRAME_SIZE = 320
_MAX_SECONDS = 12
_MAX_DTW_FRAMES = 260


class AcousticFallbackError(RuntimeError):
    pass


def _decode_with_wave(path: str) -> list[int]:
    try:
        with wave.open(path, 'rb') as reader:
            channels = reader.getnchannels()
            sample_width = reader.getsampwidth()
            frame_rate = reader.getframerate()
            raw = reader.readframes(min(reader.getnframes(), frame_rate * _MAX_SECONDS))
    except (wave.Error, OSError) as exc:
        raise AcousticFallbackError('audio decode failed') from exc
    if sample_width != 2:
        raise AcousticFallbackError('unsupported wav sample width')
    samples = array('h')
    samples.frombytes(raw)
    if channels > 1:
        samples = array('h', [
            int(sum(samples[index:index + channels]) / channels)
            for index in range(0, len(samples), channels)
        ])
    if frame_rate == _SAMPLE_RATE:
        return list(samples)
    return _resample_linear(list(samples), frame_rate, _SAMPLE_RATE)


def _decode_audio(path: str) -> list[int]:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    command = [
        ffmpeg,
        '-v',
        'error',
        '-i',
        path,
        '-ac',
        '1',
        '-ar',
        str(_SAMPLE_RATE),
        '-t',
        str(_MAX_SECONDS),
        '-f',
        's16le',
        'pipe:1',
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=10,
        )
    except (subprocess.SubprocessError, OSError):
        return _decode_with_wave(path)
    samples = array('h')
    samples.frombytes(completed.stdout)
    return list(samples)


def _resample_linear(samples: list[int], source_rate: int, target_rate: int) -> list[int]:
    if source_rate <= 0 or target_rate <= 0 or not samples:
        return []
    target_length = max(1, int(len(samples) * target_rate / source_rate))
    if target_length == 1:
        return [samples[0]]
    scale = (len(samples) - 1) / (target_length - 1)
    result = []
    for index in range(target_length):
        source_position = index * scale
        left = int(source_position)
        right = min(len(samples) - 1, left + 1)
        ratio = source_position - left
        result.append(int(samples[left] * (1 - ratio) + samples[right] * ratio))
    return result


def _trim_silence(samples: list[int]) -> list[int]:
    if not samples:
        return []
    threshold = max(500, int(max(abs(sample) for sample in samples) * 0.08))
    start = 0
    end = len(samples)
    while start < end and abs(samples[start]) < threshold:
        start += 1
    while end > start and abs(samples[end - 1]) < threshold:
        end -= 1
    return samples[start:end]


def _frame_features(samples: list[int]) -> list[tuple[float, float]]:
    samples = _trim_silence(samples)
    if len(samples) < _FRAME_SIZE:
        return []
    features: list[tuple[float, float]] = []
    for start in range(0, len(samples) - _FRAME_SIZE + 1, _FRAME_SIZE):
        frame = samples[start:start + _FRAME_SIZE]
        rms = math.sqrt(sum(sample * sample for sample in frame) / len(frame)) / 32768.0
        crossings = sum(
            1
            for index in range(1, len(frame))
            if (frame[index - 1] < 0 <= frame[index]) or (frame[index - 1] >= 0 > frame[index])
        )
        features.append((rms, crossings / len(frame)))
    max_rms = max((rms for rms, _ in features), default=0.0)
    if max_rms <= 0:
        return []
    normalized = [(rms / max_rms, zcr) for rms, zcr in features]
    return _downsample_features(normalized)


def _downsample_features(features: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(features) <= _MAX_DTW_FRAMES:
        return features
    bucket_size = len(features) / _MAX_DTW_FRAMES
    result = []
    for bucket_index in range(_MAX_DTW_FRAMES):
        start = int(bucket_index * bucket_size)
        end = max(start + 1, int((bucket_index + 1) * bucket_size))
        bucket = features[start:end]
        result.append((
            sum(item[0] for item in bucket) / len(bucket),
            sum(item[1] for item in bucket) / len(bucket),
        ))
    return result


def _feature_distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return abs(a[0] - b[0]) * 0.55 + abs(a[1] - b[1]) * 0.45


def _dtw_distance(a: list[tuple[float, float]], b: list[tuple[float, float]]) -> float:
    if not a or not b:
        return 1.0
    previous = [math.inf] * (len(b) + 1)
    previous[0] = 0.0
    for item_a in a:
        current = [math.inf] * (len(b) + 1)
        for index_b, item_b in enumerate(b, start=1):
            cost = _feature_distance(item_a, item_b)
            current[index_b] = cost + min(previous[index_b], current[index_b - 1], previous[index_b - 1])
        previous = current
    return previous[-1] / max(len(a), len(b))


def _duration_seconds(samples: list[int]) -> float:
    return len(samples) / _SAMPLE_RATE


def _score_without_reference(user_samples: list[int]) -> dict:
    duration = _duration_seconds(user_samples)
    features = _frame_features(user_samples)
    score = 60 if duration >= 0.4 and features else 35
    summary = 'AI 评分暂不可用，已完成基础录音检查；缺少参考音频，无法进行发音相似度比对。'
    return _build_payload(score=score, confidence='low', summary=summary, weak_segments=['reference'])


def _build_payload(*, score: int, confidence: str, summary: str, weak_segments: list[str]) -> dict:
    return {
        'score': max(0, min(85, int(round(score)))),
        'transcript': '',
        'feedback': {
            'summary': summary,
            'stress': '基础评分仅比较录音轮廓，暂不判断具体重音。',
            'vowel': '基础评分无法稳定定位单个元音问题。',
            'consonant': '基础评分无法稳定定位单个辅音问题。',
            'ending': '基础评分无法稳定判断词尾细节。',
            'rhythm': '请尽量贴近参考音频的时长和节奏。',
        },
        'weak_segments': weak_segments[:4],
        'provider': FALLBACK_PROVIDER,
        'model': FALLBACK_MODEL,
        'confidence': confidence,
    }


def score_follow_read_acoustic_fallback(
    *,
    audio_path: str,
    reference_audio_path: str | None,
    word: str,
    phonetic: str | None,
) -> dict:
    _ = word, phonetic
    user_samples = _decode_audio(audio_path)
    if not user_samples:
        raise AcousticFallbackError('empty user audio')
    if not reference_audio_path:
        return _score_without_reference(user_samples)
    reference_samples = _decode_audio(reference_audio_path)
    if not reference_samples:
        return _score_without_reference(user_samples)
    user_features = _frame_features(user_samples)
    reference_features = _frame_features(reference_samples)
    if not user_features or not reference_features:
        return _score_without_reference(user_samples)

    distance = _dtw_distance(user_features, reference_features)
    acoustic_score = max(0.0, 100.0 - distance * 350.0)
    user_duration = _duration_seconds(user_samples)
    reference_duration = max(0.1, _duration_seconds(reference_samples))
    duration_similarity = max(0.0, 1.0 - min(1.0, abs(user_duration - reference_duration) / reference_duration))
    score = int(round(acoustic_score * 0.55 + duration_similarity * 100.0 * 0.45))
    weak_segments = []
    if duration_similarity < 0.65:
        weak_segments.append('duration')
    if acoustic_score < 70:
        weak_segments.append('rhythm')
    confidence = 'medium' if score >= 70 and duration_similarity >= 0.75 else 'low'
    summary = 'AI 评分暂不可用，已使用参考音频完成基础声学相似度评分。'
    return _build_payload(score=score, confidence=confidence, summary=summary, weak_segments=weak_segments)
