import json
from datetime import datetime, timedelta, timezone

import routes.ai as ai_routes
import routes.books as books_routes
import services.learner_profile as learner_profile_service
from models import (
    User,
    UserChapterModeProgress,
    UserChapterProgress,
    UserLearningEvent,
    UserLearningNote,
    UserQuickMemoryRecord,
    UserSmartWordStat,
    UserStudySession,
    UserWrongWord,
    db,
)


FIXED_NOW = datetime(2026, 4, 4, 4, 0, 0)


def register_and_login(client, username='stats-contract-user', password='password123'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@example.com',
    })
    res = client.post('/api/auth/login', json={
        'email': username,
        'password': password,
    })
    assert res.status_code == 200


def utc_dt(year: int, month: int, day: int, hour: int, minute: int = 0, second: int = 0) -> datetime:
    return datetime(year, month, day, hour, minute, second)


def epoch_ms(dt: datetime) -> int:
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


def patch_stats_environment(monkeypatch):
    monkeypatch.setattr(ai_routes, 'utc_now_naive', lambda: FIXED_NOW)
    monkeypatch.setattr(learner_profile_service, 'utc_now_naive', lambda: FIXED_NOW)
    monkeypatch.setattr(books_routes, 'VOCAB_BOOKS', [
        {'id': 'book-a', 'title': 'Book A', 'word_count': 100},
        {'id': 'book-b', 'title': 'Book B', 'word_count': 80},
    ], raising=False)
    monkeypatch.setattr(ai_routes, '_chapter_title_map', lambda book_id: {
        'book-a': {'1': 'Chapter A1'},
        'book-b': {'2': 'Chapter B2'},
    }.get(book_id, {}))


def add_study_session(
    *,
    user_id: int,
    mode: str,
    book_id: str,
    chapter_id: str,
    started_at: datetime,
    words_studied: int,
    correct_count: int,
    wrong_count: int,
    duration_seconds: int,
):
    db.session.add(
        UserStudySession(
            user_id=user_id,
            mode=mode,
            book_id=book_id,
            chapter_id=chapter_id,
            words_studied=words_studied,
            correct_count=correct_count,
            wrong_count=wrong_count,
            duration_seconds=duration_seconds,
            started_at=started_at,
            ended_at=started_at + timedelta(seconds=duration_seconds),
        )
    )
