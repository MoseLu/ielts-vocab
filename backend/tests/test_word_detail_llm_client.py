from services import word_detail_llm_client as client


class _FakeResponse:
    def __init__(self, status_code=200, payload=None, text=''):
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = {}

    def json(self):
        if self._payload is None:
            raise ValueError('no json payload')
        return self._payload


def test_normalize_provider_supports_minimax_variants():
    assert client.normalize_provider(None) == 'minimax'
    assert client.normalize_provider('minimax-primary') == 'minimax-primary'
    assert client.normalize_provider('minimax_secondary') == 'minimax-secondary'


def test_request_plan_supports_model_chain(monkeypatch):
    monkeypatch.setattr(client, '_DASHSCOPE_API_KEY', 'test-key')

    assert client.request_plan(
        'dashscope',
        'qwen-turbo,qwen3.5-27b,qwen-max',
        client.DISABLE_FALLBACK_PROVIDER,
        None,
    ) == [
        ('dashscope', 'qwen-turbo'),
        ('dashscope', 'qwen3.5-27b'),
        ('dashscope', 'qwen-max'),
    ]


def test_request_plan_preserves_explicit_provider_variants(monkeypatch):
    monkeypatch.setattr(client, '_DASHSCOPE_API_KEY', 'test-key')

    assert client.request_plan('minimax-primary', None, None, None) == [
        ('minimax-primary', client.DEFAULT_MINIMAX_MODEL),
        ('dashscope', client.DEFAULT_DASHSCOPE_MODEL),
    ]
    assert client.request_plan('minimax-secondary', 'MiniMax-M2.5', None, None) == [
        ('minimax-secondary', 'MiniMax-M2.5'),
        ('dashscope', client.DEFAULT_DASHSCOPE_MODEL),
    ]


def test_request_provider_messages_routes_minimax_keys(monkeypatch):
    calls: list[dict] = []

    def fake_request(messages, model, max_tokens, force_secondary):
        calls.append({
            'messages': messages,
            'model': model,
            'max_tokens': max_tokens,
            'force_secondary': force_secondary,
        })
        return 'ok'

    monkeypatch.setattr(client, '_request_minimax', fake_request)

    assert client._request_provider_messages(
        [{'role': 'user', 'content': 'hello'}],
        provider='minimax-primary',
        model='MiniMax-M2.5',
        max_tokens=123,
    ) == 'ok'
    assert calls[-1]['force_secondary'] is False

    assert client._request_provider_messages(
        [{'role': 'user', 'content': 'hello'}],
        provider='minimax-secondary',
        model='MiniMax-M2.5',
        max_tokens=456,
    ) == 'ok'
    assert calls[-1]['force_secondary'] is True


def test_request_minimax_uses_chat_completions_endpoint(monkeypatch):
    calls: list[dict] = []

    def fake_post(url, json, headers, timeout):
        calls.append({
            'url': url,
            'json': json,
            'headers': headers,
            'timeout': timeout,
        })
        return _FakeResponse(
            status_code=200,
            payload={
                'choices': [{
                    'message': {'content': '{"items":[]}'},
                }],
            },
            text='ok',
        )

    monkeypatch.setattr(client.requests, 'post', fake_post)
    monkeypatch.setattr(client, '_MINIMAX_PRIMARY_KEY', 'test-minimax-key')
    monkeypatch.setattr(client, '_MINIMAX_BASE_URL', 'https://api.minimaxi.com/v1')

    text = client._request_minimax(
        [{'role': 'user', 'content': 'hello'}],
        'MiniMax-M2.5',
        64,
        force_secondary=False,
    )

    assert text == '{"items":[]}'
    assert calls[0]['url'] == 'https://api.minimaxi.com/v1/chat/completions'


def test_request_plan_can_disable_fallback(monkeypatch):
    monkeypatch.setattr(client, '_DASHSCOPE_API_KEY', 'test-key')

    assert client.request_plan(
        'dashscope',
        'qwen-turbo',
        client.DISABLE_FALLBACK_PROVIDER,
        None,
    ) == [('dashscope', 'qwen-turbo')]


def test_raise_for_api_error_uses_structured_message():
    response = _FakeResponse(
        status_code=403,
        payload={'error': {'message': 'quota exhausted'}},
        text='{"error":{"message":"quota exhausted"}}',
    )

    try:
        client._raise_for_api_error(response, 'dashscope')
    except RuntimeError as exc:
        assert 'dashscope http 403' in str(exc)
        assert 'quota exhausted' in str(exc)
    else:
        raise AssertionError('expected RuntimeError')


def test_is_quota_exhausted_error_matches_common_tokens():
    assert client.is_quota_exhausted_error('MiniMax http 403: quota exhausted')
    assert client.is_quota_exhausted_error('额度已用完')
    assert client.is_quota_exhausted_error(
        'your current token plan not support model, MiniMax-M2.7 (2061)',
    )
    assert not client.is_quota_exhausted_error(
        'minimax-primary http 429: usage limit exceeded (2056)',
    )
    assert not client.is_quota_exhausted_error('temporary network timeout')
    assert not client.is_quota_exhausted_error('LLM result missing words: quietness, quirk, quotation')


def test_is_rate_limit_error_matches_http_429_and_529():
    assert client.is_rate_limit_error('minimax-primary http 429: usage limit exceeded (2056)')
    assert client.is_rate_limit_error('minimax-primary http 529: 当前时段请求拥挤，请稍后再试 (2064)')
    assert not client.is_rate_limit_error(
        'your current token plan not support model, MiniMax-M2.7 (2061)',
    )


def test_extract_json_block_prefers_outer_object_over_nested_array():
    raw = """```json
{
  "word": "radish",
  "english": [
    {
      "pos": "n.",
      "definition": "a root vegetable"
    }
  ]
}
```"""

    assert client.extract_json_block(raw).startswith('{')
    assert '"word": "radish"' in client.extract_json_block(raw)
