import json
from datetime import datetime, timedelta

import routes.books as books_routes
import services.books_registry_service as books_registry_service
from models import (
    User,
    UserAddedBook,
    UserBookProgress,
    UserLearningEvent,
    UserQuickMemoryRecord,
    UserStudySession,
    UserWrongWord,
    db,
)
from platform_sdk import learning_core_home_todo_signals_application


def _patch_vocab_books(monkeypatch, books):
    normalized_books = [
        {'file': f'test-book-{index}.json', 'has_chapters': True, **book}
        for index, book in enumerate(books, start=1)
    ]
    monkeypatch.setattr(books_routes, 'VOCAB_BOOKS', normalized_books, raising=False)
    monkeypatch.setattr(books_registry_service, 'VOCAB_BOOKS', normalized_books, raising=False)


def test_learning_core_home_todo_signals_include_due_wrong_focus_and_speaking_flags(app, monkeypatch):
    now = datetime(2026, 4, 16, 4, 0, 0)
    monkeypatch.setattr(learning_core_home_todo_signals_application, 'utc_now_naive', lambda: now)
    _patch_vocab_books(monkeypatch, [{'id': 'book-a', 'title': 'Book A', 'word_count': 120}])

    with app.app_context():
        user = User(username='todo-signal-user', email='todo-signal@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.flush()

        db.session.add(UserAddedBook(user_id=user.id, book_id='book-a', added_at=now - timedelta(days=3)))
        db.session.add(UserBookProgress(
            user_id=user.id,
            book_id='book-a',
            current_index=24,
            correct_count=18,
            wrong_count=6,
            updated_at=now - timedelta(hours=1),
        ))
        db.session.add(UserQuickMemoryRecord(
            user_id=user.id,
            word='kind',
            book_id='book-a',
            chapter_id='1',
            status='known',
            first_seen=1,
            last_seen=2,
            known_count=1,
            unknown_count=0,
            next_review=int((now - timedelta(minutes=30)).timestamp() * 1000),
            fuzzy_count=0,
        ))
        db.session.add(UserWrongWord(
            user_id=user.id,
            word='dynamic',
            phonetic='/daɪˈnæmɪk/',
            pos='adj.',
            definition='不断变化的',
            wrong_count=1,
            meaning_wrong=1,
            updated_at=now - timedelta(minutes=45),
        ))
        db.session.add(UserStudySession(
            user_id=user.id,
            mode='listening',
            book_id='book-a',
            chapter_id='1',
            words_studied=6,
            correct_count=4,
            wrong_count=2,
            duration_seconds=240,
            started_at=now - timedelta(minutes=40),
            ended_at=now - timedelta(minutes=36),
        ))
        db.session.add(UserLearningEvent(
            user_id=user.id,
            event_type='pronunciation_check',
            source='assistant_tool',
            mode='speaking',
            book_id='book-a',
            chapter_id='1',
            word='dynamic',
            item_count=1,
            correct_count=1,
            wrong_count=0,
            payload=json.dumps({'sentence': 'Dynamic plans need practice.'}, ensure_ascii=False),
            occurred_at=now - timedelta(minutes=20),
        ))
        db.session.add(UserLearningEvent(
            user_id=user.id,
            event_type='speaking_simulation',
            source='assistant_tool',
            mode='speaking',
            book_id='book-a',
            chapter_id='1',
            item_count=2,
            correct_count=0,
            wrong_count=0,
            payload=json.dumps({
                'target_words': ['dynamic'],
                'response_text': 'Dynamic plans need practice.',
            }, ensure_ascii=False),
            occurred_at=now - timedelta(minutes=10),
        ))
        db.session.commit()

        payload = learning_core_home_todo_signals_application.build_learning_core_home_todo_signals_payload(
            user.id,
            target_date='2026-04-16',
        )

    assert payload['date'] == '2026-04-16'
    assert payload['due_review']['pending_count'] == 1
    assert payload['error_review']['pending_count'] == 1
    assert payload['focus_book']['book_id'] == 'book-a'
    assert payload['focus_book']['done_today'] is True
    assert payload['focus_book']['words_today'] == 6
    assert payload['activity']['studied_words'] == 6
    assert payload['activity']['sessions'] == 1
    assert payload['speaking']['has_pronunciation_today'] is True
    assert payload['speaking']['has_output_today'] is True
    assert payload['speaking']['has_simulation_today'] is True
    assert payload['speaking']['status'] in {'building', 'strengthen', 'due', 'mastered'}


def test_learning_core_home_todo_signals_response_validates_date():
    payload, status = learning_core_home_todo_signals_application.build_learning_core_home_todo_signals_response(
        7,
        target_date='2026-99-99',
    )

    assert status == 400
    assert payload == {'error': 'date must be YYYY-MM-DD'}
