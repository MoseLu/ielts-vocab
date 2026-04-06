# ── Tests for backend/services/word_tts.py ─────────────────────────────────────

import base64
import pytest
from pathlib import Path
import requests

from services import word_tts

VALID_MP3 = b'ID3' + (b'\x00' * 800)
VALID_WAV = b'RIFF' + (b'\x00' * 4) + b'WAVEfmt ' + (b'\x00' * 32)


class TestNormalizeWordKey:
    def test_strips_and_lowercases(self):
        assert word_tts.normalize_word_key('  Hello  ') == 'hello'

    def test_empty(self):
        assert word_tts.normalize_word_key('') == ''


class TestWordTtsCachePath:
    def test_same_inputs_same_filename(self):
        p1 = word_tts.word_tts_cache_path(
            Path('/tmp'), 'hello', 'cosyvoice-v3-flash', 'longanyang'
        )
        p2 = word_tts.word_tts_cache_path(
            Path('/tmp'), 'hello', 'cosyvoice-v3-flash', 'longanyang'
        )
        assert p1 == p2
        assert p1.suffix == '.mp3'
        assert len(p1.stem) == 16

    def test_different_word_different_file(self):
        a = word_tts.word_tts_cache_path(
            Path('/x'), 'hello', 'm', 'v'
        )
        b = word_tts.word_tts_cache_path(
            Path('/x'), 'world', 'm', 'v'
        )
        assert a != b


class TestCollectUniqueWords:
    def test_dedupes_case_insensitive(self, monkeypatch):
        def fake_load(book_id):
            if book_id == 'b1':
                return [
                    {'word': 'Hello'},
                    {'word': 'hello'},
                    {'word': 'World'},
                ]
            return []

        monkeypatch.setattr(
            'routes.books.load_book_vocabulary',
            fake_load,
        )
        monkeypatch.setattr(
            'routes.books.VOCAB_BOOKS',
            [{'id': 'b1', 'file': 'x.json'}],
        )

        words = word_tts.collect_unique_words(book_ids=['b1'])
        assert len(words) == 2
        assert {w.lower() for w in words} == {'hello', 'world'}


