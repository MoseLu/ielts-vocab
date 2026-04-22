from models import UserChapterProgress


def _register_user(client, username='progress-resume-user'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': 'password123',
    })


def test_chapter_progress_persists_and_clears_resume_snapshot(client, app):
    _register_user(client)

    save_response = client.post('/api/books/ielts_reading_premium/chapters/chapter-a/progress', json={
        'mode': 'meaning',
        'current_index': 3,
        'words_learned': 5,
        'correct_count': 4,
        'wrong_count': 1,
        'answered_words': ['alpha', 'beta'],
        'queue_words': ['alpha', 'beta', 'gamma'],
        'is_completed': False,
    })
    assert save_response.status_code == 200

    progress_response = client.get('/api/books/ielts_reading_premium/chapters/progress')
    assert progress_response.status_code == 200
    payload = progress_response.get_json()['chapter_progress']['chapter-a']
    assert payload['current_index'] == 3
    assert payload['words_learned'] == 5
    assert payload['answered_words'] == ['alpha', 'beta']
    assert payload['queue_words'] == ['alpha', 'beta', 'gamma']

    clear_response = client.post('/api/books/ielts_reading_premium/chapters/chapter-a/progress', json={
        'mode': 'meaning',
        'clear_session_snapshot': True,
        'current_index': 0,
        'answered_words': [],
        'queue_words': [],
    })
    assert clear_response.status_code == 200
    cleared = clear_response.get_json()['progress']
    assert cleared['current_index'] == 0
    assert cleared['answered_words'] == []
    assert cleared['queue_words'] == []
    assert cleared['words_learned'] == 5

    with app.app_context():
        record = UserChapterProgress.query.filter_by(
            book_id='ielts_reading_premium',
            chapter_id='chapter-a',
        ).one()
        assert record.words_learned == 5
        assert int(record.session_current_index or 0) == 0
        assert record.session_answered_words is None
        assert record.session_queue_words is None
