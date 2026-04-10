from __future__ import annotations

import io
import importlib.util
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient


SERVICE_PATH = Path(__file__).resolve().parents[2] / 'services' / 'tts-media-service' / 'main.py'
VALID_MP3 = b'ID3' + (b'\x00' * 800)


def _load_tts_media_service_module():
    spec = importlib.util.spec_from_file_location('tts_media_service_main', SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_tts_media_service_ready_uses_oss_configuration(monkeypatch):
    monkeypatch.setenv('AXI_ALIYUN_OSS_ACCESS_KEY_ID', 'id')
    monkeypatch.setenv('AXI_ALIYUN_OSS_ACCESS_KEY_SECRET', 'secret')
    monkeypatch.setenv('AXI_ALIYUN_OSS_PRIVATE_BUCKET', 'bucket')
    monkeypatch.setenv('AXI_ALIYUN_OSS_REGION', 'oss-cn-hangzhou')

    module = _load_tts_media_service_module()
    client = TestClient(module.app)

    response = client.get('/ready')

    assert response.status_code == 200
    assert response.json() == {
        'status': 'ready',
        'service': 'tts-media-service',
        'version': '0.1.0',
        'dependencies': {'aliyun_oss': True},
    }


def test_tts_media_service_voices_contract(monkeypatch):
    module = _load_tts_media_service_module()
    client = TestClient(module.app)

    monkeypatch.setattr(module.runtime, 'current_english_voices', lambda provider=None: {'voice-a': 'voice-a'})
    monkeypatch.setattr(module.runtime, 'current_recommended_voices', lambda provider=None: ['voice-a'])

    response = client.get('/v1/tts/voices')

    assert response.status_code == 200
    assert response.json() == {
        'voices': [{'id': 'voice-a', 'name': 'voice-a'}],
        'recommended': ['voice-a'],
    }


def test_tts_media_service_generate_uses_azure_provider_branch(monkeypatch, tmp_path):
    module = _load_tts_media_service_module()
    client = TestClient(module.app)
    seen = {}

    monkeypatch.setenv('BAILIAN_TTS_PROVIDER', 'azure')
    monkeypatch.setattr(module.runtime, 'tts_cache_dir', lambda: tmp_path)
    monkeypatch.setattr(module.runtime, 'azure_default_model', lambda: 'azure-rest:audio-24khz-48kbitrate-mono-mp3')
    monkeypatch.setattr(module.runtime, 'azure_sentence_voice', lambda: 'en-US-AndrewMultilingualNeural')
    monkeypatch.setattr(module.runtime, 'default_cache_identity', lambda: ('azure-rest:audio-24khz-48kbitrate-mono-mp3', 'en-US-AndrewMultilingualNeural'))

    def fake_synthesize(text, model, voice, provider=None, speed=None, content_mode=None, phonetic=None):
        seen['text'] = text
        seen['model'] = model
        seen['voice'] = voice
        seen['provider'] = provider
        seen['speed'] = speed
        seen['content_mode'] = content_mode
        seen['phonetic'] = phonetic
        return VALID_MP3

    monkeypatch.setattr(module.runtime, 'synthesize_word_to_bytes', fake_synthesize)

    response = client.post(
        '/v1/tts/generate',
        json={'text': 'Hello from service', 'voice_id': 'en-US-AndrewMultilingualNeural', 'speed': 1.2},
    )

    assert response.status_code == 200
    assert response.headers['content-type'].startswith('audio/mpeg')
    assert response.headers['x-audio-bytes'] == str(len(VALID_MP3))
    assert seen == {
        'text': 'Hello from service',
        'model': 'azure-rest:audio-24khz-48kbitrate-mono-mp3',
        'voice': 'en-US-AndrewMultilingualNeural',
        'provider': 'azure',
        'speed': 1.2,
        'content_mode': 'sentence',
        'phonetic': None,
    }


def test_tts_media_service_generate_uses_minimax_adapter(monkeypatch):
    module = _load_tts_media_service_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module.runtime,
        'shared_generate_speech_response',
        lambda payload, **kwargs: module.runtime.send_audio_file(
            io.BytesIO(VALID_MP3),
            mimetype='audio/mpeg',
        ),
    )

    response = client.post(
        '/v1/tts/generate',
        json={'text': 'Hello from minimax', 'provider': 'minimax', 'voice_id': 'female-tianmei'},
    )

    assert response.status_code == 200
    assert response.content == VALID_MP3
    assert response.headers['content-type'].startswith('audio/mpeg')
    assert response.headers['x-audio-bytes'] == str(len(VALID_MP3))


