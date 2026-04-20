from __future__ import annotations

from routes import tts


VALID_MP3 = b'ID3' + (b'\x00' * 800)


def test_get_falls_back_to_legacy_normal_cache_identity(client, monkeypatch, tmp_path):
    monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
    monkeypatch.setattr(
        tts,
        '_resolve_normal_word_audio_identity',
        lambda: (
            'azure',
            'azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer',
            'en-GB-RyanNeural',
        ),
    )

    current_target = tmp_path / 'current.mp3'
    legacy_ryan_target = tmp_path / 'legacy-ryan.mp3'
    legacy_libby_target = tmp_path / 'legacy-libby.mp3'
    legacy_libby_target.write_bytes(VALID_MP3)

    def fake_cache_path(cache_dir, normalized_key, model, voice):
        if model == 'azure-rest:test@azure-word-v5-ielts-rp-female-onset-buffer':
            if voice == 'en-GB-RyanNeural':
                return legacy_ryan_target
            if voice == 'en-GB-LibbyNeural':
                return legacy_libby_target
        return current_target

    monkeypatch.setattr('services.word_tts.word_tts_cache_path', fake_cache_path)
    monkeypatch.setattr('services.word_tts_oss.resolve_word_audio_oss_metadata', lambda **kwargs: None)

    res = client.get('/api/tts/word-audio?w=brain&cache_only=1')

    assert res.status_code == 200
    assert res.mimetype == 'audio/mpeg'
    assert res.headers['X-Audio-Source'] == 'local'
    assert res.data == VALID_MP3
