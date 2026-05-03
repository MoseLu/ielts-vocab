from datetime import datetime, timezone

from routes import ai as ai_routes
from services import ai_vocab_catalog_service as vocab_catalog_service


def register_and_login(client, username='release-risk-user', password='password123'):
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


def _word(index: int) -> str:
    return f'releaseword{index:02d}'


def _patch_vocab(monkeypatch, words: list[str]):
    lookup = {
        word: [{
            'word': word,
            'phonetic': f'/{word}/',
            'pos': 'n.',
            'definition': f'{word} definition',
            'book_id': 'book-release',
            'book_title': 'Release Book',
            'chapter_id': '1',
            'chapter_title': 'Release Chapter',
        }]
        for word in words
    }
    monkeypatch.setattr(vocab_catalog_service, '_get_quick_memory_vocab_lookup', lambda: lookup)
    monkeypatch.setattr(ai_routes, '_get_global_vocab_pool', lambda: [
        {
            'word': word,
            'phonetic': f'/{word}/',
            'pos': 'n.',
            'definition': f'{word} definition',
        }
        for word in words
    ])


def test_release_risk_user_journey_round_trips_practice_review_stats_and_progress(
    client,
    monkeypatch,
):
    register_and_login(client)
    words = [_word(index) for index in range(55)]
    _patch_vocab(monkeypatch, words)
    now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'listening',
        'bookId': 'book-release',
        'chapterId': '1',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    log_res = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'listening',
        'bookId': 'book-release',
        'chapterId': '1',
        'wordsStudied': 12,
        'correctCount': 9,
        'wrongCount': 3,
        'durationSeconds': 180,
        'startedAt': now_ms - 60_000,
    })
    assert log_res.status_code == 200

    stats_sync = client.post('/api/ai/smart-stats/sync', json={
        'context': {'bookId': 'book-release', 'chapterId': '1', 'mode': 'smart'},
        'stats': [{
            'word': words[0],
            'listening': {'correct': 3, 'wrong': 1},
            'meaning': {'correct': 2, 'wrong': 1},
            'dictation': {'correct': 1, 'wrong': 1},
        }],
    })
    assert stats_sync.status_code == 200

    quick_memory_sync = client.post('/api/ai/quick-memory/sync', json={
        'source': 'quickmemory',
        'records': [
            {
                'word': word,
                'bookId': 'book-release',
                'chapterId': '1',
                'status': 'known',
                'firstSeen': now_ms - 600_000,
                'lastSeen': 0,
                'knownCount': 1,
                'unknownCount': 0,
                'nextReview': now_ms - (index + 1) * 1_000,
                'fuzzyCount': 0,
            }
            for index, word in enumerate(words)
        ],
    })
    assert quick_memory_sync.status_code == 200

    wrong_sync = client.post('/api/ai/wrong-words/sync', json={
        'sourceMode': 'meaning',
        'bookId': 'book-release',
        'chapterId': '1',
        'words': [{
            'word': words[0],
            'definition': 'release risk word',
            'dimension_states': {
                'recognition': {'history_wrong': 1, 'pass_streak': 0},
                'meaning': {'history_wrong': 1, 'pass_streak': 0},
                'listening': {'history_wrong': 1, 'pass_streak': 0},
                'speaking': {'history_wrong': 1, 'pass_streak': 0},
                'dictation': {'history_wrong': 1, 'pass_streak': 0},
            },
        }],
    })
    assert wrong_sync.status_code == 200

    book_progress = client.post('/api/books/progress', json={
        'book_id': 'book-release',
        'current_index': 50,
        'correct_count': 42,
        'wrong_count': 8,
        'is_completed': False,
    })
    assert book_progress.status_code == 200

    chapter_progress = client.post('/api/books/book-release/chapters/1/progress', json={
        'mode': 'listening',
        'current_index': 50,
        'words_learned': 50,
        'correct_count': 42,
        'wrong_count': 8,
        'is_completed': False,
        'queue_words': words,
    })
    assert chapter_progress.status_code == 200

    queue_res = client.get('/api/ai/quick-memory/review-queue?limit=50&within_days=3&scope=due')
    assert queue_res.status_code == 200
    queue = queue_res.get_json()
    assert queue['summary']['due_count'] == 55
    assert queue['summary']['returned_count'] == 50
    assert queue['summary']['limit'] == 50
    assert queue['summary']['has_more'] is True
    assert queue['summary']['next_offset'] == 0
    assert len(queue['words']) == 50

    wrong_words = client.get('/api/ai/wrong-words?details=compact&search=releaseword00')
    assert wrong_words.status_code == 200
    wrong_word = wrong_words.get_json()['words'][0]
    assert wrong_word['word'] == words[0]
    assert wrong_word['pending_wrong_count'] == 5
    assert set(wrong_word['pending_dimensions']) == {
        'recognition',
        'meaning',
        'listening',
        'speaking',
        'dictation',
    }

    progress_res = client.get('/api/books/progress/book-release')
    assert progress_res.status_code == 200
    assert progress_res.get_json()['progress']['current_index'] == 50

    stats_res = client.get('/api/ai/learning-stats?days=7')
    profile_res = client.get('/api/ai/learner-profile')
    assert stats_res.status_code == 200
    assert profile_res.status_code == 200
    assert stats_res.get_json()['alltime']['ebbinghaus_due_total'] == 55
    assert profile_res.get_json()['summary']['due_reviews'] == 55
