# ── Tests for GET /api/tts/word-audio ─────────────────────────────────────────


from pathlib import Path

from routes import tts


class TestWordAudioRoute:
    def test_missing_w_returns_400(self, client):
        res = client.get('/api/tts/word-audio')
        assert res.status_code == 400

    def test_not_generated_returns_404(self, client):
        res = client.get('/api/tts/word-audio?w=nonexistent_word_xyz_12345')
        assert res.status_code == 404

    def test_uses_effective_minimax_cache_identity(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(tts, 'default_cache_identity', lambda: ('speech-2.8-hd', 'English_Trustworthy_Man'))
        target = tmp_path / 'abc123.mp3'
        target.write_bytes(b'ID3' + (b'\x00' * 800))
        monkeypatch.setattr(
            'services.word_tts.word_tts_cache_path',
            lambda cache_dir, normalized_key, model, voice: target,
        )

        res = client.get('/api/tts/word-audio?w=hello')

        assert res.status_code == 200
        assert res.mimetype == 'audio/mpeg'

    def test_invalid_cached_mp3_is_deleted_and_returns_404(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(tts, 'default_cache_identity', lambda: ('speech-2.8-hd', 'English_Trustworthy_Man'))
        broken = tmp_path / 'broken.mp3'
        broken.write_bytes(b'ID3')
        monkeypatch.setattr(
            'services.word_tts.word_tts_cache_path',
            lambda cache_dir, normalized_key, model, voice: broken,
        )

        res = client.get('/api/tts/word-audio?w=hello')

        assert res.status_code == 404
        assert not broken.exists()
