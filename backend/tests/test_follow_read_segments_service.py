import services.books_catalog_query_service as books_catalog_query_service
import re
from services.follow_read_segments_manifest_service import (
    load_follow_read_sidecar_entries,
    load_follow_read_source_words,
)
from services.follow_read_segments_service import (
    build_follow_read_entry_key,
    generate_auto_follow_read_segments,
    reset_follow_read_segment_caches,
    supported_follow_read_book_ids,
)
from services.follow_read_timeline_service import _follow_read_chunk_cache_path
from services.word_tts import normalize_word_key


def test_generate_auto_follow_read_segments_for_forced_monosyllables():
    assert [segment['letters'] for segment in generate_auto_follow_read_segments('food', '/fuːd/')] == ['f', 'ood']
    assert [segment['letters'] for segment in generate_auto_follow_read_segments('brain', '/breɪn/')] == ['br', 'ain']
    assert [segment['letters'] for segment in generate_auto_follow_read_segments('source', '/sɔːs/')] == ['s', 'ource']
    assert [segment['letters'] for segment in generate_auto_follow_read_segments('science', '/ˈsaɪəns/')] == ['sci', 'ence']


def test_follow_read_cache_key_changes_when_fallback_text_changes():
    segments_a = [{'letters': 'sci', 'audio_phonetic': 'saɪ', 'fallback_text': 'sigh'}]
    segments_b = [{'letters': 'sci', 'audio_phonetic': 'saɪ', 'fallback_text': 'sci'}]

    assert _follow_read_chunk_cache_path('science', '/ˈsaɪəns/', segments_a) != _follow_read_chunk_cache_path(
        'science',
        '/ˈsaɪəns/',
        segments_b,
    )


def test_generated_premium_sidecars_cover_all_source_words():
    for book_id in supported_follow_read_book_ids():
        entries = load_follow_read_sidecar_entries(book_id)
        assert entries
        for source_word in load_follow_read_source_words(book_id):
            key = build_follow_read_entry_key(source_word['word'], source_word['phonetic'])
            assert key in entries
            segments = entries[key]['segments']
            assert len(segments) >= 2
            joined_letters = re.sub(r'[^a-z0-9]+', '', ''.join(segment['letters'] for segment in segments).lower())
            expected_word = re.sub(r'[^a-z0-9]+', '', normalize_word_key(source_word['word']))
            assert joined_letters == expected_word
            assert all(str(segment.get('letters') or '').strip() for segment in segments)
            assert all(str(segment.get('phonetic') or '').strip() for segment in segments)
            assert all(str(segment.get('audio_phonetic') or '').strip() for segment in segments)


def test_load_book_vocabulary_attaches_follow_read_segments_for_premium_books(monkeypatch):
    reset_follow_read_segment_caches()
    books_catalog_query_service.books_vocabulary_loader_service._vocabulary_cache.clear()
    monkeypatch.setattr(books_catalog_query_service, '_hydrate_missing_phonetics', lambda words: words)

    words = books_catalog_query_service.load_book_vocabulary('ielts_listening_premium')

    art_entry = next(word for word in words if word['word'] == 'art')
    assert [segment['letters'] for segment in art_entry['follow_read_segments']] == ['a', 'rt']

    books_catalog_query_service.books_vocabulary_loader_service._vocabulary_cache.clear()
