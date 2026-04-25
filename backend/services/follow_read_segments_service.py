from __future__ import annotations

import json
import re

from services.follow_read_segments_manifest_service import (
    follow_read_sidecar_path,
    load_follow_read_sidecar_entries,
    load_follow_read_source_words,
    load_global_follow_read_sidecar_entries,
    reset_follow_read_segment_manifest_caches,
)
from services.word_tts import normalize_azure_ipa, normalize_word_key, split_azure_ipa_syllables


FOLLOW_READ_SEGMENT_BOOK_IDS = (
    'ielts_reading_premium',
    'ielts_listening_premium',
)
FOLLOW_READ_SEGMENT_SCHEMA_VERSION = 1
FOLLOW_READ_SEGMENT_MANIFEST_VERSION = 'premium-v1'

_WORD_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*")
_VOWEL_GROUP_RE = re.compile(r'[aeiouy]+', re.IGNORECASE)
_STRESS_MARKS = {'\u02c8', '\u02cc'}
_IPA_VOWELS = set('aeiouyɑɒæəɛɜɝɚɨɪʊʌɔœøɐʉʏɯɤ')
_IPA_NUCLEUS_CONTINUATIONS = {'ː', 'ˑ', '̯'}
_VALID_ONSET2 = {
    'bl', 'br', 'ch', 'cl', 'cr', 'dr', 'dw', 'fl', 'fr', 'gl', 'gr', 'kl', 'kn',
    'ph', 'pl', 'pr', 'sc', 'sh', 'sk', 'sl', 'sm', 'sn', 'sp', 'st', 'sw', 'th', 'tr', 'tw', 'wh', 'wr',
}
_VALID_ONSET3 = {'str', 'scr', 'spr', 'spl', 'squ', 'thr', 'chr'}
_COUNT2_SUFFIXES = ('ence', 'ance', 'tion', 'sion', 'ment', 'ness', 'less')
_AUDIO_PHONETIC_OVERRIDES = {
    'no': 'nəʊ',
    'me': 'miː',
    'non': 'nɔn',
}
_LEGACY_SEGMENT_OVERRIDES = {
    'phenomenon': [
        {'letters': 'phe', 'phonetic': 'fə', 'audio_phonetic': 'fʌ', 'fallback_text': 'fuh'},
        {'letters': 'no', 'phonetic': 'nə', 'audio_phonetic': 'nəʊ'},
        {'letters': 'me', 'phonetic': 'mɪ', 'audio_phonetic': 'miː'},
        {'letters': 'non', 'phonetic': 'nən', 'audio_phonetic': 'nɔn'},
    ],
    'oriented': [
        {'letters': 'o', 'phonetic': 'ˈɔː', 'audio_phonetic': 'ɔː'}, {'letters': 'ri', 'phonetic': 'ri', 'audio_phonetic': 'ri'},
        {'letters': 'en', 'phonetic': 'en', 'audio_phonetic': 'en'}, {'letters': 'ted', 'phonetic': 'tɪd', 'audio_phonetic': 'tɪd'},
    ],
}
def reset_follow_read_segment_caches() -> None:
    reset_follow_read_segment_manifest_caches()


def supported_follow_read_book_ids() -> tuple[str, ...]:
    return FOLLOW_READ_SEGMENT_BOOK_IDS

def build_follow_read_entry_key(word: str, phonetic: str | None) -> str:
    return f'{normalize_word_key(word)}|{normalize_azure_ipa(phonetic)}'

def _without_stress(value: str) -> str:
    return ''.join(char for char in value if char not in _STRESS_MARKS)

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
    if len(segments) == 1:
        segments = _split_hiatus_vowel_run(normalized)
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
        selected = [round(index * (len(vowel_groups) - 1) / (count - 1)) for index in range(count)]
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
def _single_syllable_letter_boundaries(token: str) -> list[int]:
    if len(token) <= 1:
        return [0, len(token)]
    vowel_groups = list(_VOWEL_GROUP_RE.finditer(token))
    if not vowel_groups:
        return _even_boundaries(len(token), 2)
    first_group = vowel_groups[0]
    if first_group.start() > 0:
        boundary = first_group.start()
    elif first_group.end() < len(token):
        boundary = first_group.end()
    else:
        boundary = 1
    boundary = max(1, min(len(token) - 1, boundary))
    return [0, boundary, len(token)]
