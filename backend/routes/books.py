import os
import json
import csv as csv_module
import re
from collections import defaultdict
from flask import Blueprint, jsonify, request
from models import (
    db,
    User,
    UserBookProgress,
    UserChapterProgress,
    UserChapterModeProgress,
    UserAddedBook,
    CustomBook,
    CustomBookChapter,
    CustomBookWord,
)
from routes.middleware import token_required, _extract_token, _decode_token
from services.learning_events import record_learning_event
from services.listening_confusables import attach_preset_listening_confusables

books_bp = Blueprint('books', __name__)

CONFUSABLE_MATCH_BOOK_ID = 'ielts_confusable_match'
CONFUSABLE_CUSTOM_BOOK_PREFIX = 'confusable_custom'
CONFUSABLE_CUSTOM_CHAPTER_OFFSET = 1000
CONFUSABLE_CUSTOM_MAX_GROUPS = 12
CONFUSABLE_CUSTOM_MAX_WORDS_PER_GROUP = 8
CONFUSABLE_LOOKUP_SOURCE_IDS = (
    'ielts_reading_premium',
    'ielts_listening_premium',
    'ielts_comprehensive',
    'ielts_ultimate',
    'awl_academic',
    'ielts_9400_extended',
    CONFUSABLE_MATCH_BOOK_ID,
)
CONFUSABLE_WORD_TOKEN_RE = re.compile(r"[A-Za-z]+(?:[-'][A-Za-z]+)*")


def init_books(app_instance):
    pass  # kept for API compatibility — no longer needs app reference


def _is_confusable_match_book(book_id: str) -> bool:
    return str(book_id) == CONFUSABLE_MATCH_BOOK_ID


def _build_confusable_custom_book_id(user_id: int) -> str:
    return f'{CONFUSABLE_CUSTOM_BOOK_PREFIX}_{user_id}'


def _resolve_optional_current_user() -> User | None:
    """Best-effort auth for public routes that can enrich responses per user."""
    token = _extract_token()
    if not token:
        return None

    try:
        payload = _decode_token(token)
    except Exception:
        return None

    if payload.get('type') != 'access':
        return None

    user_id = payload.get('user_id')
    if user_id is None:
        return None

    return User.query.get(user_id)


def _normalize_lookup_word_key(value) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def _score_lookup_candidate(word_entry: dict, source_priority: int) -> tuple[int, int, int]:
    definition = (word_entry.get('definition') or '').strip()
    phonetic = (word_entry.get('phonetic') or '').strip()
    pos = (word_entry.get('pos') or '').strip()
    completeness = (3 if definition else 0) + (2 if phonetic else 0) + (1 if pos else 0)
    definition_length = min(len(definition), 200)
    return (completeness, -source_priority, definition_length)


def _build_confusable_lookup() -> dict[str, dict]:
    global _confusable_lookup_cache

    if isinstance(_confusable_lookup_cache, dict):
        return _confusable_lookup_cache

    lookup = {}
    for source_priority, book_id in enumerate(CONFUSABLE_LOOKUP_SOURCE_IDS):
        words = load_book_vocabulary(book_id) or []
        for word_entry in words:
            key = _normalize_lookup_word_key(word_entry.get('word'))
            if not key:
                continue

            candidate = {
                'word': (word_entry.get('word') or '').strip() or key,
                'phonetic': (word_entry.get('phonetic') or '').strip(),
                'pos': (word_entry.get('pos') or '').strip(),
                'definition': (word_entry.get('definition') or '').strip(),
            }
            candidate['_score'] = _score_lookup_candidate(candidate, source_priority)

            existing = lookup.get(key)
            if existing is None or candidate['_score'] > existing['_score']:
                lookup[key] = candidate

    _confusable_lookup_cache = lookup
    return lookup


def _normalize_confusable_custom_groups(raw_groups) -> list[list[str]]:
    if not isinstance(raw_groups, list) or not raw_groups:
        raise ValueError('请至少输入一组易混词')

    if len(raw_groups) > CONFUSABLE_CUSTOM_MAX_GROUPS:
        raise ValueError(f'一次最多创建 {CONFUSABLE_CUSTOM_MAX_GROUPS} 组易混词')

    groups = []
    for index, raw_group in enumerate(raw_groups, start=1):
        if isinstance(raw_group, str):
            tokens = CONFUSABLE_WORD_TOKEN_RE.findall(raw_group)
        elif isinstance(raw_group, list):
            tokens = []
            for item in raw_group:
                if not isinstance(item, str):
                    continue
                tokens.extend(CONFUSABLE_WORD_TOKEN_RE.findall(item))
        else:
            tokens = []

        unique_words = []
        seen = set()
        for token in tokens:
            normalized = _normalize_lookup_word_key(token)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            unique_words.append(normalized)

        if len(unique_words) < 2:
            raise ValueError(f'第 {index} 组至少需要 2 个不同单词')
        if len(unique_words) > CONFUSABLE_CUSTOM_MAX_WORDS_PER_GROUP:
            raise ValueError(
                f'第 {index} 组最多支持 {CONFUSABLE_CUSTOM_MAX_WORDS_PER_GROUP} 个单词'
            )

        groups.append(unique_words)

    return groups


def _resolve_confusable_group_words(groups: list[list[str]]) -> tuple[list[list[dict]], list[str]]:
    lookup = _build_confusable_lookup()
    resolved_groups = []
    missing_words = set()

    for group in groups:
        resolved_words = []
        for word in group:
            candidate = lookup.get(word)
            if not candidate:
                missing_words.add(word)
                continue

            if not candidate.get('definition') or not candidate.get('phonetic'):
                missing_words.add(word)
                continue

            resolved_words.append({
                'word': candidate['word'],
                'phonetic': candidate['phonetic'],
                'pos': candidate.get('pos') or 'n.',
                'definition': candidate['definition'],
            })

        if resolved_words:
            resolved_groups.append(resolved_words)

    return resolved_groups, sorted(missing_words)


def _get_confusable_custom_book(user_id: int, create: bool = False) -> CustomBook | None:
    book_id = _build_confusable_custom_book_id(user_id)
    book = CustomBook.query.filter_by(id=book_id, user_id=user_id).first()
    if book or not create:
        return book

    book = CustomBook(
        id=book_id,
        user_id=user_id,
        title='我的易混辨析',
        description='用户手动创建的易混词组合',
        word_count=0,
    )
    db.session.add(book)
    return book


def _get_confusable_custom_word_count(user_id: int | None) -> int:
    if not user_id:
        return 0
    book = _get_confusable_custom_book(user_id)
    return int(book.word_count or 0) if book else 0


