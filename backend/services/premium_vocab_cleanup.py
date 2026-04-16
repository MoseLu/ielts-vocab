from __future__ import annotations

import csv
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
VOCAB_ROOT = REPO_ROOT / 'vocabulary_data'
TARGET_PREMIUM_BOOK_FILES = (
    'ielts_reading_premium.json',
    'ielts_listening_premium.json',
)
CURATED_REFERENCE_FILES = (
    'ielts_9400_extended.json',
    'ielts_vocabulary_complete_extended.json',
    'ielts_vocabulary_comprehensive.json',
    'ielts_vocabulary_FINAL.json',
    'ielts_vocabulary_6260.csv',
    'ielts_vocabulary_ultimate.csv',
    'ielts_vocabulary_awl_extended.json',
)
PROPER_NOUN_DEFINITION_TOKENS = (
    '人名',
    '地名',
    '州名',
    '美国国家航空航天局',
    '莎士比亚',
    '奥林匹克运动会',
    '联合王国（英国）',
)
PLACE_DEFINITION_TOKENS = (
    '马萨诸塞州',
    '威斯康星州',
    '伊利诺伊州',
    '坦桑尼亚',
    '洛杉矶',
    '新南威尔士州',
    '西澳大利亚',
    '东非',
    '东南亚',
    '南非',
    '南美洲',
    '北美洲',
    '拉丁语系国家',
)
BLOCKED_WORDS = {
    'latin',
    'olympic',
    'great britain',
    'northern ireland',
    'hollywood',
}
WORD_RE = re.compile(r"^[a-z]+(?:[-'][a-z]+|')*(?: [a-z]+(?:[-'][a-z]+|')*)*$")
ALL_CAPS_RE = re.compile(r'^[A-Z0-9&/-]+$')
POS_SUFFIX_RE = re.compile(
    r'(?<=\w)\s+(?:n|v|vi|vt|adj|adv|prep|conj|pron|det|num|phrase)\.?$',
    flags=re.IGNORECASE,
)


@dataclass(frozen=True)
class CleanupStats:
    source_chapters: int
    kept_chapters: int
    source_words: int
    kept_words: int
    removed_reason_counts: dict[str, int]


def normalize_premium_word(raw_word: str | None) -> str:
    normalized = str(raw_word or '').replace('…', ' ').strip()
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = POS_SUFFIX_RE.sub('', normalized)
    normalized = normalized.strip(" .'\"")
    normalized = normalized.lower()
    if ' ' not in normalized:
        if normalized.endswith("'s"):
            normalized = normalized[:-2]
        elif normalized.endswith("s'"):
            normalized = normalized[:-1]
    return normalized.strip()


def _iter_words_from_source(path: Path):
    if path.suffix.lower() == '.csv':
        with path.open('r', encoding='utf-8-sig', newline='') as file_obj:
            for row in csv.DictReader(file_obj):
                yield row.get('word', '')
        return

    data = json.loads(path.read_text(encoding='utf-8'))
    if isinstance(data, dict) and 'chapters' in data:
        for chapter in data['chapters']:
            for entry in chapter.get('words', []):
                if isinstance(entry, dict):
                    yield entry.get('word', '')
        return

    if isinstance(data, list):
        for entry in data:
            if isinstance(entry, dict):
                yield entry.get('word', '') or entry.get('headword', '')


def load_curated_base_word_set(vocab_root: Path | None = None) -> set[str]:
    root = vocab_root or VOCAB_ROOT
    curated_words: set[str] = set()
    for filename in CURATED_REFERENCE_FILES:
        for raw_word in _iter_words_from_source(root / filename):
            normalized = normalize_premium_word(raw_word)
            if normalized:
                curated_words.add(normalized)
    return curated_words


