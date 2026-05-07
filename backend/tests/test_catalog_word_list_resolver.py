from __future__ import annotations

from fastapi.testclient import TestClient
from types import SimpleNamespace

from platform_sdk import catalog_content_word_list_resolver as word_list_resolver

from test_internal_service_auth import (
    CATALOG_CONTENT_SERVICE_PATH,
    _configure_env,
    _create_user,
    _internal_headers,
    _load_module,
)


def _catalog_client(monkeypatch, tmp_path, module_name: str):
    _configure_env(monkeypatch, tmp_path, module_name)
    module = _load_module(module_name, CATALOG_CONTENT_SERVICE_PATH)
    user_id = _create_user(module.catalog_content_flask_app, f'{module_name}-user')
    return TestClient(module.app), _internal_headers(user_id=user_id)


def test_custom_import_rejects_unknown_words_and_word_list_stays_aligned(monkeypatch, tmp_path):
    client, headers = _catalog_client(monkeypatch, tmp_path, 'catalog-word-list-custom')
    create_response = client.post(
        '/internal/catalog/custom-books',
        headers=headers,
        json={
            'title': 'Ordered import',
            'chapters': [{'id': 'main', 'title': 'Main'}],
            'words': [
                {'chapterId': 'main', 'word': 'ability'},
                {'chapterId': 'main', 'word': 'definitely-not-in-ielts'},
                {'chapterId': 'main', 'word': 'academic'},
            ],
        },
    )

    assert create_response.status_code == 201
    created = create_response.json()
    assert [item['word'] for item in created['accepted_words']] == ['ability', 'academic']
    assert created['rejected_words'] == [{
        'input_index': 1,
        'chapter_index': 0,
        'word': 'definitely-not-in-ielts',
        'reason': 'not_found_in_system_vocabulary',
    }]

    book_id = created['bookId']
    word_list_response = client.get(
        f'/api/books/word-list?scope=book&book_id={book_id}',
        headers=headers,
    )

    assert word_list_response.status_code == 200
    payload = word_list_response.json()
    assert [word['word'] for word in payload['words']] == ['ability', 'academic']
    assert [item['word'] for item in payload['dictionary']] == ['ability', 'academic']
    assert payload['total'] == 2
    assert payload['order'] == 'canonical'
    for word, dictionary_entry in zip(payload['words'], payload['dictionary'], strict=True):
        assert word['word_key'] == dictionary_entry['word_key']
        assert word['source_order'] == dictionary_entry['source_order']
        assert str(word['chapter_id']) == str(dictionary_entry['chapter_id'])


def test_custom_wrong_word_book_list_hydrates_paid_listening_metadata(monkeypatch):
    custom_book = SimpleNamespace(id='wrong_words_7')
    listening_confusables = [
        {'word': 'better', 'phonetic': '/betə/', 'pos': 'adj.', 'definition': '更好的'},
        {'word': 'bitter', 'phonetic': '/bɪtə/', 'pos': 'adj.', 'definition': '苦的'},
        {'word': 'butter', 'phonetic': '/bʌtə/', 'pos': 'n.', 'definition': '黄油'},
    ]

    monkeypatch.setattr(word_list_resolver, '_practice_metadata_lookup_cache', None)
    monkeypatch.setattr(word_list_resolver, '_current_user_id', lambda: 7)
    monkeypatch.setattr(word_list_resolver, 'get_vocab_book', lambda book_id: None)
    monkeypatch.setattr(
        word_list_resolver.custom_book_catalog_service,
        'get_custom_book_for_user',
        lambda user_id, book_id: custom_book if book_id == 'wrong_words_7' else None,
    )
    monkeypatch.setattr(
        word_list_resolver.custom_book_catalog_service,
        'serialize_custom_book_summary',
        lambda book: {'id': book.id, 'title': '错词本'},
    )
    monkeypatch.setattr(
        word_list_resolver,
        'load_book_chapters',
        lambda book_id: {
            'chapters': [{'id': 'wrong_words_7_b', 'title': 'B', 'word_count': 1}],
        } if book_id == 'wrong_words_7' else {'chapters': []},
    )

    def fake_load_book_vocabulary(book_id):
        if book_id == 'wrong_words_7':
            return [{'word': 'beta', 'chapter_id': 'wrong_words_7_b', 'definition': 'custom beta'}]
        if book_id == 'ielts_reading_premium':
            return [{
                'word': 'beta',
                'phonetic': '/ˈbiːtə/',
                'pos': 'n.',
                'definition': 'beta source',
                'listening_confusables': listening_confusables,
            }]
        return []

    monkeypatch.setattr(word_list_resolver, 'load_book_vocabulary', fake_load_book_vocabulary)

    payload, status = word_list_resolver.build_word_list_response(
        scope='book',
        book_id='wrong_words_7',
        chapter_id='wrong_words_7_b',
    )

    assert status == 200
    assert payload['words'][0]['word'] == 'beta'
    assert payload['words'][0]['listening_confusables'] == listening_confusables
    assert payload['dictionary'][0]['listening_confusables'] == listening_confusables


