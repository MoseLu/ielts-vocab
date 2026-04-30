from __future__ import annotations

from services import books_progress_service


def test_monolith_chapter_words_delegates_to_word_list_resolver(monkeypatch):
    calls = []

    def fake_word_list_response(**kwargs):
        calls.append(kwargs)
        return {
            'chapter': {'id': '1', 'title': 'Chapter 1'},
            'words': [{'word': 'alpha', 'word_key': 'alpha', 'source_order': 0, 'chapter_id': '1'}],
        }, 200

    monkeypatch.setattr(
        books_progress_service,
        '_build_catalog_word_list_response',
        fake_word_list_response,
        raising=False,
    )

    payload, status = books_progress_service.build_chapter_words_response('book-a', '1')

    assert status == 200
    assert payload['words'][0]['word'] == 'alpha'
    assert calls == [{'scope': 'book', 'book_id': 'book-a', 'chapter_id': '1'}]


def test_monolith_book_words_delegates_to_word_list_resolver(monkeypatch):
    calls = []

    def fake_word_list_response(**kwargs):
        calls.append(kwargs)
        return {
            'words': [
                {'word': 'alpha', 'word_key': 'alpha', 'source_order': 0, 'chapter_id': '1'},
                {'word': 'beta', 'word_key': 'beta', 'source_order': 1, 'chapter_id': '1'},
            ],
        }, 200

    monkeypatch.setattr(
        books_progress_service,
        '_build_catalog_word_list_response',
        fake_word_list_response,
        raising=False,
    )

    payload, status = books_progress_service.build_book_words_response('book-a', page=1, per_page=1)

    assert status == 200
    assert [word['word'] for word in payload['words']] == ['alpha']
    assert payload['total'] == 2
    assert calls == [{'scope': 'book', 'book_id': 'book-a'}]
