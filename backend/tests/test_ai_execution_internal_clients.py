from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from platform_sdk import ai_assistant_application, ai_metric_support, ai_related_notes_support
from platform_sdk.notes_internal_client import LearningNoteSnapshot


def test_persist_ask_response_uses_internal_service_clients(app, monkeypatch):
    recorded: dict[str, object] = {}

    monkeypatch.setattr(ai_assistant_application, 'save_turn', lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_assistant_application, 'maybe_summarize_history', lambda user_id: None)
    monkeypatch.setattr(
        ai_assistant_application,
        'spawn_background',
        lambda fn: recorded.setdefault('background_spawned', True),
    )
    monkeypatch.setattr(
        ai_assistant_application,
        'create_learning_note',
        lambda user_id, **kwargs: recorded.setdefault('note', {'user_id': user_id, **kwargs}),
    )
    monkeypatch.setattr(
        ai_assistant_application,
        'record_learning_core_event',
        lambda user_id, **kwargs: recorded.setdefault('event', {'user_id': user_id, **kwargs}),
    )

    with app.app_context():
        ai_assistant_application.persist_ask_response(
            SimpleNamespace(id=17),
            'How do I use abandon?',
            {'currentWord': 'abandon', 'practiceMode': 'smart'},
            'Use it when someone leaves something behind.',
        )

    assert recorded['note'] == {
        'user_id': 17,
        'question': 'How do I use abandon?',
        'answer': 'Use it when someone leaves something behind.',
        'word_context': 'abandon',
    }
    assert recorded['event']['user_id'] == 17
    assert recorded['event']['event_type'] == 'assistant_question'
    assert recorded['event']['source'] == 'assistant'
    assert recorded['event']['mode'] == 'smart'
    assert recorded['event']['word'] == 'abandon'
    assert recorded['background_spawned'] is True


def test_collect_related_learning_notes_uses_internal_note_snapshots(monkeypatch):
    monkeypatch.setattr(
        ai_related_notes_support,
        'list_recent_learning_notes',
        lambda user_id, limit=80: [
            LearningNoteSnapshot(
                id=1,
                question='kind of 和 a kind of 有什么区别？',
                answer='第一次解释',
                word_context='kind',
                created_at=datetime(2026, 3, 30, 8, 0, 0),
            ),
            LearningNoteSnapshot(
                id=2,
                question='kind of 和 a kind of 还是分不清',
                answer='第二次解释',
                word_context='kind',
                created_at=datetime(2026, 3, 30, 9, 0, 0),
            ),
        ],
    )

    related = ai_related_notes_support.collect_related_learning_notes(
        7,
        'kind of 到底怎么用？',
        {'currentWord': 'kind'},
    )

    assert related is not None
    assert related['repeat_count'] == 2
    assert related['items'][0]['word_context'] == 'kind'


def test_collect_related_learning_notes_returns_none_when_notes_service_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        ai_related_notes_support,
        'list_recent_learning_notes',
        lambda user_id, limit=80: (_ for _ in ()).throw(RuntimeError('notes down')),
    )

    related = ai_related_notes_support.collect_related_learning_notes(
        7,
        'kind of 到底怎么用？',
        {'currentWord': 'kind'},
    )

    assert related is None


def test_track_metric_uses_learning_core_internal_client(monkeypatch):
    recorded: dict[str, object] = {}

    monkeypatch.setattr(
        ai_metric_support,
        'record_learning_core_event',
        lambda user_id, **kwargs: recorded.setdefault('event', {'user_id': user_id, **kwargs}),
    )

    ai_metric_support.track_metric(
        23,
        'adaptive_plan_generated',
        {'level': 'band-7', 'count': 0},
    )

    assert recorded['event'] == {
        'user_id': 23,
        'event_type': 'adaptive_plan_generated',
        'source': 'assistant_tool',
        'mode': None,
        'word': None,
        'item_count': 1,
        'payload': {'level': 'band-7', 'count': 0},
    }
