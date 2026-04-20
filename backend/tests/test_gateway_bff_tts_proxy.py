from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('gateway_bff_main', GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module

def test_gateway_tts_voices_proxy_returns_upstream_payload(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        'fetch_tts_voices',
        lambda **kwargs: {
            'voices': [{'id': 'voice-a', 'name': 'voice-a'}],
            'recommended': ['voice-a'],
        },
    )

    response = client.get('/api/tts/voices')

    assert response.status_code == 200
    assert response.json() == {
        'voices': [{'id': 'voice-a', 'name': 'voice-a'}],
        'recommended': ['voice-a'],
    }


def test_gateway_tts_generate_proxy_returns_audio_bytes(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    class FakeResponse:
        status_code = 200
        content = b'ID3DATA'
        headers = {'content-type': 'audio/mpeg', 'X-Audio-Bytes': '7', 'X-Audio-Cache-Key': 'gen:7:1'}

    monkeypatch.setattr(module, 'generate_tts_audio', lambda payload, **kwargs: FakeResponse())

    response = client.post('/api/tts/generate', json={'text': 'Hello', 'provider': 'minimax'})

    assert response.status_code == 200
    assert response.content == b'ID3DATA'
    assert response.headers['content-type'].startswith('audio/mpeg')
    assert response.headers['x-audio-bytes'] == '7'
    assert response.headers['x-audio-cache-key'] == 'gen:7:1'


def test_gateway_tts_generate_proxy_forwards_gateway_headers(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    class FakeResponse:
        status_code = 200
        content = b'ID3DATA'
        headers = {'content-type': 'audio/mpeg'}

    def fake_generate_tts_audio(payload, **kwargs):
        captured['payload'] = payload
        captured.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(module, 'generate_tts_audio', fake_generate_tts_audio)

    response = client.post(
        '/api/tts/generate',
        json={'text': 'Hello', 'provider': 'minimax'},
        headers={
            'Authorization': 'Bearer tts-token',
            'Idempotency-Key': 'tts-generate-1',
        },
    )

    assert response.status_code == 200
    assert captured['payload'] == {'text': 'Hello', 'provider': 'minimax'}
    assert 'authorization' not in captured['headers']
    assert captured['headers']['idempotency-key'] == 'tts-generate-1'
    assert captured['headers']['x-service-name'] == 'gateway-bff'


def test_gateway_tts_generate_proxy_passthrough_json_error(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    class FakeResponse:
        status_code = 429
        headers = {'content-type': 'application/json'}

        @staticmethod
        def json():
            return {'error': 'quota exceeded'}

    monkeypatch.setattr(module, 'generate_tts_audio', lambda payload, **kwargs: FakeResponse())

    response = client.post('/api/tts/generate', json={'text': 'Hello', 'provider': 'minimax'})

    assert response.status_code == 429
    assert response.json() == {'error': 'quota exceeded'}


def test_gateway_speech_transcribe_proxy_returns_json(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    class FakeResponse:
        status_code = 200
        headers = {'content-type': 'application/json'}

        @staticmethod
        def json():
            return {'text': 'hello world'}

    monkeypatch.setattr(
        module,
        'transcribe_speech_upload',
        lambda **kwargs: FakeResponse(),
    )

    response = client.post(
        '/api/speech/transcribe',
        files={'audio': ('sample.wav', b'RIFFtest', 'audio/wav')},
    )

    assert response.status_code == 200
    assert response.json() == {'text': 'hello world'}


def test_gateway_speech_transcribe_proxy_preserves_legacy_missing_file_error():
    module = _load_gateway_module()
    client = TestClient(module.app)

    response = client.post('/api/speech/transcribe')

    assert response.status_code == 400
    assert response.json() == {'error': '未收到音频文件'}


def test_gateway_head_word_audio_proxy_maps_legacy_headers(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        '_resolve_word_audio_request',
        lambda word: {
            'word': word,
            'normalized_word': 'hello',
            'provider': 'hybrid',
            'model': 'speech-2.8-hd@dict-v1',
            'voice': 'English_Trustworthy_Man',
            'file_name': 'hello.mp3',
        },
    )
    monkeypatch.setattr(
        module,
        'fetch_word_audio_metadata',
        lambda **kwargs: {
            'media_id': 'tts/object/hello.mp3',
            'byte_length': 321,
            'cache_key': 'oss:hello.mp3:321:etag-1',
            'signed_url': 'https://oss.example.com/hello.mp3?signature=1',
        },
    )

    response = client.head('/api/tts/word-audio', params={'w': 'hello', 'cache_only': '1'})

    assert response.status_code == 204
    assert response.headers['x-audio-bytes'] == '321'
    assert response.headers['x-audio-cache-key'] == 'oss:hello.mp3:321:etag-1'
    assert response.headers['x-audio-oss-url'] == 'https://oss.example.com/hello.mp3?signature=1'
    assert response.headers['x-audio-source'] == 'oss'
    assert response.headers['x-media-id'] == 'tts/object/hello.mp3'


def test_gateway_get_word_audio_proxy_returns_audio_bytes(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        '_resolve_word_audio_request',
        lambda word: {
            'word': word,
            'normalized_word': 'hello',
            'provider': 'hybrid',
            'model': 'speech-2.8-hd@dict-v1',
            'voice': 'English_Trustworthy_Man',
            'file_name': 'hello.mp3',
        },
    )
    monkeypatch.setattr(
        module,
        'fetch_word_audio_content',
        lambda **kwargs: {
            'body': b'ID3DATA',
            'content_type': 'audio/mpeg',
            'byte_length': '7',
            'cache_key': 'oss:hello.mp3:7:etag-1',
            'signed_url': 'https://oss.example.com/hello.mp3?signature=1',
            'media_id': 'tts/object/hello.mp3',
        },
    )

    response = client.get('/api/tts/word-audio', params={'w': 'hello', 'cache_only': '1'})

    assert response.status_code == 200
    assert response.content == b'ID3DATA'
    assert response.headers['content-type'].startswith('audio/mpeg')
    assert response.headers['x-audio-bytes'] == '7'
    assert response.headers['x-audio-cache-key'] == 'oss:hello.mp3:7:etag-1'
    assert response.headers['x-audio-oss-url'] == 'https://oss.example.com/hello.mp3?signature=1'
    assert response.headers['x-audio-source'] == 'oss'


def test_gateway_get_word_audio_proxy_returns_cached_audio_without_cache_only(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        '_resolve_word_audio_request',
        lambda word: {
            'word': word,
            'normalized_word': 'hello',
            'provider': 'hybrid',
            'model': 'speech-2.8-hd@dict-v1',
            'voice': 'English_Trustworthy_Man',
            'file_name': 'hello.mp3',
        },
    )
    monkeypatch.setattr(
        module,
        'fetch_word_audio_content',
        lambda **kwargs: {
            'body': b'ID3CACHED',
            'content_type': 'audio/mpeg',
            'byte_length': '9',
            'cache_key': 'oss:hello.mp3:9:etag-1',
            'signed_url': 'https://oss.example.com/hello.mp3?signature=1',
            'media_id': 'tts/object/hello.mp3',
        },
    )

    response = client.get('/api/tts/word-audio', params={'w': 'hello'})

    assert response.status_code == 200
    assert response.content == b'ID3CACHED'
    assert response.headers['x-audio-cache-key'] == 'oss:hello.mp3:9:etag-1'


def test_gateway_get_word_audio_proxy_generates_audio_on_cache_miss(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)
    seen: dict[str, object] = {}

    class FakeResponse:
        status_code = 200
        content = b'ID3GENERATED'
        headers = {'content-type': 'audio/mpeg', 'X-Audio-Bytes': '12'}

    monkeypatch.setattr(
        module,
        '_resolve_word_audio_request_candidates',
        lambda word, pronunciation_mode=None: [{
            'word': word,
            'normalized_word': 'hello',
            'provider': 'azure',
            'model': 'azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer',
            'voice': 'en-GB-LibbyNeural',
            'file_name': 'hello.mp3',
            'pronunciation_mode': 'word',
        }],
    )
    monkeypatch.setattr(module, 'fetch_word_audio_content', lambda **kwargs: None)

    def fake_generate_tts_audio(payload, **kwargs):
        seen['payload'] = payload
        seen.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(module, 'generate_tts_audio', fake_generate_tts_audio)

    response = client.get('/api/tts/word-audio', params={'w': 'hello'})

    assert response.status_code == 200
    assert response.content == b'ID3GENERATED'
    assert response.headers['x-audio-bytes'] == '12'
    assert seen['payload'] == {
        'text': 'hello',
        'provider': 'azure',
        'model': 'azure-rest:test',
        'voice_id': 'en-GB-LibbyNeural',
        'content_mode': 'word',
    }


def test_gateway_get_word_audio_proxy_generates_segmented_audio(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)
    seen: dict[str, object] = {}

    class FakeResponse:
        status_code = 200
        content = b'ID3DATA'
        headers = {'content-type': 'audio/mpeg', 'X-Audio-Bytes': '7'}

    def fake_generate_tts_audio(payload, **kwargs):
        seen['payload'] = payload
        seen.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(
        module,
        '_resolve_word_audio_request_candidates',
        lambda word, pronunciation_mode=None: [{
            'word': word,
            'normalized_word': 'phenomenon',
            'provider': 'azure',
            'model': 'azure-rest:test@azure-word-segmented-v1',
            'voice': 'en-GB-RyanNeural',
            'file_name': 'phenomenon.mp3',
            'pronunciation_mode': 'word-segmented',
        }],
    )
    monkeypatch.setattr(module, 'fetch_word_audio_content', lambda **kwargs: None)
    monkeypatch.setattr(module, 'generate_tts_audio', fake_generate_tts_audio)

    response = client.get(
        '/api/tts/word-audio',
        params={'w': 'phenomenon', 'pronunciation_mode': 'phonetic_segments', 'phonetic': '/fəˈnɒmɪnən/'},
    )

    assert response.status_code == 200
    assert response.content == b'ID3DATA'
    assert response.headers['x-audio-bytes'] == '7'
    assert seen['payload'] == {
        'text': 'phenomenon',
        'provider': 'azure',
        'content_mode': 'word-segmented',
        'phonetic': '/fəˈnɒmɪnən/',
    }


def test_gateway_get_word_audio_proxy_prefers_cached_segmented_audio(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        '_resolve_word_audio_request_candidates',
        lambda word, pronunciation_mode=None: [
            {
                'word': word,
                'normalized_word': 'brain',
                'provider': 'azure',
                'model': 'azure-rest:test@azure-word-segmented-v1',
                'voice': 'en-GB-RyanNeural',
                'file_name': 'brain-ryan.mp3',
                'pronunciation_mode': 'word-segmented',
            },
            {
                'word': word,
                'normalized_word': 'brain',
                'provider': 'azure',
                'model': 'azure-rest:test@azure-word-segmented-v1',
                'voice': 'en-GB-LibbyNeural',
                'file_name': 'brain-libby.mp3',
                'pronunciation_mode': 'word-segmented',
            },
        ],
    )

    def fake_fetch_word_audio_content(**kwargs):
        if kwargs['voice'] == 'en-GB-LibbyNeural':
            return {
                'body': b'ID3CACHED',
                'content_type': 'audio/mpeg',
                'byte_length': '9',
                'cache_key': 'oss:brain-libby.mp3:9:etag-1',
                'signed_url': 'https://oss.example.com/brain-libby.mp3?signature=1',
                'media_id': 'tts/object/brain-libby.mp3',
            }
        return None

    monkeypatch.setattr(module, 'fetch_word_audio_content', fake_fetch_word_audio_content)
    monkeypatch.setattr(
        module,
        'generate_tts_audio',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('should not generate segmented audio')),
    )

    response = client.get(
        '/api/tts/word-audio',
        params={'w': 'brain', 'pronunciation_mode': 'phonetic_segments'},
    )

    assert response.status_code == 200
    assert response.content == b'ID3CACHED'
    assert response.headers['x-audio-source'] == 'oss'


def test_gateway_head_example_audio_proxy_maps_legacy_headers(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        'fetch_example_audio_metadata',
        lambda **kwargs: {
            'media_id': 'example.mp3',
            'cache_hit': True,
            'byte_length': 803,
            'cache_key': 'example:803:1',
        },
    )

    response = client.head('/api/tts/example-audio', params={'sentence': 'Hello, world!', 'word': 'hello'})

    assert response.status_code == 204
    assert response.headers['x-audio-bytes'] == '803'
    assert response.headers['x-audio-cache-key'] == 'example:803:1'
    assert response.headers['x-audio-source'] == 'local'
    assert response.headers['x-media-id'] == 'example.mp3'


def test_gateway_post_example_audio_metadata_only_proxy(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        'fetch_example_audio_metadata',
        lambda **kwargs: {
            'media_id': 'example.mp3',
            'cache_hit': True,
            'byte_length': 803,
            'cache_key': 'example:803:1',
        },
    )

    response = client.post(
        '/api/tts/example-audio',
        json={'sentence': 'Hello, world!', 'word': 'hello'},
        headers={'X-Audio-Metadata-Only': '1'},
    )

    assert response.status_code == 204
    assert response.headers['x-audio-bytes'] == '803'
    assert response.headers['x-audio-cache-key'] == 'example:803:1'
    assert response.headers['x-audio-source'] == 'local'


def test_gateway_head_example_audio_proxy_maps_oss_headers(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        'fetch_example_audio_metadata',
        lambda **kwargs: {
            'media_id': 'tts-media-service/example-audio/example.mp3',
            'cache_hit': True,
            'provider': 'aliyun-oss',
            'byte_length': 803,
            'cache_key': 'oss:example.mp3:803:etag-1',
            'signed_url': 'https://oss.example.com/example.mp3?signature=1',
        },
    )

    response = client.head('/api/tts/example-audio', params={'sentence': 'Hello, world!', 'word': 'hello'})

    assert response.status_code == 204
    assert response.headers['x-audio-bytes'] == '803'
    assert response.headers['x-audio-cache-key'] == 'oss:example.mp3:803:etag-1'
    assert response.headers['x-audio-oss-url'] == 'https://oss.example.com/example.mp3?signature=1'
    assert response.headers['x-audio-source'] == 'oss'
    assert response.headers['x-media-id'] == 'tts-media-service/example-audio/example.mp3'


def test_gateway_get_example_audio_proxy_returns_audio_bytes(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        'fetch_example_audio_content',
        lambda **kwargs: {
            'body': b'ID3' + (b'\x00' * 800),
            'content_type': 'audio/mpeg',
            'byte_length': '803',
            'cache_key': 'example:803:1',
            'signed_url': '',
            'media_id': 'example.mp3',
        },
    )

    response = client.get('/api/tts/example-audio', params={'sentence': 'Hello, world!', 'word': 'hello'})

    assert response.status_code == 200
    assert response.content == b'ID3' + (b'\x00' * 800)
    assert response.headers['content-type'].startswith('audio/mpeg')
    assert response.headers['x-audio-bytes'] == '803'
    assert response.headers['x-audio-cache-key'] == 'example:803:1'
    assert response.headers['x-audio-source'] == 'local'


def test_gateway_get_example_audio_proxy_maps_oss_headers(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        'fetch_example_audio_content',
        lambda **kwargs: {
            'body': b'ID3' + (b'\x00' * 800),
            'content_type': 'audio/mpeg',
            'byte_length': '803',
            'cache_key': 'oss:example.mp3:803:etag-1',
            'signed_url': 'https://oss.example.com/example.mp3?signature=1',
            'media_id': 'tts-media-service/example-audio/example.mp3',
            'provider': 'aliyun-oss',
        },
    )

    response = client.get('/api/tts/example-audio', params={'sentence': 'Hello, world!', 'word': 'hello'})

    assert response.status_code == 200
    assert response.content == b'ID3' + (b'\x00' * 800)
    assert response.headers['content-type'].startswith('audio/mpeg')
    assert response.headers['x-audio-bytes'] == '803'
    assert response.headers['x-audio-cache-key'] == 'oss:example.mp3:803:etag-1'
    assert response.headers['x-audio-oss-url'] == 'https://oss.example.com/example.mp3?signature=1'
    assert response.headers['x-audio-source'] == 'oss'
    assert response.headers['x-media-id'] == 'tts-media-service/example-audio/example.mp3'


def test_gateway_post_example_audio_proxy_requires_sentence():
    module = _load_gateway_module()
    client = TestClient(module.app)

    response = client.post('/api/tts/example-audio', json={'sentence': ''})

    assert response.status_code == 400
    assert response.json() == {'detail': 'sentence is required'}
