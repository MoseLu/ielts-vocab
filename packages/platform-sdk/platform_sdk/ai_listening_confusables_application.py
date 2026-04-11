from __future__ import annotations

import csv as csv_module
import json
import re
from pathlib import Path

from services import books_registry_service


_listening_confusable_index_cache: dict[str, list[dict]] | None = None
_high_value_listening_confusable_index_cache: dict[str, list[dict]] | None = None
_allowed_ielts_word_keys_cache: set[str] | None = None
_HIGH_VALUE_ONLY_THRESHOLD = 3
_EXCLUDED_IELTS_CONFUSABLE_BOOK_IDS = {'ielts_confusable_match'}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def get_listening_confusables_path() -> Path:
    return _repo_root() / 'vocabulary_data' / 'ielts_listening_confusables.json'


def get_high_value_listening_confusables_path() -> Path:
    return _repo_root() / 'vocabulary_data' / 'ielts_high_value_confusables.json'


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


def _load_confusable_index_file(path: Path) -> dict[str, list[dict]]:
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        return {}
    except Exception:
        return {}

    raw_index = payload.get('words', {}) if isinstance(payload, dict) else {}
    index: dict[str, list[dict]] = {}
    if not isinstance(raw_index, dict):
        return index

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
    if _listening_confusable_index_cache is None:
        _listening_confusable_index_cache = _load_confusable_index_file(
            get_listening_confusables_path(),
        )
    return _listening_confusable_index_cache


def load_high_value_listening_confusable_index() -> dict[str, list[dict]]:
    global _high_value_listening_confusable_index_cache
    if _high_value_listening_confusable_index_cache is None:
        _high_value_listening_confusable_index_cache = _load_confusable_index_file(
            get_high_value_listening_confusables_path(),
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
    vocabulary_root = _repo_root() / 'vocabulary_data'
    for book in books_registry_service.list_vocab_books():
        if book.get('study_type') != 'ielts':
            continue
        book_id = str(book.get('id') or '').strip()
        if book_id in _EXCLUDED_IELTS_CONFUSABLE_BOOK_IDS:
            continue

        file_name = str(book.get('file') or '').strip()
        if not file_name:
            continue
        file_path = vocabulary_root / file_name

        try:
            if file_name.endswith('.csv'):
                with file_path.open('r', encoding='utf-8-sig') as file_obj:
                    for row in csv_module.DictReader(file_obj):
                        key = normalize_listening_confusable_key(row.get('word'))
                        if key:
                            allowed.add(key)
                continue

            if file_name.endswith('.json'):
                payload = json.loads(file_path.read_text(encoding='utf-8'))
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
