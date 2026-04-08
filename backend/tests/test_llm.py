from services import llm
from requests.exceptions import ReadTimeout


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


class ServiceUnavailableResponse:
    status_code = 503

    @property
    def text(self):
        return '{"error":{"message":"upstream temporarily unavailable"}}'

    def raise_for_status(self):
        from requests import HTTPError
        raise HTTPError("503 Service Unavailable", response=self)

    def json(self):
        return {
            'error': {
                'message': 'upstream temporarily unavailable',
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
    monkeypatch.setattr(llm, '_primary_unsupported_models', set())
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
    monkeypatch.setattr(llm, '_primary_unsupported_models', set())
    monkeypatch.setattr(llm.requests, 'post', fake_post)

    result = llm.chat([{'role': 'user', 'content': 'hello'}], max_tokens=32)

    assert [call['model'] for call in calls] == ['MiniMax-M2.7-highspeed', 'MiniMax-M2.7-highspeed']
    assert [call['authorization'] for call in calls] == ['Bearer primary-key', 'Bearer secondary-key']
    assert result['text'] == 'ok'


def test_chat_caches_primary_model_incompatibility(monkeypatch):
    calls = []

    def fake_post(url, json, headers, timeout, **kwargs):
        calls.append(headers['Authorization'])
        if len(calls) == 1:
            return UnsupportedModelResponse()
        return DummyResponse()

    monkeypatch.setattr(llm, 'BASE_URL', 'https://api.minimaxi.com/anthropic')
    monkeypatch.setattr(llm, 'API_KEY', 'primary-key')
    monkeypatch.setattr(llm, 'API_KEY_2', 'secondary-key')
    monkeypatch.setattr(llm, '_primary_unsupported_models', set())
    monkeypatch.setattr(llm.requests, 'post', fake_post)

    first = llm.chat([{'role': 'user', 'content': 'hello'}], max_tokens=32)
    second = llm.chat([{'role': 'user', 'content': 'hello again'}], max_tokens=32)

    assert first['text'] == 'ok'
    assert second['text'] == 'ok'
    assert calls == [
        'Bearer primary-key',
        'Bearer secondary-key',
        'Bearer secondary-key',
    ]


def test_chat_retries_transient_503_with_secondary_key(monkeypatch):
    calls = []

    def fake_post(url, json, headers, timeout, **kwargs):
        calls.append({
            'model': json['model'],
            'authorization': headers['Authorization'],
            'timeout': timeout,
        })
        if len(calls) == 1:
            return ServiceUnavailableResponse()
        return DummyResponse()

    monkeypatch.setattr(llm, 'BASE_URL', 'https://api.minimaxi.com/anthropic')
    monkeypatch.setattr(llm, 'API_KEY', 'primary-key')
    monkeypatch.setattr(llm, 'API_KEY_2', 'secondary-key')
    monkeypatch.setattr(llm, 'MAX_REQUEST_ATTEMPTS', 3)
    monkeypatch.setattr(llm, '_primary_unsupported_models', set())
    monkeypatch.setattr(llm.requests, 'post', fake_post)

    result = llm.chat([{'role': 'user', 'content': 'hello'}], max_tokens=32)

    assert result['text'] == 'ok'
    assert [call['authorization'] for call in calls] == ['Bearer primary-key', 'Bearer secondary-key']
    assert calls[0]['timeout'] == (llm.CONNECT_TIMEOUT_SECONDS, llm.READ_TIMEOUT_SECONDS)


def test_chat_retries_transient_timeout(monkeypatch):
    calls = []

    def fake_post(url, json, headers, timeout, **kwargs):
        calls.append(timeout)
        if len(calls) == 1:
            raise ReadTimeout('read timed out')
        return DummyResponse()

    monkeypatch.setattr(llm, 'BASE_URL', 'https://api.minimaxi.com/anthropic')
    monkeypatch.setattr(llm, 'API_KEY', 'test-key')
    monkeypatch.setattr(llm, 'API_KEY_2', '')
    monkeypatch.setattr(llm, 'MAX_REQUEST_ATTEMPTS', 3)
    monkeypatch.setattr(llm, 'RETRY_BACKOFF_SECONDS', 0)
    monkeypatch.setattr(llm, '_primary_unsupported_models', set())
    monkeypatch.setattr(llm.requests, 'post', fake_post)

    result = llm.chat([{'role': 'user', 'content': 'hello'}], max_tokens=32)

    assert result['text'] == 'ok'
    assert calls == [
        (llm.CONNECT_TIMEOUT_SECONDS, llm.READ_TIMEOUT_SECONDS),
        (llm.CONNECT_TIMEOUT_SECONDS, llm.READ_TIMEOUT_SECONDS),
    ]


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


def test_stream_chat_events_uses_streaming_timeout_tuple(monkeypatch):
    seen = {}

    def fake_post(url, json, headers, timeout, **kwargs):
        seen['timeout'] = timeout
        return StreamResponse([
            'data: {"type":"message_stop"}',
        ])

    monkeypatch.setattr(llm.requests, 'post', fake_post)
    monkeypatch.setattr(llm, 'BASE_URL', 'https://api.minimaxi.com/anthropic')
    monkeypatch.setattr(llm, 'API_KEY', 'test-key')
    monkeypatch.setattr(llm, 'API_KEY_2', '')

    events = list(llm.stream_chat_events([{'role': 'user', 'content': 'hello'}]))

    assert events == []
    assert seen['timeout'] == (llm.CONNECT_TIMEOUT_SECONDS, max(llm.READ_TIMEOUT_SECONDS, 120))
