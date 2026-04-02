from models import db, User, UserBookProgress, UserChapterProgress


def register_user(client, username='alice'):
    response = client.post('/api/auth/register', json={
        'username': username,
        'password': 'password123',
    })
    assert response.status_code == 201


def get_user_id(app, username='alice'):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        assert user is not None
        return user.id


def test_get_all_progress_prefers_chapter_totals_when_book_progress_is_stale(client, app):
    register_user(client)
    user_id = get_user_id(app)

    with app.app_context():
        db.session.add(UserBookProgress(
            user_id=user_id,
            book_id='ielts_listening_premium',
            current_index=46,
            correct_count=32,
            wrong_count=14,
            is_completed=False,
        ))
        db.session.add(UserChapterProgress(
            user_id=user_id,
            book_id='ielts_listening_premium',
            chapter_id=1,
            words_learned=50,
            correct_count=40,
            wrong_count=10,
            is_completed=True,
        ))
        db.session.add(UserChapterProgress(
            user_id=user_id,
            book_id='ielts_listening_premium',
            chapter_id=2,
            words_learned=70,
            correct_count=55,
            wrong_count=15,
            is_completed=False,
        ))
        db.session.commit()

    response = client.get('/api/books/progress')
    assert response.status_code == 200

    progress = response.get_json()['progress']['ielts_listening_premium']
    assert progress['current_index'] == 120
    assert progress['correct_count'] == 95
    assert progress['wrong_count'] == 25
    assert progress['is_completed'] is False


def test_get_book_progress_can_be_synthesized_from_chapter_progress_only(client, app):
    register_user(client)
    user_id = get_user_id(app)

    with app.app_context():
        db.session.add(UserChapterProgress(
            user_id=user_id,
            book_id='ielts_listening_premium',
            chapter_id=3,
            words_learned=40,
            correct_count=28,
            wrong_count=12,
            is_completed=False,
        ))
        db.session.commit()

    response = client.get('/api/books/progress/ielts_listening_premium')
    assert response.status_code == 200

    progress = response.get_json()['progress']
    assert progress is not None
    assert progress['current_index'] == 40
    assert progress['correct_count'] == 28
    assert progress['wrong_count'] == 12
    assert progress['is_completed'] is False


def test_get_book_progress_does_not_treat_completed_subset_of_chapters_as_full_book(client, app):
    register_user(client)
    user_id = get_user_id(app)

    with app.app_context():
        db.session.add(UserBookProgress(
            user_id=user_id,
            book_id='ielts_reading_premium',
            current_index=159,
            correct_count=51,
            wrong_count=5,
            is_completed=True,
        ))
        db.session.add(UserChapterProgress(
            user_id=user_id,
            book_id='ielts_reading_premium',
            chapter_id=1,
            words_learned=50,
            correct_count=50,
            wrong_count=0,
            is_completed=True,
        ))
        db.session.add(UserChapterProgress(
            user_id=user_id,
            book_id='ielts_reading_premium',
            chapter_id=2,
            words_learned=53,
            correct_count=50,
            wrong_count=3,
            is_completed=True,
        ))
        db.session.add(UserChapterProgress(
            user_id=user_id,
            book_id='ielts_reading_premium',
            chapter_id=3,
            words_learned=56,
            correct_count=51,
            wrong_count=5,
            is_completed=True,
        ))
        db.session.commit()

    response = client.get('/api/books/progress/ielts_reading_premium')
    assert response.status_code == 200

    progress = response.get_json()['progress']
    assert progress['current_index'] == 159
    assert progress['correct_count'] == 151
    assert progress['wrong_count'] == 8
    assert progress['is_completed'] is False


def test_get_book_progress_ignores_book_end_offset_from_partial_chapter_study(client, app):
    register_user(client)
    user_id = get_user_id(app)

    with app.app_context():
        db.session.add(UserBookProgress(
            user_id=user_id,
            book_id='ielts_listening_premium',
            current_index=3916,
            correct_count=40,
            wrong_count=22,
            is_completed=True,
        ))
        db.session.add(UserChapterProgress(
            user_id=user_id,
            book_id='ielts_listening_premium',
            chapter_id=1,
            words_learned=50,
            correct_count=40,
            wrong_count=10,
            is_completed=True,
        ))
        db.session.add(UserChapterProgress(
            user_id=user_id,
            book_id='ielts_listening_premium',
            chapter_id=3,
            words_learned=70,
            correct_count=55,
            wrong_count=15,
            is_completed=True,
        ))
        db.session.commit()

    response = client.get('/api/books/progress/ielts_listening_premium')
    assert response.status_code == 200

    progress = response.get_json()['progress']
    assert progress['current_index'] == 120
    assert progress['correct_count'] == 95
    assert progress['wrong_count'] == 25
    assert progress['is_completed'] is False


def test_save_progress_does_not_move_book_progress_backwards(client):
    register_user(client)

    first = client.post('/api/books/progress', json={
        'book_id': 'ielts_listening_premium',
        'current_index': 120,
    })
    assert first.status_code == 200

    second = client.post('/api/books/progress', json={
        'book_id': 'ielts_listening_premium',
        'current_index': 46,
    })
    assert second.status_code == 200
    assert second.get_json()['progress']['current_index'] == 120

    current = client.get('/api/books/progress/ielts_listening_premium')
    assert current.status_code == 200
    assert current.get_json()['progress']['current_index'] == 120
