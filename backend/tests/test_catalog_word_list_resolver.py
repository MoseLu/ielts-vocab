from __future__ import annotations

from fastapi.testclient import TestClient

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
