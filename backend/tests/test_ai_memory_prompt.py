from datetime import datetime

from models import User, UserLearningNote, db
from routes import ai as ai_routes


def register_and_login(client, username='memory-user', password='password123'):
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


def test_ask_injects_related_note_memory_for_repeated_questions(client, app, monkeypatch):
    register_and_login(client, username='memory-user')

    with app.app_context():
        user = User.query.filter_by(username='memory-user').first()
        assert user is not None
        db.session.add_all([
            UserLearningNote(
                user_id=user.id,
                question='kind of 和 a kind of 有什么区别？',
                answer='kind of 更像副词短语，a kind of 更像名词短语。',
                word_context='kind',
                created_at=datetime(2026, 3, 29, 10, 0, 0),
            ),
            UserLearningNote(
                user_id=user.id,
                question='请再解释一下 kind of 和 a kind of',
                answer='前者修饰程度，后者表示类别。',
                word_context='kind',
                created_at=datetime(2026, 3, 30, 9, 0, 0),
            ),
        ])
        db.session.commit()

    captured = {}

    def fake_chat_with_tools(messages, **kwargs):
        captured['messages'] = messages
        return {'text': '当然可以，我换一种方式解释。'}

    monkeypatch.setattr(ai_routes, '_chat_with_tools', fake_chat_with_tools)

    response = client.post('/api/ai/ask', json={
        'message': 'kind of 和 a kind of 有什么区别',
        'context': {'currentWord': 'kind'},
    })

    assert response.status_code == 200
    serialized = '\n'.join(str(message.get('content')) for message in captured['messages'])
    assert '[相关历史问答]' in serialized
    assert '已重复询问 2 次' in serialized
    assert 'kind of 和 a kind of' in serialized
