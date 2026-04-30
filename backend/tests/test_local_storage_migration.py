from models import (
    User,
    UserLearningBookRollup,
    UserLearningChapterRollup,
    UserQuickMemoryRecord,
    UserSmartWordStat,
    UserWrongWord,
)
from services.legacy_day_progress_compat import get_legacy_day_progress


def register_and_login(client, username='local-storage-user', password='password123'):
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


def test_local_storage_migration_writes_only_current_cookie_user(client, app):
    register_and_login(client, username='migration-current-user')

    response = client.post('/api/ai/local-storage-migration', json={
        'migration_task': 'local_storage_migration_v1_once',
        'user_id': 999,
        'sources': {
            'smart_word_stats': {
                'stats': [{
                    'word': 'dynamic',
                    'listening': {'correct': 2, 'wrong': 1},
                    'meaning': {'correct': 1, 'wrong': 0},
                    'dictation': {'correct': 0, 'wrong': 1},
                }],
            },
            'quick_memory_records': {
                'records': [{
                    'word': 'alpha',
                    'status': 'known',
                    'firstSeen': 100,
                    'lastSeen': 200,
                    'knownCount': 2,
                    'unknownCount': 0,
                    'nextReview': 300,
                    'fuzzyCount': 0,
                    'bookId': 'book-1',
                    'chapterId': '2',
                }],
            },
            'wrong_words': {
                'words': [{'word': 'fragile', 'definition': 'easy to break', 'wrong_count': 2}],
            },
            'book_progress': {
                'records': [{
                    'book_id': 'book-1',
                    'current_index': 8,
                    'correct_count': 6,
                    'wrong_count': 2,
                    'is_completed': False,
                }],
            },
            'chapter_progress': {
                'records': [{
                    'book_id': 'book-1',
                    'chapter_id': '2',
                    'mode': 'smart',
                    'current_index': 4,
                    'words_learned': 4,
                    'correct_count': 3,
                    'wrong_count': 1,
                    'is_completed': False,
                    'queue_words': ['alpha', 'beta'],
                }],
            },
            'day_progress': {
                'records': [{
                    'day': 7,
                    'current_index': 5,
                    'correct_count': 4,
                    'wrong_count': 1,
                }],
            },
        },
    })

    assert response.status_code == 200
    payload = response.get_json()
    assert payload['migration_task'] == 'local_storage_migration_v1_once'
    assert all(result['ok'] for result in payload['sources'].values()), payload

    with app.app_context():
        user = User.query.filter_by(username='migration-current-user').one()
        assert UserSmartWordStat.query.filter_by(user_id=user.id, word='dynamic').one().listening_correct == 2
        assert UserQuickMemoryRecord.query.filter_by(user_id=user.id, word='alpha').one().known_count == 2
        assert UserWrongWord.query.filter_by(user_id=user.id, word='fragile').one().wrong_count == 2
        assert UserLearningBookRollup.query.filter_by(
            user_id=user.id,
            book_id='book-1',
        ).one().current_index == 8
        assert UserLearningChapterRollup.query.filter_by(
            user_id=user.id,
            book_id='book-1',
            mode='smart',
            chapter_id='2',
        ).one().words_learned == 4
        assert get_legacy_day_progress(user.id, 7).current_index == 5
        assert UserSmartWordStat.query.filter_by(user_id=999).count() == 0
