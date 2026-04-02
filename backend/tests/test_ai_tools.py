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
    assert len(data['words']) == 1
    word = data['words'][0]
    assert word['word'] == 'alpha'
    assert word['phonetic'] == '/a/'
    assert word['pos'] == 'n.'
    assert word['definition'] == '测试词'
    assert word['wrong_count'] == 3
    assert word['pending_wrong_count'] == 3
    assert word['history_dimension_count'] == 1
    assert word['pending_dimension_count'] == 1
    assert word['recognition_wrong'] == 3
    assert word['recognition_pending'] is True
    assert word['recognition_pass_streak'] == 0
    assert word['listening_wrong'] == 0
    assert word['meaning_wrong'] == 0
    assert word['dictation_wrong'] == 0
    assert word['ebbinghaus_streak'] == 4
    assert word['ebbinghaus_target'] == 6
    assert word['ebbinghaus_remaining'] == 2
    assert word['ebbinghaus_completed'] is False


def test_wrong_words_sync_preserves_history_but_allows_pending_clear(client, app):
    register_and_login(client, username='wrong-words-sync-user')

    first_sync = client.post('/api/ai/wrong-words/sync', json={
        'sourceMode': 'meaning',
        'bookId': 'ielts_reading_premium',
        'chapterId': '2',
        'words': [{
            'word': 'alpha',
            'phonetic': '/a/',
            'pos': 'n.',
            'definition': '测试词',
            'wrong_count': 2,
            'meaning_wrong': 2,
            'dimension_states': {
                'meaning': {
                    'history_wrong': 2,
                    'pass_streak': 0,
                    'last_wrong_at': '2026-04-02T08:00:00+00:00',
                },
            },
        }],
    })
    assert first_sync.status_code == 200

    second_sync = client.post('/api/ai/wrong-words/sync', json={
        'sourceMode': 'meaning',
        'bookId': 'ielts_reading_premium',
        'chapterId': '2',
        'words': [{
            'word': 'alpha',
            'wrong_count': 2,
            'meaning_wrong': 2,
            'dimension_states': {
                'meaning': {
                    'history_wrong': 2,
                    'pass_streak': 4,
                    'last_pass_at': '2026-04-02T09:00:00+00:00',
                },
            },
        }],
    })
    assert second_sync.status_code == 200

    res = client.get('/api/ai/wrong-words')
    assert res.status_code == 200
    data = res.get_json()
    assert len(data['words']) == 1
    word = data['words'][0]
    assert word['word'] == 'alpha'
    assert word['wrong_count'] == 2
    assert word['pending_wrong_count'] == 0
    assert word['history_dimension_count'] == 1
    assert word['pending_dimension_count'] == 0
    assert word['meaning_wrong'] == 2
    assert word['meaning_pending'] is False
    assert word['meaning_pass_streak'] == 4


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
