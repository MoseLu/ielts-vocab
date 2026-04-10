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


def test_gateway_word_audio_metadata_proxy_returns_upstream_payload(monkeypatch):
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
            'cache_hit': True,
            'provider': 'aliyun-oss',
            'bucket_name': 'bucket',
            'object_key': 'tts/object/hello.mp3',
            'content_type': 'audio/mpeg',
            'byte_length': 321,
            'cache_key': 'oss:hello.mp3:321:etag-1',
            'signed_url': 'https://oss.example.com/hello.mp3?signature=1',
            'signed_url_expires_at': '2026-04-09T00:00:00+00:00',
        },
    )

    response = client.get('/api/tts/word-audio/metadata', params={'w': 'hello'})

    assert response.status_code == 200
    assert response.json()['cache_hit'] is True
    assert response.json()['signed_url'] == 'https://oss.example.com/hello.mp3?signature=1'


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
    assert captured['headers']['authorization'] == 'Bearer tts-token'
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


def test_gateway_get_word_audio_proxy_requires_cache_only(monkeypatch):
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

    response = client.get('/api/tts/word-audio', params={'w': 'hello'})

    assert response.status_code == 501
    assert response.json() == {'error': 'word audio generation via gateway is not implemented yet'}


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
