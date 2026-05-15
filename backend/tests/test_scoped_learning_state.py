from __future__ import annotations

from types import SimpleNamespace

from models import (
    User,
    UserQuickMemoryRecord,
    UserScopedQuickMemoryRecord,
    UserScopedWrongWord,
    UserWrongWord,
    db,
)
from services.ai_progress_sync_service import sync_quick_memory_response
from services.ai_wrong_words_service import sync_wrong_words_response
from services.learning_scope_support import resolve_learning_scope
from services.quick_memory_review_queue_service import build_review_queue_payload


def _create_user(username: str = 'scoped-user') -> User:
    user = User(username=username, email=f'{username}@example.com', password_hash='test')
    db.session.add(user)
    db.session.commit()
    return user


def _review_row(word: str, *, book_id: str, chapter_id: str, next_review: int = 1):
    return SimpleNamespace(
        word=word,
        book_id=book_id,
        chapter_id=chapter_id,
        status='known',
        known_count=2,
        unknown_count=0,
        next_review=next_review,
    )


def _vocab_entry(word: str, *, book_id: str, chapter_id: str) -> dict:
    return {
        'word': word,
        'phonetic': f'/{word}/',
        'pos': 'n.',
        'definition': f'{word} definition',
        'book_id': book_id,
        'book_title': book_id,
        'chapter_id': chapter_id,
        'chapter_title': f'Chapter {chapter_id}',
    }


def test_legacy_global_scope_key_normalizes_to_user_scope():
    assert resolve_learning_scope({'scopeKey': 'global'}).scope_key == 'user'


def test_quick_memory_sync_keeps_same_word_scoped_by_book_and_chapter(app):
    with app.app_context():
        user = _create_user()

        response, status = sync_quick_memory_response(user.id, {
            'source': 'quickmemory',
            'sourceMode': 'quickmemory',
            'records': [{
                'word': 'Alpha',
                'bookId': 'book-a',
                'chapterId': '1',
                'status': 'known',
                'firstSeen': 100,
                'lastSeen': 1_000,
                'knownCount': 2,
                'unknownCount': 0,
                'nextReview': 10_000,
                'fuzzyCount': 0,
            }],
        })
        assert (response, status) == ({'ok': True}, 200)

        response, status = sync_quick_memory_response(user.id, {
            'source': 'quickmemory',
            'sourceMode': 'quickmemory',
            'records': [{
                'word': 'alpha',
                'bookId': 'book-b',
                'chapterId': '1',
                'status': 'unknown',
                'firstSeen': 200,
                'lastSeen': 2_000,
                'knownCount': 0,
                'unknownCount': 1,
                'nextReview': 20_000,
                'fuzzyCount': 0,
            }],
        })

        assert (response, status) == ({'ok': True}, 200)
        scoped_rows = UserScopedQuickMemoryRecord.query.filter_by(
            user_id=user.id,
            word='alpha',
        ).order_by(UserScopedQuickMemoryRecord.scope_key).all()
        assert [row.scope_key for row in scoped_rows] == ['chapter:book-a:1', 'chapter:book-b:1']
        assert [row.status for row in scoped_rows] == ['known', 'unknown']

        projection = UserQuickMemoryRecord.query.filter_by(user_id=user.id, word='alpha').one()
        assert projection.book_id == 'book-a'
        assert projection.chapter_id == '1'
        assert projection.status == 'unknown'


def test_wrong_word_sync_keeps_same_word_scoped_by_book_and_chapter(app):
    with app.app_context():
        user = _create_user('scoped-wrong-user')

        sync_wrong_words_response(user.id, {
            'sourceMode': 'meaning',
            'bookId': 'book-a',
            'chapterId': '1',
            'words': [{'word': 'alpha', 'wrong_count': 1, 'meaning_wrong': 1}],
        })
        sync_wrong_words_response(user.id, {
            'sourceMode': 'meaning',
            'bookId': 'book-b',
            'chapterId': '1',
            'words': [{'word': 'alpha', 'wrong_count': 2, 'meaning_wrong': 2}],
        })

        scoped_rows = UserScopedWrongWord.query.filter_by(
            user_id=user.id,
            word='alpha',
        ).order_by(UserScopedWrongWord.scope_key).all()
        assert [row.scope_key for row in scoped_rows] == ['chapter:book-a:1', 'chapter:book-b:1']
        assert [row.wrong_count for row in scoped_rows] == [1, 2]

        projection = UserWrongWord.query.filter_by(user_id=user.id, word='alpha').one()
        assert projection.wrong_count == 2


def test_review_queue_with_scope_filter_uses_scoped_quick_memory_rows_only():
    scoped_rows = [_review_row('alpha', book_id='book-a', chapter_id='1')]
    global_rows = [_review_row('beta', book_id='book-a', chapter_id='1')]

    payload = build_review_queue_payload(
        user_id=1,
        limit=None,
        offset=0,
        within_days=1,
        due_only=False,
        book_id_filter='book-a',
        chapter_id_filter='1',
        now_ms=5_000,
        normalize_chapter_id=lambda value: str(value) if value is not None else None,
        load_user_quick_memory_records=lambda _user_id: global_rows,
        load_user_scoped_quick_memory_records=lambda _user_id, scope_key: (
            scoped_rows if scope_key == 'chapter:book-a:1' else []
        ),
        resolve_quick_memory_vocab_entry=lambda word, **_kwargs: (
            _vocab_entry(word, book_id='book-a', chapter_id='1') if word == 'alpha' else None
        ),
        get_global_vocab_pool=lambda: (_ for _ in ()).throw(
            AssertionError('scoped queue must not consult global catalog fallback'),
        ),
    )

    assert [item['word'] for item in payload['words']] == ['alpha']
    assert payload['summary']['total_count'] == 1
