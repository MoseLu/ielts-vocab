from routes import ai as ai_routes
from services import ai_assistant_ask_service as ask_service


def register_and_login(client, username='ai-stream-user', password='password123'):
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


def test_ask_stream_returns_sse_text_options_and_done(client, monkeypatch):
    register_and_login(client)

    persisted = {}

    monkeypatch.setattr(ask_service, 'build_ask_messages', lambda *args, **kwargs: [{'role': 'system', 'content': 'test'}])
    monkeypatch.setattr(ask_service, 'build_ask_extra_handlers', lambda *args, **kwargs: {})
    monkeypatch.setattr(
        ask_service,
        'persist_ask_response',
        lambda current_user, user_message, frontend_context, clean_reply: persisted.update({
            'message': user_message,
            'reply': clean_reply,
        }),
    )

    def fake_stream(*args, **kwargs):
        yield {'type': 'status', 'stage': 'tool', 'tool': 'get_wrong_words'}
        yield {'type': 'text_delta', 'text': '先复习错词。'}
        yield {'type': 'text_delta', 'text': '\n[options]\nA. 开始复习\nB. 先看计划\n[/options]'}

    monkeypatch.setattr(ask_service, 'stream_chat_with_tools', fake_stream)

    response = client.post('/api/ai/ask/stream', json={
        'message': '今天怎么复习？',
        'context': {'currentWord': 'kind'},
    })

    assert response.status_code == 200
    assert response.headers['Content-Type'].startswith('text/event-stream')

    payload = b''.join(response.response).decode('utf-8')
    assert '"type": "status"' in payload
    assert '"type": "text"' in payload
    assert '"type": "options"' in payload
    assert '"type": "done"' in payload
    assert 'A. 开始复习' in payload
    assert '先复习错词。' in payload
    assert persisted == {
        'message': '今天怎么复习？',
        'reply': '先复习错词。',
    }


def test_build_tool_status_message_returns_tool_specific_copy():
    assert ai_routes._build_tool_status_message('web_search') == 'AI 正在检索相关资料...'
    assert ai_routes._build_tool_status_message('get_wrong_words') == 'AI 正在分析你的错词记录...'
    assert ai_routes._build_tool_status_message('get_chapter_words', {'chapter_id': 3}) == 'AI 正在读取第 3 章词表...'
    assert ai_routes._build_tool_status_message('get_book_chapters') == 'AI 正在读取词书章节结构...'
    assert ai_routes._build_tool_status_message('remember_user_note', {'category': 'preference'}) == 'AI 正在记录你的学习偏好...'
