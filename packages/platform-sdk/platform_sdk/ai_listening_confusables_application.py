from __future__ import annotations

import json
import re
from pathlib import Path


_listening_confusable_index_cache: dict[str, list[dict]] | None = None
_high_value_listening_confusable_index_cache: dict[str, list[dict]] | None = None
_HIGH_VALUE_ONLY_THRESHOLD = 3


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


def get_preset_listening_confusables(word: str | None, limit: int | None = None) -> list[dict]:
    key = normalize_listening_confusable_key(word)
    if not key:
        return []

    high_value_candidates = load_high_value_listening_confusable_index().get(key, [])
    if len(high_value_candidates) >= _HIGH_VALUE_ONLY_THRESHOLD:
        candidates = _merge_confusable_candidates(high_value_candidates)
    else:
        candidates = _merge_confusable_candidates(
            high_value_candidates,
            load_listening_confusable_index().get(key, []),
        )
    if limit is not None:
        candidates = candidates[:max(0, int(limit))]
    return [dict(candidate) for candidate in candidates]
