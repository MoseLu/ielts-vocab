from services import llm


class DummyResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {
            'content': [
                {'type': 'text', 'text': 'ok'},
            ]
        }


class UnsupportedModelResponse:
    status_code = 500

    @property
    def text(self):
        return '{"type":"error","error":{"type":"api_error","message":"your current token plan not support model, MiniMax-M2.7-highspeed (2061)"}}'

    def raise_for_status(self):
        from requests import HTTPError
        raise HTTPError("500 Server Error", response=self)

    def json(self):
        return {
            'type': 'error',
            'error': {
                'type': 'api_error',
                'message': 'your current token plan not support model, MiniMax-M2.7-highspeed (2061)',
            },
        }


class StreamResponse:
    status_code = 200

    def __init__(self, lines):
        self._lines = lines

    def raise_for_status(self):
        return None

    def iter_lines(self, decode_unicode=True):
        return iter(self._lines)


def test_chat_maps_legacy_minimax_v1_base_to_anthropic_messages_endpoint(monkeypatch):
    called = {}

    def fake_post(url, json, headers, timeout, **kwargs):
        called['url'] = url
        return DummyResponse()

    monkeypatch.setattr(llm, 'BASE_URL', 'https://api.minimaxi.com/v1')
    monkeypatch.setattr(llm, 'API_KEY', 'test-key')
    monkeypatch.setattr(llm, 'API_KEY_2', '')
    monkeypatch.setattr(llm.requests, 'post', fake_post)

    result = llm.chat([{'role': 'user', 'content': 'hello'}], max_tokens=32)

    assert called['url'] == 'https://api.minimaxi.com/anthropic/v1/messages'
    assert result['text'] == 'ok'


def test_chat_adds_v1_messages_to_anthropic_base(monkeypatch):
    called = {}

    def fake_post(url, json, headers, timeout, **kwargs):
        called['url'] = url
        return DummyResponse()

    monkeypatch.setattr(llm, 'BASE_URL', 'https://api.minimaxi.com/anthropic')
    monkeypatch.setattr(llm, 'API_KEY', 'test-key')
    monkeypatch.setattr(llm, 'API_KEY_2', '')
    monkeypatch.setattr(llm.requests, 'post', fake_post)

    result = llm.chat([{'role': 'user', 'content': 'hello'}], max_tokens=32)

    assert called['url'] == 'https://api.minimaxi.com/anthropic/v1/messages'
    assert result['text'] == 'ok'


def test_chat_accepts_anthropic_v1_base_without_duplicating_version(monkeypatch):
    called = {}

    def fake_post(url, json, headers, timeout, **kwargs):
        called['url'] = url
        return DummyResponse()

    monkeypatch.setattr(llm, 'BASE_URL', 'https://api.minimaxi.com/anthropic/v1')
    monkeypatch.setattr(llm, 'API_KEY', 'test-key')
    monkeypatch.setattr(llm, 'API_KEY_2', '')
    monkeypatch.setattr(llm.requests, 'post', fake_post)

    result = llm.chat([{'role': 'user', 'content': 'hello'}], max_tokens=32)

    assert called['url'] == 'https://api.minimaxi.com/anthropic/v1/messages'
    assert result['text'] == 'ok'


def test_chat_retries_with_fallback_model_when_default_model_is_not_supported(monkeypatch):
    calls = []

    def fake_post(url, json, headers, timeout, **kwargs):
        calls.append({'url': url, 'model': json['model']})
        if len(calls) == 1:
            return UnsupportedModelResponse()
        return DummyResponse()

    monkeypatch.setattr(llm, 'BASE_URL', 'https://api.minimaxi.com/anthropic')
    monkeypatch.setattr(llm, 'API_KEY', 'test-key')
    monkeypatch.setattr(llm, 'API_KEY_2', '')
    monkeypatch.setattr(llm.requests, 'post', fake_post)

    result = llm.chat([{'role': 'user', 'content': 'hello'}], max_tokens=32)

    assert [call['model'] for call in calls] == ['MiniMax-M2.7-highspeed', 'MiniMax-M2.5']
    assert result['text'] == 'ok'


def test_chat_retries_same_model_with_secondary_key_before_downgrading(monkeypatch):
    calls = []

    def fake_post(url, json, headers, timeout, **kwargs):
        calls.append({
            'url': url,
            'model': json['model'],
            'authorization': headers['Authorization'],
        })
        if len(calls) == 1:
            return UnsupportedModelResponse()
        return DummyResponse()

    monkeypatch.setattr(llm, 'BASE_URL', 'https://api.minimaxi.com/anthropic')
    monkeypatch.setattr(llm, 'API_KEY', 'primary-key')
    monkeypatch.setattr(llm, 'API_KEY_2', 'secondary-key')
    monkeypatch.setattr(llm.requests, 'post', fake_post)

    result = llm.chat([{'role': 'user', 'content': 'hello'}], max_tokens=32)

    assert [call['model'] for call in calls] == ['MiniMax-M2.7-highspeed', 'MiniMax-M2.7-highspeed']
    assert [call['authorization'] for call in calls] == ['Bearer primary-key', 'Bearer secondary-key']
    assert result['text'] == 'ok'


def test_stream_chat_events_yields_text_and_tool_calls(monkeypatch):
    lines = [
        'data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}',
        'data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"你好"}}',
        'data: {"type":"content_block_stop","index":0}',
        'data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"tool_1","name":"get_wrong_words","input":{}}}',
        'data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\\"limit\\":5}"}}',
        'data: {"type":"content_block_stop","index":1}',
        'data: {"type":"message_stop"}',
    ]

    monkeypatch.setattr(llm, '_post_messages_request', lambda *args, **kwargs: StreamResponse(lines))

    events = list(llm.stream_chat_events(
        [{'role': 'user', 'content': 'hello'}],
        tools=[{
            'name': 'get_wrong_words',
            'description': 'Fetch wrong words',
            'parameters': {
                'type': 'object',
                'properties': {'limit': {'type': 'integer'}},
            },
        }],
    ))

    assert events[0] == {'type': 'text_delta', 'text': '你好'}
    assert events[1] == {
        'type': 'tool_call',
        'tool': 'get_wrong_words',
        'input': {'limit': 5},
        'tool_call_id': 'tool_1',
    }
