import json

from models import UserQuickMemoryRecord, UserWrongWord, db
from routes import ai as ai_routes


def register_and_login(client, username='ai-tools-user', password='password123'):
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


def test_validate_tool_input_accepts_chapter_tools():
    assert ai_routes._validate_tool_input(
        'get_chapter_words',
        {'book_id': 'ielts_reading_premium', 'chapter_id': 2},
    ) == {
        'book_id': 'ielts_reading_premium',
        'chapter_id': 2,
    }

    assert ai_routes._validate_tool_input(
        'get_book_chapters',
        {'book_id': 'ielts_reading_premium'},
    ) == {
        'book_id': 'ielts_reading_premium',
    }


def test_get_wrong_words_handler_tolerates_unsupported_book_filter(app):
    with app.app_context():
        from models import User

        user = User(username='handler-user', email='handler@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        db.session.add(UserWrongWord(user_id=user.id, word='alpha', wrong_count=2))
        db.session.commit()

        handler = ai_routes._make_get_wrong_words(user.id)
        result = handler(limit=10, book_id='ielts_ultimate')

    assert 'alpha' in result


def test_ask_executes_get_wrong_words_tool_call(client, app, monkeypatch):
    register_and_login(client, username='wrong-words-user')

    with app.app_context():
        from models import User

        user = User.query.filter_by(username='wrong-words-user').first()
        db.session.add(UserWrongWord(
            user_id=user.id,
            word='alpha',
            phonetic='/a/',
            pos='n.',
            definition='测试词',
            wrong_count=3,
        ))
        db.session.commit()

    calls: list[list[dict]] = []

    def fake_chat(messages, tools=None, max_tokens=4096):
        calls.append(messages)
        if len(calls) == 1:
            return {
                'type': 'tool_call',
                'tool': 'get_wrong_words',
                'input': {'limit': 5},
                'tool_call_id': 'call_1',
            }
        return {
            'type': 'text',
            'text': '已根据你的错词记录整理出复习建议。',
        }

    monkeypatch.setattr(ai_routes, 'chat', fake_chat)
    monkeypatch.setattr(ai_routes, '_maybe_summarize_history', lambda user_id: None)

    res = client.post('/api/ai/ask', json={
        'message': '帮我复习错词',
        'context': {},
    })

    assert res.status_code == 200
    assert res.get_json()['reply'] == '已根据你的错词记录整理出复习建议。'
    assert len(calls) == 2

    second_call_dump = json.dumps(calls[1], ensure_ascii=False)
    assert 'tool_result' in second_call_dump
    assert 'alpha' in second_call_dump
    assert 'input validation failed' not in second_call_dump


def test_get_wrong_words_api_includes_ebbinghaus_progress(client, app):
    register_and_login(client, username='wrong-words-progress-user')

    with app.app_context():
        from models import User

        user = User.query.filter_by(username='wrong-words-progress-user').first()
        db.session.add(UserWrongWord(
            user_id=user.id,
            word='alpha',
            phonetic='/a/',
            pos='n.',
            definition='测试词',
            wrong_count=3,
        ))
        db.session.add(UserQuickMemoryRecord(
            user_id=user.id,
            word='alpha',
            status='known',
            first_seen=1000,
            last_seen=2000,
            known_count=4,
            unknown_count=1,
            next_review=3000,
            fuzzy_count=0,
        ))
        db.session.commit()

    res = client.get('/api/ai/wrong-words')

    assert res.status_code == 200
    data = res.get_json()
    assert data['words'] == [
        {
            'id': data['words'][0]['id'],
            'user_id': data['words'][0]['user_id'],
            'word': 'alpha',
            'phonetic': '/a/',
            'pos': 'n.',
            'definition': '测试词',
            'wrong_count': 3,
            'listening_correct': 0,
            'listening_wrong': 0,
            'meaning_correct': 0,
            'meaning_wrong': 0,
            'dictation_correct': 0,
            'dictation_wrong': 0,
            'updated_at': data['words'][0]['updated_at'],
            'ebbinghaus_streak': 4,
            'ebbinghaus_target': 6,
            'ebbinghaus_remaining': 2,
            'ebbinghaus_completed': False,
        }
    ]


def test_generate_book_accepts_text_response_payload(client, monkeypatch):
    register_and_login(client, username='generate-book-user')

    payload = {
        'title': '学术高频词',
        'description': '聚焦常见学术场景',
        'chapters': [
            {'id': 'ch1', 'title': '校园', 'wordCount': 1},
        ],
        'words': [
            {
                'chapterId': 'ch1',
                'word': 'lecture',
                'phonetic': '/ˈlektʃə/',
                'pos': 'n.',
                'definition': '讲座',
            },
        ],
    }

    monkeypatch.setattr(ai_routes, 'chat', lambda messages, max_tokens=8192: {
        'type': 'text',
        'text': json.dumps(payload, ensure_ascii=False),
    })

    res = client.post('/api/ai/generate-book', json={
        'targetWords': 20,
        'userLevel': 'intermediate',
        'focusAreas': ['academic'],
    })

    assert res.status_code == 200
    data = res.get_json()
    assert data['title'] == '学术高频词'
    assert len(data['chapters']) == 1
    assert len(data['words']) == 1
