# ── Tests for POST /api/tts/example-audio ──────────────────────────────────────

from routes import tts

VALID_MP3 = b'ID3' + (b'\x00' * 800)


class TestExampleAudioRoute:
    def test_dashscope_example_audio_uses_provider_aware_tts(self, client, monkeypatch, tmp_path):
        calls = []

        monkeypatch.setattr(tts, '_cache_dir', lambda: tmp_path)
        monkeypatch.setattr(tts, 'default_cache_identity', lambda: ('qwen-tts-2025-05-22', 'Cherry'))
        monkeypatch.setenv('BAILIAN_TTS_PROVIDER', 'dashscope')

        def fake_synthesize(text, model, voice):
            calls.append((text, model, voice))
            return VALID_MP3

        monkeypatch.setattr('services.word_tts.synthesize_word_to_bytes', fake_synthesize)

        res = client.post('/api/tts/example-audio', json={'sentence': 'Hello, world!'})

        assert res.status_code == 200
        assert res.mimetype == 'audio/mpeg'
        assert res.headers['X-Audio-Bytes'] == str(len(VALID_MP3))
        assert calls == [('Hello, world!', 'qwen-tts-2025-05-22', 'Cherry')]

        cached_files = list(tmp_path.glob('*.mp3'))
        assert len(cached_files) == 1
        assert cached_files[0].read_bytes() == VALID_MP3

    def test_example_audio_metadata_only_returns_cached_size(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, '_cache_dir', lambda: tmp_path)
        monkeypatch.setattr(tts, 'default_cache_identity', lambda: ('qwen-tts-2025-05-22', 'Cherry'))
        monkeypatch.setenv('BAILIAN_TTS_PROVIDER', 'dashscope')

        cache_key = tts.hashlib.md5('ex:Hello, world!:qwen-tts-2025-05-22:Cherry'.encode()).hexdigest()[:16]
        cached = tmp_path / f'{cache_key}.mp3'
        cached.write_bytes(VALID_MP3)

        res = client.post(
            '/api/tts/example-audio',
            json={'sentence': 'Hello, world!'},
            headers={'X-Audio-Metadata-Only': '1'},
        )

        assert res.status_code == 204
        assert res.headers['X-Audio-Bytes'] == str(len(VALID_MP3))
        assert not res.data