def _suffix_boundaries(token: str, count: int) -> list[int] | None:
    if count != 2 or len(token) <= 4:
        return None
    lower = token.lower()
    for suffix in _COUNT2_SUFFIXES:
        if lower.endswith(suffix) and len(token) > len(suffix):
            return [0, len(token) - len(suffix), len(token)]
    return None


def _letter_boundaries(token: str, count: int, *, force_onset_rime: bool = False) -> list[int]:
    if not token:
        return [0, 0]
    if force_onset_rime:
        return _single_syllable_letter_boundaries(token)
    if count <= 1:
        return [0, len(token)]
    return (
        _suffix_boundaries(token, count)
        or
        _syllable_boundaries(token, count)
        or _vowel_boundaries(token, count)
        or _even_boundaries(len(token), count)
    )


def _distribute_counts(total_segments: int, token_lengths: list[int]) -> list[int]:
    lengths = [max(1, length) for length in token_lengths]
    if not lengths:
        return []
    if total_segments <= len(lengths):
        return [1 if index < total_segments else 0 for index in range(len(lengths))]

    total_length = sum(lengths)
    raw_counts = [max(1, total_segments * length // total_length) for length in lengths]
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


def _phonetic_nuclei(phonetic: str) -> list[tuple[int, int]]:
    nuclei: list[tuple[int, int]] = []
    index = 0
    while index < len(phonetic):
        if phonetic[index] in _IPA_VOWELS:
            start = index
            index += 1
            while index < len(phonetic) and (
                phonetic[index] in _IPA_VOWELS or phonetic[index] in _IPA_NUCLEUS_CONTINUATIONS
            ):
                index += 1
            nuclei.append((start, index))
            continue
        index += 1
    return nuclei


def _single_syllable_phonetic_segments(phonetic: str) -> list[str]:
    normalized = _without_stress(normalize_azure_ipa(phonetic))
    if not normalized:
        return []
    nuclei = _phonetic_nuclei(normalized)
    if nuclei:
        first_start, first_end = nuclei[0]
        if first_start > 0:
            parts = [normalized[:first_start], normalized[first_start:]]
        else:
            boundary = first_end if first_end < len(normalized) else max(1, len(normalized) // 2)
            parts = [normalized[:boundary], normalized[boundary:]]
    else:
        boundary = max(1, len(normalized) // 2)
        parts = [normalized[:boundary], normalized[boundary:]]
    if all(parts):
        return parts
    boundary = max(1, len(normalized) // 2)
    return [normalized[:boundary], normalized[boundary:]]


def _split_hiatus_vowel_run(phonetic: str) -> list[str]:
    normalized = _without_stress(normalize_azure_ipa(phonetic))
    for index in range(1, len(normalized)):
        if normalized[index] == 'ə' and normalized[index - 1] in _IPA_VOWELS:
            left = normalized[:index]
            right = normalized[index:]
            if left and right:
                return [left, right]
    return [normalized]


def _normalize_audio_chunk_phonetic(letters: str, phonetic_segment: str) -> str:
    normalized_segment = _without_stress(str(phonetic_segment or '').strip())
    letters_key = letters.strip().lower()
    if letters_key == 'ence' and normalized_segment in {'əns', 'ɛns'}:
        return 'ɛns'
    return _AUDIO_PHONETIC_OVERRIDES.get(letters_key, normalized_segment or letters)


def _segment_fallback_text(letters: str, audio_phonetic: str) -> str:
    normalized_letters = letters.strip().lower()
    normalized_phonetic = _without_stress(normalize_azure_ipa(audio_phonetic))
    if normalized_letters == 'phe':
        return 'fuh'
    if normalized_letters == 'sci':
        return 'sigh'
    if normalized_letters == 'ence' and normalized_phonetic in {'əns', 'ɛns'}:
        return 'ens'
    if normalized_letters == 'ph':
        return 'f'
    if normalized_letters == 'tion' and normalized_phonetic.startswith('ʃ'):
        return 'shun'
    if normalized_phonetic in {'ə', 'ɚ', 'ər'}:
        return 'uh'
    return ''


def _legacy_override_segments(word: str) -> list[dict] | None:
    override = _LEGACY_SEGMENT_OVERRIDES.get(re.sub(r'\s+', ' ', word.strip().lower()))
    if not override:
        return None
    return [{**segment} for segment in override]


def generate_auto_follow_read_segments(word: str, phonetic: str | None) -> list[dict]:
    trimmed_word = str(word or '').strip()
    if not trimmed_word:
        return []

    legacy_segments = _legacy_override_segments(trimmed_word)
    if legacy_segments:
        return legacy_segments

    tokens = _word_token_spans(trimmed_word)
    phonetic_groups = _split_phonetic_word_groups(phonetic)
    if not phonetic_groups:
        return []

    if len(phonetic_groups) == len(tokens):
        grouped_segments = phonetic_groups
    else:
        flat_segments = [segment for group in phonetic_groups for segment in group]
        counts = _distribute_counts(len(flat_segments), [end - start for start, end, _ in tokens])
        grouped_segments = []
        cursor = 0
        for count in counts:
            grouped_segments.append(flat_segments[cursor:cursor + count])
            cursor += count

    payloads: list[dict] = []
    for token_index, (token_start, _token_end, token) in enumerate(tokens):
        group = grouped_segments[token_index] if token_index < len(grouped_segments) else []
        if not group:
            continue
        force_onset_rime = len(tokens) == 1 and len(group) == 1 and token.isalpha() and len(token) > 1
        if force_onset_rime:
            group = _single_syllable_phonetic_segments(group[0])
        boundaries = _letter_boundaries(token, len(group), force_onset_rime=force_onset_rime)
        for segment_index, phonetic_segment in enumerate(group):
            start = token_start + boundaries[segment_index]
            end = token_start + boundaries[segment_index + 1]
            letters = trimmed_word[start:end]
            normalized_phonetic = str(phonetic_segment or '').strip() or letters
            audio_phonetic = _normalize_audio_chunk_phonetic(letters, phonetic_segment)
            segment = {
                'letters': letters,
                'phonetic': normalized_phonetic,
                'audio_phonetic': audio_phonetic,
            }
            fallback_text = _segment_fallback_text(letters, audio_phonetic)
            if fallback_text:
                segment['fallback_text'] = fallback_text
            payloads.append(segment)
    payloads = [segment for segment in payloads if segment.get('letters')]
    joined_letters = re.sub(r'\s+', '', ''.join(segment['letters'] for segment in payloads))
    expected_letters = re.sub(r'\s+', '', normalize_word_key(trimmed_word))
    if len(payloads) >= 2 and joined_letters == expected_letters:
        return payloads
    if len(tokens) <= 1:
        return payloads

    normalized_phonetic = normalize_azure_ipa(phonetic)
    focus_index = max(range(len(tokens)), key=lambda index: len(tokens[index][2]))
    fallback_segments: list[dict] = []
    for token_index, (_token_start, _token_end, token) in enumerate(tokens):
        token_phonetic = normalized_phonetic if token_index == focus_index and normalized_phonetic else token
        audio_phonetic = _normalize_audio_chunk_phonetic(token, token_phonetic)
        segment = {
            'letters': token,
            'phonetic': token_phonetic,
            'audio_phonetic': audio_phonetic,
        }
        fallback_text = _segment_fallback_text(token, audio_phonetic)
        if fallback_text:
            segment['fallback_text'] = fallback_text
        fallback_segments.append(segment)
    return fallback_segments
def _build_payloads_from_segments(word: str, segments: list[dict]) -> list[dict]:
    payloads: list[dict] = []
    cursor = 0
    lower_word = word.lower()
    for index, segment in enumerate(segments):
        letters = str(segment.get('letters') or '').strip()
        if not letters:
            return []
        lowered_letters = letters.lower()
        if lower_word[cursor:cursor + len(letters)] == lowered_letters:
            start = cursor
        else:
            start = lower_word.find(lowered_letters, cursor)
        if start < 0:
            return []
        end = start + len(letters)
        cursor = end
        payload = {
            'id': f'seg-{index}',
            'letter_start': start,
            'letter_end': end,
            'letters': word[start:end],
            'phonetic': str(segment.get('phonetic') or segment.get('audio_phonetic') or letters),
            'audio_phonetic': str(segment.get('audio_phonetic') or segment.get('phonetic') or letters),
        }
        fallback_text = str(segment.get('fallback_text') or '').strip()
        if fallback_text:
            payload['fallback_text'] = fallback_text
        payloads.append(payload)
    return payloads
def lookup_follow_read_segments(word: str, phonetic: str | None, *, book_id: str | None = None) -> list[dict] | None:
    key = build_follow_read_entry_key(word, phonetic)
    if book_id:
        entries = load_follow_read_sidecar_entries(book_id)
        if key in entries:
            return [{**segment} for segment in entries[key].get('segments', [])]
    global_entries = load_global_follow_read_sidecar_entries(FOLLOW_READ_SEGMENT_BOOK_IDS)
    if key in global_entries:
        return [{**segment} for segment in global_entries[key].get('segments', [])]
    return None
def build_follow_read_segment_payloads(
    word: str,
    phonetic: str | None,
    *,
    follow_read_segments: list[dict] | None = None,
    book_id: str | None = None,
) -> list[dict]:
    trimmed_word = str(word or '').strip()
    segment_specs = (
        [{**segment} for segment in follow_read_segments]
        if follow_read_segments
        else lookup_follow_read_segments(trimmed_word, phonetic, book_id=book_id)
    )
    if segment_specs:
        payloads = _build_payloads_from_segments(trimmed_word, segment_specs)
        if payloads:
            return payloads

    segment_specs = generate_auto_follow_read_segments(trimmed_word, phonetic)
    if segment_specs:
        payloads = _build_payloads_from_segments(trimmed_word, segment_specs)
        if payloads:
            return payloads

    normalized_phonetic = normalize_azure_ipa(phonetic) or trimmed_word
    return [{
        'id': 'seg-0',
        'letter_start': 0,
        'letter_end': len(trimmed_word),
        'letters': trimmed_word,
        'phonetic': normalized_phonetic,
        'audio_phonetic': normalized_phonetic,
    }]
def attach_follow_read_segments(book_id: str, words: list[dict]) -> list[dict]:
    entries = load_follow_read_sidecar_entries(book_id)
    if not entries:
        return words
    output = []
    for word in words:
        key = build_follow_read_entry_key(str(word.get('word') or ''), str(word.get('phonetic') or ''))
        entry = entries.get(key)
        if not entry:
            output.append(word)
            continue
        output.append({
            **word,
            'follow_read_segments': [{**segment} for segment in entry.get('segments', [])],
        })
    return output
def build_follow_read_sidecar(book_id: str) -> dict:
    words = load_follow_read_source_words(book_id)
    entries: dict[str, dict] = {}
    for word in words:
        key = build_follow_read_entry_key(word['word'], word['phonetic'])
        if key in entries:
            continue
        segments = generate_auto_follow_read_segments(word['word'], word['phonetic'])
        if not segments:
            continue
        entries[key] = {
            'word': word['word'],
            'phonetic': normalize_azure_ipa(word['phonetic']),
            'segments': segments,
        }
    return {
        'version': FOLLOW_READ_SEGMENT_SCHEMA_VERSION,
        'manifest_version': FOLLOW_READ_SEGMENT_MANIFEST_VERSION,
        'book_id': book_id,
        'entry_count': len(entries),
        'entries': dict(sorted(entries.items())),
    }
def write_follow_read_sidecar(book_id: str) -> Path:
    payload = build_follow_read_sidecar(book_id)
    path = follow_read_sidecar_path(book_id)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    reset_follow_read_segment_caches()
    return path
