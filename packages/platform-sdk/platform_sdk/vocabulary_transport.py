from __future__ import annotations

import csv
from pathlib import Path

from flask import Blueprint, jsonify


vocabulary_bp = Blueprint('vocabulary', __name__)

_word_list = None
_vocabulary_data = None


def _csv_path() -> Path:
    return Path(__file__).resolve().parents[3] / 'vocabulary_data' / 'ielts_vocabulary_6260.csv'


def load_vocabulary_from_csv():
    global _word_list
    if _word_list is not None:
        return _word_list

    words = []
    try:
        with _csv_path().open('r', encoding='utf-8-sig') as handle:
            reader = csv.DictReader(handle)
            seen_words = set()
            for row in reader:
                word = row.get('word', '').strip()
                if not word or word in seen_words:
                    continue
                seen_words.add(word)
                pos = row.get('pos', '').strip()
                pos_map = {
                    'noun': 'n.',
                    'verb': 'v.',
                    'adj': 'adj.',
                    'adverb': 'adv.',
                    'adjective': 'adj.',
                    'adv': 'adv.',
                    'n': 'n.',
                    'v': 'v.',
                }
                normalized_pos = pos_map.get(
                    pos.lower(),
                    pos + '.' if pos and not pos.endswith('.') else (pos or 'n.'),
                )
                words.append({
                    'word': word,
                    'phonetic': '',
                    'pos': normalized_pos,
                    'definition': row.get('translation', '').strip(),
                    'category': row.get('category', '').strip(),
                    'level': row.get('level', '').strip(),
                })
    except FileNotFoundError:
        words = [
            {'word': 'abandon', 'phonetic': '/əˈbændən/', 'pos': 'v.', 'definition': '放弃；遗弃'},
            {'word': 'ability', 'phonetic': '/əˈbɪləti/', 'pos': 'n.', 'definition': '能力'},
            {'word': 'academic', 'phonetic': '/ˌækəˈdemɪk/', 'pos': 'adj.', 'definition': '学术的'},
            {'word': 'accept', 'phonetic': '/əkˈsept/', 'pos': 'v.', 'definition': '接受；承认'},
            {'word': 'access', 'phonetic': '/ˈækses/', 'pos': 'n.', 'definition': '进入；访问'},
        ]

    _word_list = words
    return _word_list


def _generate_vocabulary():
    word_list = load_vocabulary_from_csv()
    words = []
    words_to_use = word_list[:3000]
    for day in range(1, 31):
        start_idx = (day - 1) * 100
        for offset in range(100):
            idx = start_idx + offset
            source_idx = idx if idx < len(words_to_use) else (idx % len(word_list))
            source = words_to_use[source_idx] if idx < len(words_to_use) else word_list[source_idx]
            words.append({
                'id': idx + 1,
                'day': day,
                **source,
            })
    return words


def get_vocabulary_data():
    global _vocabulary_data
    if _vocabulary_data is None:
        _vocabulary_data = _generate_vocabulary()
    return _vocabulary_data


@vocabulary_bp.route('', methods=['GET'])
def get_vocabulary():
    return jsonify({'vocabulary': get_vocabulary_data()}), 200


@vocabulary_bp.route('/day/<int:day>', methods=['GET'])
def get_day_vocabulary(day):
    if day < 1 or day > 30:
        return jsonify({'error': 'Day must be between 1 and 30'}), 400

    day_vocabulary = [row for row in get_vocabulary_data() if row['day'] == day]
    return jsonify({'vocabulary': day_vocabulary}), 200


@vocabulary_bp.route('/stats', methods=['GET'])
def get_vocabulary_stats():
    word_list = load_vocabulary_from_csv()
    return jsonify({
        'total_words_available': len(word_list),
        'total_words_used': min(len(word_list), 3000),
        'days': 30,
        'words_per_day': 100,
    }), 200