def _list_confusable_custom_chapters(user_id: int | None) -> list[dict]:
    if not user_id:
        return []

    book = _get_confusable_custom_book(user_id)
    if not book:
        return []

    chapters = []
    for chapter in book.chapters:
        try:
            chapter_id = int(str(chapter.id))
        except (TypeError, ValueError):
            continue

        chapters.append({
            'id': chapter_id,
            'title': chapter.title,
            'word_count': int(chapter.word_count or len(chapter.words)),
            'is_custom': True,
        })

    return chapters


def _get_confusable_custom_chapter(user_id: int | None, chapter_id: int) -> CustomBookChapter | None:
    if not user_id:
        return None

    book_id = _build_confusable_custom_book_id(user_id)
    return CustomBookChapter.query.filter_by(book_id=book_id, id=str(chapter_id)).first()


def _next_confusable_custom_chapter_id(book: CustomBook) -> int:
    numeric_ids = []
    for chapter in book.chapters:
        try:
            numeric_ids.append(int(str(chapter.id)))
        except (TypeError, ValueError):
            continue

    return max([CONFUSABLE_CUSTOM_CHAPTER_OFFSET] + numeric_ids) + 1


def _build_confusable_custom_chapter_title(words: list[str], sequence: int) -> str:
    preview = ' / '.join(words[:3])
    if len(words) > 3:
        preview += ' / ...'
    return f'自定义易混组 {sequence:02d} · {preview}'


def _serialize_confusable_custom_words(chapter: CustomBookChapter) -> list[dict]:
    group_key = f'custom-{chapter.id}'
    return [
        {
            'word': (word.word or '').strip(),
            'phonetic': (word.phonetic or '').strip(),
            'pos': (word.pos or 'n.').strip() or 'n.',
            'definition': (word.definition or '').strip(),
            'group_key': group_key,
        }
        for word in chapter.words
        if (word.word or '').strip()
    ]


def _merge_confusable_custom_chapters(chapters_data: dict, user_id: int | None) -> dict:
    custom_chapters = _list_confusable_custom_chapters(user_id)
    if not custom_chapters:
        return chapters_data

    merged = {
        'total_chapters': int(chapters_data.get('total_chapters') or 0) + len(custom_chapters),
        'total_words': int(chapters_data.get('total_words') or 0) + sum(
            int(chapter.get('word_count') or 0) for chapter in custom_chapters
        ),
        'chapters': [*(chapters_data.get('chapters') or []), *custom_chapters],
    }
    return merged


def _augment_book_for_user(book: dict, user_id: int | None) -> dict:
    book_data = dict(book)
    if _is_confusable_match_book(book_data.get('id')) and user_id:
        book_data['word_count'] = int(book_data.get('word_count') or 0) + _get_confusable_custom_word_count(user_id)
    return book_data

# Vocabulary books configuration
VOCAB_BOOKS = [
    # Premium vocabulary (已购词汇)
    {
        'id': 'ielts_reading_premium',
        'title': '雅思阅读高频词汇',
        'description': '雅思阅读训练核心词汇，提升阅读理解能力',
        'icon': 'book-open',
        'color': '#7C3AED',
        'category': 'reading',
        'level': 'intermediate',
        'word_count': 3401,
        'file': 'ielts_reading_premium.json',
        'is_paid': True,
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'ielts_listening_premium',
        'title': '雅思听力高频词汇',
        'description': '雅思听力考试核心高频词汇，精选自听力真题',
        'icon': 'headphones',
        'color': '#2563EB',
        'category': 'listening',
        'level': 'intermediate',
        'word_count': 3910,
        'file': 'ielts_listening_premium.json',
        'is_paid': True,
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'ielts_comprehensive',
        'title': '雅思综合词汇5000+',
        'description': '雅思全面词汇库，覆盖听说读写全部场景',
        'icon': 'library',
        'color': '#EC4899',
        'category': 'comprehensive',
        'level': 'advanced',
        'word_count': 6260,
        'file': 'ielts_vocabulary_6260.csv',
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'ielts_ultimate',
        'title': '雅思终极词汇库',
        'description': '精选1938个雅思高频词汇',
        'icon': 'star',
        'color': '#F97316',
        'category': 'comprehensive',
        'level': 'advanced',
        'word_count': 1938,
        'file': 'ielts_vocabulary_ultimate.csv',
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'awl_academic',
        'title': 'AWL学术词汇表',
        'description': 'Academic Word List 570核心学术词汇，雅思学术类必备',
        'icon': 'graduation-cap',
        'color': '#8B5CF6',
        'category': 'academic',
        'level': 'advanced',
        'word_count': 570,
        'file': 'ielts_vocabulary_awl_extended.json',
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'ielts_9400_extended',
        'title': '雅思9400扩展词书',
        'description': '基于9400词表整理的扩展词库，已过滤明显缩写、专名与异常词条',
        'icon': 'library',
        'color': '#F97316',
        'category': 'comprehensive',
        'level': 'advanced',
        'word_count': 9248,
        'file': 'ielts_9400_extended.json',
        'study_type': 'ielts',
        'has_chapters': True
    },
    {
        'id': 'ielts_confusable_match',
        'title': '雅思易混词辨析',
        'description': '自动抽取音近词与形近词，配合消消乐专项辨析',
        'icon': 'sparkles',
        'color': '#22C55E',
        'category': 'confusable',
        'level': 'advanced',
        'word_count': 2026,
        'file': 'ielts_confusable_match.json',
        'study_type': 'ielts',
        'has_chapters': True,
        'practice_mode': 'match',
    }
]

# ── CSV chapter grouping rules ──────────────────────────────────────────────
# Each entry: (chapter_label, filter_fn(row) -> bool)
# Groups are processed in order; each CSV row is assigned to the FIRST matching group.
# Rows not matching any group are placed in a catch-all "其他词汇" group at the end.
# Large groups are automatically split into chunks of CSV_CHAPTER_SIZE words.
# ────────────────────────────────────────────────────────────────────────────
CSV_CHAPTER_SIZE = 50  # words per chapter unit

