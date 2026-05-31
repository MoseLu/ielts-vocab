from routes import tts
from services import phonetic_lookup_service, word_tts


VALID_MP3 = b'ID3' + (b'\x00' * 800)


def test_word_audio_uses_explicit_phonetic_override_cache_identity(client, monkeypatch, tmp_path):
    seen = {'models': []}
    original_cache_path = word_tts.word_tts_cache_path

    monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
    monkeypatch.setattr(
        tts,
        '_resolve_normal_word_audio_identity',
        lambda: (
            'azure',
            'azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer',
            'en-GB-LibbyNeural',
        ),
    )
    monkeypatch.setattr(
        phonetic_lookup_service,
        'load_phonetic_overrides',
        lambda: {'record': '/rɪˈkɔːd/'},
    )
    monkeypatch.setattr('services.word_tts_oss.resolve_word_audio_oss_metadata', lambda **kwargs: None)

    def fake_cache_path(cache_dir, normalized_key, model, voice):
        seen['models'].append(model)
        return original_cache_path(cache_dir, normalized_key, model, voice)

    def fake_synthesize(text, model, voice, provider=None, content_mode=None, phonetic=None):
        seen['synthesize'] = {
            'text': text,
            'model': model,
            'voice': voice,
            'provider': provider,
            'content_mode': content_mode,
            'phonetic': phonetic,
        }
        return VALID_MP3

    monkeypatch.setattr('services.word_tts.word_tts_cache_path', fake_cache_path)
    monkeypatch.setattr('services.word_tts.synthesize_word_to_bytes', fake_synthesize)

    res = client.get('/api/tts/word-audio?w=record')

    assert res.status_code == 200
    assert seen['synthesize'] == {
        'text': 'record',
        'model': 'azure-rest:test',
        'voice': 'en-GB-LibbyNeural',
        'provider': 'azure',
        'content_mode': 'word',
        'phonetic': '/rɪˈkɔːd/',
    }
    assert any('@ipa-' in model for model in seen['models'])


def test_word_audio_skips_uncertain_optional_phonetic_for_tts(client, monkeypatch, tmp_path):
    seen = {'models': []}
    original_cache_path = word_tts.word_tts_cache_path

    monkeypatch.setattr(tts, '_word_tts_dir', lambda: tmp_path)
    monkeypatch.setattr(
        tts,
        '_resolve_normal_word_audio_identity',
        lambda: (
            'azure',
            'azure-rest:test@azure-word-v6-ielts-rp-female-onset-buffer',
            'en-GB-LibbyNeural',
        ),
    )
    monkeypatch.setattr(
        phonetic_lookup_service,
        'load_phonetic_overrides',
        lambda: {'transaction': '/trænˈzækʃ(ə)n/'},
    )
    monkeypatch.setattr('services.word_tts_oss.resolve_word_audio_oss_metadata', lambda **kwargs: None)

    def fake_cache_path(cache_dir, normalized_key, model, voice):
        seen['models'].append(model)
        return original_cache_path(cache_dir, normalized_key, model, voice)

    def fake_synthesize(text, model, voice, provider=None, content_mode=None, phonetic=None):
        seen['phonetic'] = phonetic
        return VALID_MP3

    monkeypatch.setattr('services.word_tts.word_tts_cache_path', fake_cache_path)
    monkeypatch.setattr('services.word_tts.synthesize_word_to_bytes', fake_synthesize)

    res = client.get('/api/tts/word-audio?w=transaction')

    assert res.status_code == 200
    assert seen['phonetic'] is None
    assert any('@ipa-review-' in model for model in seen['models'])
