from models import User, UserBookProgress, UserChapterProgress, db


def register_and_login(client, username='ai-context-user', password='password123'):
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


def test_ai_context_avoids_double_counting_book_and_chapter_progress(client, app):
    register_and_login(client)

    with app.app_context():
        user = User.query.filter_by(username='ai-context-user').first()
        assert user is not None

        db.session.add(UserBookProgress(
            user_id=user.id,
            book_id='ielts_listening_premium',
            current_index=3916,
            correct_count=40,
            wrong_count=22,
            is_completed=True,
        ))
        db.session.add(UserChapterProgress(
            user_id=user.id,
            book_id='ielts_listening_premium',
            chapter_id=1,
            words_learned=50,
            correct_count=40,
            wrong_count=10,
            is_completed=True,
        ))
        db.session.add(UserChapterProgress(
            user_id=user.id,
            book_id='ielts_listening_premium',
            chapter_id=3,
            words_learned=70,
            correct_count=55,
            wrong_count=15,
            is_completed=True,
        ))
        db.session.commit()

    response = client.get('/api/ai/context')

    assert response.status_code == 200
    data = response.get_json()
    assert data['totalLearned'] == 120
    assert data['totalCorrect'] == 95
    assert data['totalWrong'] == 25

    book = next(item for item in data['books'] if item['id'] == 'ielts_listening_premium')
    assert book['correctCount'] == 95
    assert book['wrongCount'] == 25
    assert book['accuracy'] == 79
