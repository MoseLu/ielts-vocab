# ── Tests for backend/services/word_tts.py ─────────────────────────────────────

import pytest
from pathlib import Path

from services import word_tts


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
            'speech-2.8-hd',
            'English_Trustworthy_Man',
        )

    def test_uses_dashscope_defaults_for_non_minimax(self, monkeypatch):
        monkeypatch.setattr(word_tts, '_TTS_PROVIDER', 'dashscope')
        assert word_tts.default_cache_identity() == (
            word_tts.DEFAULT_MODEL,
            word_tts.DEFAULT_VOICE,
        )


class TestCachedMp3Validation:
    def test_rejects_tiny_payload(self):
        assert not word_tts.is_probably_valid_mp3_bytes(b'ID3')

    def test_accepts_id3_payload(self):
        payload = b'ID3' + (b'\x00' * 800)
        assert word_tts.is_probably_valid_mp3_bytes(payload)
