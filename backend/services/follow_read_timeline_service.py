from __future__ import annotations

import hashlib
import math
import re
from pathlib import Path
from typing import Iterable
from urllib.parse import urlencode

from services.follow_read_chunk_audio_service import (
    FOLLOW_READ_CHUNK_AUDIO_CACHE_TAG,
    FOLLOW_READ_SEGMENT_PAUSE_MS,
    FOLLOW_READ_STAGE_PAUSE_MS,
    generate_follow_read_three_pass_audio_bytes,
)
from services.follow_read_segments_service import build_follow_read_segment_payloads
from services.word_tts import (
    normalize_azure_ipa,
    is_probably_valid_mp3_file,
    remove_invalid_cached_audio,
    split_azure_ipa_syllables,
    write_bytes_atomically,
)


FOLLOW_READ_AUDIO_PLAYBACK_RATE = 1.0
FOLLOW_READ_AUDIO_PROFILE = 'full_chunk_full'
_MIN_SEGMENT_SPOKEN_DURATION_MS = 900
_SEGMENT_BASE_DURATION_MS = 380
_LETTER_DURATION_MS = 22
_MIN_FULL_WORD_DURATION_MS = 760
_FULL_WORD_BASE_DURATION_MS = 360
_FULL_WORD_LETTER_DURATION_MS = 72
_WORD_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*")
_VOWEL_GROUP_RE = re.compile(r'[aeiouy]+', re.IGNORECASE)
_STRESS_MARKS = {'\u02c8', '\u02cc'}
_FOLLOW_READ_SPLIT_AUDIO_PROFILE = 'full_chunk_full_merged'
_FOLLOW_READ_SEQUENCE_LABEL = '完整示范 -> 拆分跟读 -> 完整回放'
_VALID_ONSET2 = {
    'bl', 'br', 'ch', 'cl', 'cr', 'dr', 'dw', 'fl', 'fr', 'gl', 'gr', 'kl', 'kn',
    'ph', 'pl', 'pr', 'sc', 'sh', 'sk', 'sl', 'sm', 'sn', 'sp', 'st', 'sw', 'th', 'tr', 'tw', 'wh', 'wr',
}
_VALID_ONSET3 = {'str', 'scr', 'spr', 'spl', 'squ', 'thr', 'chr'}
_FOLLOW_READ_AUDIO_PHONETIC_OVERRIDES = {
    'no': 'nəʊ',
    'me': 'miː',
    'non': 'nɒn',
}
_FOLLOW_READ_AUDIO_FALLBACK_TEXT_OVERRIDES = {
    'phe': 'fuh',
    'sci': 'sigh',
    'ence': 'ens',
}
_FOLLOW_READ_SEGMENT_OVERRIDES = {
    'phenomenon': [
        {'letters': 'phe', 'phonetic': 'fə', 'audio_phonetic': 'fʌ'},
        {'letters': 'no', 'phonetic': 'nə', 'audio_phonetic': 'nəʊ'},
        {'letters': 'me', 'phonetic': 'mɪ', 'audio_phonetic': 'miː'},
        {'letters': 'non', 'phonetic': 'nən', 'audio_phonetic': 'nɒn'},
    ],
    'science': [
        {'letters': 'sci', 'phonetic': 'saɪ', 'audio_phonetic': 'saɪ'},
        {'letters': 'ence', 'phonetic': 'əns', 'audio_phonetic': 'ɛns'},
    ],
}


def _strip_ipa_wrapper(value: str) -> str:
    return value.strip().strip('/[]').strip()


def _split_phonetic_word_groups(phonetic: str | None) -> list[list[str]]:
    normalized = normalize_azure_ipa(phonetic)
    if not normalized:
        return []

    raw_groups = [
        _strip_ipa_wrapper(part)
        for part in re.split(r'\s+', normalized)
        if _strip_ipa_wrapper(part)
    ]
    if len(raw_groups) > 1:
        return [split_azure_ipa_syllables(group) or [group] for group in raw_groups]

    segments = split_azure_ipa_syllables(normalized) or [normalized]
    return [segments]


