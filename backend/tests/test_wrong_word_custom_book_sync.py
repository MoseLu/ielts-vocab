from types import SimpleNamespace

from models import CustomBook, CustomBookChapter, CustomBookWord, User, db
from platform_sdk import learning_core_internal_client
from platform_sdk.learning_core_wrong_words_application import sync_learning_core_wrong_words_response
from services import books_catalog_query_service
from services.custom_book_catalog_service import (
    get_custom_book_response,
    list_custom_books_response,
    update_custom_book_response,
)
from services.wrong_word_custom_book_service import build_wrong_word_custom_book_id


def register_and_login(client, username='wrong-book-user', password='password123'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@example.com',
    })
    response = client.post('/api/auth/login', json={
        'email': username,
        'password': password,
    })
    assert response.status_code == 200


def _create_user(username='wrong-book-core-user') -> User:
    user = User(username=username, email=f'{username}@example.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


def _load_wrong_word_book(user_id: int) -> CustomBook:
    book = CustomBook.query.filter_by(
        id=build_wrong_word_custom_book_id(user_id),
        user_id=user_id,
    ).one()
    assert book.title == '错词本'
    assert len(book.chapters) >= 26
    assert [chapter.title for chapter in book.chapters[:26]] == [chr(code) for code in range(65, 91)]
    return book


def _chapter_words(book: CustomBook, title: str) -> list[str]:
    chapter = next(chapter for chapter in book.chapters if chapter.title == title)
    return [word.word for word in chapter.words]


def test_wrong_words_sync_mirrors_words_to_alphabetized_custom_book(client, app):
    register_and_login(client)

    response = client.post('/api/ai/wrong-words/sync', json={
        'sourceMode': 'meaning',
        'words': [
            {'word': 'zebra', 'definition': 'striped animal', 'wrong_count': 1},
            {'word': 'alpha', 'definition': 'first', 'wrong_count': 1},
            {'word': 'ability', 'definition': 'skill', 'wrong_count': 1},
            {'word': 'beta', 'definition': 'second', 'wrong_count': 1},
        ],
    })

    assert response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username='wrong-book-user').one()
        book = _load_wrong_word_book(user.id)
        assert len(book.chapters) == 26
        assert book.word_count == 4
        assert _chapter_words(book, 'A') == ['ability', 'alpha']
        assert _chapter_words(book, 'B') == ['beta']
        assert _chapter_words(book, 'Z') == ['zebra']
        extra_chapter = CustomBookChapter(
            id=f'{book.id}_manual',
            book_id=book.id,
            title='Manual',
            word_count=1,
            sort_order=99,
        )
        db.session.add(extra_chapter)
        db.session.flush()
        db.session.add(CustomBookWord(
            chapter_id=extra_chapter.id,
            word='manual',
            phonetic='',
            pos='',
            definition='manual entry',
            sort_order=0,
        ))
        db.session.commit()

    update_response = client.post('/api/ai/wrong-words/sync', json={
        'sourceMode': 'meaning',
        'words': [
            {'word': 'aardvark', 'definition': 'burrowing mammal', 'wrong_count': 1},
            {'word': 'alpha', 'definition': 'updated first', 'wrong_count': 2},
        ],
    })

    assert update_response.status_code == 200
    with app.app_context():
        user = User.query.filter_by(username='wrong-book-user').one()
        book = _load_wrong_word_book(user.id)
        assert len(book.chapters) == 27
        assert book.word_count == 6
        assert _chapter_words(book, 'A') == ['aardvark', 'ability', 'alpha']
        assert _chapter_words(book, 'Manual') == ['manual']
        alpha = next(word for word in next(ch for ch in book.chapters if ch.title == 'A').words if word.word == 'alpha')
        assert alpha.definition == 'updated first'


def test_learning_core_wrong_words_sync_updates_system_custom_book(app):
    with app.app_context():
        user = _create_user()

        payload, status = sync_learning_core_wrong_words_response(user.id, {
            'sourceMode': 'listening',
            'words': [
                {'word': 'delta', 'definition': 'change', 'wrongCount': 1},
                {'word': 'charter', 'definition': 'formal document', 'wrongCount': 1},
            ],
        })

        book = _load_wrong_word_book(user.id)
        assert status == 200
        assert payload == {'updated': 2}
        assert book.word_count == 2
        assert _chapter_words(book, 'C') == ['charter']
        assert _chapter_words(book, 'D') == ['delta']


