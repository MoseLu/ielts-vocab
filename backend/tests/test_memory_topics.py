from datetime import datetime, timedelta

import jwt

from models import User, UserLearningNote, db


def _make_user_and_token(app, username: str):
    user = User(username=username, email=f'{username}@example.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()

    token = jwt.encode(
        {
            'user_id': user.id,
            'type': 'access',
            'jti': f'jti-{username}',
            'iat': int(datetime.utcnow().timestamp()),
            'exp': datetime.utcnow() + timedelta(seconds=app.config['JWT_ACCESS_TOKEN_EXPIRES']),
        },
        app.config['JWT_SECRET_KEY'],
        algorithm='HS256',
    )
    return token, user.id


def test_notes_endpoint_returns_memory_topics(client, app):
    token, user_id = _make_user_and_token(app, 'memory-topics-user')

    db.session.add_all([
        UserLearningNote(
            user_id=user_id,
            question='kind of 和 a kind of 有什么区别？',
            answer='第一次解释',
            word_context='kind',
            created_at=datetime(2026, 3, 30, 8, 0, 0),
        ),
        UserLearningNote(
            user_id=user_id,
            question='kind of 和 a kind of 还是分不清',
            answer='第二次解释',
            word_context='kind',
            created_at=datetime(2026, 3, 30, 9, 0, 0),
        ),
        UserLearningNote(
            user_id=user_id,
            question='evidence 和 proof 的区别？',
            answer='另一个主题',
            word_context='evidence',
            created_at=datetime(2026, 3, 30, 10, 0, 0),
        ),
    ])
    db.session.commit()

    response = client.get('/api/notes', headers={'Authorization': f'Bearer {token}'})

    assert response.status_code == 200
    data = response.get_json()
    assert 'memory_topics' in data
    assert data['memory_topics'][0]['word_context'] == 'kind'
    assert data['memory_topics'][0]['count'] == 2
    assert data['memory_topics'][0]['related_notes'][0]['question']
    assert data['memory_topics'][0]['follow_up_hint']
