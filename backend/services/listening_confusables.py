from __future__ import annotations

import csv as csv_module
import json
import os
import re

from services import books_registry_service

_listening_confusable_index_cache: dict[str, list[dict]] | None = None
_high_value_listening_confusable_index_cache: dict[str, list[dict]] | None = None
_allowed_ielts_word_keys_cache: set[str] | None = None
_HIGH_VALUE_ONLY_THRESHOLD = 3
_EXCLUDED_IELTS_CONFUSABLE_BOOK_IDS = {'ielts_confusable_match'}
_IPA_STRIP_RE = re.compile(r'[/\[\]ˈˌ.: ]')
_MEANING_POS_RE = re.compile(
    r'\b(?:n|v|vi|vt|adj|adv|prep|pron|conj|aux|int|num|art|a)\.\s*',
    re.IGNORECASE,
)
_MEANING_NOISE_TOKENS = {'复数', '现在分词', '过去式', '过去分词', '第三人称单数', '比较级', '最高级', '口语', '英', '美'}


def get_listening_confusables_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..',
        '..',
        'vocabulary_data',
        'ielts_listening_confusables.json',
    )


def get_high_value_listening_confusables_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..',
        '..',
        'vocabulary_data',
        'ielts_high_value_confusables.json',
    )


def normalize_listening_confusable_key(word: str | None) -> str:
    normalized = str(word or '').strip().lower()
    normalized = normalized.replace('…', ' ')
    normalized = re.sub(r'\.+', ' ', normalized)
    normalized = re.sub(r"(?<=s)'(?=\s|$)", '', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = normalized.strip()
    normalized = re.sub(
        r"\s+(?:n|v|vi|vt|adj|adv|prep|conj|pron|det|num|phrase)\s*$",
        '',
        normalized,
    )
    return normalized.strip(" .'")


def _levenshtein(left: str, right: str) -> int:
    row = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        previous_diagonal = row[0]
        row[0] = left_index
        for right_index, right_char in enumerate(right, start=1):
            previous_value = row[right_index]
            row[right_index] = previous_diagonal if left_char == right_char else 1 + min(
                previous_diagonal,
                row[right_index],
                row[right_index - 1],
            )
            previous_diagonal = previous_value
    return row[len(right)]


def _common_prefix_length(left: str, right: str) -> int:
    prefix = 0
    while prefix < len(left) and prefix < len(right) and left[prefix] == right[prefix]:
        prefix += 1
    return prefix


def _normalize_meaning_parts(value: str | None) -> list[str]:
    cleaned = _MEANING_POS_RE.sub(' ', str(value or ''))
    cleaned = re.sub(r'[“”"()（）[\]【】]', ' ', cleaned)
    parts = re.split(r'[;；，,、/。！？\s]+', cleaned)
    return [
        part.strip()
        for part in parts
        if part.strip() and part.strip() not in _MEANING_NOISE_TOKENS and re.search(r'[\u4e00-\u9fff]', part)
    ]


def _meaning_similarity(left: str | None, right: str | None) -> float:
    left_parts = _normalize_meaning_parts(left)
    right_parts = _normalize_meaning_parts(right)
    if not left_parts or not right_parts:
        return 0.0

    left_set = set(left_parts)
    right_set = set(right_parts)
    if left_set & right_set:
        return 1.0

    best_score = 0.0
    for left_part in left_parts:
        left_bigrams = {left_part[index:index + 2] for index in range(max(0, len(left_part) - 1))} or {left_part}
        for right_part in right_parts:
            right_bigrams = {right_part[index:index + 2] for index in range(max(0, len(right_part) - 1))} or {right_part}
            union = left_bigrams | right_bigrams
            if not union:
                continue
            best_score = max(best_score, len(left_bigrams & right_bigrams) / len(union))
    return best_score


def _phonetic_similarity(left: str | None, right: str | None) -> float:
    left_value = _IPA_STRIP_RE.sub('', str(left or '').lower())
    right_value = _IPA_STRIP_RE.sub('', str(right or '').lower())
    if not left_value or not right_value:
        return 0.0
    return 1 - _levenshtein(left_value, right_value) / max(len(left_value), len(right_value))


def _listening_candidate_priority(word_entry: dict, candidate: dict, index: int) -> tuple[float, int]:
    target_word = normalize_listening_confusable_key(word_entry.get('word'))
    candidate_word = normalize_listening_confusable_key(candidate.get('word'))
    if not target_word or not candidate_word:
        return (-1.0, -index)

    edit_distance = _levenshtein(target_word, candidate_word)
    max_length = max(len(target_word), len(candidate_word), 1)
    spelling_similarity = 1 - edit_distance / max_length
    prefix_length = _common_prefix_length(target_word, candidate_word)
    phonetic_similarity = _phonetic_similarity(word_entry.get('phonetic'), candidate.get('phonetic'))
    meaning_similarity = _meaning_similarity(word_entry.get('definition'), candidate.get('definition'))
    same_pos = int(str(word_entry.get('pos') or '').strip() == str(candidate.get('pos') or '').strip())

    spelling_close = (
        spelling_similarity >= 0.8
        or (
            edit_distance <= 1
            and prefix_length >= min(3, max(2, min(len(target_word), len(candidate_word)) // 2))
        )
    )
    phonetic_close = phonetic_similarity >= 0.78
    meaning_close = meaning_similarity >= 0.5
    meaning_distinct = int(
        ' '.join(_normalize_meaning_parts(word_entry.get('definition')))
        != ' '.join(_normalize_meaning_parts(candidate.get('definition')))
    )

    category_rank = 3 if spelling_close else 2 if phonetic_close else 1 if meaning_close else 0
    priority_score = (
        category_rank * 1000
        + meaning_distinct * 100
        + same_pos * 10
        + spelling_similarity * 8
        + phonetic_similarity * 12
        + meaning_similarity * 5
        + prefix_length * 0.5
        - edit_distance * 0.5
    )
    return (priority_score, -index)


def rank_preset_listening_confusables(word_entry: dict, candidates: list[dict]) -> list[dict]:
    ranked = sorted(
        enumerate(candidates),
        key=lambda item: _listening_candidate_priority(word_entry, item[1], item[0]),
        reverse=True,
    )
    return [dict(candidate) for _, candidate in ranked]


def _load_confusable_index_file(path: str, *, warning_label: str) -> dict[str, list[dict]]:
    try:
        with open(path, 'r', encoding='utf-8') as file_obj:
            payload = json.load(file_obj)
    except FileNotFoundError:
        return {}
    except Exception as exc:
        print(f"Warning: could not load {warning_label}: {exc}")
        return {}

    raw_index = payload.get('words', {}) if isinstance(payload, dict) else {}
    index: dict[str, list[dict]] = {}

    if isinstance(raw_index, dict):
        for raw_word, raw_candidates in raw_index.items():
            key = normalize_listening_confusable_key(raw_word)
            if not key or not isinstance(raw_candidates, list):
                continue

            candidates: list[dict] = []
            seen_words: set[str] = set()
            for raw_candidate in raw_candidates:
                if not isinstance(raw_candidate, dict):
                    continue

                candidate_word = str(raw_candidate.get('word', '')).strip()
                candidate_definition = str(raw_candidate.get('definition', '')).strip()
                if not candidate_word or not candidate_definition:
                    continue

                candidate_key = normalize_listening_confusable_key(candidate_word)
                if candidate_key in seen_words:
                    continue

                seen_words.add(candidate_key)
                candidates.append({
                    'word': candidate_word,
                    'phonetic': str(raw_candidate.get('phonetic', '')).strip(),
                    'pos': str(raw_candidate.get('pos', 'n.')).strip() or 'n.',
                    'definition': candidate_definition,
                })

            if candidates:
                index[key] = candidates

    return index


def load_listening_confusable_index() -> dict[str, list[dict]]:
    global _listening_confusable_index_cache

    if _listening_confusable_index_cache is not None:
        return _listening_confusable_index_cache

    _listening_confusable_index_cache = _load_confusable_index_file(
        get_listening_confusables_path(),
        warning_label='listening confusables index',
    )
    return _listening_confusable_index_cache


def load_high_value_listening_confusable_index() -> dict[str, list[dict]]:
    global _high_value_listening_confusable_index_cache

    if _high_value_listening_confusable_index_cache is not None:
        return _high_value_listening_confusable_index_cache

    _high_value_listening_confusable_index_cache = _load_confusable_index_file(
        get_high_value_listening_confusables_path(),
        warning_label='high-value listening confusables index',
    )
    return _high_value_listening_confusable_index_cache


def _merge_confusable_candidates(*candidate_groups: list[dict]) -> list[dict]:
    merged: list[dict] = []
    seen_words: set[str] = set()

    for candidates in candidate_groups:
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue

            candidate_key = normalize_listening_confusable_key(candidate.get('word'))
            if not candidate_key or candidate_key in seen_words:
                continue

            seen_words.add(candidate_key)
            merged.append(dict(candidate))

    return merged


def _iter_payload_words(payload):
    if isinstance(payload, list):
        for item in payload:
            if isinstance(item, dict):
                yield item
        return

    if not isinstance(payload, dict):
        return

    chapters = payload.get('chapters')
    if isinstance(chapters, list):
        for chapter in chapters:
            if not isinstance(chapter, dict):
                continue
            words = chapter.get('words')
            if not isinstance(words, list):
                continue
            for item in words:
                if isinstance(item, dict):
                    yield item

    words = payload.get('words')
    if isinstance(words, list):
        for item in words:
            if isinstance(item, dict):
                yield item


def load_allowed_ielts_word_keys() -> set[str]:
    global _allowed_ielts_word_keys_cache
    if _allowed_ielts_word_keys_cache is not None:
        return _allowed_ielts_word_keys_cache

    allowed: set[str] = set()
    vocabulary_root = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..',
        '..',
        'vocabulary_data',
    )
    for book in books_registry_service.list_vocab_books():
        if book.get('study_type') != 'ielts':
            continue
        book_id = str(book.get('id') or '').strip()
        if book_id in _EXCLUDED_IELTS_CONFUSABLE_BOOK_IDS:
            continue

        file_name = str(book.get('file') or '').strip()
        if not file_name:
            continue
        file_path = os.path.join(vocabulary_root, file_name)

        try:
            if file_name.endswith('.csv'):
                with open(file_path, 'r', encoding='utf-8-sig') as file_obj:
                    for row in csv_module.DictReader(file_obj):
                        key = normalize_listening_confusable_key(row.get('word'))
                        if key:
                            allowed.add(key)
                continue

            if file_name.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as file_obj:
                    payload = json.load(file_obj)
                for item in _iter_payload_words(payload):
                    key = normalize_listening_confusable_key(item.get('word'))
                    if key:
                        allowed.add(key)
        except Exception:
            continue

    _allowed_ielts_word_keys_cache = allowed
    return _allowed_ielts_word_keys_cache


def _filter_candidates_to_ielts_vocab(candidates: list[dict]) -> list[dict]:
    allowed = load_allowed_ielts_word_keys()
    if not allowed:
        return candidates
    return [
        dict(candidate)
        for candidate in candidates
        if normalize_listening_confusable_key(candidate.get('word')) in allowed
    ]


def get_preset_listening_confusables(word: str | None, limit: int | None = None) -> list[dict]:
    key = normalize_listening_confusable_key(word)
    if not key:
        return []

    high_value_candidates = _filter_candidates_to_ielts_vocab(
        load_high_value_listening_confusable_index().get(key, []),
    )
    if len(high_value_candidates) >= _HIGH_VALUE_ONLY_THRESHOLD:
        candidates = _merge_confusable_candidates(high_value_candidates)
    else:
        candidates = _merge_confusable_candidates(
            high_value_candidates,
            _filter_candidates_to_ielts_vocab(load_listening_confusable_index().get(key, [])),
        )
    if limit is not None:
        candidates = candidates[:max(0, int(limit))]
    return [dict(candidate) for candidate in candidates]


def attach_preset_listening_confusables(word_entry: dict, limit: int | None = None) -> dict:
    word_text = str(word_entry.get('word', '')).strip()
    if not word_text:
        return word_entry

    candidates = rank_preset_listening_confusables(
        word_entry,
        get_preset_listening_confusables(word_text, limit=None),
    )
    if limit is not None:
        candidates = candidates[:max(0, int(limit))]
    if not candidates:
        return word_entry

    return {
        **word_entry,
        'listening_confusables': candidates,
    }
