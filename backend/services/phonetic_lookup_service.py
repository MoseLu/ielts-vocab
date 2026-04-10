from __future__ import annotations

import html
import json
import re
from pathlib import Path

import requests
from flask import has_app_context

from models import WordCatalogEntry, WordDerivativeEntry, db


_DICT_API_BASE_URL = 'https://api.dictionaryapi.dev/api/v2/entries/en/'
_DICT_API_TIMEOUT_SECONDS = 12
_WIKTIONARY_PARSE_URL = 'https://en.wiktionary.org/w/api.php'
_PHONETIC_OVERRIDES_CACHE: dict[str, str] | None = None
_LOCAL_VOCAB_PHONETIC_CACHE: dict[str, str] | None = None
_SLASHED_PHONETIC_PATTERN = re.compile(r'/[^/]+/')
_WIKTIONARY_ENGLISH_SECTION_PATTERN = re.compile(
    r'<div class="mw-heading mw-heading2"><h2 id="English">.*?(?=<div class="mw-heading mw-heading2"><h2 id=|$)',
    re.S,
)
_WIKTIONARY_IPA_PATTERN = re.compile(r'<span class="IPA(?: [^"]*)?">(.*?)</span>', re.S)


def normalize_word_key(value: object) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def normalize_phonetic_text(value: object) -> str:
    text = str(value or '').strip()
    if not text:
        return ''

    match = _SLASHED_PHONETIC_PATTERN.search(text)
    if match:
        text = match.group(0)
    else:
        text = text.strip().strip('[]/')
        if not text:
            return ''
        text = f'/{text}/'

    text = re.sub(r'\s+', ' ', text).strip()
    return '' if text == '//' else text


def get_phonetic_overrides_path() -> Path:
    return Path(__file__).resolve().parents[2] / 'vocabulary_data' / 'phonetic_overrides.json'


def get_vocabulary_data_path() -> Path:
    return get_phonetic_overrides_path().parent


def invalidate_phonetic_overrides_cache() -> None:
    global _PHONETIC_OVERRIDES_CACHE
    _PHONETIC_OVERRIDES_CACHE = None


def load_phonetic_overrides() -> dict[str, str]:
    global _PHONETIC_OVERRIDES_CACHE
    if _PHONETIC_OVERRIDES_CACHE is not None:
        return _PHONETIC_OVERRIDES_CACHE

    path = get_phonetic_overrides_path()
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        raw = {}
    except Exception:
        raw = {}

    overrides: dict[str, str] = {}
    if isinstance(raw, dict):
        for raw_word, raw_phonetic in raw.items():
            normalized_word = normalize_word_key(raw_word)
            normalized_phonetic = normalize_phonetic_text(raw_phonetic)
            if normalized_word and normalized_phonetic:
                overrides[normalized_word] = normalized_phonetic

    _PHONETIC_OVERRIDES_CACHE = overrides
    return _PHONETIC_OVERRIDES_CACHE


def save_phonetic_overrides(overrides: dict[str, str]) -> None:
    normalized_overrides = {
        normalize_word_key(word): normalize_phonetic_text(phonetic)
        for word, phonetic in overrides.items()
    }
    payload = {
        word: phonetic
        for word, phonetic in sorted(normalized_overrides.items())
        if word and phonetic
    }
    path = get_phonetic_overrides_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + '\n',
        encoding='utf-8',
    )
    invalidate_phonetic_overrides_cache()


def _lookup_override_phonetics(words: list[str]) -> dict[str, str]:
    overrides = load_phonetic_overrides()
    return {
        normalized_word: overrides[normalized_word]
        for normalized_word in words
        if normalized_word in overrides
    }


def _store_local_vocab_phonetic(lookup: dict[str, str], word: object, phonetic: object) -> None:
    normalized_word = normalize_word_key(word)
    normalized_phonetic = normalize_phonetic_text(phonetic)
    if normalized_word and normalized_phonetic and normalized_word not in lookup:
        lookup[normalized_word] = normalized_phonetic


