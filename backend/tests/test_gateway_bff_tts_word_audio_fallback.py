from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'
GATEWAY_MEDIA_PROXY_PATH = Path(__file__).resolve().parents[2] / 'packages' / 'platform-sdk' / 'platform_sdk' / 'gateway_media_proxy.py'


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('gateway_bff_main', GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _load_gateway_media_proxy_module():
    spec = importlib.util.spec_from_file_location('gateway_media_proxy', GATEWAY_MEDIA_PROXY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_resolve_word_audio_request_uses_ryan_hotfix_voice(monkeypatch):
    module = _load_gateway_media_proxy_module()

    monkeypatch.setattr(
        module,
        'resolve_normal_word_audio_identity',
        lambda: (
            'azure',
            'azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer',
            'en-GB-LibbyNeural',
        ),
    )
    monkeypatch.setattr(
        module,
        'word_tts_cache_path',
        lambda base, normalized, model, voice: Path(f'{normalized}-{voice}.mp3'),
    )

    request = module.resolve_word_audio_request('bread')

    assert request['voice'] == 'en-GB-RyanNeural'
    assert request['file_name'] == 'bread-en-GB-RyanNeural.mp3'


def test_resolve_segmented_word_audio_request_candidates_include_legacy_voice(monkeypatch):
    module = _load_gateway_media_proxy_module()

    monkeypatch.setattr(module, 'azure_default_model', lambda: 'azure-rest:test')
    monkeypatch.setattr(module, 'azure_word_voice', lambda: 'en-GB-RyanNeural')
    monkeypatch.setattr(
        module,
        'word_tts_cache_path',
        lambda base, normalized, model, voice: Path(f'{normalized}-{model}-{voice}.mp3'),
    )

    candidates = module.resolve_word_audio_request_candidates(
        'brain',
        pronunciation_mode='phonetic_segments',
    )

    assert [candidate['voice'] for candidate in candidates] == [
        'en-GB-RyanNeural',
        'en-GB-LibbyNeural',
    ]
    assert candidates[0]['model'] == 'azure-rest:test@azure-word-segmented-v1'


def test_resolve_normal_word_audio_request_candidates_include_legacy_cache_identities(monkeypatch):
    module = _load_gateway_media_proxy_module()

    monkeypatch.setattr(
        module,
        'resolve_normal_word_audio_identity',
        lambda: (
            'azure',
            'azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer',
            'en-GB-RyanNeural',
        ),
    )
    monkeypatch.setattr(
        module,
        'word_tts_cache_path',
        lambda base, normalized, model, voice: Path(f'{normalized}-{model}-{voice}.mp3'),
    )

    candidates = module.resolve_word_audio_request_candidates('bread')

    assert [(candidate['model'], candidate['voice']) for candidate in candidates] == [
        ('azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer', 'en-GB-RyanNeural'),
        ('azure-rest:test@azure-word-v5-ielts-rp-female-onset-buffer', 'en-GB-RyanNeural'),
        ('azure-rest:test@azure-word-v5-ielts-rp-female-onset-buffer', 'en-GB-LibbyNeural'),
    ]


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


def test_gateway_get_word_audio_proxy_prefers_cached_legacy_normal_audio(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

    monkeypatch.setattr(
        module,
        '_resolve_word_audio_request_candidates',
        lambda word, pronunciation_mode=None: [
            {
                'word': word,
                'normalized_word': 'bread',
                'provider': 'azure',
                'model': 'azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer',
                'voice': 'en-GB-RyanNeural',
                'file_name': 'bread-current.mp3',
                'pronunciation_mode': 'word',
            },
            {
                'word': word,
                'normalized_word': 'bread',
                'provider': 'azure',
                'model': 'azure-rest:test@azure-word-v5-ielts-rp-female-onset-buffer',
                'voice': 'en-GB-RyanNeural',
                'file_name': 'bread-legacy-ryan.mp3',
                'pronunciation_mode': 'word',
            },
            {
                'word': word,
                'normalized_word': 'bread',
                'provider': 'azure',
                'model': 'azure-rest:test@azure-word-v5-ielts-rp-female-onset-buffer',
                'voice': 'en-GB-LibbyNeural',
                'file_name': 'bread-legacy-libby.mp3',
                'pronunciation_mode': 'word',
            },
        ],
    )

    def fake_fetch_word_audio_content(**kwargs):
        if kwargs['model'] == 'azure-rest:test@azure-word-v5-ielts-rp-female-onset-buffer' and kwargs['voice'] == 'en-GB-LibbyNeural':
            return {
                'body': b'ID3LEGACY',
                'content_type': 'audio/mpeg',
                'byte_length': '9',
                'cache_key': 'oss:bread-legacy-libby.mp3:9:etag-1',
                'signed_url': 'https://oss.example.com/bread-legacy-libby.mp3?signature=1',
                'media_id': 'tts/object/bread-legacy-libby.mp3',
            }
        return None

    monkeypatch.setattr(module, 'fetch_word_audio_content', fake_fetch_word_audio_content)
    monkeypatch.setattr(
        module,
        'generate_tts_audio',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('should not generate normal audio')),
    )

    response = client.get('/api/tts/word-audio', params={'w': 'bread'})

    assert response.status_code == 200
    assert response.content == b'ID3LEGACY'
    assert response.headers['x-audio-source'] == 'oss'
    assert response.headers['x-audio-cache-key'] == 'oss:bread-legacy-libby.mp3:9:etag-1'