CSV_CHAPTER_GROUPS = {
    # ── 雅思综合词汇5000+ ──────────────────────────────────────────────────
    'ielts_comprehensive': [
        # AWL学术词汇: grouped by sublist (sublist 1-4 each have 230-320 words)
        ('AWL学术词汇 Sublist 1',
            lambda r: r.get('source') == 'AWL' and r.get('sublist') == '1'),
        ('AWL学术词汇 Sublist 2',
            lambda r: r.get('source') == 'AWL' and r.get('sublist') == '2'),
        ('AWL学术词汇 Sublist 3',
            lambda r: r.get('source') == 'AWL' and r.get('sublist') == '3'),
        ('AWL学术词汇 Sublist 4',
            lambda r: r.get('source') == 'AWL' and r.get('sublist') == '4'),
        ('AWL学术词汇 其他',
            lambda r: r.get('source') == 'AWL'),

        # IELTS听力词汇: by listening topic
        ('听力词汇·住宿',
            lambda r: r.get('category') == 'listening_accommodation'),
        ('听力词汇·教育',
            lambda r: r.get('category') == 'listening_education'),
        ('听力词汇·交通',
            lambda r: r.get('category') in ('listening_travel_transport', 'listening_travel')),
        ('听力词汇·医疗',
            lambda r: r.get('category') in ('listening_medical', 'listening_medical_health')),
        ('听力词汇·银行金融',
            lambda r: r.get('category') == 'listening_banking'),
        ('听力词汇·就业职场',
            lambda r: r.get('category') == 'listening_employment'),
        ('听力词汇·购物',
            lambda r: r.get('category') == 'listening_shopping'),
        ('听力词汇·餐饮',
            lambda r: r.get('category') == 'listening_restaurant'),
        # remaining IELTS_Listening words not matched above
        ('听力词汇·综合',
            lambda r: r.get('source') == 'IELTS_Listening'),

        # IELTS写作词汇
        ('写作词汇',
            lambda r: r.get('source') == 'IELTS_Writing'),

        # IELTS口语词汇
        ('口语词汇',
            lambda r: r.get('source') == 'IELTS_Speaking'),

        # 学术短语
        ('学术短语',
            lambda r: r.get('source') == 'Academic_Phrases'),

        # Cambridge IELTS 高频词
        ('Cambridge IELTS高频词',
            lambda r: r.get('source') == 'Cambridge_IELTS'),

        # Oxford 3000核心词
        ('Oxford 3000核心词',
            lambda r: r.get('source') == 'Oxford_3000'),

        # IELTS核心词汇
        ('IELTS核心词汇',
            lambda r: r.get('source') == 'IELTS_Core'),

        # IELTS阅读词汇: by reading topic (small topic groups first)
        ('阅读词汇·科学技术',
            lambda r: r.get('category') in ('reading_science', 'reading_science_technology')),
        ('阅读词汇·环境',
            lambda r: r.get('category') == 'reading_environment'),
        ('阅读词汇·医疗健康',
            lambda r: r.get('category') in ('reading_health', 'reading_health_medicine')),
        ('阅读词汇·社会文化',
            lambda r: r.get('category') == 'reading_society_culture'),
        ('阅读词汇·心理学',
            lambda r: r.get('category') == 'reading_psychology'),

        # reading_society is the largest group (3003 words) — split into 50-word units
        ('IELTS阅读词汇',
            lambda r: r.get('source') == 'IELTS_Reading'),
    ],

    # ── 雅思终极词汇库 ──────────────────────────────────────────────────────
    'ielts_ultimate': [
        # AWL学术词汇 (1039 words, no sublist column in this CSV)
        ('AWL学术词汇',
            lambda r: r.get('category') == 'academic'),

        # 写作词汇
        ('写作词汇',
            lambda r: r.get('category') == 'writing'),

        # 听力词汇: by topic
        ('听力词汇·住宿',
            lambda r: r.get('category') == 'listening_accommodation'),
        ('听力词汇·教育',
            lambda r: r.get('category') == 'listening_education'),
        ('听力词汇·交通',
            lambda r: r.get('category') == 'listening_travel_transport'),
        ('听力词汇·医疗',
            lambda r: r.get('category') == 'listening_medical'),

        # 阅读词汇: by topic
        ('阅读词汇·科学技术',
            lambda r: r.get('category') == 'reading_science_technology'),
        ('阅读词汇·环境',
            lambda r: r.get('category') == 'reading_environment'),
        ('阅读词汇·医疗健康',
            lambda r: r.get('category') == 'reading_health_medicine'),
        ('阅读词汇·社会文化',
            lambda r: r.get('category') == 'reading_society_culture'),
        ('阅读词汇·心理学',
            lambda r: r.get('category') == 'reading_psychology'),

        # 口语词汇
        ('口语词汇',
            lambda r: r.get('category') == 'speaking'),

        # 学术短语
        ('学术短语',
            lambda r: r.get('category') == 'academic_phrases'),
    ],
}

# ── Flat-JSON chapter grouping rules ────────────────────────────────────────
# Same structure as CSV_CHAPTER_GROUPS but applies to flat JSON list books.
# Each entry: (chapter_label, filter_fn(word_dict) -> bool)
JSON_CHAPTER_GROUPS = {
    # ── AWL学术词汇表 ──────────────────────────────────────────────────────
    'awl_academic': [
        ('Sublist 1', lambda w: w.get('sublist') == 1),
        ('Sublist 2', lambda w: w.get('sublist') == 2),
        ('Sublist 3', lambda w: w.get('sublist') == 3),
        ('其他词汇',  lambda w: True),
    ],
}

# Cache for loaded vocabulary data
_vocabulary_cache = {}
# Cache for CSV chapter structures: {book_id: {'chapters': [...], 'row_data': [...]}}
_csv_chapter_cache = {}
# Cache for flat-JSON chapter structures: {book_id: {'chapters': [...], 'words': [...]}}
_json_chapter_cache = {}
# Cache for normalized word lookup used by custom confusable groups.
_confusable_lookup_cache = None
# Cache for vocabulary examples: {word_lower: [examples]}
_examples_cache = None
_CORRUPTED_CHAPTER_TITLE_RE = re.compile(r'^[?？\uFFFD]\s*(\d+)\s*[?？\uFFFD]\s+(\d{4}-\d{4})$')


def _load_examples():
    """Load example sentences from vocabulary_examples.json once."""
    global _examples_cache
    if _examples_cache is not None:
        return _examples_cache

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, 'vocabulary_examples.json')
    _examples_cache = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        examples_map = data.get('examples', {})
        # Normalise: support both string keys and store lowercase keys for fast lookup
        for word, ex_list in examples_map.items():
            if ex_list:
                _examples_cache[word.lower()] = ex_list
    except Exception as e:
        print(f"Warning: could not load vocabulary examples: {e}")
        _examples_cache = {}
    return _examples_cache


def _merge_examples(word_entry):
    """Add examples to a word entry if available. Returns a new dict (non-mutating)."""
    word_text = word_entry.get('word', '').strip()
    if not word_text:
        return word_entry
    examples = _load_examples().get(word_text.lower())
    if examples:
        return {**word_entry, 'examples': examples}
    return word_entry


def _enrich_word_entry(word_entry):
    return attach_preset_listening_confusables(_merge_examples(word_entry), limit=6)


