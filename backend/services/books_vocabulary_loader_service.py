from __future__ import annotations

import csv as csv_module
import json
import os
import re

from services import books_registry_service, word_catalog_repository
from services.listening_confusables import attach_preset_listening_confusables


CSV_CHAPTER_SIZE = 50
CSV_CHAPTER_GROUPS = {
    'ielts_comprehensive': [
        ('AWL学术词汇 Sublist 1', lambda r: r.get('source') == 'AWL' and r.get('sublist') == '1'),
        ('AWL学术词汇 Sublist 2', lambda r: r.get('source') == 'AWL' and r.get('sublist') == '2'),
        ('AWL学术词汇 Sublist 3', lambda r: r.get('source') == 'AWL' and r.get('sublist') == '3'),
        ('AWL学术词汇 Sublist 4', lambda r: r.get('source') == 'AWL' and r.get('sublist') == '4'),
        ('AWL学术词汇 其他', lambda r: r.get('source') == 'AWL'),
        ('听力词汇·住宿', lambda r: r.get('category') == 'listening_accommodation'),
        ('听力词汇·教育', lambda r: r.get('category') == 'listening_education'),
        ('听力词汇·交通', lambda r: r.get('category') in ('listening_travel_transport', 'listening_travel')),
        ('听力词汇·医疗', lambda r: r.get('category') in ('listening_medical', 'listening_medical_health')),
        ('听力词汇·银行金融', lambda r: r.get('category') == 'listening_banking'),
        ('听力词汇·就业职场', lambda r: r.get('category') == 'listening_employment'),
        ('听力词汇·购物', lambda r: r.get('category') == 'listening_shopping'),
        ('听力词汇·餐饮', lambda r: r.get('category') == 'listening_restaurant'),
        ('听力词汇·综合', lambda r: r.get('source') == 'IELTS_Listening'),
        ('写作词汇', lambda r: r.get('source') == 'IELTS_Writing'),
        ('口语词汇', lambda r: r.get('source') == 'IELTS_Speaking'),
        ('学术短语', lambda r: r.get('source') == 'Academic_Phrases'),
        ('Cambridge IELTS高频词', lambda r: r.get('source') == 'Cambridge_IELTS'),
        ('Oxford 3000核心词', lambda r: r.get('source') == 'Oxford_3000'),
        ('IELTS核心词汇', lambda r: r.get('source') == 'IELTS_Core'),
        ('阅读词汇·科学技术', lambda r: r.get('category') in ('reading_science', 'reading_science_technology')),
        ('阅读词汇·环境', lambda r: r.get('category') == 'reading_environment'),
        ('阅读词汇·医疗健康', lambda r: r.get('category') in ('reading_health', 'reading_health_medicine')),
        ('阅读词汇·社会文化', lambda r: r.get('category') == 'reading_society_culture'),
        ('阅读词汇·心理学', lambda r: r.get('category') == 'reading_psychology'),
        ('IELTS阅读词汇', lambda r: r.get('source') == 'IELTS_Reading'),
    ],
    'ielts_ultimate': [
        ('AWL学术词汇', lambda r: r.get('category') == 'academic'),
        ('写作词汇', lambda r: r.get('category') == 'writing'),
        ('听力词汇·住宿', lambda r: r.get('category') == 'listening_accommodation'),
        ('听力词汇·教育', lambda r: r.get('category') == 'listening_education'),
        ('听力词汇·交通', lambda r: r.get('category') == 'listening_travel_transport'),
        ('听力词汇·医疗', lambda r: r.get('category') == 'listening_medical'),
        ('阅读词汇·科学技术', lambda r: r.get('category') == 'reading_science_technology'),
        ('阅读词汇·环境', lambda r: r.get('category') == 'reading_environment'),
        ('阅读词汇·医疗健康', lambda r: r.get('category') == 'reading_health_medicine'),
        ('阅读词汇·社会文化', lambda r: r.get('category') == 'reading_society_culture'),
        ('阅读词汇·心理学', lambda r: r.get('category') == 'reading_psychology'),
        ('口语词汇', lambda r: r.get('category') == 'speaking'),
        ('学术短语', lambda r: r.get('category') == 'academic_phrases'),
    ],
}
JSON_CHAPTER_GROUPS = {
    'awl_academic': [
        ('Sublist 1', lambda w: w.get('sublist') == 1),
        ('Sublist 2', lambda w: w.get('sublist') == 2),
        ('Sublist 3', lambda w: w.get('sublist') == 3),
        ('其他词汇', lambda w: True),
    ],
}
_vocabulary_cache = {}
_csv_chapter_cache = {}
_json_chapter_cache = {}
_catalog_examples_cache = None
_examples_cache = None
_CORRUPTED_CHAPTER_TITLE_RE = re.compile(r'^[?？\uFFFD]\s*(\d+)\s*[?？\uFFFD]\s+(\d{4}-\d{4})$')