def _collect_json_vocab_phonetics(node: object, lookup: dict[str, str]) -> None:
    stack = [node]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            _store_local_vocab_phonetic(
                lookup,
                current.get('word'),
                current.get('phonetic'),
            )
            stack.extend(current.values())
        elif isinstance(current, list):
            stack.extend(current)


def load_local_vocabulary_phonetics() -> dict[str, str]:
    global _LOCAL_VOCAB_PHONETIC_CACHE
    if _LOCAL_VOCAB_PHONETIC_CACHE is not None:
        return _LOCAL_VOCAB_PHONETIC_CACHE

    lookup: dict[str, str] = {}
    for path in sorted(get_vocabulary_data_path().iterdir()):
        if not path.is_file():
            continue
        if path.name == get_phonetic_overrides_path().name:
            continue
        if path.suffix.lower() not in {'.json', '.csv'}:
            continue

        try:
            if path.suffix.lower() == '.csv':
                import csv

                with path.open('r', encoding='utf-8-sig', newline='') as handle:
                    for row in csv.DictReader(handle):
                        _store_local_vocab_phonetic(
                            lookup,
                            row.get('word'),
                            row.get('phonetic'),
                        )
            else:
                _collect_json_vocab_phonetics(
                    json.loads(path.read_text(encoding='utf-8')),
                    lookup,
                )
        except Exception:
            continue

    _LOCAL_VOCAB_PHONETIC_CACHE = lookup
    return _LOCAL_VOCAB_PHONETIC_CACHE


def _lookup_local_vocab_phonetics(words: list[str]) -> dict[str, str]:
    local_vocab = load_local_vocabulary_phonetics()
    return {
        normalized_word: local_vocab[normalized_word]
        for normalized_word in words
        if normalized_word in local_vocab
    }


def _lookup_catalog_phonetics(words: list[str]) -> dict[str, str]:
    if not has_app_context() or not words:
        return {}

    found: dict[str, str] = {}
    entries = WordCatalogEntry.query.filter(
        WordCatalogEntry.normalized_word.in_(words),
    ).all()
    for entry in entries:
        phonetic = normalize_phonetic_text(entry.phonetic)
        if phonetic:
            found[entry.normalized_word] = phonetic
    return found


def _lookup_derivative_phonetics(words: list[str]) -> dict[str, str]:
    if not has_app_context() or not words:
        return {}

    lowered_derivative = db.func.lower(WordDerivativeEntry.derivative_word)
    rows = WordDerivativeEntry.query.filter(
        lowered_derivative.in_(words),
    ).all()

    found: dict[str, str] = {}
    for row in rows:
        normalized_word = normalize_word_key(row.derivative_word)
        phonetic = normalize_phonetic_text(row.derivative_phonetic)
        if normalized_word and phonetic and normalized_word not in found:
            found[normalized_word] = phonetic
    return found


def lookup_local_phonetics(words: list[str]) -> dict[str, str]:
    normalized_words = []
    seen = set()
    for word in words:
        normalized_word = normalize_word_key(word)
        if normalized_word and normalized_word not in seen:
            seen.add(normalized_word)
            normalized_words.append(normalized_word)

    if not normalized_words:
        return {}

    resolved = _lookup_override_phonetics(normalized_words)
    unresolved = [word for word in normalized_words if word not in resolved]
    if unresolved:
        resolved.update(_lookup_local_vocab_phonetics(unresolved))

    unresolved = [word for word in normalized_words if word not in resolved]
    if unresolved:
        resolved.update(_lookup_catalog_phonetics(unresolved))

    unresolved = [word for word in normalized_words if word not in resolved]
    if unresolved:
        resolved.update(_lookup_derivative_phonetics(unresolved))

    return resolved


def lookup_local_phonetic(word: str) -> str:
    normalized_word = normalize_word_key(word)
    if not normalized_word:
        return ''
    return lookup_local_phonetics([normalized_word]).get(normalized_word, '')


