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
        assert res.headers['X-Audio-Bytes'] == str(len(VALID_MP3))
        assert res.headers['X-Audio-Cache-Key'].startswith('abc123:')

    def test_head_returns_cached_audio_metadata_without_generation(self, client, monkeypatch, tmp_path):
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

        res = client.head('/api/tts/word-audio?w=hello')

        assert res.status_code == 204
        assert res.headers['X-Audio-Bytes'] == str(len(VALID_MP3))
        assert res.headers['X-Audio-Cache-Key'].startswith('abc123:')
        assert not res.data

    def test_head_prefers_oss_metadata_when_available(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(
            tts,
            'default_word_tts_identity',
            lambda: ('azure', 'azure-rest:audio@cache-tag', 'en-GB-LibbyNeural'),
        )
        target = tmp_path / 'abc123.mp3'
        target.write_bytes(VALID_MP3)
        monkeypatch.setattr(
            'services.word_tts.word_tts_cache_path',
            lambda cache_dir, normalized_key, model, voice: target,
        )
        monkeypatch.setattr(
            'services.word_tts_oss.resolve_word_audio_oss_metadata',
            lambda **kwargs: type(
                'OssMetadata',
                (),
                {
                    'byte_length': 321,
                    'cache_key': 'oss:abc123.mp3:321:etag',
                    'signed_url': 'https://oss.example.com/abc123.mp3?signature=1',
                },
            )(),
        )

        res = client.head('/api/tts/word-audio?w=hello')

        assert res.status_code == 204
        assert res.headers['X-Audio-Bytes'] == '321'
        assert res.headers['X-Audio-Cache-Key'] == 'oss:abc123.mp3:321:etag'
        assert res.headers['X-Audio-Oss-Url'].startswith('https://oss.example.com/abc123.mp3')
        assert res.headers['X-Audio-Source'] == 'oss'

    def test_get_prefers_oss_audio_bytes_when_available(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(
            tts,
            'default_word_tts_identity',
            lambda: ('azure', 'azure-rest:audio@cache-tag', 'en-GB-LibbyNeural'),
        )
        target = tmp_path / 'abc123.mp3'
        target.write_bytes(VALID_MP3)
        monkeypatch.setattr(
            'services.word_tts.word_tts_cache_path',
            lambda cache_dir, normalized_key, model, voice: target,
        )
        monkeypatch.setattr(
            'services.word_tts_oss.resolve_word_audio_oss_metadata',
            lambda **kwargs: type(
                'OssMetadata',
                (),
                {
                    'byte_length': 321,
                    'cache_key': 'oss:abc123.mp3:321:etag',
                    'signed_url': 'https://oss.example.com/abc123.mp3?signature=1',
                },
            )(),
        )
        monkeypatch.setattr(
            'services.word_tts_oss.fetch_word_audio_oss_payload',
            lambda **kwargs: type(
                'OssPayload',
                (),
                {
                    'audio_bytes': b'ID3' + (b'\x01' * 318),
                    'byte_length': 321,
                    'cache_key': 'oss:abc123.mp3:321:etag',
                    'signed_url': 'https://oss.example.com/abc123.mp3?signature=1',
                    'content_type': 'audio/mpeg',
                },
            )(),
        )

        res = client.get('/api/tts/word-audio?w=hello&cache_only=1')

        assert res.status_code == 200
        assert res.mimetype == 'audio/mpeg'
        assert res.data == b'ID3' + (b'\x01' * 318)
        assert res.headers['X-Audio-Bytes'] == '321'
        assert res.headers['X-Audio-Cache-Key'] == 'oss:abc123.mp3:321:etag'
        assert res.headers['X-Audio-Source'] == 'oss'
        assert res.headers['X-Audio-Oss-Url'].startswith('https://oss.example.com/abc123.mp3')

    def test_get_ignores_range_and_returns_full_audio(self, client, monkeypatch, tmp_path):
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

        res = client.get('/api/tts/word-audio?w=hello', headers={'Range': 'bytes=0-'})

        assert res.status_code == 200
        assert res.headers['Accept-Ranges'] == 'none'
        assert res.headers.get('Content-Range') is None
        assert res.data == VALID_MP3

    def test_cache_only_missing_cache_returns_404_without_generation(self, client, monkeypatch, tmp_path):
        seen = {'called': False}

        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(
            tts,
            'default_word_tts_identity',
            lambda: ('hybrid', 'speech-2.8-hd@dict-v1', 'English_Trustworthy_Man'),
        )

        def fake_synthesize(*args, **kwargs):
            seen['called'] = True
            return VALID_MP3

        monkeypatch.setattr('services.word_tts.synthesize_word_to_bytes', fake_synthesize)

        res = client.get('/api/tts/word-audio?w=hello&cache_only=1')

        assert res.status_code == 404
        assert res.get_json() == {'error': 'word audio cache miss'}
        assert seen['called'] is False

    def test_missing_cache_generates_and_returns_audio(self, client, monkeypatch, tmp_path):
        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(
            tts,
            'default_word_tts_identity',
            lambda: ('hybrid', 'speech-2.8-hd@dict-v1', 'English_Trustworthy_Man'),
        )
        monkeypatch.setattr(
            'services.word_tts.synthesize_word_to_bytes',
            lambda text, model, voice, provider=None, content_mode=None: VALID_MP3,
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
        assert res.headers['X-Audio-Bytes'] == str(len(VALID_MP3))
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
            lambda text, model, voice, provider=None, content_mode=None: VALID_MP3,
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

        def raise_error(text, model, voice, provider=None, content_mode=None):
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

        def fake_synthesize(text, model, voice, provider=None, content_mode=None):
            seen['provider'] = provider
            seen['model'] = model
            seen['voice'] = voice
            seen['content_mode'] = content_mode
            return VALID_MP3

        monkeypatch.setattr('services.word_tts.synthesize_word_to_bytes', fake_synthesize)

        res = client.get('/api/tts/word-audio?w=community')

        assert res.status_code == 200
        assert seen == {
            'provider': 'hybrid',
            'model': 'speech-2.8-hd',
            'voice': 'English_Trustworthy_Man',
            'content_mode': 'word',
        }

    def test_segmented_generation_uses_azure_word_profile(self, client, monkeypatch, tmp_path):
        seen = {}

        monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
        monkeypatch.setattr(
            'services.word_tts.azure_default_model',
            lambda: 'azure-rest:audio-24khz-48kbitrate-mono-mp3',
        )
        monkeypatch.setattr(
            'services.word_tts.azure_word_voice',
            lambda: 'en-GB-LibbyNeural',
        )

        def fake_synthesize(text, model, voice, provider=None, content_mode=None):
            seen['text'] = text
            seen['provider'] = provider
            seen['model'] = model
            seen['voice'] = voice
            seen['content_mode'] = content_mode
            return VALID_MP3

        monkeypatch.setattr('services.word_tts.synthesize_word_to_bytes', fake_synthesize)

        res = client.get('/api/tts/word-audio?w=phenomenon&pronunciation_mode=phonetic_segments')

        target = word_tts.word_tts_cache_path(
            tmp_path,
            'phenomenon',
            'azure-rest:audio-24khz-48kbitrate-mono-mp3@azure-word-segmented-v1',
            'en-GB-LibbyNeural',
        )
        assert res.status_code == 200
        assert target.exists()
        assert seen == {
            'text': 'phenomenon',
            'provider': 'azure',
            'model': 'azure-rest:audio-24khz-48kbitrate-mono-mp3',
            'voice': 'en-GB-LibbyNeural',
            'content_mode': 'word-segmented',
        }
