import time

from models import db, User, UserQuickMemoryRecord
from routes import ai as ai_routes
from services.quick_memory_schedule import compute_quick_memory_next_review_ms


def register_and_login(client, username='qm-review-user', password='password123'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@example.com',
    })
    res = client.post('/api/auth/login', json={
        'email': username,
        'password': password,
    })
    assert res.status_code == 200


def test_quick_memory_review_queue_returns_due_words_with_metadata(client, app, monkeypatch):
    register_and_login(client)

    now_ms = int(time.time() * 1000)
    upcoming_next_review = compute_quick_memory_next_review_ms(1, now_ms - 3_000)

    monkeypatch.setattr(ai_routes, '_get_quick_memory_vocab_lookup', lambda: {
        'alpha': [{
            'word': 'alpha',
            'phonetic': '/a/',
            'pos': 'n.',
            'definition': 'alpha def',
            'group_key': 'alpha-group',
            'listening_confusables': [{'word': 'alfa', 'phonetic': '/ˈalfə/', 'pos': 'n.', 'definition': 'alfa def', 'group_key': 'alpha-group-2'}],
            'examples': [{'en': 'Alpha appears in the first example.', 'zh': 'alpha 出现在第一个例句里。'}],
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        }],
        'beta': [{
            'word': 'beta',
            'phonetic': '/b/',
            'pos': 'n.',
            'definition': 'beta def',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        }],
        'gamma': [{
            'word': 'gamma',
            'phonetic': '/g/',
            'pos': 'n.',
            'definition': 'gamma def',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '2',
            'chapter_title': 'Chapter 2',
        }],
        'delta': [{
            'word': 'delta',
            'phonetic': '/d/',
            'pos': 'n.',
            'definition': 'delta def',
            'book_id': 'book-b',
            'book_title': 'Book B',
            'chapter_id': '3',
            'chapter_title': 'Chapter 3',
        }],
    })
    monkeypatch.setattr(ai_routes, '_get_global_vocab_pool', lambda: [
        {'word': 'alpha', 'phonetic': '/a/', 'pos': 'n.', 'definition': 'alpha def'},
        {'word': 'beta', 'phonetic': '/b/', 'pos': 'n.', 'definition': 'beta def'},
        {'word': 'gamma', 'phonetic': '/g/', 'pos': 'n.', 'definition': 'gamma def'},
        {'word': 'delta', 'phonetic': '/d/', 'pos': 'n.', 'definition': 'delta def'},
    ])

    with app.app_context():
        user = User.query.filter_by(username='qm-review-user').first()
        assert user is not None
        db.session.add_all([
            UserQuickMemoryRecord(
                user_id=user.id,
                word='alpha',
                status='known',
                first_seen=now_ms - 10_000,
                last_seen=now_ms - 5_000,
                known_count=2,
                unknown_count=0,
                next_review=now_ms - 2_000,
                fuzzy_count=0,
            ),
            UserQuickMemoryRecord(
                user_id=user.id,
                word='beta',
                status='unknown',
                first_seen=now_ms - 8_000,
                last_seen=now_ms - 4_000,
                known_count=0,
                unknown_count=1,
                next_review=now_ms - 1_000,
                fuzzy_count=1,
            ),
            UserQuickMemoryRecord(
                user_id=user.id,
                word='gamma',
                status='known',
                first_seen=now_ms - 6_000,
                last_seen=now_ms - 3_000,
                known_count=1,
                unknown_count=0,
                next_review=now_ms + 86_400_000,
                fuzzy_count=0,
            ),
            UserQuickMemoryRecord(
                user_id=user.id,
                word='delta',
                status='known',
                first_seen=now_ms - 6_000,
                last_seen=now_ms - 3_000,
                known_count=1,
                unknown_count=0,
                next_review=now_ms + 10 * 86_400_000,
                fuzzy_count=0,
            ),
        ])
        db.session.commit()

    res = client.get('/api/ai/quick-memory/review-queue?limit=3&within_days=3')

    assert res.status_code == 200
    data = res.get_json()
    assert data['summary'] == {
        'due_count': 2,
        'upcoming_count': 1,
        'returned_count': 3,
        'review_window_days': 3,
        'offset': 0,
        'limit': 3,
        'total_count': 3,
        'has_more': False,
        'next_offset': None,
        'contexts': [
            {
                'book_id': 'book-a',
                'book_title': 'Book A',
                'chapter_id': '1',
                'chapter_title': 'Chapter 1',
                'due_count': 2,
                'upcoming_count': 0,
                'total_count': 2,
                'next_review': now_ms - 2_000,
            },
            {
                'book_id': 'book-a',
                'book_title': 'Book A',
                'chapter_id': '2',
                'chapter_title': 'Chapter 2',
                'due_count': 0,
                'upcoming_count': 1,
                'total_count': 1,
                'next_review': upcoming_next_review,
            },
        ],
        'selected_context': {
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
            'due_count': 2,
            'upcoming_count': 0,
            'total_count': 2,
            'next_review': now_ms - 2_000,
        },
    }
    assert [word['word'] for word in data['words']] == ['alpha', 'beta', 'gamma']
    assert data['words'][0]['definition'] == 'alpha def'
    assert data['words'][0]['chapter_title'] == 'Chapter 1'
    assert data['words'][0]['examples'] == [{'en': 'Alpha appears in the first example.', 'zh': 'alpha 出现在第一个例句里。'}]
    assert data['words'][0]['listening_confusables'][0]['word'] == 'alfa'
    assert data['words'][1]['dueState'] == 'due'
    assert data['words'][2]['dueState'] == 'upcoming'