def _word_token_spans(word: str) -> list[tuple[int, int, str]]:
    tokens = [(match.start(), match.end(), match.group(0)) for match in _WORD_TOKEN_RE.finditer(word)]
    return tokens or [(0, len(word), word)]


def _even_boundaries(length: int, count: int) -> list[int]:
    if count <= 1:
        return [0, length]
    boundaries = [0]
    for index in range(1, count):
        boundary = round(length * index / count)
        boundary = max(boundaries[-1] + 1, min(length - (count - index), boundary))
        boundaries.append(boundary)
    boundaries.append(length)
    return boundaries


def _vowel_boundaries(token: str, count: int) -> list[int] | None:
    vowel_groups = list(_VOWEL_GROUP_RE.finditer(token))
    if count <= 1 or len(vowel_groups) < count:
        return None

    if count == 2:
        selected = [0, len(vowel_groups) - 1]
    else:
        selected = [
            round(index * (len(vowel_groups) - 1) / (count - 1))
            for index in range(count)
        ]
    if len(set(selected)) != count:
        return None

    boundaries = [0]
    for left_group_index, right_group_index in zip(selected, selected[1:]):
        left = vowel_groups[left_group_index]
        right = vowel_groups[right_group_index]
        cluster = token[left.end():right.start()]
        boundary = left.end() if len(cluster) <= 1 else right.start() - 1
        boundary = max(boundaries[-1] + 1, min(len(token) - 1, boundary))
        boundaries.append(boundary)
    boundaries.append(len(token))
    return boundaries


def _is_token_vowel(token: str, index: int) -> bool:
    char = token[index]
    if char in 'aeiou':
        return True
    return char == 'y' and index > 0 and token[index - 1] not in 'aeiou'


def _syllable_boundaries(token: str, count: int) -> list[int] | None:
    if count <= 1 or len(token) <= 2 or not token.isalpha():
        return None

    lower = token.lower()
    vowel_groups: list[tuple[int, int]] = []
    index = 0
    while index < len(lower):
        if _is_token_vowel(lower, index):
            end = index + 1
            while end < len(lower) and _is_token_vowel(lower, end):
                end += 1
            vowel_groups.append((index, end))
            index = end
            continue
        index += 1

    if len(vowel_groups) <= 1:
        return None

    split_points: list[int] = []
    for group_index, (_group_start, group_end) in enumerate(vowel_groups[:-1]):
        next_start = vowel_groups[group_index + 1][0]
        gap = next_start - group_end
        consonants = lower[group_end:next_start]

        if gap <= 1:
            split_points.append(group_end)
        elif gap == 2:
            split_points.append(group_end if consonants in _VALID_ONSET2 else group_end + 1)
        else:
            split_points.append(
                group_end + 1
                if consonants in _VALID_ONSET3 or consonants[1:] in _VALID_ONSET2
                else group_end + 1,
            )

    split_points = split_points[:count - 1]
    if len(split_points) != count - 1:
        return None
    return [0, *split_points, len(token)]


def _letter_boundaries(token: str, count: int) -> list[int]:
    if not token:
        return [0, 0]
    if count <= 1:
        return [0, len(token)]
    return (
        _syllable_boundaries(token, count)
        or _vowel_boundaries(token, count)
        or _even_boundaries(len(token), count)
    )


def _distribute_counts(total_segments: int, token_lengths: Iterable[int]) -> list[int]:
    lengths = [max(1, length) for length in token_lengths]
    if not lengths:
        return []
    if total_segments <= len(lengths):
        return [1 if index < total_segments else 0 for index in range(len(lengths))]

    total_length = sum(lengths)
    raw_counts = [max(1, math.floor(total_segments * length / total_length)) for length in lengths]
    while sum(raw_counts) < total_segments:
        target = max(range(len(lengths)), key=lambda index: lengths[index] / raw_counts[index])
        raw_counts[target] += 1
    while sum(raw_counts) > total_segments:
        target = max(
            (index for index, count in enumerate(raw_counts) if count > 1),
            key=lambda index: raw_counts[index] / lengths[index],
        )
        raw_counts[target] -= 1
    return raw_counts


