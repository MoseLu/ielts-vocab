from __future__ import annotations

from types import SimpleNamespace

from platform_sdk import ai_custom_books_application


def test_custom_book_routes_use_catalog_content_internal_client(app, monkeypatch):
    monkeypatch.setattr(
        ai_custom_books_application,
        'create_catalog_content_custom_book_internal_response',
        lambda user_id, payload: ({'bookId': 'custom-71', 'title': payload.get('title')}, 201),
    )
    monkeypatch.setattr(
        ai_custom_books_application,
        'list_catalog_content_custom_books_internal_response',
        lambda user_id: ({'books': [{'id': 'custom-71'}], 'user_id': user_id}, 200),
    )
    monkeypatch.setattr(
        ai_custom_books_application,
        'get_catalog_content_custom_book_internal_response',
        lambda user_id, book_id: ({'id': book_id, 'user_id': user_id}, 200),
    )
    monkeypatch.setattr(
        ai_custom_books_application,
        'build_catalog_content_custom_book_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )
    monkeypatch.setattr(
        ai_custom_books_application,
        'build_catalog_content_list_custom_books_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )
    monkeypatch.setattr(
        ai_custom_books_application,
        'build_catalog_content_get_custom_book_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )
    monkeypatch.setattr(
        ai_custom_books_application,
        'build_context_payload',
        lambda user_id: {'wrongWords': []},
    )
    monkeypatch.setattr(
        ai_custom_books_application,
        'chat',
        lambda *args, **kwargs: {'text': '{"title":"Band 7","description":"desc","chapters":[],"words":[]}'},
    )

    with app.app_context():
        create_response, create_status = ai_custom_books_application.generate_book_response(
            SimpleNamespace(id=71),
            {'targetWords': 20},
        )
        list_response, list_status = ai_custom_books_application.list_custom_books_response(SimpleNamespace(id=71))
        get_response, get_status = ai_custom_books_application.get_custom_book_response(
            SimpleNamespace(id=71),
            'custom-71',
        )

    assert create_status == 200
    assert create_response.get_json() == {'bookId': 'custom-71', 'title': 'Band 7'}
    assert list_status == 200
    assert list_response.get_json()['user_id'] == 71
    assert get_status == 200
    assert get_response.get_json() == {'id': 'custom-71', 'user_id': 71}