def test_quick_memory_review_queue_supports_offset_pagination(client, app, monkeypatch):
    register_and_login(client, username='qm-review-offset-user')

    now_ms = int(time.time() * 1000)
    upcoming_next_review = compute_quick_memory_next_review_ms(1, now_ms - 2_000)

    monkeypatch.setattr(ai_routes, '_get_quick_memory_vocab_lookup', lambda: {
        'alpha': [{
            'word': 'alpha',
            'phonetic': '/a/',
            'pos': 'n.',
            'definition': 'alpha def',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        }],
        'beta': [{
            'word': 'beta',
            'phonetic': '/b/',
            'pos': 'n.',
            'definition': 'beta def',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        }],
        'gamma': [{
            'word': 'gamma',
            'phonetic': '/g/',
            'pos': 'n.',
            'definition': 'gamma def',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        }],
        'delta': [{
            'word': 'delta',
            'phonetic': '/d/',
            'pos': 'n.',
            'definition': 'delta def',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '2',
            'chapter_title': 'Chapter 2',
        }],
    })
    monkeypatch.setattr(ai_routes, '_get_global_vocab_pool', lambda: [
        {'word': 'alpha', 'phonetic': '/a/', 'pos': 'n.', 'definition': 'alpha def'},
        {'word': 'beta', 'phonetic': '/b/', 'pos': 'n.', 'definition': 'beta def'},
        {'word': 'gamma', 'phonetic': '/g/', 'pos': 'n.', 'definition': 'gamma def'},
        {'word': 'delta', 'phonetic': '/d/', 'pos': 'n.', 'definition': 'delta def'},
    ])

    with app.app_context():
        user = User.query.filter_by(username='qm-review-offset-user').first()
        assert user is not None
        db.session.add_all([
            UserQuickMemoryRecord(
                user_id=user.id,
                word='alpha',
                status='known',
                first_seen=now_ms - 10_000,
                last_seen=now_ms - 5_000,
                known_count=2,
                unknown_count=0,
                next_review=now_ms - 4_000,
                fuzzy_count=0,
            ),
            UserQuickMemoryRecord(
                user_id=user.id,
                word='beta',
                status='known',
                first_seen=now_ms - 9_000,
                last_seen=now_ms - 4_000,
                known_count=2,
                unknown_count=0,
                next_review=now_ms - 3_000,
                fuzzy_count=0,
            ),
            UserQuickMemoryRecord(
                user_id=user.id,
                word='gamma',
                status='unknown',
                first_seen=now_ms - 8_000,
                last_seen=now_ms - 3_000,
                known_count=0,
                unknown_count=1,
                next_review=now_ms - 2_000,
                fuzzy_count=1,
            ),
            UserQuickMemoryRecord(
                user_id=user.id,
                word='delta',
                status='known',
                first_seen=now_ms - 7_000,
                last_seen=now_ms - 2_000,
                known_count=1,
                unknown_count=0,
                next_review=now_ms + 86_400_000,
                fuzzy_count=0,
            ),
        ])
        db.session.commit()

    res = client.get('/api/ai/quick-memory/review-queue?limit=2&within_days=3&offset=2')

    assert res.status_code == 200
    data = res.get_json()
    assert [word['word'] for word in data['words']] == ['gamma', 'delta']
    assert data['words'][0]['dueState'] == 'due'
    assert data['words'][1]['dueState'] == 'upcoming'
    assert data['summary'] == {
        'due_count': 3,
        'upcoming_count': 1,
        'returned_count': 2,
        'review_window_days': 3,
        'offset': 2,
        'limit': 2,
        'total_count': 4,
        'has_more': False,
        'next_offset': None,
        'contexts': [
            {
                'book_id': 'book-a',
                'book_title': 'Book A',
                'chapter_id': '1',
                'chapter_title': 'Chapter 1',
                'due_count': 3,
                'upcoming_count': 0,
                'total_count': 3,
                'next_review': now_ms - 4_000,
            },
            {
                'book_id': 'book-a',
                'book_title': 'Book A',
                'chapter_id': '2',
                'chapter_title': 'Chapter 2',
                'due_count': 0,
                'upcoming_count': 1,
                'total_count': 1,
                'next_review': upcoming_next_review,
            },
        ],
        'selected_context': {
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
            'due_count': 3,
            'upcoming_count': 0,
            'total_count': 3,
            'next_review': now_ms - 4_000,
        },
    }