def hydrate_missing_entry_phonetics(entries: list[dict]) -> list[dict]:
    lookup = lookup_local_phonetics([
        str(entry.get('word') or '')
        for entry in entries
        if not normalize_phonetic_text(entry.get('phonetic'))
    ])
    if not lookup:
        return entries

    hydrated_entries: list[dict] = []
    for entry in entries:
        phonetic = normalize_phonetic_text(entry.get('phonetic'))
        if phonetic:
            hydrated_entries.append(entry)
            continue

        normalized_word = normalize_word_key(entry.get('word'))
        resolved_phonetic = lookup.get(normalized_word, '')
        if resolved_phonetic:
            hydrated_entries.append({**entry, 'phonetic': resolved_phonetic})
            continue

        hydrated_entries.append(entry)
    return hydrated_entries


def _iter_remote_phonetic_candidates(payload: object):
    if not isinstance(payload, list):
        return

    for entry in payload:
        if not isinstance(entry, dict):
            continue

        entry_phonetic = normalize_phonetic_text(entry.get('phonetic'))
        if entry_phonetic:
            yield 0, entry_phonetic

        for phonetic in entry.get('phonetics') or []:
            if not isinstance(phonetic, dict):
                continue
            text = normalize_phonetic_text(phonetic.get('text'))
            if not text:
                continue
            has_audio = bool(str(phonetic.get('audio') or '').strip())
            yield (1 if has_audio else 2), text


def fetch_remote_phonetic(word: str) -> str:
    normalized_word = normalize_word_key(word)
    if not normalized_word or ' ' in normalized_word:
        return ''

    try:
        response = requests.get(
            f'{_DICT_API_BASE_URL}{normalized_word}',
            timeout=_DICT_API_TIMEOUT_SECONDS,
        )
    except Exception:
        return ''

    if not response.ok:
        return ''

    try:
        payload = response.json()
    except Exception:
        payload = None

    ranked_candidates: list[tuple[int, int, str]] = []
    seen = set()
    for rank, phonetic in _iter_remote_phonetic_candidates(payload):
        if phonetic in seen:
            continue
        seen.add(phonetic)
        ranked_candidates.append((rank, len(phonetic), phonetic))

    if not ranked_candidates:
        return fetch_wiktionary_phonetic(normalized_word)

    ranked_candidates.sort(key=lambda item: (item[0], item[1], item[2]))
    return ranked_candidates[0][2]


def fetch_wiktionary_phonetic(word: str) -> str:
    normalized_word = normalize_word_key(word)
    if not normalized_word or ' ' in normalized_word:
        return ''

    try:
        response = requests.get(
            _WIKTIONARY_PARSE_URL,
            params={
                'action': 'parse',
                'page': normalized_word,
                'prop': 'text',
                'formatversion': 2,
                'format': 'json',
            },
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=_DICT_API_TIMEOUT_SECONDS,
        )
    except Exception:
        return ''

    if not response.ok:
        return ''

    try:
        payload = response.json()
    except Exception:
        return ''

    raw_html = str(((payload or {}).get('parse') or {}).get('text') or '')
    if not raw_html:
        return ''

    match = _WIKTIONARY_ENGLISH_SECTION_PATTERN.search(raw_html)
    english_section = match.group(0) if match else raw_html

    candidates: list[str] = []
    seen = set()
    for raw_candidate in _WIKTIONARY_IPA_PATTERN.findall(english_section):
        candidate = normalize_phonetic_text(
            html.unescape(re.sub(r'<[^>]+>', '', raw_candidate)),
        )
        core = candidate.strip('/')
        if not candidate or core.startswith('-') or len(core) < 3 or candidate in seen:
            continue
        seen.add(candidate)
        candidates.append(candidate)

    if not candidates:
        return ''

    candidates.sort(key=lambda value: (len(value), value))
    return candidates[0]


def prime_runtime_phonetic(word: str, phonetic: str) -> None:
    normalized_word = normalize_word_key(word)
    normalized_phonetic = normalize_phonetic_text(phonetic)
    if not normalized_word or not normalized_phonetic:
        return
    load_phonetic_overrides()[normalized_word] = normalized_phonetic


def resolve_phonetic(word: str, *, allow_remote: bool = False) -> str:
    phonetic = lookup_local_phonetic(word)
    if phonetic or not allow_remote:
        return phonetic

    remote_phonetic = fetch_remote_phonetic(word)
    if remote_phonetic:
        prime_runtime_phonetic(word, remote_phonetic)
    return remote_phonetic
