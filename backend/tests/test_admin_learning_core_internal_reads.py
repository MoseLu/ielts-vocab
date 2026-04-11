from __future__ import annotations

from datetime import datetime, timedelta

import pytest

import services.admin_user_detail_repository as repository
from platform_sdk.learning_core_admin_detail_internal_client import (
    AdminBookProgressSnapshot,
    AdminChapterProgressSnapshot,
    AdminFavoriteWordSnapshot,
    AdminLearningEventSnapshot,
)
from models import User, UserBookProgress, UserChapterProgress, UserLearningEvent, db


def _create_user(*, username: str) -> User:
    user = User(username=username, email=f'{username}@example.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.commit()
    return user


def test_admin_detail_book_and_chapter_reads_prefer_learning_core_internal_client(app, monkeypatch):
    with app.app_context():
        user = _create_user(username='admin-detail-internal-progress-user')
        db.session.add_all([
            UserBookProgress(
                user_id=user.id,
                book_id='legacy-book',
                current_index=3,
                correct_count=2,
                wrong_count=1,
            ),
            UserChapterProgress(
                user_id=user.id,
                book_id='legacy-book',
                chapter_id='1',
                words_learned=3,
                correct_count=2,
                wrong_count=1,
            ),
        ])
        db.session.commit()

        monkeypatch.setattr(
            repository,
            'fetch_learning_core_admin_book_progress_rows',
            lambda user_id: [
                AdminBookProgressSnapshot(
                    id=501,
                    user_id=user_id,
                    book_id='projected-book',
                    current_index=12,
                    correct_count=9,
                    wrong_count=3,
                    is_completed=False,
                    updated_at=datetime(2026, 4, 11, 21, 0, 0),
                ),
            ],
        )
        monkeypatch.setattr(
            repository,
            'fetch_learning_core_admin_chapter_progress_rows',
            lambda user_id, book_id=None, limit=None: [
                AdminChapterProgressSnapshot(
                    id=601,
                    user_id=user_id,
                    book_id=book_id or 'projected-book',
                    chapter_id='2',
                    words_learned=12,
                    correct_count=9,
                    wrong_count=3,
                    is_completed=True,
                    updated_at=datetime(2026, 4, 11, 21, 5, 0),
                ),
            ],
        )

        book_rows = repository.list_user_book_progress_rows(user.id)
        chapter_rows = repository.list_user_chapter_progress_rows(user.id, book_id='projected-book', limit=10)

        assert len(book_rows) == 1
        assert book_rows[0].book_id == 'projected-book'
        assert len(chapter_rows) == 1
        assert chapter_rows[0].chapter_id == '2'
        assert chapter_rows[0].to_dict()['accuracy'] == 75


def test_admin_detail_learning_events_fall_back_to_shared_rows_when_internal_client_fails(app, monkeypatch):
    with app.app_context():
        user = _create_user(username='admin-detail-event-fallback-user')
        start_at = datetime(2026, 4, 11, 10, 0, 0)
        db.session.add_all([
            UserLearningEvent(
                user_id=user.id,
                event_type='quick_memory_review',
                source='quickmemory',
                word='alpha',
                occurred_at=start_at + timedelta(minutes=1),
            ),
            UserLearningEvent(
                user_id=user.id,
                event_type='wrong_word_recorded',
                source='wrong_words',
                word='beta',
                occurred_at=start_at + timedelta(minutes=2),
            ),
        ])
        db.session.commit()

        def _raise(*args, **kwargs):
            raise RuntimeError('learning-core unavailable')

        monkeypatch.setattr(repository, 'fetch_learning_core_admin_session_word_events', _raise)

        rows = repository.list_learning_events_for_sessions(
            user.id,
            lower_bound=start_at,
            upper_bound=start_at + timedelta(minutes=5),
        )

        assert [row.word for row in rows] == ['alpha', 'beta']


def test_admin_detail_learning_events_prefer_internal_client_when_available(app, monkeypatch):
    with app.app_context():
        user = _create_user(username='admin-detail-event-internal-user')
        start_at = datetime(2026, 4, 11, 12, 0, 0)

        monkeypatch.setattr(
            repository,
            'fetch_learning_core_admin_session_word_events',
            lambda user_id, start_at, end_at: [
                AdminLearningEventSnapshot(
                    id=701,
                    user_id=user_id,
                    event_type='quick_memory_review',
                    source='quickmemory',
                    mode='quickmemory',
                    book_id='ielts_listening_premium',
                    chapter_id='3',
                    word='gamma',
                    occurred_at=start_at + timedelta(minutes=1),
                ),
            ],
        )

        rows = repository.list_learning_events_for_sessions(
            user.id,
            lower_bound=start_at,
            upper_bound=start_at + timedelta(minutes=5),
        )

        assert len(rows) == 1
        assert rows[0].word == 'gamma'
        assert rows[0].event_type == 'quick_memory_review'


def test_admin_detail_favorite_words_prefer_learning_core_internal_client(app, monkeypatch):
    with app.app_context():
        user = _create_user(username='admin-detail-favorite-internal-user')

        monkeypatch.setattr(
            repository,
            'fetch_learning_core_admin_favorite_words',
            lambda user_id: [
                AdminFavoriteWordSnapshot(
                    word='delta',
                    normalized_word='delta',
                    phonetic='/d/',
                    pos='n.',
                    definition='delta definition',
                    source_book_id='ielts_reading_premium',
                    source_book_title='IELTS Reading',
                    source_chapter_id='5',
                    source_chapter_title='Chapter 5',
                    created_at=datetime(2026, 4, 11, 21, 30, 0),
                    updated_at=datetime(2026, 4, 11, 21, 35, 0),
                ),
            ],
        )

        rows = repository.list_user_favorite_word_rows(user.id)

        assert len(rows) == 1
        assert rows[0].word == 'delta'
        assert rows[0].source_book_id == 'ielts_reading_premium'


def test_admin_detail_learning_events_block_shared_fallback_when_strict_boundary_enabled(app, monkeypatch):
    with app.app_context():
        user = _create_user(username='admin-detail-event-strict-user')
        start_at = datetime(2026, 4, 11, 15, 0, 0)
        db.session.add(UserLearningEvent(
            user_id=user.id,
            event_type='quick_memory_review',
            source='quickmemory',
            word='alpha',
            occurred_at=start_at + timedelta(minutes=1),
        ))
        db.session.commit()

        monkeypatch.setenv('CURRENT_SERVICE_NAME', 'admin-ops-service')
        monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'false')

        def _raise(*args, **kwargs):
            raise RuntimeError('learning-core unavailable')

        monkeypatch.setattr(repository, 'fetch_learning_core_admin_session_word_events', _raise)

        with pytest.raises(repository.LearningCoreAdminDetailUnavailable) as excinfo:
            repository.list_learning_events_for_sessions(
                user.id,
                lower_bound=start_at,
                upper_bound=start_at + timedelta(minutes=5),
            )

        assert excinfo.value.action == 'admin-detail-session-word-events-read'
