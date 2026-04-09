from routes import tts


VALID_MP3 = b'ID3' + (b'\x00' * 800)


class FakeResponse:
    status_code = 200
    content = VALID_MP3
    text = ''


def test_generate_route_uses_azure_provider_branch(client, monkeypatch, tmp_path):
    seen = {}

    def fake_synthesize(text, model, voice, provider=None, speed=None, content_mode=None, phonetic=None):
        seen['text'] = text
        seen['model'] = model
        seen['voice'] = voice
        seen['provider'] = provider
        seen['speed'] = speed
        seen['content_mode'] = content_mode
        seen['phonetic'] = phonetic
        return VALID_MP3

    monkeypatch.setenv('BAILIAN_TTS_PROVIDER', 'azure')
    monkeypatch.setattr(tts, '_cache_dir', lambda: tmp_path)
    monkeypatch.setattr(tts, 'default_cache_identity', lambda: ('azure-rest:audio-24khz-48kbitrate-mono-mp3', 'en-US-AndrewMultilingualNeural'))
    monkeypatch.setattr(tts, 'azure_default_model', lambda: 'azure-rest:audio-24khz-48kbitrate-mono-mp3')
    monkeypatch.setattr(tts, 'azure_sentence_voice', lambda: 'en-US-AndrewMultilingualNeural')
    monkeypatch.setattr(tts, 'synthesize_word_to_bytes', fake_synthesize)

    res = client.post(
        '/api/tts/generate',
        json={'text': 'Hello from route', 'voice_id': 'en-US-AndrewMultilingualNeural', 'speed': 1.2},
    )

    assert res.status_code == 200
    assert res.mimetype == 'audio/mpeg'
    assert res.headers['X-Audio-Bytes'] == str(len(VALID_MP3))
    assert seen == {
        'text': 'Hello from route',
        'model': 'azure-rest:audio-24khz-48kbitrate-mono-mp3',
        'voice': 'en-US-AndrewMultilingualNeural',
        'provider': 'azure',
        'speed': 1.2,
        'content_mode': 'sentence',
        'phonetic': None,
    }


def test_generate_route_supports_volcengine_provider_branch(client, monkeypatch, tmp_path):
    seen = {}

    def fake_synthesize(text, model, voice, provider=None, speed=None):
        seen['text'] = text
        seen['model'] = model
        seen['voice'] = voice
        seen['provider'] = provider
        seen['speed'] = speed
        return VALID_MP3

    monkeypatch.setenv('BAILIAN_TTS_PROVIDER', 'volcengine')
    monkeypatch.setattr(tts, '_cache_dir', lambda: tmp_path)
    monkeypatch.setattr(tts, 'default_cache_identity', lambda: ('seed-tts-2.0', 'zh_female_vv_uranus_bigtts'))
    monkeypatch.setattr(tts, 'synthesize_word_to_bytes', fake_synthesize)

    res = client.post(
        '/api/tts/generate',
        json={
            'text': 'Hello from Volcengine',
            'voice_id': 'custom_voice_id',
            'model': 'seed-tts-2.0',
            'speed': 1.1,
        },
    )

    assert res.status_code == 200
    assert res.mimetype == 'audio/mpeg'
    assert res.headers['X-Audio-Bytes'] == str(len(VALID_MP3))
    assert seen == {
        'text': 'Hello from Volcengine',
        'model': 'seed-tts-2.0',
        'voice': 'custom_voice_id',
        'provider': 'volcengine',
        'speed': 1.1,
    }


def test_generate_route_allows_per_request_minimax_override(client, monkeypatch):
    seen = {}

    def fake_generate(data, **kwargs):
        seen['data'] = data
        seen['voices'] = kwargs['english_voices']
        return b'minimax-audio', 200, {'Content-Type': 'audio/mpeg'}

    monkeypatch.setenv('BAILIAN_TTS_PROVIDER', 'azure')
    monkeypatch.setattr(tts, '_service_generate_speech_response', fake_generate)

    res = client.post(
        '/api/tts/generate',
        json={
            'text': '你好，我是雅思助手。',
            'provider': 'minimax',
            'voice_id': 'female-tianmei',
        },
    )

    assert res.status_code == 200
    assert res.mimetype == 'audio/mpeg'
    assert seen['data']['provider'] == 'minimax'
    assert seen['data']['voice_id'] == 'female-tianmei'
    assert 'female-tianmei' in seen['voices']
