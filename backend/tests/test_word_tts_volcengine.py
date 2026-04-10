import base64
import requests

from services import word_tts


VALID_MP3 = b'ID3' + (b'\x00' * 800)


class TestVolcengineDefaults:
    def test_global_volcengine_provider_overrides_minimax_fallback(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'volcengine')
        monkeypatch.setattr(word_tts, '_MINIMAX_API_KEYS', ['primary-key'])
        monkeypatch.setattr(word_tts, 'WORD_TTS_PROVIDER', '')
        monkeypatch.setattr(word_tts, 'WORD_TTS_MODEL', '')
        monkeypatch.setattr(word_tts, 'WORD_TTS_VOICE', '')
        monkeypatch.setattr(word_tts, 'volcengine_default_model', lambda: 'seed-tts-2.0')
        monkeypatch.setattr(word_tts, 'volcengine_default_voice', lambda: 'zh_female_vv_uranus_bigtts')

        assert word_tts.default_word_tts_identity() == (
            'volcengine',
            f'seed-tts-2.0@{word_tts._WORD_TTS_STRATEGY_TAG}',
            'zh_female_vv_uranus_bigtts',
        )


class TestVolcengineSynthesis:
    def test_synthesize_word_to_bytes_parses_sse_audio_chunks(self, monkeypatch):
        seen = {}

        class FakeResponse:
            status_code = 200
            text = ''

            def iter_lines(self, decode_unicode=False):
                payload = base64.b64encode(VALID_MP3).decode('ascii')
                lines = [
                    'event: message',
                    f'data: {{"code":0,"message":"","sequence":1,"data":"{payload}"}}',
                    'data: {"code":20000000,"message":"Success","sequence":-1,"addition":{"usage":{"text_words":1}}}',
                ]
                for line in lines:
                    yield line if decode_unicode else line.encode('utf-8')

            def close(self):
                seen['closed'] = True

        def fake_post(url, headers=None, json=None, stream=None, timeout=None):
            seen['url'] = url
            seen['headers'] = headers
            seen['json'] = json
            seen['stream'] = stream
            seen['timeout'] = timeout
            return FakeResponse()

        monkeypatch.setenv('VOLCENGINE_TTS_APP_ID', 'app-id')
        monkeypatch.setenv('VOLCENGINE_TTS_ACCESS_KEY', 'access-key')
        monkeypatch.setenv('VOLCENGINE_TTS_RESOURCE_ID', 'seed-tts-2.0')
        monkeypatch.setenv('VOLCENGINE_TTS_VOICE', 'zh_female_vv_uranus_bigtts')
        monkeypatch.setenv('VOLCENGINE_TTS_EXPLICIT_LANGUAGE', 'en')
        monkeypatch.setattr(requests, 'post', fake_post)

        audio = word_tts.synthesize_word_to_bytes(
            'hello world',
            'seed-tts-2.0',
            'zh_female_vv_uranus_bigtts',
            provider='volcengine',
            speed=1.15,
        )

        assert audio == VALID_MP3
        assert seen['url'] == 'https://openspeech.bytedance.com/api/v3/tts/unidirectional/sse'
        assert seen['headers']['X-Api-App-Id'] == 'app-id'
        assert seen['headers']['X-Api-Access-Key'] == 'access-key'
        assert seen['headers']['X-Api-Resource-Id'] == 'seed-tts-2.0'
        assert seen['headers']['Accept'] == 'text/event-stream'
        assert seen['stream'] is True
        assert seen['timeout'] == (10, 60)
        assert seen['json'] == {
            'user': {'uid': 'ielts-vocab'},
            'req_params': {
                'text': 'hello world',
                'speaker': 'zh_female_vv_uranus_bigtts',
                'audio_params': {
                    'format': 'mp3',
                    'sample_rate': 24000,
                    'speed_ratio': 1.15,
                },
                'additions': '{"explicit_language": "en"}',
            },
        }
        assert seen['closed'] is True
