from datetime import datetime, timedelta

from models import User, UserHomeTodoItem, UserHomeTodoPlan, db
from platform_sdk import ai_home_todo_application


def _create_user() -> User:
    user = User(username='ai-home-todo-user', email='ai-home-todo@example.com')
    user.set_password('password123')
    db.session.add(user)
    db.session.flush()
    return user


def _task_map(payload: dict) -> dict[str, dict]:
    items = [*(payload.get('primary_items') or []), *(payload.get('overflow_items') or [])]
    return {item['kind']: item for item in items}


def test_build_home_todos_response_rolls_previous_pending_items_into_today_plan(app, monkeypatch):
    now = datetime(2026, 4, 16, 4, 0, 0)
    signals = {
        'date': '2026-04-16',
        'due_review': {'pending_count': 2, 'done_today': False},
        'error_review': {
            'pending_count': 1,
            'recommended_dimension': 'meaning',
            'recommended_count': 1,
            'done_today': False,
        },
        'focus_book': None,
        'activity': {'studied_words': 0, 'duration_seconds': 0, 'sessions': 0},
        'weakest_mode': None,
        'speaking': {
            'status': 'needs_setup',
            'status_label': '待建立',
            'tracked_words': 0,
            'due_words': 0,
            'backlog_words': 0,
            'accuracy': None,
            'focus_words': ['dynamic'],
            'next_action': '先做一次发音检查，再补一条英文输出。',
            'has_pronunciation_today': False,
            'has_output_today': False,
            'has_assessment_today': False,
            'has_simulation_today': False,
        },
    }
    monkeypatch.setattr(ai_home_todo_application, 'fetch_learning_core_home_todo_signals', lambda *args, **kwargs: signals)

    with app.app_context():
        user = _create_user()
        previous_plan = UserHomeTodoPlan(
            user_id=user.id,
            plan_date='2026-04-15',
            pending_count=2,
            completed_count=0,
            carry_over_count=0,
            last_generated_at=now - timedelta(days=1),
        )
        db.session.add(previous_plan)
        db.session.flush()
        stale_due = UserHomeTodoItem(
            plan_id=previous_plan.id,
            task_key='due-review',
            kind='due-review',
            status='pending',
            priority=10,
            title='到期复习',
            description='old',
            badge='old',
            carry_over_count=0,
        )
        stale_due.set_action({'kind': 'due-review', 'cta_label': '去复习'})
        stale_due.set_steps([])
        stale_due.set_evidence({})
        stale_speaking = UserHomeTodoItem(
            plan_id=previous_plan.id,
            task_key='speaking',
            kind='speaking',
            status='pending',
            priority=30,
            title='口语任务',
            description='old',
            badge='old',
            carry_over_count=0,
        )
        stale_speaking.set_action({'kind': 'speaking', 'cta_label': '去练口语'})
        stale_speaking.set_steps([{'id': 'pronunciation', 'label': '1 次发音检查', 'status': 'current'}])
        stale_speaking.set_evidence({'variant': 'needs_setup'})
        db.session.add_all([stale_due, stale_speaking])
        db.session.commit()

        payload, status = ai_home_todo_application.build_home_todos_response(
            user.id,
            target_date='2026-04-16',
        )
        db.session.expire_all()

        assert status == 200
        assert payload['summary']['carry_over_count'] == 2
        assert [item['kind'] for item in payload['primary_items']] == [
            'due-review',
            'add-book',
            'speaking',
            'error-review',
        ]
        assert payload['overflow_items'] == []

        tasks = _task_map(payload)
        assert tasks['due-review']['carry_over_count'] == 1
        assert tasks['speaking']['carry_over_count'] == 1

        previous_statuses = {
            item.task_key: item.status
            for item in UserHomeTodoItem.query.filter_by(plan_id=previous_plan.id).all()
        }
        assert previous_statuses == {
            'due-review': 'rolled_over',
            'speaking': 'rolled_over',
        }


def test_build_home_todos_response_marks_continue_book_and_speaking_completed(app, monkeypatch):
    signals = {
        'date': '2026-04-16',
        'due_review': {'pending_count': 0, 'done_today': True},
        'error_review': {
            'pending_count': 0,
            'recommended_dimension': None,
            'recommended_count': 0,
            'done_today': False,
        },
        'focus_book': {
            'book_id': 'book-a',
            'title': 'Book A',
            'current_index': 30,
            'total_words': 100,
            'progress_percent': 30,
            'remaining_words': 70,
            'is_completed': False,
            'done_today': True,
            'words_today': 20,
        },
        'activity': {'studied_words': 20, 'duration_seconds': 360, 'sessions': 1},
        'weakest_mode': {'mode': 'meaning', 'label': '词义', 'accuracy': 66},
        'speaking': {
            'status': 'needs_setup',
            'status_label': '待建立',
            'tracked_words': 0,
            'due_words': 0,
            'backlog_words': 2,
            'accuracy': None,
            'focus_words': ['dynamic'],
            'next_action': '先做发音检查，再补英文输出。',
            'has_pronunciation_today': True,
            'has_output_today': True,
            'has_assessment_today': False,
            'has_simulation_today': True,
        },
    }
    monkeypatch.setattr(ai_home_todo_application, 'fetch_learning_core_home_todo_signals', lambda *args, **kwargs: signals)

    with app.app_context():
        user = _create_user()
        payload, status = ai_home_todo_application.build_home_todos_response(
            user.id,
            target_date='2026-04-16',
        )

    assert status == 200
    assert payload['summary']['pending_count'] == 0
    tasks = _task_map(payload)

    assert tasks['continue-book']['status'] == 'completed'
    assert tasks['continue-book']['completion_source'] == 'completed_today'
    assert tasks['continue-book']['badge'] == '20/20 今日新词'
    assert tasks['continue-book']['steps'][0]['label'] == '今日推进 20 个新词（已完成 20/20）'
    assert tasks['speaking']['status'] == 'completed'
    assert tasks['speaking']['completion_source'] == 'completed_today'
    assert all(step['status'] == 'completed' for step in tasks['speaking']['steps'])
    assert 'add-book' not in tasks


def test_build_home_todos_response_returns_strict_boundary_when_learning_core_is_unavailable(monkeypatch):
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'ai-execution-service')
    monkeypatch.delenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', raising=False)
    monkeypatch.setattr(
        ai_home_todo_application,
        'fetch_learning_core_home_todo_signals',
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('learning-core unavailable')),
    )
    monkeypatch.setattr(
        ai_home_todo_application,
        'build_learning_core_home_todo_signals_payload',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should stay disabled')),
    )

    payload, status = ai_home_todo_application.build_home_todos_response(7, target_date='2026-04-16')

    assert status == 503
    assert payload['boundary'] == 'strict-internal-contract'
    assert payload['upstream'] == 'learning-core-service'
    assert payload['action'] == 'home-todo-signals-read'
