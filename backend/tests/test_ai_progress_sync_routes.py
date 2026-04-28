import json

from models import (
    User,
    UserLearningDailyLedger,
    UserLearningEvent,
    UserQuickMemoryRecord,
    UserSmartWordStat,
    UserWordMasteryState,
    UserWrongWord,
    db,
)


def register_and_login(client, username='sync-route-user', password='password123'):
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


def test_quick_memory_sync_ignores_older_snapshot(client, app):
    register_and_login(client, username='quick-memory-sync-user')

    with app.app_context():
        user = User.query.filter_by(username='quick-memory-sync-user').first()
        assert user is not None
        db.session.add(UserQuickMemoryRecord(
            user_id=user.id,
            word='alpha',
            book_id='book-new',
            chapter_id='5',
            status='known',
            first_seen=100,
            last_seen=300,
            known_count=2,
            unknown_count=0,
            next_review=400,
            fuzzy_count=1,
        ))
        db.session.commit()

    res = client.post('/api/ai/quick-memory/sync', json={
        'records': [{
            'word': 'alpha',
            'bookId': 'book-old',
            'chapterId': '1',
            'status': 'unknown',
            'firstSeen': 50,
            'lastSeen': 200,
            'knownCount': 0,
            'unknownCount': 2,
            'nextReview': 250,
            'fuzzyCount': 0,
        }],
    })

    assert res.status_code == 200
    with app.app_context():
        record = UserQuickMemoryRecord.query.filter_by(word='alpha').first()
        assert record is not None
        assert record.book_id == 'book-new'
        assert record.chapter_id == '5'
        assert record.status == 'known'
        assert record.last_seen == 300
        assert record.known_count == 2


def test_quick_memory_sync_records_unified_attempt_and_mastery(client, app):
    register_and_login(client, username='quick-memory-attempt-user')

    res = client.post('/api/ai/quick-memory/sync', json={
        'source': 'quickmemory',
        'records': [
            {
                'word': 'alpha',
                'bookId': 'book-a',
                'chapterId': '1',
                'status': 'known',
                'firstSeen': 100,
                'lastSeen': 200,
                'knownCount': 1,
                'unknownCount': 0,
                'nextReview': 300,
                'fuzzyCount': 0,
            },
            {
                'word': 'beta',
                'bookId': 'book-a',
                'chapterId': '1',
                'status': 'unknown',
                'firstSeen': 100,
                'lastSeen': 210,
                'knownCount': 0,
                'unknownCount': 1,
                'nextReview': 0,
                'fuzzyCount': 0,
            },
        ],
    })

    assert res.status_code == 200
    with app.app_context():
        alpha = UserWordMasteryState.query.filter_by(word='alpha').one()
        beta = UserWordMasteryState.query.filter_by(word='beta').one()
        assert alpha.to_dict()['dimension_states']['recognition']['pass_streak'] == 1
        assert beta.to_dict()['dimension_states']['recognition']['history_wrong'] == 1

        wrong_word = UserWrongWord.query.filter_by(word='beta').one()
        wrong_states = json.loads(wrong_word.dimension_state)
        assert wrong_states['recognition']['history_wrong'] == 1

        events = UserLearningEvent.query.filter_by(event_type='practice_attempt').all()
        assert {event.word for event in events} == {'alpha', 'beta'}
        assert all(event.mode == 'quickmemory' for event in events)

        ledger = UserLearningDailyLedger.query.filter_by(
            book_id='book-a',
            mode='quickmemory',
            chapter_id='1',
        ).one()
        assert ledger.review_count == 2
        assert ledger.correct_count == 1
        assert ledger.wrong_count == 1


def test_smart_stats_sync_and_get_round_trip(client, app):
    register_and_login(client, username='smart-stats-sync-user')

    sync = client.post('/api/ai/smart-stats/sync', json={
        'context': {
            'bookId': 'ielts_listening_premium',
            'chapterId': '6',
            'mode': 'smart',
        },
        'stats': [{
            'word': 'dynamic',
            'listening': {'correct': 3, 'wrong': 1},
            'meaning': {'correct': 2, 'wrong': 0},
            'dictation': {'correct': 1, 'wrong': 2},
        }],
    })
    assert sync.status_code == 200

    get_res = client.get('/api/ai/smart-stats')
    assert get_res.status_code == 200
    data = get_res.get_json()['stats']
    assert len(data) == 1
    assert data[0]['word'] == 'dynamic'
    assert data[0]['listening'] == {'correct': 3, 'wrong': 1}
    assert data[0]['meaning'] == {'correct': 2, 'wrong': 0}
    assert data[0]['dictation'] == {'correct': 1, 'wrong': 2}

    with app.app_context():
        record = UserSmartWordStat.query.filter_by(word='dynamic').first()
        assert record is not None
        assert record.listening_correct == 3
        assert record.dictation_wrong == 2


def test_wrong_word_sync_records_dimension_attempts_in_mastery(client, app):
    register_and_login(client, username='wrong-word-attempt-user')

    first = client.post('/api/ai/wrong-words/sync', json={
        'sourceMode': 'meaning',
        'bookId': 'book-a',
        'chapterId': '2',
        'words': [{
            'word': 'dynamic',
            'definition': 'changing',
            'dimension_states': {
                'recognition': {'history_wrong': 0, 'pass_streak': 0},
                'meaning': {'history_wrong': 1, 'pass_streak': 0, 'last_wrong_at': '2026-04-28T01:00:00'},
                'listening': {'history_wrong': 0, 'pass_streak': 0},
                'dictation': {'history_wrong': 0, 'pass_streak': 0},
            },
        }],
    })
    second = client.post('/api/ai/wrong-words/sync', json={
        'sourceMode': 'meaning',
        'bookId': 'book-a',
        'chapterId': '2',
        'words': [{
            'word': 'dynamic',
            'definition': 'changing',
            'dimension_states': {
                'recognition': {'history_wrong': 0, 'pass_streak': 0},
                'meaning': {
                    'history_wrong': 1,
                    'pass_streak': 1,
                    'last_wrong_at': '2026-04-28T01:00:00',
                    'last_pass_at': '2026-04-28T02:00:00',
                },
                'listening': {'history_wrong': 0, 'pass_streak': 0},
                'dictation': {'history_wrong': 0, 'pass_streak': 0},
            },
        }],
    })

    assert first.status_code == 200
    assert second.status_code == 200
    with app.app_context():
        state = UserWordMasteryState.query.filter_by(word='dynamic').one()
        meaning = state.to_dict()['dimension_states']['meaning']
        assert meaning['history_wrong'] == 1
        assert meaning['pass_streak'] == 1

        attempts = UserLearningEvent.query.filter_by(
            event_type='practice_attempt',
            word='dynamic',
            mode='meaning',
        ).all()
        assert [event.wrong_count for event in attempts] == [1, 0]
        assert [event.correct_count for event in attempts] == [0, 1]
