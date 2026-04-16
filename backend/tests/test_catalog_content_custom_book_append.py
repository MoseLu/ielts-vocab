from fastapi.testclient import TestClient

from test_internal_service_auth import (
    CATALOG_CONTENT_SERVICE_PATH,
    _configure_env,
    _create_user,
    _internal_headers,
    _load_module,
)


def test_catalog_content_internal_custom_book_append_creates_new_chapters(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'catalog-content-custom-book-append')
    module = _load_module('catalog_content_custom_book_append', CATALOG_CONTENT_SERVICE_PATH)
    user_id = _create_user(module.catalog_content_flask_app, 'catalog-content-custom-book-append-user')
    client = TestClient(module.app)
    headers = _internal_headers(user_id=user_id)

    create_response = client.post(
        '/internal/catalog/custom-books',
        headers=headers,
        json={
            'title': 'Band 7',
            'description': 'desc',
            'education_stage': 'abroad',
            'exam_type': 'ielts',
            'ielts_skill': 'listening',
            'share_enabled': True,
            'chapter_word_target': 30,
            'chapters': [{'id': 'ch1', 'title': 'One', 'wordCount': 1}],
            'words': [{
                'chapterId': 'ch1',
                'word': 'abandon',
                'phonetic': '/əˈbændən/',
                'pos': 'v.',
                'definition': '放弃',
            }],
        },
    )
    created_book_id = create_response.json()['bookId']

    append_response = client.post(
        f'/internal/catalog/custom-books/{created_book_id}/chapters',
        headers=headers,
        json={
            'chapters': [{'id': 'ch2', 'title': 'Two', 'wordCount': 1}],
            'words': [{
                'chapterId': 'ch2',
                'word': 'ability',
                'phonetic': '/əˈbɪləti/',
                'pos': 'n.',
                'definition': '能力',
            }],
        },
    )
    get_response = client.get(f'/internal/catalog/custom-books/{created_book_id}', headers=headers)
    chapters_response = client.get(f'/api/books/{created_book_id}/chapters', headers=headers)

    assert create_response.status_code == 201
    assert append_response.status_code == 201
    assert append_response.json()['created_count'] == 1
    assert append_response.json()['created_chapters'][0]['id'] == f'{created_book_id}_2'
    assert get_response.status_code == 200
    assert len(get_response.json()['chapters']) == 2
    assert get_response.json()['word_count'] == 2
    assert chapters_response.status_code == 200
    assert chapters_response.json()['chapters'][0]['id'] == f'{created_book_id}_1'
    assert chapters_response.json()['chapters'][1]['id'] == f'{created_book_id}_2'
