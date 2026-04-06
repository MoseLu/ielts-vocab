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


def test_ask_injects_behavior_breakdown_into_learning_data_prompt(client, monkeypatch):
    register_and_login(client, username='behavior-prompt-user')

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'listening',
        'bookId': 'ielts_reading_premium',
        'chapterId': '3',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    log_res = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'listening',
        'bookId': 'ielts_reading_premium',
        'chapterId': '3',
        'wordsStudied': 8,
        'correctCount': 6,
        'wrongCount': 2,
        'durationSeconds': 90,
        'startedAt': int(datetime.utcnow().timestamp() * 1000),
    })
    assert log_res.status_code == 200

    monkeypatch.setattr(ai_routes, 'correct_text', lambda text: {
        'is_valid_english': True,
        'original_text': text,
        'corrected_text': text,
        'explanation': 'ok',
    })
    correction_res = client.post('/api/ai/correct-text', json={'text': 'This is a sample sentence.'})
    assert correction_res.status_code == 200

    feedback_res = client.post('/api/ai/correction-feedback', json={'adopted': True})
    assert feedback_res.status_code == 200

    captured = {}

    def fake_chat_with_tools(messages, **kwargs):
        captured['messages'] = messages
        return {'text': '可以先复习今天的薄弱点。'}

    monkeypatch.setattr(ai_routes, '_chat_with_tools', fake_chat_with_tools)

    ask_res = client.post('/api/ai/ask', json={
        'message': '今天怎么复习更合适？',
        'context': {
            'currentWord': 'kind',
            'practiceMode': 'listening',
        },
    })
    assert ask_res.status_code == 200

    serialized = '\n'.join(str(message.get('content')) for message in captured['messages'])
    assert '[学习数据]' in serialized
    assert '模式投入分布：' in serialized
    assert 'AI 工具动作：2 次' in serialized
    assert '行为类型：' in serialized
    assert '写作纠错' in serialized
