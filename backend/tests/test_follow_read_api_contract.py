from __future__ import annotations

import importlib.util
from pathlib import Path

from fastapi.testclient import TestClient


SERVICE_PATH = Path(__file__).resolve().parents[2] / 'services' / 'tts-media-service' / 'main.py'
GATEWAY_PATH = Path(__file__).resolve().parents[2] / 'apps' / 'gateway-bff' / 'main.py'


def _configure_tts_media_env(monkeypatch, tmp_path: Path) -> None:
    sqlite_uri = f"sqlite:///{tmp_path / 'tts-media-service.sqlite'}"
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('SQLITE_DB_PATH', str(tmp_path / 'tts-media-service.sqlite'))
    monkeypatch.setenv('SQLALCHEMY_DATABASE_URI', sqlite_uri)
    monkeypatch.setenv('TTS_MEDIA_SERVICE_SQLALCHEMY_DATABASE_URI', sqlite_uri)
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')


def _load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_monolith_follow_read_route_returns_three_pass_payload(client):
    response = client.get(
        '/api/tts/follow-read-word',
        query_string={
            'w': 'phenomenon',
            'phonetic': '/fəˈnɒmɪnən/',
            'definition': '现象；迹象；非凡的人',
            'pos': 'n.',
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body['audio_profile'] == 'full_chunk_full'
    assert body['audio_playback_rate'] == 1.0
    assert body['audio_url'].startswith('/api/tts/word-audio?w=phenomenon')
    assert body['chunk_audio_url'].startswith('/api/tts/follow-read-chunked-audio?w=phenomenon')
    assert [clip['kind'] for clip in body['audio_sequence']] == ['follow']
    assert [segment['letters'] for segment in body['segments']] == ['phe', 'no', 'me', 'non']
    assert body['segments']


def test_tts_media_service_follow_read_route_returns_payload(monkeypatch, tmp_path):
    _configure_tts_media_env(monkeypatch, tmp_path)
    module = _load_module('tts_media_service_main_follow_read', SERVICE_PATH)
    client = TestClient(module.app)

    response = client.get(
        '/v1/media/follow-read-word',
        params={
            'w': 'child care',
            'phonetic': '/ˈtʃaɪld keər/',
            'definition': '儿童保育；儿童托管',
            'pos': 'n.',
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body['word'] == 'child care'
    assert body['audio_profile'] == 'full_chunk_full'
    assert [segment['letters'] for segment in body['segments']] == ['child', 'care']


def test_gateway_follow_read_proxy_forwards_request(monkeypatch):
    module = _load_module('gateway_bff_main_follow_read', GATEWAY_PATH)
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    def fake_fetch_follow_read_word(**kwargs):
        captured.update(kwargs)
        return {
            'word': kwargs['word'],
            'phonetic': kwargs.get('phonetic') or '',
            'definition': kwargs.get('definition') or '',
            'pos': kwargs.get('pos') or '',
            'audio_url': '/api/tts/word-audio?w=phenomenon',
            'audio_profile': 'full_chunk_full',
            'audio_playback_rate': 1.0,
            'chunk_audio_url': '/api/tts/follow-read-chunked-audio?w=phenomenon',
            'audio_sequence': [
                {'id': 'follow-read-track', 'kind': 'follow', 'label': '完整示范 -> 拆分跟读 -> 完整回放', 'url': '/api/tts/follow-read-chunked-audio?w=phenomenon', 'playback_rate': 1.0, 'track_segments': True},
            ],
            'estimated_duration_ms': 4200,
            'segments': [{'id': 'seg-0', 'letter_start': 0, 'letter_end': 10, 'letters': 'phenomenon', 'phonetic': 'fəˈnɒmɪnən', 'start_ms': 1100, 'end_ms': 2500}],
        }

    monkeypatch.setattr(module, 'fetch_follow_read_word', fake_fetch_follow_read_word)

    response = client.get(
        '/api/tts/follow-read-word',
        params={
            'w': 'phenomenon',
            'phonetic': '/fəˈnɒmɪnən/',
            'definition': '现象',
            'pos': 'n.',
        },
        headers={
            'Authorization': 'Bearer hidden-token',
            'Idempotency-Key': 'follow-read-1',
        },
    )

    assert response.status_code == 200
    assert response.json()['audio_profile'] == 'full_chunk_full'
    assert captured['word'] == 'phenomenon'
    assert captured['phonetic'] == '/fəˈnɒmɪnən/'
    assert captured['headers']['x-service-name'] == 'gateway-bff'
    assert captured['headers']['idempotency-key'] == 'follow-read-1'
    assert 'authorization' not in captured['headers']


def test_tts_media_service_follow_read_chunked_audio_returns_mp3(monkeypatch, tmp_path):
    _configure_tts_media_env(monkeypatch, tmp_path)
    module = _load_module('tts_media_service_main_follow_read_audio', SERVICE_PATH)
    client = TestClient(module.app)

    monkeypatch.setattr(module, 'generate_follow_read_chunked_audio_bytes', lambda **kwargs: b'ID3' + (b'\x00' * 32))

    response = client.get(
        '/v1/media/follow-read-chunked-audio',
        params={'w': 'phenomenon', 'phonetic': '/fəˈnɒmɪnən/'},
    )

    assert response.status_code == 200
    assert response.content.startswith(b'ID3')
    assert response.headers['x-audio-bytes'] == '35'


def test_gateway_follow_read_chunked_audio_proxy_forwards_request(monkeypatch):
    module = _load_module('gateway_bff_main_follow_read_audio', GATEWAY_PATH)
    client = TestClient(module.app, base_url='https://axiomaticworld.com')
    captured: dict[str, object] = {}

    def fake_fetch_follow_read_chunked_audio(**kwargs):
        captured.update(kwargs)
        return {
            'body': b'ID3' + (b'\x01' * 24),
            'content_type': 'audio/mpeg',
            'byte_length': '27',
            'cache_key': '',
            'signed_url': '',
            'media_id': 'follow-read/phenomenon.mp3',
        }

    monkeypatch.setattr(module, 'fetch_follow_read_chunked_audio', fake_fetch_follow_read_chunked_audio)

    response = client.get(
        '/api/tts/follow-read-chunked-audio',
        params={'w': 'phenomenon', 'phonetic': '/fəˈnɒmɪnən/'},
        headers={'Idempotency-Key': 'follow-chunk-1'},
    )

    assert response.status_code == 200
    assert response.content.startswith(b'ID3')
    assert response.headers['x-audio-bytes'] == '27'
    assert captured['word'] == 'phenomenon'
    assert captured['phonetic'] == '/fəˈnɒmɪnən/'
    assert captured['headers']['idempotency-key'] == 'follow-chunk-1'