def get_vocab_data_path():
    """Get the path to vocabulary_data directory"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'vocabulary_data')


def _normalize_chapter_title(title, chapter_id=None):
    """Repair known mojibake placeholders in chapter titles before returning them to clients."""
    if title is None:
        return f'第{chapter_id}章' if chapter_id is not None else ''

    normalized = ' '.join(str(title).split())
    match = _CORRUPTED_CHAPTER_TITLE_RE.fullmatch(normalized)
    if match:
        chapter_number, word_range = match.groups()
        return f'第{chapter_number}章 {word_range}'

    return normalized


def _chunk_group(label, rows_with_indices, chunk_size, starting_id):
    """
    Split a group of (original_index, row) tuples into chunk_size chapters.
    Returns list of chapter dicts and the next available chapter id.
    """
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
            'row_indices': [i for i, _ in chunk],
        })
        chapter_id += 1

    return chapters, chapter_id


def _build_csv_chapters(book_id):
    """
    Read the CSV file for book_id and build a list of chapter dicts.
    Each chapter: {id, title, word_count, row_indices: [int, ...]}.
    Results are stored in _csv_chapter_cache[book_id].
    """
    if book_id in _csv_chapter_cache:
        return

    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book or not book['file'].endswith('.csv'):
        return

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, book['file'])

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            raw_rows = list(csv_module.DictReader(f))
    except Exception as e:
        print(f"Error reading CSV for chapters ({book_id}): {e}")
        return

    groups = CSV_CHAPTER_GROUPS.get(book_id)
    if not groups:
        # No grouping defined → single sequential chunking
        indexed = list(enumerate(raw_rows))
        chapters, _ = _chunk_group('Unit', indexed, CSV_CHAPTER_SIZE, 1)
        _csv_chapter_cache[book_id] = {'chapters': chapters, 'row_data': raw_rows}
        return

    assigned_indices = set()
    chapters = []
    next_id = 1

    for (label, predicate) in groups:
        matched = [
            (i, r) for i, r in enumerate(raw_rows)
            if i not in assigned_indices and predicate(r)
        ]
        if not matched:
            continue
        new_chapters, next_id = _chunk_group(label, matched, CSV_CHAPTER_SIZE, next_id)
        chapters.extend(new_chapters)
        for i, _ in matched:
            assigned_indices.add(i)

    # Remaining unassigned rows → catch-all
    remaining = [(i, r) for i, r in enumerate(raw_rows) if i not in assigned_indices]
    if remaining:
        extra, _ = _chunk_group('其他词汇', remaining, CSV_CHAPTER_SIZE, next_id)
        chapters.extend(extra)

    _csv_chapter_cache[book_id] = {'chapters': chapters, 'row_data': raw_rows}
    print(f"Built {len(chapters)} chapters for '{book_id}' "
          f"covering {sum(c['word_count'] for c in chapters)} words")


def _build_json_chapters(book_id):
    """
    Read a flat-JSON file for book_id and build chapter dicts using JSON_CHAPTER_GROUPS.
    Each chapter: {id, title, word_count, word_indices: [int, ...]}.
    Results stored in _json_chapter_cache[book_id].
    """
    if book_id in _json_chapter_cache:
        return

    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book or not book['file'].endswith('.json'):
        return

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, book['file'])

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON for chapters ({book_id}): {e}")
        return

    # Only handle flat list JSON here; structured JSON is handled inline
    if not isinstance(data, list):
        return

    groups = JSON_CHAPTER_GROUPS.get(book_id)
    chapters = []
    next_id = 1

    if groups:
        assigned = set()
        for (label, predicate) in groups:
            matched = [(i, w) for i, w in enumerate(data) if i not in assigned and predicate(w)]
            if not matched:
                continue
            new_chapters, next_id = _chunk_group(label, matched, CSV_CHAPTER_SIZE, next_id)
            # Rename row_indices → word_indices for clarity
            for ch in new_chapters:
                ch['word_indices'] = ch.pop('row_indices')
            chapters.extend(new_chapters)
            for i, _ in matched:
                assigned.add(i)
        remaining = [(i, w) for i, w in enumerate(data) if i not in assigned]
        if remaining:
            extra, _ = _chunk_group('其他词汇', remaining, CSV_CHAPTER_SIZE, next_id)
            for ch in extra:
                ch['word_indices'] = ch.pop('row_indices')
            chapters.extend(extra)
    else:
        indexed = list(enumerate(data))
        chapters, _ = _chunk_group('Unit', indexed, CSV_CHAPTER_SIZE, 1)
        for ch in chapters:
            ch['word_indices'] = ch.pop('row_indices')

    _json_chapter_cache[book_id] = {'chapters': chapters, 'words': data}
    print(f"Built {len(chapters)} JSON chapters for '{book_id}' "
          f"covering {sum(c['word_count'] for c in chapters)} words")


def _normalize_csv_word(row):
    """Convert a CSV row dict to a normalized word dict."""
    return {
        'word': row.get('word', '').strip(),
        'phonetic': row.get('phonetic', ''),
        'pos': row.get('pos', 'n.'),
        'definition': row.get('translation', '') or row.get('definition', ''),
    }


def _copy_optional_word_fields(source_word, target_word):
    """Preserve optional metadata fields used by specialized practice modes."""
    group_key = source_word.get('group_key')
    if isinstance(group_key, str) and group_key.strip():
        target_word['group_key'] = group_key.strip()
    return target_word


def load_book_vocabulary(book_id):
    """Load vocabulary for a specific book (with chapter_id/chapter_title for JSON books)."""
    if book_id in _vocabulary_cache:
        return _vocabulary_cache[book_id]

    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return None

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, book['file'])

    try:
        if book['file'].endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Handle chapter-based structure (premium books)
                if isinstance(data, dict) and 'chapters' in data:
                    raw_words = []
                    for chapter in data['chapters']:
                        chapter_title = _normalize_chapter_title(chapter.get('title'), chapter.get('id'))
                        for w in chapter.get('words', []):
                            raw_words.append(_copy_optional_word_fields(w, {
                                'word': w.get('word', ''),
                                'phonetic': w.get('phonetic', ''),
                                'pos': w.get('pos', 'n.'),
                                'definition': w.get('definition', ''),
                                'chapter_id': chapter.get('id'),
                                'chapter_title': chapter_title
                            }))
                elif isinstance(data, list):
                    # Flat-list JSON: attach chapter metadata via _build_json_chapters
                    _build_json_chapters(book_id)
                    cached_json = _json_chapter_cache.get(book_id)
                    if cached_json:
                        words = []
                        for ch in cached_json['chapters']:
                            for idx in ch['word_indices']:
                                w = data[idx]
                                if w.get('word', '').strip():
                                    words.append(_enrich_word_entry(_copy_optional_word_fields(w, {
                                        'word': w.get('word', ''),
                                        'phonetic': w.get('phonetic', ''),
                                        'pos': w.get('pos', 'n.'),
                                        'definition': w.get('definition', '') or w.get('translation', ''),
                                        'chapter_id': ch['id'],
                                        'chapter_title': ch['title'],
                                    })))
                        _vocabulary_cache[book_id] = words
                        return words
                    raw_words = data
                elif isinstance(data, dict) and 'vocabulary' in data:
                    raw_words = data['vocabulary']
                else:
                    raw_words = []
            words = []
            for w in raw_words:
                word_entry = {
                    'word': w.get('word', ''),
                    'phonetic': w.get('phonetic', ''),
                    'pos': w.get('pos', 'n.'),
                    'definition': w.get('definition', '') or w.get('translation', ''),
                }
                if 'chapter_id' in w:
                    word_entry['chapter_id'] = w['chapter_id']
                if 'chapter_title' in w:
                    word_entry['chapter_title'] = w['chapter_title']
                words.append(_enrich_word_entry(_copy_optional_word_fields(w, word_entry)))

        elif book['file'].endswith('.csv'):
            # Ensure chapters are built first (populates cache with row_data)
            _build_csv_chapters(book_id)
            cached = _csv_chapter_cache.get(book_id)
            if cached:
                # Build vocabulary list in chapter order, with chapter metadata
                words = []
                for ch in cached['chapters']:
                    for idx in ch['row_indices']:
                        row = cached['row_data'][idx]
                        word = row.get('word', '').strip()
                        if word:
                            words.append(_enrich_word_entry({
                                'word': word,
                                'phonetic': row.get('phonetic', ''),
                                'pos': row.get('pos', 'n.'),
                                'definition': row.get('translation', '') or row.get('definition', ''),
                                'chapter_id': ch['id'],
                                'chapter_title': ch['title'],
                            }))
            else:
                # Fallback: flat load without chapters
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    words = [
                        _enrich_word_entry(_normalize_csv_word(row))
                        for row in csv_module.DictReader(f)
                        if row.get('word', '').strip()
                    ]
        else:
            words = []

        # Merge examples into all word entries before caching
        words = [_enrich_word_entry(w) for w in words]
        _vocabulary_cache[book_id] = words
        return words
    except FileNotFoundError:
        print(f"Warning: Vocabulary file not found: {file_path}")
        return []
    except Exception as e:
        print(f"Error loading vocabulary: {e}")
        return []


@books_bp.route('', methods=['GET'])
def get_books():
    """Get all vocabulary books with optional filtering"""
    category = request.args.get('category')
    level = request.args.get('level')
    study_type = request.args.get('study_type')

    current_user = _resolve_optional_current_user()
    books = [_augment_book_for_user(book, current_user.id if current_user else None) for book in VOCAB_BOOKS]

    if study_type and study_type != 'ielts':
        books = [b for b in books if b.get('study_type') == study_type]

    if category:
        books = [b for b in books if b['category'] == category]

    if level:
        books = [b for b in books if b['level'] == level]

    return jsonify({'books': books}), 200


@books_bp.route('/<book_id>', methods=['GET'])
def get_book(book_id):
    """Get details of a specific book"""
    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return jsonify({'error': 'Book not found'}), 404

    current_user = _resolve_optional_current_user()
    return jsonify({'book': _augment_book_for_user(book, current_user.id if current_user else None)}), 200


def load_book_chapters(book_id):
    """Load chapters structure for a book (metadata only, no word data)."""
    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return None

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, book['file'])

    try:
        # ── JSON books ───────────────────────────────────────────────────────
        if book['file'].endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Structured JSON (premium books): has top-level 'chapters' key
            if isinstance(data, dict) and 'chapters' in data:
                chapters = [
                    {
                        'id': ch.get('id'),
                        'title': _normalize_chapter_title(ch.get('title'), ch.get('id')),
                        'word_count': ch.get('word_count'),
                    }
                    for ch in data['chapters']
                ]
                return {
                    'total_chapters': data.get('total_chapters', len(chapters)),
                    'total_words': data.get('total_words', 0),
                    'chapters': chapters,
                }

            # Flat-list JSON (AWL etc.): build chapters via JSON_CHAPTER_GROUPS
            if isinstance(data, list):
                _build_json_chapters(book_id)
                cached = _json_chapter_cache.get(book_id)
                if cached:
                    chapters = [
                        {'id': c['id'], 'title': c['title'], 'word_count': c['word_count']}
                        for c in cached['chapters']
                    ]
                    return {
                        'total_chapters': len(chapters),
                        'total_words': sum(c['word_count'] for c in cached['chapters']),
                        'chapters': chapters,
                    }

            return None

        # ── CSV books (comprehensive, ultimate) ─────────────────────────────
        elif book['file'].endswith('.csv'):
            _build_csv_chapters(book_id)
            cached = _csv_chapter_cache.get(book_id)
            if not cached:
                return None
            chapters = [
                {'id': c['id'], 'title': c['title'], 'word_count': c['word_count']}
                for c in cached['chapters']
            ]
            return {
                'total_chapters': len(chapters),
                'total_words': sum(c['word_count'] for c in cached['chapters']),
                'chapters': chapters,
            }

    except Exception as e:
        print(f"Error loading chapters ({book_id}): {e}")
        return None


def _get_book_word_count(book_id, user_id: int | None = None):
    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return 0

    base_count = int(book.get('word_count') or 0)
    if _is_confusable_match_book(book_id):
        base_count += _get_confusable_custom_word_count(user_id)
    return base_count


def _get_book_chapter_count(book_id, user_id: int | None = None):
    chapters_data = load_book_chapters(book_id)
    if not chapters_data:
        return 0

    base_count = int(chapters_data.get('total_chapters') or 0)
    if _is_confusable_match_book(book_id):
        base_count += len(_list_confusable_custom_chapters(user_id))
    return base_count


def _serialize_effective_book_progress(book_id, progress_record=None, chapter_records=None, user_id: int | None = None):
    chapter_records = chapter_records or []
    if not progress_record and not chapter_records:
        return None

    base_current_index = int(progress_record.current_index or 0) if progress_record else 0
    base_correct_count = int(progress_record.correct_count or 0) if progress_record else 0
    base_wrong_count = int(progress_record.wrong_count or 0) if progress_record else 0

    chapter_words_learned = sum(max(int(record.words_learned or 0), 0) for record in chapter_records)
    chapter_correct_count = sum(max(int(record.correct_count or 0), 0) for record in chapter_records)
    chapter_wrong_count = sum(max(int(record.wrong_count or 0), 0) for record in chapter_records)

    total_words = _get_book_word_count(book_id, user_id=user_id)
    total_chapters = _get_book_chapter_count(book_id, user_id=user_id) if chapter_records else 0
    completed_chapter_count = sum(1 for record in chapter_records if bool(record.is_completed))
    all_chapters_completed = total_chapters > 0 and completed_chapter_count >= total_chapters

    # Chapter sessions are aggregated by learned-word totals, not by the absolute
    # offset of the last chapter touched. Offsets can hit the end of the book
    # even when many earlier chapters are still untouched.
    effective_current_index = chapter_words_learned if chapter_records else base_current_index
    if total_words > 0:
        if all_chapters_completed or (
            not chapter_records and progress_record and bool(progress_record.is_completed)
        ):
            effective_current_index = total_words
        else:
            effective_current_index = min(effective_current_index, total_words)

    effective_is_completed = (
        all_chapters_completed
        or (
            not chapter_records and (
                (bool(progress_record.is_completed) if progress_record else False)
                or (total_words > 0 and effective_current_index >= total_words)
            )
        )
        or (bool(chapter_records) and total_words > 0 and chapter_words_learned >= total_words)
    )

    updated_candidates = []
    if progress_record and progress_record.updated_at:
        updated_candidates.append(progress_record.updated_at)
    updated_candidates.extend(
        record.updated_at for record in chapter_records if getattr(record, 'updated_at', None)
    )
    latest_updated_at = max(updated_candidates) if updated_candidates else None

    return {
        'book_id': book_id,
        'current_index': effective_current_index,
        'correct_count': max(base_correct_count, chapter_correct_count),
        'wrong_count': max(base_wrong_count, chapter_wrong_count),
        'is_completed': effective_is_completed,
        'updated_at': latest_updated_at.isoformat() if latest_updated_at else None,
    }


@books_bp.route(f'/{CONFUSABLE_MATCH_BOOK_ID}/custom-chapters', methods=['POST'])
@token_required
def create_confusable_custom_chapters(current_user):
    """Create one or more custom confusable groups for the current user."""
    data = request.get_json() or {}

    try:
        groups = _normalize_confusable_custom_groups(data.get('groups'))
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    resolved_groups, missing_words = _resolve_confusable_group_words(groups)
    if missing_words:
        missing_summary = '、'.join(missing_words[:12])
        if len(missing_words) > 12:
            missing_summary += ' 等'
        return jsonify({
            'error': f'以下单词在现有词库中未找到完整音标或中文释义：{missing_summary}',
            'missing_words': missing_words,
        }), 400

    custom_book = _get_confusable_custom_book(current_user.id, create=True)
    existing_chapter_count = len(custom_book.chapters)
    next_chapter_id = _next_confusable_custom_chapter_id(custom_book)

    created_chapters = []
    total_words_added = 0

    for index, words in enumerate(resolved_groups, start=1):
        chapter_id = str(next_chapter_id + index - 1)
        chapter = CustomBookChapter(
            id=chapter_id,
            book_id=custom_book.id,
            title=_build_confusable_custom_chapter_title(
                [word['word'] for word in words],
                existing_chapter_count + index,
            ),
            word_count=len(words),
            sort_order=existing_chapter_count + index - 1,
        )
        db.session.add(chapter)

        for word in words:
            db.session.add(CustomBookWord(
                chapter_id=chapter_id,
                word=word['word'],
                phonetic=word['phonetic'],
                pos=word['pos'],
                definition=word['definition'],
            ))

        total_words_added += len(words)
        created_chapters.append({
            'id': int(chapter_id),
            'title': chapter.title,
            'word_count': len(words),
            'is_custom': True,
        })

    custom_book.word_count = int(custom_book.word_count or 0) + total_words_added
    db.session.commit()

    return jsonify({
        'created_count': len(created_chapters),
        'created_chapters': created_chapters,
    }), 201


@books_bp.route('/<book_id>/chapters', methods=['GET'])
def get_book_chapters(book_id):
    """Get chapters structure for a book"""
    chapters_data = load_book_chapters(book_id)
    if chapters_data is None:
        return jsonify({'error': 'No chapters found for this book'}), 404

    if _is_confusable_match_book(book_id):
        current_user = _resolve_optional_current_user()
        chapters_data = _merge_confusable_custom_chapters(
            chapters_data,
            current_user.id if current_user else None,
        )

    return jsonify(chapters_data), 200


@books_bp.route('/<book_id>/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter_words(book_id, chapter_id):
    """Get words from a specific chapter"""
    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return jsonify({'error': 'Book not found'}), 404

    if _is_confusable_match_book(book_id):
        current_user = _resolve_optional_current_user()
        custom_chapter = _get_confusable_custom_chapter(
            current_user.id if current_user else None,
            chapter_id,
        )
        if custom_chapter:
            return jsonify({
                'chapter': {
                    'id': chapter_id,
                    'title': custom_chapter.title,
                    'word_count': int(custom_chapter.word_count or len(custom_chapter.words)),
                    'is_custom': True,
                },
                'words': _serialize_confusable_custom_words(custom_chapter),
            }), 200

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, book['file'])

    try:
        # ── JSON books ───────────────────────────────────────────────────────
        if book['file'].endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Structured JSON (premium books)
            if isinstance(data, dict) and 'chapters' in data:
                chapter = next(
                    (ch for ch in data['chapters'] if ch.get('id') == chapter_id), None
                )
                if not chapter:
                    return jsonify({'error': 'Chapter not found'}), 404
                chapter_title = _normalize_chapter_title(chapter.get('title'), chapter.get('id'))
                words = [
                    _enrich_word_entry(_copy_optional_word_fields(w, {
                        'word': w.get('word', ''),
                        'phonetic': w.get('phonetic', ''),
                        'pos': w.get('pos', 'n.'),
                        'definition': w.get('definition', ''),
                    }))
                    for w in chapter.get('words', [])
                ]
                return jsonify({
                    'chapter': {
                        'id': chapter.get('id'),
                        'title': chapter_title,
                        'word_count': chapter.get('word_count'),
                    },
                    'words': words,
                }), 200

            # Flat-list JSON (AWL etc.)
            if isinstance(data, list):
                _build_json_chapters(book_id)
                cached = _json_chapter_cache.get(book_id)
                if not cached:
                    return jsonify({'error': 'Chapters not available for this book'}), 404
                chapter_meta = next(
                    (c for c in cached['chapters'] if c['id'] == chapter_id), None
                )
                if not chapter_meta:
                    return jsonify({'error': 'Chapter not found'}), 404
                all_words = cached['words']
                words = [
                    _enrich_word_entry(_copy_optional_word_fields(all_words[i], {
                        'word': all_words[i].get('word', ''),
                        'phonetic': all_words[i].get('phonetic', ''),
                        'pos': all_words[i].get('pos', 'n.'),
                        'definition': all_words[i].get('definition', '') or all_words[i].get('translation', ''),
                    }))
                    for i in chapter_meta['word_indices']
                    if all_words[i].get('word', '').strip()
                ]
                return jsonify({
                    'chapter': {
                        'id': chapter_meta['id'],
                        'title': chapter_meta['title'],
                        'word_count': chapter_meta['word_count'],
                    },
                    'words': words,
                }), 200

            return jsonify({'error': 'No chapters in this book'}), 404

        # ── CSV books ────────────────────────────────────────────────────────
        elif book['file'].endswith('.csv'):
            _build_csv_chapters(book_id)
            cached = _csv_chapter_cache.get(book_id)
            if not cached:
                return jsonify({'error': 'Chapters not available for this book'}), 404

            chapter_meta = next(
                (c for c in cached['chapters'] if c['id'] == chapter_id), None
            )
            if not chapter_meta:
                return jsonify({'error': 'Chapter not found'}), 404

            raw_rows = cached['row_data']
            words = [
                _enrich_word_entry(_normalize_csv_word(raw_rows[i]))
                for i in chapter_meta['row_indices']
                if raw_rows[i].get('word', '').strip()
            ]

            return jsonify({
                'chapter': {
                    'id': chapter_meta['id'],
                    'title': chapter_meta['title'],
                    'word_count': chapter_meta['word_count'],
                },
                'words': words,
            }), 200

    except Exception as e:
        print(f"Error loading chapter words ({book_id}/{chapter_id}): {e}")
        return jsonify({'error': 'Failed to load chapter'}), 500

    return jsonify({'error': 'Unsupported book format'}), 404


@books_bp.route('/<book_id>/words', methods=['GET'])
def get_book_words(book_id):
    """Get words from a specific book with pagination"""
    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return jsonify({'error': 'Book not found'}), 404

    words = load_book_vocabulary(book_id)
    if words is None:
        return jsonify({'error': 'Failed to load vocabulary'}), 500

    if _is_confusable_match_book(book_id):
        current_user = _resolve_optional_current_user()
        custom_book = _get_confusable_custom_book(current_user.id) if current_user else None
        if custom_book:
            custom_words = []
            for chapter in custom_book.chapters:
                try:
                    chapter_id = int(str(chapter.id))
                except (TypeError, ValueError):
                    continue

                for word in _serialize_confusable_custom_words(chapter):
                    custom_words.append({
                        **word,
                        'chapter_id': chapter_id,
                        'chapter_title': chapter.title,
                    })

            if custom_words:
                words = [*words, *custom_words]

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 100, type=int)

    start = (page - 1) * per_page
    end = start + per_page
    paginated_words = words[start:end]

    return jsonify({
        'words': paginated_words,
        'total': len(words),
        'page': page,
        'per_page': per_page,
        'total_pages': (len(words) + per_page - 1) // per_page
    }), 200


@books_bp.route('/categories', methods=['GET'])
def get_categories():
    """Get all available categories"""
    categories = list(set(b['category'] for b in VOCAB_BOOKS))
    category_names = {
        'listening': '听力词汇',
        'reading': '阅读词汇',
        'writing': '写作词汇',
        'speaking': '口语词汇',
        'academic': '学术词汇',
        'comprehensive': '综合词汇',
        'confusable': '易混辨析',
        'phrases': '短语搭配'
    }
    return jsonify({
        'categories': [
            {'id': c, 'name': category_names.get(c, c)}
            for c in categories
        ]
    }), 200


@books_bp.route('/levels', methods=['GET'])
def get_levels():
    """Get all available levels"""
    levels = list(set(b['level'] for b in VOCAB_BOOKS))
    level_names = {
        'beginner': '初级',
        'intermediate': '中级',
        'advanced': '高级'
    }
    return jsonify({
        'levels': [
            {'id': l, 'name': level_names.get(l, l)}
            for l in levels
        ]
    }), 200


@books_bp.route('/stats', methods=['GET'])
def get_books_stats():
    """Get overall statistics"""
    total_words = sum(b['word_count'] for b in VOCAB_BOOKS)
    return jsonify({
        'total_books': len(VOCAB_BOOKS),
        'total_words': total_words,
        'categories': len(set(b['category'] for b in VOCAB_BOOKS))
    }), 200


@books_bp.route('/progress', methods=['GET'])
@token_required
def get_user_progress(current_user):
    """Get user's progress for all books"""
    user_id = current_user.id
    progress_records = UserBookProgress.query.filter_by(user_id=user_id).all()
    chapter_records = UserChapterProgress.query.filter_by(user_id=user_id).all()

    progress_by_book = {record.book_id: record for record in progress_records}
    chapters_by_book = defaultdict(list)
    for record in chapter_records:
        chapters_by_book[record.book_id].append(record)

    progress_dict = {}
    for book_id in sorted(set(progress_by_book) | set(chapters_by_book)):
        effective_progress = _serialize_effective_book_progress(
            book_id,
            progress_record=progress_by_book.get(book_id),
            chapter_records=chapters_by_book.get(book_id, []),
            user_id=user_id,
        )
        if effective_progress:
            progress_dict[book_id] = effective_progress

    return jsonify({'progress': progress_dict}), 200


