from models import UserConversationHistory, User, db
from services.ai_assistant_memory_service import load_history
from services import ai_practice_support_service as practice_support_service


def register_and_login(client, username='greet-history-user', password='password123'):
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


def test_greet_does_not_persist_open_panel_turns(client, app, monkeypatch):
    register_and_login(client, username='greet-history-user')

    monkeypatch.setattr(
        practice_support_service,
        'chat_with_tools',
        lambda *args, **kwargs: {'text': '你好，今天先把到期复习清掉。'},
    )

    res = client.post('/api/ai/greet', json={'context': {}})

    assert res.status_code == 200

    with app.app_context():
        user = User.query.filter_by(username='greet-history-user').first()
        assert user is not None
        assert UserConversationHistory.query.filter_by(user_id=user.id).count() == 0


def test_load_history_filters_legacy_greet_turns(client, app):
    register_and_login(client, username='greet-legacy-history-user')

    with app.app_context():
        user = User.query.filter_by(username='greet-legacy-history-user').first()
        assert user is not None

        UserConversationHistory.query.filter_by(user_id=user.id).delete()
        db.session.add(UserConversationHistory(
            user_id=user.id,
            role='user',
            content='[用户打开了AI助手]',
        ))
        db.session.add(UserConversationHistory(
            user_id=user.id,
            role='assistant',
            content='这是一条旧欢迎语',
        ))
        db.session.add(UserConversationHistory(
            user_id=user.id,
            role='user',
            content='今天怎么复习？',
        ))
        db.session.add(UserConversationHistory(
            user_id=user.id,
            role='assistant',
            content='先做听力复习。',
        ))
        db.session.commit()

        history = load_history(user.id)

    assert history == [
        {'role': 'user', 'content': '今天怎么复习？'},
        {'role': 'assistant', 'content': '先做听力复习。'},
    ]
