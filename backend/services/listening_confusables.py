from __future__ import annotations

import json
import os
import re

_listening_confusable_index_cache: dict[str, list[dict]] | None = None


def get_listening_confusables_path() -> str:
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..',
        '..',
        'vocabulary_data',
        'ielts_listening_confusables.json',
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


def load_listening_confusable_index() -> dict[str, list[dict]]:
    global _listening_confusable_index_cache

    if _listening_confusable_index_cache is not None:
        return _listening_confusable_index_cache

    path = get_listening_confusables_path()
    try:
        with open(path, 'r', encoding='utf-8') as file_obj:
            payload = json.load(file_obj)
    except FileNotFoundError:
        _listening_confusable_index_cache = {}
        return _listening_confusable_index_cache
    except Exception as exc:
        print(f"Warning: could not load listening confusables index: {exc}")
        _listening_confusable_index_cache = {}
        return _listening_confusable_index_cache

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

                candidate_key = candidate_word.lower()
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

    _listening_confusable_index_cache = index
    return _listening_confusable_index_cache


def get_preset_listening_confusables(word: str | None, limit: int | None = None) -> list[dict]:
    key = normalize_listening_confusable_key(word)
    if not key:
        return []

    candidates = load_listening_confusable_index().get(key, [])
    if limit is not None:
        candidates = candidates[:max(0, int(limit))]
    return [dict(candidate) for candidate in candidates]


def attach_preset_listening_confusables(word_entry: dict, limit: int | None = None) -> dict:
    word_text = str(word_entry.get('word', '')).strip()
    if not word_text:
        return word_entry

    candidates = get_preset_listening_confusables(word_text, limit=limit)
    if not candidates:
        return word_entry

    return {
        **word_entry,
        'listening_confusables': candidates,
    }