@books_bp.route('/progress/<book_id>', methods=['GET'])
@token_required
def get_book_progress(current_user, book_id):
    """Get user's progress for a specific book"""
    user_id = current_user.id
    progress = UserBookProgress.query.filter_by(user_id=user_id, book_id=book_id).first()
    chapter_records = UserChapterProgress.query.filter_by(user_id=user_id, book_id=book_id).all()

    effective_progress = _serialize_effective_book_progress(
        book_id,
        progress_record=progress,
        chapter_records=chapter_records,
        user_id=user_id,
    )
    if not effective_progress:
        return jsonify({'progress': None}), 200

    return jsonify({'progress': effective_progress}), 200


@books_bp.route('/progress', methods=['POST'])
@token_required
def save_progress(current_user):
    """Save user's progress for a book"""
    user_id = current_user.id
    data = request.get_json()

    book_id = data.get('book_id')
    if not book_id:
        return jsonify({'error': 'book_id is required'}), 400

    progress = UserBookProgress.query.filter_by(user_id=user_id, book_id=book_id).first()

    if not progress:
        progress = UserBookProgress(user_id=user_id, book_id=book_id)
        db.session.add(progress)

    if 'current_index' in data:
        progress.current_index = max(progress.current_index or 0, int(data['current_index'] or 0))
    if 'correct_count' in data:
        progress.correct_count = data['correct_count']
    if 'wrong_count' in data:
        progress.wrong_count = data['wrong_count']
    if 'is_completed' in data:
        progress.is_completed = data['is_completed']

    db.session.commit()

    chapter_records = UserChapterProgress.query.filter_by(user_id=user_id, book_id=book_id).all()
    effective_progress = _serialize_effective_book_progress(
        book_id,
        progress_record=progress,
        chapter_records=chapter_records,
        user_id=user_id,
    )

    return jsonify({'progress': effective_progress}), 200


