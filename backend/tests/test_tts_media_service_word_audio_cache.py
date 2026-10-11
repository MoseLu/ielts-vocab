from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient
from flask import has_app_context


SERVICE_PATH = Path(__file__).resolve().parents[2] / 'services' / 'tts-media-service' / 'main.py'
VALID_MP3 = b'ID3' + (b'\x00' * 800)


def _configure_tts_media_env(monkeypatch, tmp_path: Path) -> None:
    sqlite_uri = f"sqlite:///{tmp_path / 'tts-media-service.sqlite'}"
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path / 'tts-media-service.sqlite'))
    monkeypatch.setenv('SQLALCHEMY_DATABASE_URI', sqlite_uri)
    monkeypatch.setenv('TTS_MEDIA_SERVICE_SQLALCHEMY_DATABASE_URI', sqlite_uri)
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')


def _load_tts_media_service_module():
    spec = importlib.util.spec_from_file_location('tts_media_service_word_audio_cache', SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_word_audio_generation_materializes_local_word_cache(monkeypatch, tmp_path):
    _configure_tts_media_env(monkeypatch, tmp_path)
    module = _load_tts_media_service_module()
    client = TestClient(module.app)
    seen: dict[str, object] = {'synthesis_calls': []}

    monkeypatch.setattr(module, 'BACKEND_PATH', tmp_path)
    monkeypatch.setattr(module, 'resolve_object_metadata', lambda **kwargs: None)
    monkeypatch.setattr(module, 'fetch_object_payload', lambda **kwargs: None)
    monkeypatch.setattr(
        module,
        '_record_tts_media_materialization',
        lambda request, **payload: seen.setdefault('materialization', payload),
    )

    def fake_synthesize(text, model, voice, provider=None, speed=None, content_mode=None, phonetic=None):
        seen['has_app_context'] = has_app_context()
        seen['synthesis_calls'].append({
            'text': text,
            'model': model,
            'voice': voice,
            'provider': provider,
            'content_mode': content_mode,
            'phonetic': phonetic,
        })
        return VALID_MP3

    monkeypatch.setattr(module.runtime, 'synthesize_word_to_bytes', fake_synthesize)

    response = client.post('/v1/tts/generate', json={
        'text': 'language',
        'provider': 'azure',
        'model': 'azure-rest:test',
        'voice_id': 'en-GB-LibbyNeural',
        'content_mode': 'word',
        'word_audio_file_name': 'language.mp3',
        'word_audio_model': 'azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer',
        'word_audio_voice': 'en-GB-LibbyNeural',
    })

    assert response.status_code == 200
    assert response.content == VALID_MP3
    assert response.headers['x-audio-bytes'] == str(len(VALID_MP3))
    assert response.headers['x-media-id'] == 'local:language.mp3'
    assert (tmp_path / 'word_tts_cache' / 'language.mp3').read_bytes() == VALID_MP3
    assert seen['synthesis_calls'] == [{
        'text': 'language',
        'model': 'azure-rest:test',
        'voice': 'en-GB-LibbyNeural',
        'provider': 'azure',
        'content_mode': 'word',
        'phonetic': None,
    }]
    assert seen['has_app_context'] is True
    assert seen['materialization']['media_kind'] == 'word-audio'
    assert seen['materialization']['media_id'] == 'language.mp3'
    assert seen['materialization']['model'] == 'azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer'

    cached_response = client.get('/v1/media/word-audio/content', params={
        'file_name': 'language.mp3',
        'model': 'azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer',
        'voice': 'en-GB-LibbyNeural',
    })
    metadata_response = client.get('/v1/media/word-audio', params={
        'file_name': 'language.mp3',
        'model': 'azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer',
        'voice': 'en-GB-LibbyNeural',
    })

    assert cached_response.status_code == 200
    assert cached_response.content == VALID_MP3
    assert cached_response.headers['x-media-id'] == 'local:language.mp3'
    assert metadata_response.status_code == 200
    assert metadata_response.json()['provider'] == 'local-cache'