class TestDefaultCacheIdentity:
    def test_uses_minimax_cache_identity_when_provider_is_minimax(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'minimax')
        assert word_tts.default_cache_identity() == (
            word_tts._MINIMAX_DEFAULT_MODEL,
            'English_Trustworthy_Man',
        )

    def test_uses_dashscope_defaults_for_non_minimax(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        assert word_tts.default_cache_identity() == (
            word_tts.DEFAULT_MODEL,
            word_tts.DEFAULT_VOICE,
        )


class TestDefaultWordTtsIdentity:
    def test_defaults_word_audio_to_tts_with_versioned_cache_identity(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, 'WORD_TTS_PROVIDER', '')
        monkeypatch.setattr(word_tts, '_MINIMAX_API_KEYS', ['primary-key'])
        monkeypatch.setattr(word_tts, 'WORD_TTS_MODEL', '')
        monkeypatch.setattr(word_tts, 'WORD_TTS_VOICE', '')
        monkeypatch.setattr(word_tts, '_MINIMAX_VOICE', 'English_Trustworthy_Man')

        assert word_tts.default_word_tts_identity() == (
            'minimax',
            f'{word_tts._MINIMAX_DEFAULT_MODEL}@{word_tts._WORD_TTS_STRATEGY_TAG}',
            'English_Trustworthy_Man',
        )

    def test_explicit_hybrid_override_keeps_dictionary_first_strategy(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, 'WORD_TTS_PROVIDER', 'hybrid')
        monkeypatch.setattr(word_tts, '_MINIMAX_API_KEYS', ['primary-key'])
        monkeypatch.setattr(word_tts, 'WORD_TTS_MODEL', '')
        monkeypatch.setattr(word_tts, 'WORD_TTS_VOICE', '')
        monkeypatch.setattr(word_tts, '_MINIMAX_VOICE', 'English_Trustworthy_Man')

        assert word_tts.default_word_tts_identity() == (
            'hybrid',
            f'{word_tts._MINIMAX_DEFAULT_MODEL}@{word_tts._WORD_TTS_STRATEGY_TAG}',
            'English_Trustworthy_Man',
        )

    def test_explicit_word_provider_can_stay_on_dashscope(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, 'WORD_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, 'WORD_TTS_MODEL', 'qwen-tts-2025-05-22')
        monkeypatch.setattr(word_tts, 'WORD_TTS_VOICE', 'Cherry')

        assert word_tts.default_word_tts_identity() == (
            'dashscope',
            f'qwen-tts-2025-05-22@{word_tts._WORD_TTS_STRATEGY_TAG}',
            'Cherry',
        )


class TestBatchRateRecommendations:
    def test_qwen_rest_model_gets_safe_default_interval(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, 'MODELS', [word_tts.DEFAULT_MODEL])
        assert word_tts.recommended_batch_rate_interval('qwen-tts-2025-05-22') == 7.0

    def test_non_qwen_models_default_to_no_extra_interval(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, 'MODELS', [word_tts.DEFAULT_MODEL])
        assert word_tts.recommended_batch_rate_interval('sambert-cindy-v1') == 0.0

    def test_rate_limited_models_get_longer_backoff(self, monkeypatch):
        monkeypatch.setattr(word_tts, 'MODELS', [word_tts.DEFAULT_MODEL])
        assert word_tts.recommended_batch_backoff_delays(7.0) == (21.0, 42.0, 63.0)

    def test_generation_pool_disables_global_interval(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, 'DEFAULT_MODEL', 'qwen-tts-2025-05-22')
        monkeypatch.setattr(
            word_tts,
            'MODELS',
            ['qwen3-tts-flash-2025-11-27', 'qwen-tts-2025-05-22'],
        )
        assert word_tts.recommended_batch_rate_interval('qwen-tts-2025-05-22') == 0.0

    def test_generation_pool_raises_recommended_concurrency(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, 'DEFAULT_MODEL', 'qwen-tts-2025-05-22')
        monkeypatch.setattr(
            word_tts,
            'MODELS',
            ['qwen3-tts-flash-2025-11-27', 'qwen3-tts-instruct-flash', 'qwen-tts'],
        )
        assert word_tts.recommended_batch_concurrency('qwen-tts-2025-05-22') == 8

    def test_minimax_word_provider_never_uses_dashscope_generation_pool(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, 'DEFAULT_MODEL', 'qwen-tts-2025-05-22')
        monkeypatch.setattr(
            word_tts,
            'MODELS',
            ['qwen3-tts-flash-2025-11-27', 'qwen-tts-2025-05-22'],
        )

        assert not word_tts._should_use_generation_pool('qwen-tts-2025-05-22', provider='minimax')
        assert word_tts.recommended_batch_concurrency('qwen-tts-2025-05-22', provider='minimax') == 16
        assert not word_tts._should_use_generation_pool('qwen-tts-2025-05-22', provider='hybrid')


class TestCachedMp3Validation:
    def test_rejects_tiny_payload(self):
        assert not word_tts.is_probably_valid_mp3_bytes(b'ID3')

    def test_accepts_id3_payload(self):
        assert word_tts.is_probably_valid_mp3_bytes(VALID_MP3)

    def test_prepends_leading_silence_for_word_audio(self, monkeypatch):
        import imageio_ffmpeg

        seen = {}

        class FakeResult:
            returncode = 0
            stderr = b''
            stdout = VALID_MP3

        def fake_run(command, **kwargs):
            seen['command'] = command
            seen['input'] = kwargs['input']
            return FakeResult()

        monkeypatch.setattr(imageio_ffmpeg, 'get_ffmpeg_exe', lambda: 'ffmpeg')
        monkeypatch.setattr(word_tts.subprocess, 'run', fake_run)

        audio = word_tts.add_leading_silence_to_mp3_bytes(VALID_MP3)

        assert audio == VALID_MP3
        assert seen['input'] == VALID_MP3
        assert f'adelay={word_tts._WORD_TTS_LEADING_SILENCE_MS}:all=1' in seen['command']


class TestDashScopeAudioNormalization:
    def test_transcodes_wave_payloads_to_mp3(self, monkeypatch):
        seen = {}

        def fake_transcode(audio):
            seen['audio'] = audio
            return VALID_MP3

        monkeypatch.setattr(word_tts, 'transcode_wav_to_mp3_bytes', fake_transcode)

        assert word_tts.ensure_mp3_bytes(VALID_WAV) == VALID_MP3
        assert seen['audio'] == VALID_WAV

    def test_qwen_tts_normalizes_wave_payloads(self, monkeypatch):
        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {
                    'output': {
                        'audio': {
                            'data': base64.b64encode(VALID_WAV).decode('ascii'),
                        },
                    },
                }

        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, '_get_api_key', lambda: 'test-key')
        monkeypatch.setattr(word_tts, 'transcode_wav_to_mp3_bytes', lambda audio: VALID_MP3)
        monkeypatch.setattr(requests, 'post', lambda *args, **kwargs: FakeResponse())

        audio = word_tts.synthesize_word_to_bytes('hello', 'qwen-tts-2025-05-22', 'Cherry')

        assert audio == VALID_MP3

    def test_default_cache_model_can_dispatch_through_generation_pool(self, monkeypatch):
        seen = {}

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {
                    'output': {
                        'audio': {
                            'data': base64.b64encode(VALID_MP3).decode('ascii'),
                        },
                    },
                }

        def fake_post(url, headers=None, json=None, timeout=None):
            seen['model'] = json['model']
            return FakeResponse()

        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, 'DEFAULT_MODEL', 'qwen-tts-2025-05-22')
        monkeypatch.setattr(
            word_tts,
            'MODELS',
            ['qwen3-tts-flash-2025-11-27', 'qwen-tts-2025-05-22'],
        )
        monkeypatch.setattr(word_tts, '_get_api_key', lambda: 'test-key')
        monkeypatch.setattr(word_tts._MODEL_SCHEDULER, 'acquire', lambda models: 'qwen3-tts-flash-2025-11-27')
        monkeypatch.setattr(requests, 'post', fake_post)

        audio = word_tts.synthesize_word_to_bytes('hello', 'qwen-tts-2025-05-22', 'Cherry')

        assert audio == VALID_MP3
        assert seen['model'] == 'qwen3-tts-flash-2025-11-27'

    def test_provider_override_can_force_minimax_even_when_global_provider_is_dashscope(self, monkeypatch):
        seen = {}

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {
                    'base_resp': {'status_code': 0},
                    'data': {'audio': ('494433' + ('00' * 800))},
                }

        def fake_post(url, headers=None, json=None, timeout=None):
            seen['model'] = json['model']
            seen['voice_id'] = json['voice_setting']['voice_id']
            return FakeResponse()

        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(
            word_tts,
            '_get_minimax_key_with_sem',
            lambda: ('fake-key', type('Sem', (), {'release': lambda self: None})(), type('Sem', (), {'release': lambda self: None})(), 'English_Trustworthy_Man'),
        )
        monkeypatch.setattr(requests, 'post', fake_post)

        audio = word_tts.synthesize_word_to_bytes(
            'community',
            word_tts._MINIMAX_DEFAULT_MODEL,
            'English_Trustworthy_Man',
            provider='minimax',
        )

        assert audio == VALID_MP3
        assert seen['model'] == word_tts._MINIMAX_DEFAULT_MODEL
        assert seen['voice_id'] == 'English_Trustworthy_Man'

    def test_hybrid_provider_uses_dictionary_audio_before_tts(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, 'fetch_dictionary_word_audio_bytes', lambda text: VALID_MP3)

        audio = word_tts.synthesize_word_to_bytes(
            'subjects',
            f'{word_tts._MINIMAX_DEFAULT_MODEL}@{word_tts._WORD_TTS_STRATEGY_TAG}',
            'English_Trustworthy_Man',
            provider='hybrid',
        )

        assert audio == VALID_MP3

    def test_hybrid_provider_falls_back_to_minimax_when_dictionary_audio_missing(self, monkeypatch):
        seen = {}

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {
                    'base_resp': {'status_code': 0},
                    'data': {'audio': ('494433' + ('00' * 800))},
                }

        def fake_post(url, headers=None, json=None, timeout=None):
            seen['model'] = json['model']
            seen['voice_id'] = json['voice_setting']['voice_id']
            return FakeResponse()

        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        monkeypatch.setattr(word_tts, '_MINIMAX_API_KEYS', ['primary-key'])
        monkeypatch.setattr(word_tts, 'fetch_dictionary_word_audio_bytes', lambda text: None)
        monkeypatch.setattr(
            word_tts,
            '_get_minimax_key_with_sem',
            lambda: ('fake-key', type('Sem', (), {'release': lambda self: None})(), type('Sem', (), {'release': lambda self: None})(), 'English_Trustworthy_Man'),
        )
        monkeypatch.setattr(requests, 'post', fake_post)

        audio = word_tts.synthesize_word_to_bytes(
            'subjects',
            f'{word_tts._MINIMAX_DEFAULT_MODEL}@{word_tts._WORD_TTS_STRATEGY_TAG}',
            'English_Trustworthy_Man',
            provider='hybrid',
        )

        assert audio == VALID_MP3
        assert seen['model'] == word_tts._MINIMAX_DEFAULT_MODEL
        assert seen['voice_id'] == 'English_Trustworthy_Man'