def test_wrong_word_custom_book_update_preserves_system_chapters(app):
    with app.app_context():
        user = _create_user(username='wrong-book-update-user')
        sync_learning_core_wrong_words_response(user.id, {
            'sourceMode': 'meaning',
            'words': [{'word': 'abandon', 'definition': 'leave behind', 'wrongCount': 1}],
        })
        book = _load_wrong_word_book(user.id)

        payload, status = update_custom_book_response(user.id, book.id, {
            'title': '用户改名',
            'chapters': [
                {'id': f'{book.id}_a', 'title': 'Edited A'},
                {'id': 'user-extra', 'title': '用户章节'},
            ],
            'words': [
                {'chapterId': f'{book.id}_a', 'word': 'ability'},
                {'chapterId': 'user-extra', 'word': 'ability'},
            ],
        })

        updated_book = _load_wrong_word_book(user.id)
        assert status == 200
        assert payload['title'] == '错词本'
        assert updated_book.word_count == 2
        assert _chapter_words(updated_book, 'A') == ['abandon']
        assert _chapter_words(updated_book, '用户章节') == ['ability']


def test_catalog_read_syncs_system_book_from_learning_core_snapshot(app, monkeypatch):
    with app.app_context():
        user = _create_user(username='wrong-book-catalog-user')
        legacy_book = CustomBook(
            id='custom_legacy_wrong_words',
            user_id=user.id,
            title='错词本',
            description='old export',
            word_count=2,
        )
        db.session.add(legacy_book)
        db.session.flush()
        db.session.add(CustomBookChapter(
            id='custom_legacy_wrong_words_manual',
            book_id=legacy_book.id,
            title='STR',
            word_count=1,
            sort_order=0,
        ))
        db.session.add(CustomBookChapter(
            id='custom_legacy_wrong_words_a',
            book_id=legacy_book.id,
            title='字母a开头',
            word_count=1,
            sort_order=1,
        ))
        db.session.flush()
        db.session.add(CustomBookWord(
            chapter_id='custom_legacy_wrong_words_manual',
            word='strategy',
            phonetic='',
            pos='',
            definition='plan',
            sort_order=0,
        ))
        db.session.add(CustomBookWord(
            chapter_id='custom_legacy_wrong_words_a',
            word='alpha',
            phonetic='',
            pos='',
            definition='old first',
            sort_order=0,
        ))
        db.session.commit()

        def fake_wrong_words(user_id, **kwargs):
            assert kwargs['source_service_name'] == 'catalog-content-service'
            return {
                'words': [
                    {'word': 'beta', 'definition': 'second'},
                    {'word': 'ability', 'definition': 'skill'},
                    {'word': 'alpha', 'definition': 'first'},
                ],
            }

        monkeypatch.setattr(
            learning_core_internal_client,
            'fetch_learning_core_wrong_words_response',
            fake_wrong_words,
        )

        payload, status = list_custom_books_response(user.id)
        monkeypatch.setattr(
            books_catalog_query_service.books_confusable_service,
            'resolve_optional_current_user',
            lambda: SimpleNamespace(id=user.id),
        )
        monkeypatch.setattr(
            books_catalog_query_service,
            '_build_optional_favorite_book',
            lambda user_id: None,
        )
        books_payload, books_status = books_catalog_query_service.build_books_response()
        book = _load_wrong_word_book(user.id)
        legacy_payload, legacy_status = get_custom_book_response(user.id, legacy_book.id)
        update_payload, update_status = update_custom_book_response(user.id, legacy_book.id, {
            'title': 'stale edit',
            'chapters': [
                {'id': f'{book.id}_a', 'title': 'Edited A'},
                {'id': 'stale-extra', 'title': '用户补充'},
            ],
            'words': [
                {'chapterId': f'{book.id}_a', 'word': 'alter'},
                {'chapterId': 'stale-extra', 'word': 'supplement', 'definition': 'extra'},
            ],
        })
        updated_book = _load_wrong_word_book(user.id)

        assert status == 200
        assert build_wrong_word_custom_book_id(user.id) in [item['id'] for item in payload['books']]
        assert legacy_book.id not in [item['id'] for item in payload['books']]
        assert books_status == 200
        visible_wrong_books = [
            item
            for item in books_payload['books']
            if item.get('title') == '错词本'
        ]
        assert [item['id'] for item in visible_wrong_books] == [build_wrong_word_custom_book_id(user.id)]
        assert len(updated_book.chapters) == 28
        assert updated_book.word_count == 5
        assert _chapter_words(updated_book, 'A') == ['ability', 'alpha']
        assert _chapter_words(updated_book, 'B') == ['beta']
        assert _chapter_words(updated_book, 'STR') == ['strategy']
        assert _chapter_words(updated_book, '用户补充') == ['supplement']
        assert legacy_status == 200
        assert legacy_payload['id'] == build_wrong_word_custom_book_id(user.id)
        assert update_status == 200
        assert update_payload['bookId'] == build_wrong_word_custom_book_id(user.id)
