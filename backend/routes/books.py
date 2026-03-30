import os
import json
import csv as csv_module
from flask import Blueprint, jsonify, request
from models import db, UserBookProgress, UserChapterProgress, UserChapterModeProgress, UserAddedBook
from routes.middleware import token_required

books_bp = Blueprint('books', __name__)


def init_books(app_instance):
    pass  # kept for API compatibility — no longer needs app reference

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
# Cache for vocabulary examples: {word_lower: [examples]}
_examples_cache = None


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


def get_vocab_data_path():
    """Get the path to vocabulary_data directory"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'vocabulary_data')


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
                        for w in chapter.get('words', []):
                            raw_words.append({
                                'word': w.get('word', ''),
                                'phonetic': w.get('phonetic', ''),
                                'pos': w.get('pos', 'n.'),
                                'definition': w.get('definition', ''),
                                'chapter_id': chapter.get('id'),
                                'chapter_title': chapter.get('title')
                            })
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
                                    words.append({
                                        'word': w.get('word', ''),
                                        'phonetic': w.get('phonetic', ''),
                                        'pos': w.get('pos', 'n.'),
                                        'definition': w.get('definition', '') or w.get('translation', ''),
                                        'chapter_id': ch['id'],
                                        'chapter_title': ch['title'],
                                    })
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
                words.append(word_entry)

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
                            words.append({
                                'word': word,
                                'phonetic': row.get('phonetic', ''),
                                'pos': row.get('pos', 'n.'),
                                'definition': row.get('translation', '') or row.get('definition', ''),
                                'chapter_id': ch['id'],
                                'chapter_title': ch['title'],
                            })
            else:
                # Fallback: flat load without chapters
                with open(file_path, 'r', encoding='utf-8-sig') as f:
                    words = [
                        _normalize_csv_word(row)
                        for row in csv_module.DictReader(f)
                        if row.get('word', '').strip()
                    ]
        else:
            words = []

        # Merge examples into all word entries before caching
        words = [_merge_examples(w) for w in words]
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

    books = VOCAB_BOOKS.copy()

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

    return jsonify({'book': book}), 200


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
                        'title': ch.get('title'),
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


@books_bp.route('/<book_id>/chapters', methods=['GET'])
def get_book_chapters(book_id):
    """Get chapters structure for a book"""
    chapters_data = load_book_chapters(book_id)
    if chapters_data is None:
        return jsonify({'error': 'No chapters found for this book'}), 404

    return jsonify(chapters_data), 200


@books_bp.route('/<book_id>/chapters/<int:chapter_id>', methods=['GET'])
def get_chapter_words(book_id, chapter_id):
    """Get words from a specific chapter"""
    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book:
        return jsonify({'error': 'Book not found'}), 404

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
                words = [
                    _merge_examples({
                        'word': w.get('word', ''),
                        'phonetic': w.get('phonetic', ''),
                        'pos': w.get('pos', 'n.'),
                        'definition': w.get('definition', ''),
                    })
                    for w in chapter.get('words', [])
                ]
                return jsonify({
                    'chapter': {
                        'id': chapter.get('id'),
                        'title': chapter.get('title'),
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
                    _merge_examples({
                        'word': all_words[i].get('word', ''),
                        'phonetic': all_words[i].get('phonetic', ''),
                        'pos': all_words[i].get('pos', 'n.'),
                        'definition': all_words[i].get('definition', '') or all_words[i].get('translation', ''),
                    })
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
                _merge_examples(_normalize_csv_word(raw_rows[i]))
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

    progress_dict = {}
    for record in progress_records:
        progress_dict[record.book_id] = record.to_dict()

    return jsonify({'progress': progress_dict}), 200


@books_bp.route('/progress/<book_id>', methods=['GET'])
@token_required
def get_book_progress(current_user, book_id):
    """Get user's progress for a specific book"""
    user_id = current_user.id
    progress = UserBookProgress.query.filter_by(user_id=user_id, book_id=book_id).first()

    if not progress:
        return jsonify({'progress': None}), 200

    return jsonify({'progress': progress.to_dict()}), 200


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
        progress.current_index = data['current_index']
    if 'correct_count' in data:
        progress.correct_count = data['correct_count']
    if 'wrong_count' in data:
        progress.wrong_count = data['wrong_count']
    if 'is_completed' in data:
        progress.is_completed = data['is_completed']

    db.session.commit()

    return jsonify({'progress': progress.to_dict()}), 200


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

    if 'correct_count' in data:
        record.correct_count = data['correct_count']
    if 'wrong_count' in data:
        record.wrong_count = data['wrong_count']
    if 'is_completed' in data:
        record.is_completed = data['is_completed']

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
