from models import User, UserQuickMemoryRecord, UserSmartWordStat, db


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