def test_custom_book_word_list_returns_more_than_one_hundred_words(monkeypatch, tmp_path):
    client, headers = _catalog_client(monkeypatch, tmp_path, 'catalog-word-list-large')
    create_response = client.post(
        '/internal/catalog/custom-books',
        headers=headers,
        json={
            'title': 'Large import',
            'chapters': [{'id': 'main', 'title': 'Main'}],
            'words': [
                {'chapterId': 'main', 'word': 'ability'}
                for _ in range(105)
            ],
        },
    )
    book_id = create_response.json()['bookId']

    response = client.get(f'/api/books/word-list?scope=book&book_id={book_id}', headers=headers)

    assert response.status_code == 200
    payload = response.json()
    assert len(payload['words']) == 105
    assert len(payload['dictionary']) == 105
    assert [word['source_order'] for word in payload['words']] == list(range(105))


def test_quickmemory_word_list_uses_due_review_queue(monkeypatch, tmp_path):
    monkeypatch.setattr(word_list_resolver, '_current_user_id', lambda: 7)
    monkeypatch.setattr(
        word_list_resolver,
        'load_book_vocabulary',
        lambda book_id: [
            {'word': 'ability', 'chapter_id': '1'},
            {'word': 'academic', 'chapter_id': '2'},
        ] if book_id == 'ielts_reading_premium' else [],
    )

    def fake_review_queue(user_id, args):
        assert user_id == 7
        return {
            'words': [
                {
                    'word': 'academic',
                    'phonetic': '/ac/',
                    'pos': 'adj.',
                    'definition': 'academic def',
                    'book_id': 'ielts_reading_premium',
                    'chapter_id': '2',
                    'nextReview': 1,
                    'dueState': 'due',
                },
                {
                    'word': 'ability',
                    'phonetic': '/a/',
                    'pos': 'n.',
                    'definition': 'ability def',
                    'book_id': 'ielts_reading_premium',
                    'chapter_id': '1',
                    'nextReview': 2,
                    'dueState': 'due',
                },
            ],
            'summary': {'total_count': 2},
        }, 200

    monkeypatch.setattr(
        word_list_resolver,
        'build_quick_memory_review_queue_response',
        fake_review_queue,
        raising=False,
    )

    payload, status = word_list_resolver.build_word_list_response(scope='quickmemory')

    assert status == 200
    assert payload['chapter']['title'] == '艾宾浩斯复习'
    assert [word['word'] for word in payload['words']] == ['ability', 'academic']
    assert payload['dictionary'][0]['word_key'] == payload['words'][0]['word_key']
    assert payload['dictionary'][0]['source_order'] == payload['words'][0]['source_order']
    assert payload['words'][0]['dueState'] == 'due'
    assert payload['words'][0]['source_order'] == 0


def test_wrong_selection_word_list_preserves_selected_order(monkeypatch, tmp_path):
    payload, status = word_list_resolver.build_word_list_response(
        scope='wrong-selection',
        selected_words=['academic', 'ability'],
    )

    assert status == 200
    assert payload['chapter']['title'] == '自选错词本'
    assert [word['word'] for word in payload['words']] == ['academic', 'ability']
    assert [item['source_order'] for item in payload['dictionary']] == [0, 1]
    for word, dictionary_entry in zip(payload['words'], payload['dictionary'], strict=True):
        assert word['word_key'] == dictionary_entry['word_key']
        assert word['source_order'] == dictionary_entry['source_order']


def test_wrong_selection_word_list_falls_back_to_first_wrong_order(monkeypatch, tmp_path):
    monkeypatch.setattr(word_list_resolver, '_current_user_id', lambda: 7)
    monkeypatch.setattr(
        word_list_resolver,
        'build_wrong_words_response',
        lambda user_id, detail_mode=None: ({
            'words': [
                SimpleNamespace(word='ability', phonetic='/a/', pos='n.', definition='ability def'),
                SimpleNamespace(word='academic', phonetic='/ac/', pos='adj.', definition='academic def'),
            ],
        }, 200),
        raising=False,
    )

    payload, status = word_list_resolver.build_word_list_response(scope='wrong-selection')

    assert status == 200
    assert [word['word'] for word in payload['words']] == ['ability', 'academic']
    assert [word['source_order'] for word in payload['words']] == [0, 1]


def test_wrong_selection_word_list_preserves_listening_metadata(monkeypatch, tmp_path):
    listening_confusables = [
        {'word': 'better', 'phonetic': '/betə/', 'pos': 'adj.', 'definition': '更好的'},
        {'word': 'bitter', 'phonetic': '/bɪtə/', 'pos': 'adj.', 'definition': '苦的'},
        {'word': 'butter', 'phonetic': '/bʌtə/', 'pos': 'n.', 'definition': '黄油'},
    ]

    monkeypatch.setattr(word_list_resolver, '_current_user_id', lambda: 7)
    monkeypatch.setattr(word_list_resolver, 'load_book_vocabulary', lambda book_id: [])
    monkeypatch.setattr(
        word_list_resolver,
        'build_wrong_words_response',
        lambda user_id, detail_mode=None: ({
            'words': [{
                'id': 1,
                'word': 'beta',
                'phonetic': '/ˈbiːtə/',
                'pos': 'n.',
                'definition': 'beta source',
                'listening_confusables': listening_confusables,
            }],
        }, 200),
        raising=False,
    )

    payload, status = word_list_resolver.build_word_list_response(scope='wrong-selection')

    assert status == 200
    assert payload['words'][0]['listening_confusables'] == listening_confusables
    assert payload['dictionary'][0]['listening_confusables'] == listening_confusables