def load_catalog_examples():
    global _catalog_examples_cache
    if _catalog_examples_cache is not None:
        return _catalog_examples_cache

    loaded_examples = {}
    try:
        for row in word_catalog_repository.list_all_word_catalog_entries():
            normalized_word = str(row.normalized_word or '').strip().lower()
            examples = row.get_examples()
            if normalized_word and examples:
                loaded_examples[normalized_word] = examples
    except Exception:
        return {}

    _catalog_examples_cache = loaded_examples
    return _catalog_examples_cache


def load_examples():
    global _examples_cache
    if _examples_cache is not None:
        return _examples_cache

    file_path = os.path.join(get_vocab_data_path(), 'vocabulary_examples.json')
    _examples_cache = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
        for word, example_list in data.get('examples', {}).items():
            if example_list:
                _examples_cache[word.lower()] = example_list
    except Exception as exc:
        print(f"Warning: could not load vocabulary examples: {exc}")
        _examples_cache = {}
    return _examples_cache


def _normalize_example_entries(example_list, *, limit: int = 1) -> list[dict]:
    normalized = []
    seen = set()
    for item in example_list or []:
        if not isinstance(item, dict):
            continue
        en = ' '.join(str(item.get('en') or '').split())
        zh = ' '.join(str(item.get('zh') or '').split())
        key = en.lower()
        if not en or key in seen:
            continue
        seen.add(key)
        normalized.append({'en': en, 'zh': zh})
        if len(normalized) >= limit:
            break
    return normalized


def resolve_unified_examples(word: str, *, fallback_examples=None, limit: int = 1) -> list[dict]:
    normalized_word = str(word or '').strip().lower()
    if not normalized_word:
        return []

    short_examples = _normalize_example_entries(load_examples().get(normalized_word), limit=limit)
    if short_examples:
        return short_examples

    fallback = fallback_examples
    if fallback is None:
        fallback = load_catalog_examples().get(normalized_word)
    return _normalize_example_entries(fallback, limit=limit)


def merge_examples(word_entry):
    word_text = str(word_entry.get('word') or '').strip()
    if not word_text:
        return word_entry
    examples = resolve_unified_examples(word_text)
    if examples:
        return {**word_entry, 'examples': examples}
    return word_entry


def enrich_word_entry(word_entry):
    return attach_preset_listening_confusables(merge_examples(word_entry), limit=6)


def get_vocab_data_path():
    return os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        '..',
        '..',
        'vocabulary_data',
    )


def normalize_chapter_title(title, chapter_id=None):
    if title is None:
        return f'第{chapter_id}章' if chapter_id is not None else ''
    normalized = ' '.join(str(title).split())
    match = _CORRUPTED_CHAPTER_TITLE_RE.fullmatch(normalized)
    if match:
        chapter_number, word_range = match.groups()
        return f'第{chapter_number}章 {word_range}'
    return normalized


def chunk_group(label, rows_with_indices, chunk_size, starting_id):
    chapters = []
    total_chunks = (len(rows_with_indices) + chunk_size - 1) // chunk_size
    chapter_id = starting_id
    for chunk_num, offset in enumerate(range(0, len(rows_with_indices), chunk_size), start=1):
        chunk = rows_with_indices[offset:offset + chunk_size]
        title = label if total_chunks == 1 else f'{label} · Part {chunk_num}'
        chapters.append({
            'id': chapter_id,
            'title': title,
            'word_count': len(chunk),
            'row_indices': [index for index, _ in chunk],
        })
        chapter_id += 1
    return chapters, chapter_id