@books_bp.route('/<book_id>/chapters/progress', methods=['GET'])
@token_required
def get_chapter_progress(current_user, book_id):
    """Get user's progress for all chapters in a book, including per-mode breakdown."""
    user_id = current_user.id
    progress_records = UserChapterProgress.query.filter_by(user_id=user_id, book_id=book_id).all()
    mode_records = UserChapterModeProgress.query.filter_by(user_id=user_id, book_id=book_id).all()

    progress_dict = {}
    for record in progress_records:
        d = record.to_dict()
        d['modes'] = {}
        progress_dict[str(record.chapter_id)] = d

    for record in mode_records:
        key = str(record.chapter_id)
        if key not in progress_dict:
            progress_dict[key] = {'modes': {}}
        progress_dict[key]['modes'][record.mode] = record.to_dict()

    return jsonify({'chapter_progress': progress_dict}), 200


@books_bp.route('/<book_id>/chapters/<int:chapter_id>/progress', methods=['POST'])
@token_required
def save_chapter_progress(current_user, book_id, chapter_id):
    """Save user's progress for a specific chapter"""
    user_id = current_user.id
    data = request.get_json()

    progress = UserChapterProgress.query.filter_by(
        user_id=user_id, book_id=book_id, chapter_id=chapter_id
    ).first()

    if not progress:
        progress = UserChapterProgress(
            user_id=user_id, book_id=book_id, chapter_id=chapter_id
        )
        db.session.add(progress)

    before_snapshot = {
        'words_learned': progress.words_learned or 0,
        'correct_count': progress.correct_count or 0,
        'wrong_count': progress.wrong_count or 0,
        'is_completed': bool(progress.is_completed),
    }

    if 'words_learned' in data:
        incoming = int(data['words_learned'] or 0)
        # 客户端可能因「新一轮练习」暂传较小值；取 max 避免已学词数被答题次数语义误伤后回退
        progress.words_learned = max(progress.words_learned or 0, incoming)
    if 'correct_count' in data:
        progress.correct_count = data['correct_count']
    if 'wrong_count' in data:
        progress.wrong_count = data['wrong_count']
    if 'is_completed' in data:
        progress.is_completed = data['is_completed']

    after_snapshot = {
        'words_learned': progress.words_learned or 0,
        'correct_count': progress.correct_count or 0,
        'wrong_count': progress.wrong_count or 0,
        'is_completed': bool(progress.is_completed),
    }
    if after_snapshot != before_snapshot:
        record_learning_event(
            user_id=user_id,
            event_type='chapter_progress_updated',
            source='chapter_progress',
            book_id=book_id,
            chapter_id=str(chapter_id),
            item_count=after_snapshot['words_learned'],
            correct_count=after_snapshot['correct_count'],
            wrong_count=after_snapshot['wrong_count'],
            payload={
                'is_completed': after_snapshot['is_completed'],
            },
        )

    db.session.commit()

    return jsonify({'progress': progress.to_dict()}), 200