def test_quick_memory_review_queue_can_limit_to_due_scope(client, app, monkeypatch):
    register_and_login(client, username='qm-review-due-only-user')

    now_ms = int(time.time() * 1000)

    monkeypatch.setattr(ai_routes, '_get_quick_memory_vocab_lookup', lambda: {
        'alpha': [{
            'word': 'alpha',
            'phonetic': '/a/',
            'pos': 'n.',
            'definition': 'alpha def',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        }],
        'beta': [{
            'word': 'beta',
            'phonetic': '/b/',
            'pos': 'n.',
            'definition': 'beta def',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '2',
            'chapter_title': 'Chapter 2',
        }],
    })
    monkeypatch.setattr(ai_routes, '_get_global_vocab_pool', lambda: [
        {'word': 'alpha', 'phonetic': '/a/', 'pos': 'n.', 'definition': 'alpha def'},
        {'word': 'beta', 'phonetic': '/b/', 'pos': 'n.', 'definition': 'beta def'},
    ])

    with app.app_context():
        user = User.query.filter_by(username='qm-review-due-only-user').first()
        assert user is not None
        db.session.add_all([
            UserQuickMemoryRecord(
                user_id=user.id,
                word='alpha',
                status='known',
                first_seen=now_ms - 10_000,
                last_seen=now_ms - 5_000,
                known_count=2,
                unknown_count=0,
                next_review=now_ms - 2_000,
                fuzzy_count=0,
            ),
            UserQuickMemoryRecord(
                user_id=user.id,
                word='beta',
                status='known',
                first_seen=now_ms - 9_000,
                last_seen=now_ms - 4_000,
                known_count=1,
                unknown_count=0,
                next_review=now_ms + 86_400_000,
                fuzzy_count=0,
            ),
        ])
        db.session.commit()

    res = client.get('/api/ai/quick-memory/review-queue?limit=10&within_days=3&scope=due')

    assert res.status_code == 200
    data = res.get_json()
    assert [word['word'] for word in data['words']] == ['alpha']
    assert data['summary']['due_count'] == 1
    assert data['summary']['upcoming_count'] == 0
    assert data['summary']['total_count'] == 1


def test_quick_memory_review_queue_filters_by_book_and_chapter(client, app, monkeypatch):
    register_and_login(client, username='qm-review-filter-user')

    now_ms = int(time.time() * 1000)

    monkeypatch.setattr(ai_routes, '_get_quick_memory_vocab_lookup', lambda: {
        'alpha': [{
            'word': 'alpha',
            'phonetic': '/a/',
            'pos': 'n.',
            'definition': 'alpha def',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '1',
            'chapter_title': 'Chapter 1',
        }],
        'beta': [{
            'word': 'beta',
            'phonetic': '/b/',
            'pos': 'n.',
            'definition': 'beta def',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'chapter_id': '2',
            'chapter_title': 'Chapter 2',
        }],
    })
    monkeypatch.setattr(ai_routes, '_get_global_vocab_pool', lambda: [
        {'word': 'alpha', 'phonetic': '/a/', 'pos': 'n.', 'definition': 'alpha def'},
        {'word': 'beta', 'phonetic': '/b/', 'pos': 'n.', 'definition': 'beta def'},
    ])

    with app.app_context():
        user = User.query.filter_by(username='qm-review-filter-user').first()
        assert user is not None
        db.session.add_all([
            UserQuickMemoryRecord(
                user_id=user.id,
                word='alpha',
                book_id='book-a',
                chapter_id='1',
                status='known',
                first_seen=now_ms - 10_000,
                last_seen=now_ms - 5_000,
                known_count=2,
                unknown_count=0,
                next_review=now_ms - 2_000,
                fuzzy_count=0,
            ),
            UserQuickMemoryRecord(
                user_id=user.id,
                word='beta',
                book_id='book-a',
                chapter_id='2',
                status='known',
                first_seen=now_ms - 9_000,
                last_seen=now_ms - 4_000,
                known_count=1,
                unknown_count=0,
                next_review=now_ms - 1_000,
                fuzzy_count=0,
            ),
        ])
        db.session.commit()

    res = client.get('/api/ai/quick-memory/review-queue?limit=10&within_days=3&book_id=book-a&chapter_id=2')

    assert res.status_code == 200
    data = res.get_json()
    assert [word['word'] for word in data['words']] == ['beta']
    assert data['summary']['selected_context'] == {
        'book_id': 'book-a',
        'book_title': 'Book A',
        'chapter_id': '2',
        'chapter_title': 'Chapter 2',
        'due_count': 1,
        'upcoming_count': 0,
        'total_count': 1,
        'next_review': now_ms - 1_000,
    }
