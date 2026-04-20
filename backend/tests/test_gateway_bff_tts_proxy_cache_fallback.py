from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi import HTTPException
from fastapi.testclient import TestClient


GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'


def _load_gateway_module():
    spec = importlib.util.spec_from_file_location('gateway_bff_main', GATEWAY_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_gateway_head_word_audio_proxy_treats_transient_cache_errors_as_miss(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)

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

    def fake_fetch_word_audio_metadata(**kwargs):
        raise HTTPException(status_code=504, detail='tts media service timed out')

    monkeypatch.setattr(module, 'fetch_word_audio_metadata', fake_fetch_word_audio_metadata)

    response = client.head('/api/tts/word-audio', params={'w': 'hello', 'cache_only': '1'})

    assert response.status_code == 204
    assert response.headers['x-audio-source'] == 'missing'
    assert 'x-audio-bytes' not in response.headers


def test_gateway_get_word_audio_proxy_generates_audio_after_transient_cache_failure(monkeypatch):
    module = _load_gateway_module()
    client = TestClient(module.app)
    seen: dict[str, object] = {}

    class FakeResponse:
        status_code = 200
        content = b'ID3RECOVERED'
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

    def fake_fetch_word_audio_content(**kwargs):
        raise HTTPException(status_code=503, detail='tts media service error')

    def fake_generate_tts_audio(payload, **kwargs):
        seen['payload'] = payload
        seen.update(kwargs)
        return FakeResponse()

    monkeypatch.setattr(module, 'fetch_word_audio_content', fake_fetch_word_audio_content)
    monkeypatch.setattr(module, 'generate_tts_audio', fake_generate_tts_audio)

    response = client.get('/api/tts/word-audio', params={'w': 'hello'})

    assert response.status_code == 200
    assert response.content == b'ID3RECOVERED'
    assert response.headers['x-audio-bytes'] == '12'
    assert seen['payload'] == {
        'text': 'hello',
        'provider': 'azure',
        'model': 'azure-rest:test',
        'voice_id': 'en-GB-LibbyNeural',
        'content_mode': 'word',
    }