@books_bp.route('/<book_id>/chapters/<int:chapter_id>/mode-progress', methods=['POST'])
@token_required
def save_chapter_mode_progress(current_user, book_id, chapter_id):
    """Save per-mode accuracy for a specific chapter. Each mode is stored independently."""
    user_id = current_user.id
    data = request.get_json()
    mode = data.get('mode')

    if not mode:
        return jsonify({'error': '缺少 mode 参数'}), 400

    record = UserChapterModeProgress.query.filter_by(
        user_id=user_id, book_id=book_id, chapter_id=chapter_id, mode=mode
    ).first()

    if not record:
        record = UserChapterModeProgress(
            user_id=user_id, book_id=book_id, chapter_id=chapter_id, mode=mode
        )
        db.session.add(record)

    before_snapshot = {
        'correct_count': record.correct_count or 0,
        'wrong_count': record.wrong_count or 0,
        'is_completed': bool(record.is_completed),
    }

    if 'correct_count' in data:
        record.correct_count = data['correct_count']
    if 'wrong_count' in data:
        record.wrong_count = data['wrong_count']
    if 'is_completed' in data:
        record.is_completed = data['is_completed']

    after_snapshot = {
        'correct_count': record.correct_count or 0,
        'wrong_count': record.wrong_count or 0,
        'is_completed': bool(record.is_completed),
    }
    if after_snapshot != before_snapshot:
        record_learning_event(
            user_id=user_id,
            event_type='chapter_mode_progress_updated',
            source='chapter_mode_progress',
            mode=mode,
            book_id=book_id,
            chapter_id=str(chapter_id),
            correct_count=after_snapshot['correct_count'],
            wrong_count=after_snapshot['wrong_count'],
            payload={
                'is_completed': after_snapshot['is_completed'],
            },
        )

    db.session.commit()
    return jsonify({'mode_progress': record.to_dict()}), 200