def build_csv_chapters(book_id):
    if book_id in _csv_chapter_cache:
        return

    book = books_registry_service.get_vocab_book(book_id)
    file_name = str((book or {}).get('file') or '').strip()
    if not file_name.endswith('.csv'):
        return

    file_path = os.path.join(get_vocab_data_path(), file_name)
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            raw_rows = list(csv_module.DictReader(file))
    except Exception as exc:
        print(f"Error reading CSV for chapters ({book_id}): {exc}")
        return

    groups = CSV_CHAPTER_GROUPS.get(book_id)
    if not groups:
        indexed_rows = list(enumerate(raw_rows))
        chapters, _ = chunk_group('Unit', indexed_rows, CSV_CHAPTER_SIZE, 1)
        _csv_chapter_cache[book_id] = {'chapters': chapters, 'row_data': raw_rows}
        return

    assigned_indices = set()
    chapters = []
    next_id = 1
    for label, predicate in groups:
        matched = [
            (index, row)
            for index, row in enumerate(raw_rows)
            if index not in assigned_indices and predicate(row)
        ]
        if not matched:
            continue
        new_chapters, next_id = chunk_group(label, matched, CSV_CHAPTER_SIZE, next_id)
        chapters.extend(new_chapters)
        for index, _ in matched:
            assigned_indices.add(index)

    remaining = [(index, row) for index, row in enumerate(raw_rows) if index not in assigned_indices]
    if remaining:
        extra_chapters, _ = chunk_group('其他词汇', remaining, CSV_CHAPTER_SIZE, next_id)
        chapters.extend(extra_chapters)

    _csv_chapter_cache[book_id] = {'chapters': chapters, 'row_data': raw_rows}


def build_json_chapters(book_id):
    if book_id in _json_chapter_cache:
        return

    book = books_registry_service.get_vocab_book(book_id)
    file_name = str((book or {}).get('file') or '').strip()
    if not file_name.endswith('.json'):
        return

    file_path = os.path.join(get_vocab_data_path(), file_name)
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = json.load(file)
    except Exception as exc:
        print(f"Error reading JSON for chapters ({book_id}): {exc}")
        return

    if not isinstance(data, list):
        return

    groups = JSON_CHAPTER_GROUPS.get(book_id)
    chapters = []
    next_id = 1
    if groups:
        assigned = set()
        for label, predicate in groups:
            matched = [
                (index, word)
                for index, word in enumerate(data)
                if index not in assigned and predicate(word)
            ]
            if not matched:
                continue
            new_chapters, next_id = chunk_group(label, matched, CSV_CHAPTER_SIZE, next_id)
            for chapter in new_chapters:
                chapter['word_indices'] = chapter.pop('row_indices')
            chapters.extend(new_chapters)
            for index, _ in matched:
                assigned.add(index)

        remaining = [(index, word) for index, word in enumerate(data) if index not in assigned]
        if remaining:
            extra_chapters, _ = chunk_group('其他词汇', remaining, CSV_CHAPTER_SIZE, next_id)
            for chapter in extra_chapters:
                chapter['word_indices'] = chapter.pop('row_indices')
            chapters.extend(extra_chapters)
    else:
        indexed_words = list(enumerate(data))
        chapters, _ = chunk_group('Unit', indexed_words, CSV_CHAPTER_SIZE, 1)
        for chapter in chapters:
            chapter['word_indices'] = chapter.pop('row_indices')

    _json_chapter_cache[book_id] = {'chapters': chapters, 'words': data}


def normalize_csv_word(row):
    normalized = {
        'word': row.get('word', '').strip(),
        'phonetic': row.get('phonetic', ''),
        'pos': row.get('pos', 'n.'),
        'definition': row.get('translation', '') or row.get('definition', ''),
    }
    return copy_optional_word_fields(row, normalized)


def copy_optional_word_fields(source_word, target_word):
    group_key = source_word.get('group_key')
    if isinstance(group_key, str) and group_key.strip():
        target_word['group_key'] = group_key.strip()

    headword = source_word.get('headword')
    if isinstance(headword, str) and headword.strip():
        target_word['headword'] = headword.strip()
    return target_word
