import os
import json
import csv as csv_module
from flask import Blueprint, jsonify, request
from models import db, UserBookProgress, UserChapterProgress, User
import jwt
from functools import wraps

books_bp = Blueprint('books', __name__)


def token_required(f):
    """Custom JWT decorator - same as auth.py"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]

        if not token:
            return jsonify({'error': 'Token is missing'}), 401

        try:
            from config import Config
            data = jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(data['user_id'])
            if not current_user:
                return jsonify({'error': 'User not found'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)

    return decorated

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

# Cache for loaded vocabulary data
_vocabulary_cache = {}
# Cache for CSV chapter structures: {book_id: {'chapters': [...], 'row_data': [...]}}
_csv_chapter_cache = {}


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
        # ── JSON books (premium, AWL) ────────────────────────────────────────
        if book['file'].endswith('.json'):
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
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
                if isinstance(data, dict) and 'chapters' in data:
                    chapter = next(
                        (ch for ch in data['chapters'] if ch.get('id') == chapter_id), None
                    )
                    if not chapter:
                        return jsonify({'error': 'Chapter not found'}), 404

                    words = [
                        {
                            'word': w.get('word', ''),
                            'phonetic': w.get('phonetic', ''),
                            'pos': w.get('pos', 'n.'),
                            'definition': w.get('definition', ''),
                        }
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
                _normalize_csv_word(raw_rows[i])
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
    """Get user's progress for all chapters in a book"""
    user_id = current_user.id
    progress_records = UserChapterProgress.query.filter_by(user_id=user_id, book_id=book_id).all()

    progress_dict = {}
    for record in progress_records:
        progress_dict[record.chapter_id] = record.to_dict()

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
        progress.words_learned = data['words_learned']
    if 'correct_count' in data:
        progress.correct_count = data['correct_count']
    if 'wrong_count' in data:
        progress.wrong_count = data['wrong_count']
    if 'is_completed' in data:
        progress.is_completed = data['is_completed']

    db.session.commit()

    return jsonify({'progress': progress.to_dict()}), 200
