import requests

from services import word_tts


VALID_MP3 = b'ID3' + (b'\x00' * 800)


def test_default_cache_identity_uses_azure_defaults(monkeypatch):
    monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'azure')
    monkeypatch.setattr(word_tts, '_AZURE_DEFAULT_MODEL', 'azure-rest:audio-24khz-48kbitrate-mono-mp3')
    monkeypatch.setattr(word_tts, '_AZURE_DEFAULT_VOICE', 'en-US-AndrewMultilingualNeural')
    monkeypatch.setenv('AZURE_TTS_SENTENCE_VOICE', 'en-US-AndrewMultilingualNeural')

    assert word_tts.default_cache_identity() == (
        'azure-rest:audio-24khz-48kbitrate-mono-mp3@azure-sentence-v4-ielts-rp-female',
        'en-US-AndrewMultilingualNeural',
    )


def test_default_word_identity_prefers_azure_when_global_provider_is_azure(monkeypatch):
    monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'azure')
    monkeypatch.setattr(word_tts, 'WORD_TTS_PROVIDER', '')
    monkeypatch.setattr(word_tts, '_MINIMAX_API_KEYS', ['primary-key'])
    monkeypatch.setattr(word_tts, 'WORD_TTS_MODEL', '')
    monkeypatch.setattr(word_tts, 'WORD_TTS_VOICE', '')
    monkeypatch.setattr(word_tts, '_AZURE_DEFAULT_MODEL', 'azure-rest:audio-24khz-48kbitrate-mono-mp3')
    monkeypatch.setattr(word_tts, '_AZURE_DEFAULT_VOICE', 'en-US-AndrewMultilingualNeural')
    monkeypatch.setenv('AZURE_TTS_WORD_VOICE', 'en-US-AndrewMultilingualNeural')

    assert word_tts.default_word_tts_identity() == (
        'azure',
        'azure-rest:audio-24khz-48kbitrate-mono-mp3@azure-word-v5-ielts-rp-female-onset-buffer',
        'en-US-AndrewMultilingualNeural',
    )


def test_build_azure_ssml_uses_word_profile_and_lookup_phonetic(monkeypatch):
    monkeypatch.setattr(word_tts, '_AZURE_WORD_PRONUNCIATION_LOOKUP', {'economy': 'ɪˈkɒnəmi'})
    monkeypatch.setenv('AZURE_TTS_WORD_PITCH', '')
    monkeypatch.setenv('AZURE_TTS_WORD_LEADING_BREAK_MS', '100')
    monkeypatch.setenv('AZURE_TTS_WORD_TRAILING_BREAK_MS', '')
    monkeypatch.setenv('AZURE_TTS_WORD_AUDIO_DURATION_MS', '')

    ssml = word_tts.build_azure_ssml(
        'economy',
        'en-GB-RyanNeural',
        content_mode='word',
    )

    assert "phoneme alphabet='ipa' ph='ɪˈkɒnəmi'" in ssml
    assert "rate='-6.00%'" in ssml
    assert 'pitch=' not in ssml
    assert "<break time='100ms'/>" in ssml
    assert 'xmlns:mstts' not in ssml
    assert 'mstts:audioduration' not in ssml


def test_normalize_azure_ipa_converts_ascii_stress_marks():
    assert word_tts.normalize_azure_ipa("/'bʊklɪsts/") == 'ˈbʊklɪsts'


def test_azure_provider_uses_rest_ssml_endpoint(monkeypatch):
    seen = {}

    class FakeResponse:
        status_code = 200
        content = VALID_MP3
        text = ''

    def fake_post(url, headers=None, data=None, timeout=None):
        seen['url'] = url
        seen['headers'] = headers
        seen['data'] = data
        return FakeResponse()

    monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'azure')
    monkeypatch.setattr(word_tts, '_AZURE_SPEECH_KEY', 'test-key')
    monkeypatch.setattr(word_tts, '_AZURE_SPEECH_REGION', 'eastus')
    monkeypatch.setattr(word_tts, '_AZURE_DEFAULT_VOICE', 'en-US-AndrewMultilingualNeural')
    monkeypatch.setenv('AZURE_TTS_SENTENCE_VOICE', 'en-US-AndrewMultilingualNeural')
    monkeypatch.setattr(requests, 'post', fake_post)

    audio = word_tts.synthesize_word_to_bytes('Hello <world>', provider='azure')

    assert audio == VALID_MP3
    assert seen['url'] == 'https://eastus.tts.speech.microsoft.com/cognitiveservices/v1'
    assert seen['headers']['X-Microsoft-OutputFormat'] == word_tts.azure_output_format()
    assert 'en-US-AndrewMultilingualNeural' in seen['data']
    assert 'Hello &lt;world&gt;' in seen['data']
    assert "rate='-2.00%'" in seen['data']


def test_azure_word_400_with_phoneme_retries_without_phoneme(monkeypatch):
    seen = {'payloads': []}

    class FakeResponse:
        def __init__(self, status_code, content=b'', text=''):
            self.status_code = status_code
            self.content = content
            self.text = text

    def fake_post(url, headers=None, data=None, timeout=None):
        seen['payloads'].append(data)
        if len(seen['payloads']) == 1:
            return FakeResponse(400, text='bad phoneme')
        return FakeResponse(200, content=VALID_MP3)

    monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'azure')
    monkeypatch.setattr(word_tts, '_AZURE_SPEECH_KEY', 'test-key')
    monkeypatch.setattr(word_tts, '_AZURE_SPEECH_REGION', 'eastus')
    monkeypatch.setenv('AZURE_TTS_WORD_VOICE', 'en-GB-LibbyNeural')
    monkeypatch.setattr(word_tts, '_AZURE_WORD_PRONUNCIATION_LOOKUP', {'booklists': 'ˈbʊklɪsts'})
    monkeypatch.setattr(requests, 'post', fake_post)

    audio = word_tts.synthesize_word_to_bytes('booklists', provider='azure', content_mode='word')

    assert audio == VALID_MP3
    assert len(seen['payloads']) == 2
    assert "<phoneme alphabet='ipa'" in seen['payloads'][0]
    assert "<phoneme alphabet='ipa'" not in seen['payloads'][1]