def _without_stress(value: str) -> str:
    return ''.join(char for char in value if char not in _STRESS_MARKS)


def _follow_read_split_cache_dir() -> Path:
    cache_dir = Path(__file__).resolve().parents[1] / 'word_tts_cache' / 'follow_read_chunks'
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir


def _follow_read_chunk_cache_path(word: str, phonetic: str | None, segments: list[dict]) -> Path:
    digest_source = '|'.join([
        FOLLOW_READ_CHUNK_AUDIO_CACHE_TAG,
        word.strip().lower(),
        normalize_azure_ipa(phonetic),
        ';'.join(
            f"{segment['letters']}:{segment.get('audio_phonetic') or segment.get('phonetic')}:{segment.get('fallback_text') or ''}"
            for segment in segments
        ),
    ])
    digest = hashlib.md5(digest_source.encode('utf-8')).hexdigest()[:20]
    return _follow_read_split_cache_dir() / f'{digest}.mp3'


def _segment_override_payloads(word: str) -> list[dict] | None:
    normalized_word = re.sub(r'\s+', ' ', word.strip().lower())
    override_specs = _FOLLOW_READ_SEGMENT_OVERRIDES.get(normalized_word)
    if not override_specs:
        return None

    payloads: list[dict] = []
    cursor = 0
    for index, spec in enumerate(override_specs):
        letters = spec['letters']
        start = cursor
        end = start + len(letters)
        payloads.append({
            'id': f'seg-{index}',
            'letter_start': start,
            'letter_end': end,
            'letters': letters,
            'phonetic': spec['phonetic'],
            'audio_phonetic': spec.get('audio_phonetic') or spec['phonetic'],
        })
        cursor = end
    return payloads if cursor == len(word) else None


def _normalize_audio_chunk_phonetic(letters: str, phonetic_segment: str) -> str:
    normalized_segment = _without_stress(str(phonetic_segment or '').strip())
    return _FOLLOW_READ_AUDIO_PHONETIC_OVERRIDES.get(letters.strip().lower(), normalized_segment or letters)


def _build_segment_payloads(word: str, phonetic: str | None) -> list[dict]:
    return build_follow_read_segment_payloads(word, phonetic)


def _estimate_segment_spoken_duration_ms(segments: list[dict]) -> int:
    letter_count = sum(len(str(segment.get('letters') or '').strip()) for segment in segments)
    return max(
        _MIN_SEGMENT_SPOKEN_DURATION_MS,
        len(segments) * _SEGMENT_BASE_DURATION_MS + letter_count * _LETTER_DURATION_MS,
    )


def _estimate_full_word_duration_ms(word: str) -> int:
    letter_count = len(re.sub(r'[^A-Za-z]+', '', word))
    return max(
        _MIN_FULL_WORD_DURATION_MS,
        _FULL_WORD_BASE_DURATION_MS + letter_count * _FULL_WORD_LETTER_DURATION_MS,
    )


def _estimate_duration_ms(word: str, segments: list[dict]) -> int:
    spoken_duration_ms = _estimate_segment_spoken_duration_ms(segments)
    split_phase_duration_ms = spoken_duration_ms + max(0, len(segments) - 1) * FOLLOW_READ_SEGMENT_PAUSE_MS
    full_word_duration_ms = _estimate_full_word_duration_ms(word)
    return full_word_duration_ms * 2 + split_phase_duration_ms + FOLLOW_READ_STAGE_PAUSE_MS * 2