def test_tts_media_service_word_audio_metadata_contract(monkeypatch):
    module = _load_tts_media_service_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        'resolve_object_metadata',
        lambda **kwargs: SimpleNamespace(
            provider='aliyun-oss',
            bucket_name='bucket',
            object_key=kwargs['object_key'],
            byte_length=321,
            content_type='audio/mpeg',
            cache_key='oss:hello.mp3:321:etag-1',
            signed_url='https://oss.example.com/hello.mp3?signature=1',
        ),
    )

    response = client.get(
        '/v1/media/word-audio',
        params={
            'file_name': 'hello.mp3',
            'model': 'speech-2.8-hd@dict-v1',
            'voice': 'English_Trustworthy_Man',
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['media_id'] == body['object_key']
    assert body['cache_hit'] is True
    assert body['provider'] == 'aliyun-oss'
    assert body['bucket_name'] == 'bucket'
    assert body['object_key'] == (
        'projects/ielts-vocab/word-tts-cache/'
        'speech-2-8-hd-dict-v1-english-trustworthy-man/hello.mp3'
    )
    assert body['content_type'] == 'audio/mpeg'
    assert body['byte_length'] == 321
    assert body['cache_key'] == 'oss:hello.mp3:321:etag-1'
    assert body['signed_url'] == 'https://oss.example.com/hello.mp3?signature=1'
    assert body['signed_url_expires_at'].endswith('+00:00')


def test_tts_media_service_word_audio_content_contract(monkeypatch):
    module = _load_tts_media_service_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        'fetch_object_payload',
        lambda **kwargs: SimpleNamespace(
            provider='aliyun-oss',
            bucket_name='bucket',
            object_key=kwargs['object_key'],
            body=b'ID3DATA',
            byte_length=7,
            content_type='audio/mpeg',
            cache_key='oss:hello.mp3:7:etag-1',
            signed_url='https://oss.example.com/hello.mp3?signature=1',
        ),
    )

    response = client.get(
        '/v1/media/word-audio/content',
        params={
            'file_name': 'hello.mp3',
            'model': 'speech-2.8-hd@dict-v1',
            'voice': 'English_Trustworthy_Man',
        },
    )

    assert response.status_code == 200
    assert response.content == b'ID3DATA'
    assert response.headers['content-type'].startswith('audio/mpeg')
    assert response.headers['x-audio-bytes'] == '7'
    assert response.headers['x-audio-cache-key'] == 'oss:hello.mp3:7:etag-1'
    assert response.headers['x-audio-oss-url'] == 'https://oss.example.com/hello.mp3?signature=1'
    assert response.headers['x-media-id'] == (
        'projects/ielts-vocab/word-tts-cache/'
        'speech-2-8-hd-dict-v1-english-trustworthy-man/hello.mp3'
    )


def test_tts_media_service_example_audio_metadata_contract(monkeypatch):
    module = _load_tts_media_service_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module.runtime,
        'example_audio_metadata',
        lambda sentence: {
            'media_id': 'example.mp3',
            'cache_hit': True,
            'provider': 'local-cache',
            'bucket_name': None,
            'object_key': None,
            'content_type': 'audio/mpeg',
            'byte_length': 803,
            'cache_key': 'example:803:1',
            'signed_url': None,
            'signed_url_expires_at': None,
        },
    )

    response = client.post('/v1/media/example-audio/metadata', json={'sentence': 'Hello, world!'})

    assert response.status_code == 200
    assert response.json() == {
        'media_id': 'example.mp3',
        'cache_hit': True,
        'provider': 'local-cache',
        'bucket_name': None,
        'object_key': None,
        'content_type': 'audio/mpeg',
        'byte_length': 803,
        'cache_key': 'example:803:1',
        'signed_url': None,
        'signed_url_expires_at': None,
    }


def test_tts_media_service_example_audio_content_generates_and_returns_audio(monkeypatch, tmp_path):
    module = _load_tts_media_service_module()
    client = TestClient(module.app)
    target = tmp_path / 'example.mp3'

    monkeypatch.setattr(module.runtime, 'example_cache_file', lambda sentence, model, voice: target)
    monkeypatch.setattr(module.runtime, 'example_tts_identity', lambda sentence: ('qwen-tts-2025-05-22', 'Cherry'))
    monkeypatch.setattr(module.runtime, 'synthesize_example_audio', lambda sentence, model, voice: VALID_MP3)
    monkeypatch.setattr(module.runtime, 'remove_invalid_cached_audio', lambda path: None)

    response = client.post('/v1/media/example-audio/content', json={'sentence': 'Hello, world!'})

    assert response.status_code == 200
    assert response.content == VALID_MP3
    assert response.headers['content-type'].startswith('audio/mpeg')
    assert response.headers['x-audio-bytes'] == str(len(VALID_MP3))
    assert response.headers['x-audio-cache-key'].startswith('example:')
    assert response.headers['x-media-id'] == 'example.mp3'
    assert target.read_bytes() == VALID_MP3