# ── User's Added Books ──────────────────────────────────────────────────────────

@books_bp.route('/my', methods=['GET'])
@token_required
def get_my_books(current_user):
    """Get all books added by the user."""
    records = UserAddedBook.query.filter_by(user_id=current_user.id).all()
    return jsonify({'book_ids': [r.book_id for r in records]}), 200


@books_bp.route('/my', methods=['POST'])
@token_required
def add_my_book(current_user):
    """Add a book to the user's list."""
    data = request.get_json()
    book_id = data.get('book_id')
    if not book_id:
        return jsonify({'error': '缺少 book_id'}), 400

    existing = UserAddedBook.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if existing:
        return jsonify({'message': '已在词书中'}), 200

    record = UserAddedBook(user_id=current_user.id, book_id=book_id)
    db.session.add(record)
    db.session.commit()
    return jsonify({'book_id': book_id}), 201


@books_bp.route('/my/<book_id>', methods=['DELETE'])
@token_required
def remove_my_book(current_user, book_id):
    """Remove a book from the user's list."""
    record = UserAddedBook.query.filter_by(user_id=current_user.id, book_id=book_id).first()
    if record:
        db.session.delete(record)
        db.session.commit()
    return jsonify({'message': '已移除'}), 200


# ── GET /api/books/examples ───────────────────────────────────────────────────

@books_bp.route('/examples', methods=['GET'])
def get_word_examples():
    """Return example sentences for one or more words.

    Query params:
      word   — single word lookup, e.g. ?word=record
      words  — comma-separated batch lookup, e.g. ?words=record,library,transport

    Response:
      { "examples": { "<word>": [{"en": "...", "zh": "..."}] } }
    """
    examples_map = _load_examples()

    single = request.args.get('word', '').strip().lower()
    batch_raw = request.args.get('words', '').strip()

    if single:
        # Single-word lookup
        result = {}
        hits = examples_map.get(single)
        if hits:
            result[single] = hits
        return jsonify({'examples': result}), 200

    if batch_raw:
        # Batch lookup — comma-separated
        words = [w.strip().lower() for w in batch_raw.split(',') if w.strip()]
        result = {}
        for w in words:
            hits = examples_map.get(w)
            if hits:
                result[w] = hits
        return jsonify({'examples': result}), 200

    return jsonify({'error': 'Provide ?word=<word> or ?words=<word1,word2,...>'}), 400