def classify_premium_entry(
    *,
    raw_word: str | None,
    definition: str | None,
    curated_base_words: set[str],
    seen_words: set[str],
) -> tuple[str, list[str]]:
    normalized_word = normalize_premium_word(raw_word)
    normalized_definition = str(definition or '').strip()
    definition_lower = normalized_definition.lower()
    reasons: list[str] = []

    if not normalized_word:
        reasons.append('empty_word')
    if any(token in normalized_definition for token in PROPER_NOUN_DEFINITION_TOKENS):
        reasons.append('proper_noun_definition')
    if any(token in normalized_definition for token in PLACE_DEFINITION_TOKENS):
        reasons.append('place_definition')
    if 'abbr.' in definition_lower or '缩写' in normalized_definition:
        reasons.append('abbreviation_entry')
    if ALL_CAPS_RE.fullmatch(str(raw_word or '').strip()) and normalized_word not in curated_base_words:
        reasons.append('all_caps_noise')
    if normalized_word and not WORD_RE.fullmatch(normalized_word):
        reasons.append('malformed_word')
    if normalized_word in BLOCKED_WORDS:
        reasons.append('blocked_word')
    if normalized_word and normalized_word in seen_words:
        reasons.append('duplicate_word')

    return normalized_word, reasons


def _normalize_entry(entry: dict, normalized_word: str) -> dict:
    normalized_entry = dict(entry)
    normalized_entry['word'] = normalized_word
    if 'phonetic' in normalized_entry:
        normalized_entry['phonetic'] = str(normalized_entry.get('phonetic') or '').strip()
    if 'pos' in normalized_entry:
        normalized_entry['pos'] = str(normalized_entry.get('pos') or '').strip()
    if 'definition' in normalized_entry:
        normalized_entry['definition'] = str(normalized_entry.get('definition') or '').strip()
    if 'translation' in normalized_entry:
        normalized_entry['translation'] = str(normalized_entry.get('translation') or '').strip()
    return normalized_entry


def clean_premium_book_payload(
    payload: dict,
    *,
    curated_base_words: set[str],
) -> tuple[dict, CleanupStats]:
    source_chapters = payload.get('chapters', []) if isinstance(payload, dict) else []
    seen_words: set[str] = set()
    cleaned_chapters: list[dict] = []
    removed_reason_counts: Counter[str] = Counter()
    source_word_count = 0
    kept_word_count = 0

    for chapter in source_chapters:
        raw_words = chapter.get('words', []) if isinstance(chapter, dict) else []
        source_word_count += len(raw_words)
        cleaned_words: list[dict] = []
        for entry in raw_words:
            if not isinstance(entry, dict):
                removed_reason_counts['non_dict_entry'] += 1
                continue
            normalized_word, reasons = classify_premium_entry(
                raw_word=entry.get('word'),
                definition=entry.get('definition') or entry.get('translation'),
                curated_base_words=curated_base_words,
                seen_words=seen_words,
            )
            if reasons:
                removed_reason_counts.update(reasons)
                continue
            seen_words.add(normalized_word)
            cleaned_words.append(_normalize_entry(entry, normalized_word))

        if not cleaned_words:
            continue

        kept_word_count += len(cleaned_words)
        cleaned_chapters.append({
            **chapter,
            'word_count': len(cleaned_words),
            'words': cleaned_words,
        })

    cleaned_payload = dict(payload)
    cleaned_payload['chapters'] = cleaned_chapters
    cleaned_payload['total_chapters'] = len(cleaned_chapters)
    cleaned_payload['total_words'] = kept_word_count

    return cleaned_payload, CleanupStats(
        source_chapters=len(source_chapters),
        kept_chapters=len(cleaned_chapters),
        source_words=source_word_count,
        kept_words=kept_word_count,
        removed_reason_counts=dict(sorted(removed_reason_counts.items())),
    )


def clean_premium_book_file(
    filename: str,
    *,
    curated_base_words: set[str] | None = None,
    vocab_root: Path | None = None,
) -> tuple[dict, CleanupStats]:
    root = vocab_root or VOCAB_ROOT
    base_words = curated_base_words or load_curated_base_word_set(root)
    payload = json.loads((root / filename).read_text(encoding='utf-8'))
    return clean_premium_book_payload(payload, curated_base_words=base_words)
