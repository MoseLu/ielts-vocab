import os
import csv
from flask import Blueprint, jsonify

vocabulary_bp = Blueprint('vocabulary', __name__)

# Cache for vocabulary data
_word_list = None
_vocabulary_data = None


def load_vocabulary_from_csv():
    """Load vocabulary from CSV file"""
    global _word_list
    if _word_list is not None:
        return _word_list

    csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'vocabulary_data', 'ielts_vocabulary_6260.csv')
    words = []

    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            seen_words = set()
            for row in reader:
                word = row.get('word', '').strip()
                if word and word not in seen_words:
                    seen_words.add(word)
                    # Map CSV fields to expected format
                    pos = row.get('pos', '').strip()
                    # Normalize part of speech
                    pos_map = {
                        'noun': 'n.', 'verb': 'v.', 'adj': 'adj.', 'adverb': 'adv.',
                        'adjective': 'adj.', 'adv': 'adv.', 'n': 'n.', 'v': 'v.'
                    }
                    pos = pos_map.get(pos.lower(), pos + '.' if pos and not pos.endswith('.') else pos or 'n.')

                    words.append({
                        'word': word,
                        'phonetic': '',  # CSV doesn't have phonetic, can be added later
                        'pos': pos,
                        'definition': row.get('translation', '').strip(),
                        'category': row.get('category', '').strip(),
                        'level': row.get('level', '').strip(),
                    })
        _word_list = words
        print(f"Loaded {len(words)} words from vocabulary CSV")
    except FileNotFoundError:
        print(f"Warning: CSV file not found at {csv_path}, using fallback vocabulary")
        _word_list = get_fallback_vocabulary()

    return _word_list


def get_fallback_vocabulary():
    """Fallback vocabulary if CSV is not available"""
    return [
        {'word': 'abandon', 'phonetic': '/əˈbændən/', 'pos': 'v.', 'definition': '放弃；遗弃'},
        {'word': 'ability', 'phonetic': '/əˈbɪləti/', 'pos': 'n.', 'definition': '能力'},
        {'word': 'academic', 'phonetic': '/ˌækəˈdemɪk/', 'pos': 'adj.', 'definition': '学术的'},
        {'word': 'accept', 'phonetic': '/əkˈsept/', 'pos': 'v.', 'definition': '接受；承认'},
        {'word': 'access', 'phonetic': '/ˈækses/', 'pos': 'n.', 'definition': '进入；访问'},
    ]


def generate_vocabulary():
    """Generate 30 days of vocabulary (3000 words total)"""
    word_list = load_vocabulary_from_csv()
    words = []

    # Use first 3000 unique words for 30 days (100 words/day)
    total_needed = 3000
    words_to_use = word_list[:total_needed]

    for day in range(1, 31):
        start_idx = (day - 1) * 100
        for i in range(100):
            idx = start_idx + i
            if idx < len(words_to_use):
                words.append({
                    'id': idx + 1,
                    'day': day,
                    **words_to_use[idx]
                })
            else:
                # Fallback: cycle through available words
                cycle_idx = idx % len(word_list)
                words.append({
                    'id': idx + 1,
                    'day': day,
                    **word_list[cycle_idx]
                })

    return words


def get_vocabulary_data():
    """Get cached vocabulary data"""
    global _vocabulary_data
    if _vocabulary_data is None:
        _vocabulary_data = generate_vocabulary()
    return _vocabulary_data


@vocabulary_bp.route('', methods=['GET'])
def get_vocabulary():
    """Get all vocabulary"""
    return jsonify({'vocabulary': get_vocabulary_data()}), 200


@vocabulary_bp.route('/day/<int:day>', methods=['GET'])
def get_day_vocabulary(day):
    """Get vocabulary for a specific day"""
    if day < 1 or day > 30:
        return jsonify({'error': 'Day must be between 1 and 30'}), 400

    vocabulary = get_vocabulary_data()
    day_vocabulary = [w for w in vocabulary if w['day'] == day]
    return jsonify({'vocabulary': day_vocabulary}), 200


@vocabulary_bp.route('/stats', methods=['GET'])
def get_vocabulary_stats():
    """Get vocabulary statistics"""
    word_list = load_vocabulary_from_csv()
    return jsonify({
        'total_words_available': len(word_list),
        'total_words_used': min(len(word_list), 3000),
        'days': 30,
        'words_per_day': 100
    }), 200