def _apply_timing(segments: list[dict], duration_ms: int) -> list[dict]:
    weights = [
        max(1.0, len(str(segment.get('letters') or '').strip()) + len(_without_stress(str(segment.get('phonetic') or ''))) * 0.35)
        for segment in segments
    ]
    total_weight = sum(weights) or 1.0
    cursor = 0
    timed_segments: list[dict] = []
    for index, (segment, weight) in enumerate(zip(segments, weights)):
        start_ms = cursor
        if index == len(segments) - 1:
            end_ms = duration_ms
        else:
            end_ms = min(duration_ms, round(cursor + duration_ms * weight / total_weight))
        timed_segments.append({
            **segment,
            'start_ms': start_ms,
            'end_ms': max(start_ms + 1, end_ms),
        })
        cursor = timed_segments[-1]['end_ms']
    return timed_segments


def _apply_follow_read_timing(word: str, segments: list[dict]) -> list[dict]:
    spoken_duration_ms = _estimate_segment_spoken_duration_ms(segments)
    full_word_duration_ms = _estimate_full_word_duration_ms(word)
    segment_phase_offset_ms = full_word_duration_ms + FOLLOW_READ_STAGE_PAUSE_MS
    timed_segments = _apply_timing(segments, spoken_duration_ms)
    return [
        {
            **segment,
            'start_ms': segment['start_ms'] + segment_phase_offset_ms + FOLLOW_READ_SEGMENT_PAUSE_MS * index,
            'end_ms': segment['end_ms'] + segment_phase_offset_ms + FOLLOW_READ_SEGMENT_PAUSE_MS * index,
        }
        for index, segment in enumerate(timed_segments)
    ]


def generate_follow_read_chunked_audio_bytes(*, word: str, phonetic: str | None = None) -> bytes:
    trimmed_word = word.strip()
    segments = _build_segment_payloads(trimmed_word, phonetic)
    cache_path = _follow_read_chunk_cache_path(trimmed_word, phonetic, segments)
    if cache_path.exists():
        if is_probably_valid_mp3_file(cache_path):
            return cache_path.read_bytes()
        remove_invalid_cached_audio(cache_path)

    stitched_audio = generate_follow_read_three_pass_audio_bytes(
        word=trimmed_word,
        phonetic=phonetic,
        segments=segments,
        fallback_text_overrides=_FOLLOW_READ_AUDIO_FALLBACK_TEXT_OVERRIDES,
    )
    write_bytes_atomically(cache_path, stitched_audio)
    return stitched_audio


def build_follow_read_payload(
    *,
    word: str,
    phonetic: str | None = None,
    definition: str | None = None,
    pos: str | None = None,
) -> dict:
    trimmed_word = word.strip()
    segments = _build_segment_payloads(trimmed_word, phonetic)
    estimated_duration_ms = _estimate_duration_ms(trimmed_word, segments)
    params = urlencode({'w': trimmed_word})
    chunk_params = {'w': trimmed_word}
    if phonetic:
        chunk_params['phonetic'] = phonetic
    chunk_audio_url = f"/api/tts/follow-read-chunked-audio?{urlencode(chunk_params)}"
    full_audio_url = f'/api/tts/word-audio?{params}'

    return {
        'word': trimmed_word,
        'phonetic': phonetic or '',
        'definition': definition or '',
        'pos': pos or '',
        'audio_url': full_audio_url,
        'audio_profile': FOLLOW_READ_AUDIO_PROFILE,
        'audio_playback_rate': FOLLOW_READ_AUDIO_PLAYBACK_RATE,
        'chunk_audio_url': chunk_audio_url,
        'chunk_audio_profile': _FOLLOW_READ_SPLIT_AUDIO_PROFILE,
        'estimated_duration_ms': estimated_duration_ms,
        'segments': _apply_follow_read_timing(trimmed_word, segments),
        'audio_sequence': [
            {
                'id': 'follow-read-track',
                'kind': 'follow',
                'label': _FOLLOW_READ_SEQUENCE_LABEL,
                'url': chunk_audio_url,
                'playback_rate': 1.0,
                'track_segments': True,
            },
        ],
    }
