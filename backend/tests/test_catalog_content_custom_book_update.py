from fastapi.testclient import TestClient

from test_internal_service_auth import (
    CATALOG_CONTENT_SERVICE_PATH,
    _configure_env,
    _create_user,
    _internal_headers,
    _load_module,
)


def test_catalog_content_custom_book_update_replaces_existing_chapters(monkeypatch, tmp_path):
    _configure_env(monkeypatch, tmp_path, 'catalog-content-custom-book-update')
    module = _load_module('catalog_content_custom_book_update', CATALOG_CONTENT_SERVICE_PATH)
    user_id = _create_user(module.catalog_content_flask_app, 'catalog-content-custom-book-update-user')
    client = TestClient(module.app)
    headers = _internal_headers(user_id=user_id)

    create_response = client.post(
        '/internal/catalog/custom-books',
        headers=headers,
        json={
            'title': 'Band 7',
            'description': 'desc',
            'chapters': [{'id': 'ch1', 'title': 'Old One'}],
            'words': [{'chapterId': 'ch1', 'word': 'abandon', 'definition': '放弃'}],
        },
    )
    created_book_id = create_response.json()['bookId']

    update_response = client.put(
        f'/api/books/custom-books/{created_book_id}',
        headers=headers,
        json={
            'title': 'Band 8',
            'description': 'updated',
            'education_stage': 'abroad',
            'exam_type': 'ielts',
            'ielts_skill': 'reading',
            'share_enabled': True,
            'chapter_word_target': 30,
            'chapters': [
                {'id': 'first', 'title': 'Updated One'},
                {'id': 'second', 'title': 'Updated Two'},
            ],
            'words': [
                {'chapterId': 'first', 'word': 'coherent', 'definition': '连贯的'},
                {'chapterId': 'second', 'word': 'resilient', 'definition': '有韧性的'},
            ],
        },
    )
    get_response = client.get(f'/internal/catalog/custom-books/{created_book_id}', headers=headers)

    assert create_response.status_code == 201
    assert update_response.status_code == 200
    assert update_response.json()['bookId'] == created_book_id
    assert update_response.json()['title'] == 'Band 8'
    assert update_response.json()['book']['word_count'] == 2
    assert [chapter['title'] for chapter in get_response.json()['chapters']] == [
        'Updated One',
        'Updated Two',
    ]
    assert [
        word['word']
        for chapter in get_response.json()['chapters']
        for word in chapter['words']
    ] == ['coherent', 'resilient']
