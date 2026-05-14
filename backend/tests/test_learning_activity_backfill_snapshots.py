from datetime import datetime

from models import (
    CustomBook,
    CustomBookChapter,
    CustomBookWord,
    User,
    UserLearningChapterRollup,
    UserQuickMemoryRecord,
    UserStudySession,
    db,
)
from services.learning_activity_backfill import backfill_learning_activity_rollups


def _create_user(username='learning-backfill-snapshot-user') -> User:
    user = User(username=username)
    user.set_password('password123')
    db.session.add(user)
    db.session.flush()
    return user


def _create_custom_chapter(user: User, *, book_id='custom_snapshot_book', chapter_id='custom_snapshot_book_1') -> None:
    words = ['alpha', 'beta', 'gamma']
    db.session.add(CustomBook(
        id=book_id,
        user_id=user.id,
        title='Snapshot Book',
        word_count=len(words),
    ))
    db.session.add(CustomBookChapter(
        id=chapter_id,
        book_id=book_id,
        title='Chapter 1',
        word_count=len(words),
        sort_order=1,
    ))
    for index, word in enumerate(words):
        db.session.add(CustomBookWord(
            chapter_id=chapter_id,
            word=word,
            definition=word,
            sort_order=index,
        ))


def test_session_only_backfill_restores_chapter_snapshot(app):
    with app.app_context():
        user = _create_user('learning-backfill-session-snapshot')
        _create_custom_chapter(user)
        db.session.add(UserStudySession(
            user_id=user.id,
            mode='quickmemory',
            book_id='custom_snapshot_book',
            chapter_id='custom_snapshot_book_1',
            words_studied=3,
            duration_seconds=90,
            started_at=datetime(2026, 5, 1, 1, 0),
            ended_at=datetime(2026, 5, 1, 1, 5),
        ))
        db.session.commit()

        backfill_learning_activity_rollups(user_ids=[user.id])

        rollup = UserLearningChapterRollup.query.filter_by(
            user_id=user.id,
            book_id='custom_snapshot_book',
            mode='quickmemory',
            chapter_id='custom_snapshot_book_1',
        ).one()
        assert rollup.items_studied == 3
        assert rollup.words_learned == 3
        assert rollup.current_index == 3
        assert rollup.is_completed is True


def test_quick_memory_backfill_uses_unique_words_as_snapshot(app):
    with app.app_context():
        user = _create_user('learning-backfill-quick-snapshot')
        _create_custom_chapter(user)
        for index, word in enumerate(['alpha', 'beta', 'gamma']):
            db.session.add(UserQuickMemoryRecord(
                user_id=user.id,
                word=word,
                book_id='custom_snapshot_book',
                chapter_id='custom_snapshot_book_1',
                status='known',
                last_seen=1_777_577_000_000 + index,
                known_count=1,
            ))
        db.session.commit()

        backfill_learning_activity_rollups(user_ids=[user.id])

        rollup = UserLearningChapterRollup.query.filter_by(
            user_id=user.id,
            book_id='custom_snapshot_book',
            mode='quickmemory',
            chapter_id='custom_snapshot_book_1',
        ).one()
        assert rollup.items_studied == 3
        assert rollup.review_count == 3
        assert rollup.words_learned == 3
        assert rollup.current_index == 3
        assert rollup.is_completed is True