class TestDictionaryAudioLookup:
    def test_prefers_dictionaryapi_audio_when_available(self, monkeypatch):
        class FakeJsonResponse:
            def __init__(self, payload):
                self.ok = True
                self._payload = payload

            def json(self):
                return self._payload

        class FakeAudioResponse:
            def __init__(self, content):
                self.ok = True
                self.content = content

        def fake_get(url, timeout=None):
            if 'dictionaryapi.dev/api/v2/entries/en/community' in url:
                return FakeJsonResponse([
                    {'phonetics': [{'audio': 'https://audio.example/community.mp3'}]},
                ])
            if url == 'https://audio.example/community.mp3':
                return FakeAudioResponse(VALID_MP3)
            raise AssertionError(f'unexpected url: {url}')

        monkeypatch.setattr(requests, 'get', fake_get)

        assert word_tts.fetch_dictionary_word_audio_bytes('community') == VALID_MP3

    def test_falls_back_to_youdao_when_dictionaryapi_has_no_audio(self, monkeypatch):
        class FakeJsonResponse:
            ok = True

            @staticmethod
            def json():
                return [{'phonetics': []}]

        class FakeAudioResponse:
            def __init__(self, content):
                self.ok = True
                self.content = content

        def fake_get(url, timeout=None):
            if 'dictionaryapi.dev/api/v2/entries/en/subjects' in url:
                return FakeJsonResponse()
            if 'dict.youdao.com/dictvoice' in url:
                return FakeAudioResponse(VALID_MP3)
            raise AssertionError(f'unexpected url: {url}')

        monkeypatch.setattr(requests, 'get', fake_get)

        assert word_tts.fetch_dictionary_word_audio_bytes('subjects') == VALID_MP3


class TestMiniMaxSemaphoreRelease:
    def test_releases_semaphores_after_success(self, monkeypatch):
        class FakeSemaphore:
            def __init__(self):
                self.release_count = 0

            def release(self):
                self.release_count += 1

        class FakeResponse:
            status_code = 200

            @staticmethod
            def json():
                return {
                    'base_resp': {'status_code': 0},
                    'data': {'audio': ('494433' + ('00' * 800))},
                }

        per_key_sem = FakeSemaphore()
        global_sem = FakeSemaphore()

        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'minimax')
        monkeypatch.setattr(
            word_tts,
            '_get_minimax_key_with_sem',
            lambda: ('fake-key', per_key_sem, global_sem, 'English_Trustworthy_Man'),
        )
        monkeypatch.setattr(requests, 'post', lambda *args, **kwargs: FakeResponse())

        audio = word_tts.synthesize_word_to_bytes('hello', 'speech-2.8-hd', 'English_Trustworthy_Man')

        assert audio.startswith(b'ID3')
        assert per_key_sem.release_count == 1
        assert global_sem.release_count == 1
