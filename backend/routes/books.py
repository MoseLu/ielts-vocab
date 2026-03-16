import os
import json
from flask import Blueprint, jsonify, request
from models import db, UserBookProgress, User
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
    {
        'id': 'ielts_listening',
        'title': '雅思听力核心词汇',
        'description': '雅思听力考试高频词汇，覆盖教育、租房、旅游等常见场景',
        'icon': 'headphones',
        'color': '#3B82F6',
        'category': 'listening',
        'level': 'intermediate',
        'word_count': 224,
        'file': 'ielts_vocabulary_listening.json'
    },
    {
        'id': 'ielts_reading',
        'title': '雅思阅读核心词汇',
        'description': '雅思阅读同义替换词汇，提升阅读理解能力',
        'icon': 'book-open',
        'color': '#10B981',
        'category': 'reading',
        'level': 'intermediate',
        'word_count': 120,
        'file': 'ielts_vocabulary_reading.json'
    },
    {
        'id': 'ielts_writing',
        'title': '雅思写作核心词汇',
        'description': '雅思写作高分词汇，学术表达必备',
        'icon': 'edit',
        'color': '#F59E0B',
        'category': 'writing',
        'level': 'advanced',
        'word_count': 523,
        'file': 'ielts_vocabulary_writing.json'
    },
    {
        'id': 'ielts_speaking',
        'title': '雅思口语核心词汇',
        'description': '雅思口语话题词汇，提升口语表达能力',
        'icon': 'mic',
        'color': '#EF4444',
        'category': 'speaking',
        'level': 'beginner',
        'word_count': 51,
        'file': 'ielts_vocabulary_speaking.json'
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
        'file': 'ielts_vocabulary_awl_extended.json'
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
        'file': 'ielts_vocabulary_6260.csv'
    },
    {
        'id': 'ielts_phrases',
        'title': '雅思学术短语',
        'description': '雅思常用学术短语和搭配',
        'icon': 'link',
        'color': '#06B6D4',
        'category': 'phrases',
        'level': 'intermediate',
        'word_count': 30,
        'file': 'ielts_vocabulary_phrases.json'
    },
    {
        'id': 'ielts_ultimate',
        'title': '雅思终极词汇库',
        'description': '精选2814个雅思高频词汇',
        'icon': 'star',
        'color': '#F97316',
        'category': 'comprehensive',
        'level': 'advanced',
        'word_count': 2814,
        'file': 'ielts_vocabulary_ultimate.csv'
    }
]

# Cache for loaded vocabulary data
_vocabulary_cache = {}


def get_vocab_data_path():
    """Get the path to vocabulary_data directory"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'vocabulary_data')


def load_book_vocabulary(book_id):
    """Load vocabulary for a specific book"""
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
                if isinstance(data, list):
                    raw_words = data
                elif isinstance(data, dict) and 'vocabulary' in data:
                    raw_words = data['vocabulary']
                else:
                    raw_words = []
            # Normalize field names
            words = []
            for w in raw_words:
                words.append({
                    'word': w.get('word', ''),
                    'phonetic': w.get('phonetic', ''),
                    'pos': w.get('pos', 'n.'),
                    'definition': w.get('definition', '') or w.get('translation', ''),
                })
        elif book['file'].endswith('.csv'):
            import csv
            words = []
            with open(file_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    word = row.get('word', '').strip()
                    if word:
                        words.append({
                            'word': word,
                            'phonetic': row.get('phonetic', ''),
                            'pos': row.get('pos', 'n.'),
                            'definition': row.get('translation', '') or row.get('definition', ''),
                        })
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

    books = VOCAB_BOOKS.copy()

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