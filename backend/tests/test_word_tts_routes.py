# ── Tests for GET /api/tts/word-audio ─────────────────────────────────────────


from routes import tts
from services import word_tts


VALID_MP3 = b'ID3' + (b'\x00' * 800)


class TestWordAudioRoute:
    def test_missing_w_returns_400(self, client):
        res = client.get('/api/tts/word-audio')
        assert res.status_code == 400

    def test_uses_effective_minimax_cache_identity(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(
            tts,
            'default_word_tts_identity',
            lambda: ('hybrid', 'speech-2.8-hd@dict-v1', 'English_Trustworthy_Man'),
        )
        target = tmp_path / 'abc123.mp3'
        target.write_bytes(VALID_MP3)
        monkeypatch.setattr(
            'services.word_tts.word_tts_cache_path',
            lambda cache_dir, normalized_key, model, voice: target,
        )

        res = client.get('/api/tts/word-audio?w=hello')

        assert res.status_code == 200
        assert res.mimetype == 'audio/mpeg'
        assert res.headers['Cache-Control'] == 'no-store, max-age=0'

    def test_missing_cache_generates_and_returns_audio(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(
            tts,
            'default_word_tts_identity',
            lambda: ('hybrid', 'speech-2.8-hd@dict-v1', 'English_Trustworthy_Man'),
        )
        monkeypatch.setattr(
            'services.word_tts.synthesize_word_to_bytes',
            lambda text, model, voice, provider=None: VALID_MP3,
        )

        res = client.get('/api/tts/word-audio?w=hello')

        target = word_tts.word_tts_cache_path(
            tmp_path,
            'hello',
            'speech-2.8-hd@dict-v1',
            'English_Trustworthy_Man',
        )
        assert res.status_code == 200
        assert res.mimetype == 'audio/mpeg'
        assert target.exists()
        assert target.read_bytes() == VALID_MP3

    def test_invalid_cached_mp3_is_deleted_and_regenerated(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(
            tts,
            'default_word_tts_identity',
            lambda: ('hybrid', 'speech-2.8-hd@dict-v1', 'English_Trustworthy_Man'),
        )
        broken = tmp_path / 'broken.mp3'
        broken.write_bytes(b'ID3')
        monkeypatch.setattr(
            'services.word_tts.word_tts_cache_path',
            lambda cache_dir, normalized_key, model, voice: broken,
        )
        monkeypatch.setattr(
            'services.word_tts.synthesize_word_to_bytes',
            lambda text, model, voice, provider=None: VALID_MP3,
        )

        res = client.get('/api/tts/word-audio?w=hello')

        assert res.status_code == 200
        assert broken.exists()
        assert broken.read_bytes() == VALID_MP3

    def test_generation_failure_returns_502(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(
            tts,
            'default_word_tts_identity',
            lambda: ('hybrid', 'speech-2.8-hd@dict-v1', 'English_Trustworthy_Man'),
        )

        def raise_error(text, model, voice, provider=None):
            raise RuntimeError('boom')

        monkeypatch.setattr('services.word_tts.synthesize_word_to_bytes', raise_error)

        res = client.get('/api/tts/word-audio?w=hello')

        assert res.status_code == 502
        assert res.get_json() == {'error': 'word audio generation failed'}

    def test_generation_uses_word_provider_override(self, client, monkeypatch, tmp_path):
        seen = {}

        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(
            tts,
            'default_word_tts_identity',
            lambda: ('hybrid', 'speech-2.8-hd@dict-v1', 'English_Trustworthy_Man'),
        )

        def fake_synthesize(text, model, voice, provider=None):
            seen['provider'] = provider
            seen['model'] = model
            seen['voice'] = voice
            return VALID_MP3

        monkeypatch.setattr('services.word_tts.synthesize_word_to_bytes', fake_synthesize)

        res = client.get('/api/tts/word-audio?w=community')

        assert res.status_code == 200
        assert seen == {
            'provider': 'hybrid',
            'model': 'speech-2.8-hd@dict-v1',
            'voice': 'English_Trustworthy_Man',
        }
