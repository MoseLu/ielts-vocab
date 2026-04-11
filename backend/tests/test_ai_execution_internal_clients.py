from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from platform_sdk import (
    ai_assistant_application,
    ai_assistant_tool_support,
    ai_learning_stats_application,
    ai_metric_support,
    ai_practice_speaking_application,
    ai_progress_sync_application,
    ai_related_notes_support,
    ai_session_application,
    ai_wrong_words_application,
)
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


def test_record_smart_dimension_delta_event_uses_learning_core_internal_client(monkeypatch):
    recorded: dict[str, object] = {}

    monkeypatch.setattr(
        ai_metric_support,
        'record_learning_core_event',
        lambda user_id, **kwargs: recorded.setdefault('event', {'user_id': user_id, **kwargs}),
    )

    ai_metric_support.record_smart_dimension_delta_event(
        user_id=29,
        event_type='listening_review',
        mode='listening',
        word='alpha',
        book_id='book-1',
        chapter_id='2',
        source_mode='smart',
        previous_correct=1,
        previous_wrong=0,
        current_correct=3,
        current_wrong=1,
    )

    assert recorded['event']['user_id'] == 29
    assert recorded['event']['event_type'] == 'listening_review'
    assert recorded['event']['correct_count'] == 2
    assert recorded['event']['wrong_count'] == 1
    assert recorded['event']['payload']['source_mode'] == 'smart'


def test_get_wrong_words_tool_uses_learning_core_internal_client(monkeypatch):
    captured: dict[str, object] = {}

    def fake_fetch(user_id: int, *, limit: int, query: str, recent_first: bool):
        captured.update({
            'user_id': user_id,
            'limit': limit,
            'query': query,
            'recent_first': recent_first,
        })
        return [{
            'word': 'alpha',
            'phonetic': '/a/',
            'pos': 'n.',
            'definition': 'first letter',
            'wrong_count': 3,
            'ebbinghaus_streak': 2,
            'ebbinghaus_target': 6,
            'updated_at': '2026-04-10T08:00:00',
        }]

    monkeypatch.setattr(ai_assistant_tool_support, 'fetch_learning_core_wrong_words_for_ai', fake_fetch)

    result = ai_assistant_tool_support.make_get_wrong_words(31)(
        limit=8,
        query=' alp ',
        recent_first=False,
        book_id='ielts_reading_premium',
    )

    assert captured == {
        'user_id': 31,
        'limit': 8,
        'query': 'alp',
        'recent_first': False,
    }
    assert '当前错词记录暂不支持按词书过滤' in result
    assert 'alpha' in result
    assert '艾宾浩斯2/6' in result


def test_get_book_chapters_tool_uses_learning_core_internal_progress(monkeypatch):
    monkeypatch.setattr(
        ai_assistant_tool_support,
        '_load_vocab_books',
        lambda: [{'id': 'book-1', 'title': 'Book One'}],
    )
    monkeypatch.setattr(
        ai_assistant_tool_support,
        'load_book_chapters',
        lambda book_id: {
            'total_words': 20,
            'total_chapters': 2,
            'chapters': [
                {'id': 1, 'title': 'Start', 'word_count': 10},
                {'id': 2, 'title': 'Next', 'word_count': 10},
            ],
        },
    )
    monkeypatch.setattr(
        ai_assistant_tool_support,
        'fetch_learning_core_chapter_progress_for_ai',
        lambda user_id, *, book_id: [{
            'chapter_id': 1,
            'correct_count': 8,
            'wrong_count': 2,
            'accuracy': 80,
            'is_completed': True,
        }],
    )

    result = ai_assistant_tool_support.make_get_book_chapters(42)('book-1')

    assert 'Book One（共2章、20词，已完成1章）' in result
    assert '第1章《Start》 10词 — 已完成 正确率80%' in result
    assert '第2章《Next》 10词 — 未开始' in result


def test_pronunciation_check_uses_learning_core_internal_event(app, monkeypatch):
    recorded: dict[str, object] = {}

    monkeypatch.setattr(
        ai_practice_speaking_application,
        'record_learning_core_event',
        lambda user_id, **kwargs: recorded.setdefault('event', {'user_id': user_id, **kwargs}),
    )
    monkeypatch.setattr(ai_practice_speaking_application, 'track_metric', lambda *args, **kwargs: None)

    with app.app_context():
        response, status = ai_practice_speaking_application.pronunciation_check_response(
            SimpleNamespace(id=51),
            {
                'word': 'dynamic',
                'transcript': 'dynamic',
                'sentence': 'Dynamic pricing can confuse users.',
                'bookId': 'book-1',
                'chapterId': '2',
            },
        )

    assert status == 200
    assert response.get_json()['passed'] is True
    assert recorded['event']['event_type'] == 'pronunciation_check'
    assert recorded['event']['word'] == 'dynamic'
    assert recorded['event']['correct_count'] == 1


def test_review_plan_uses_learning_core_wrong_word_count(app, monkeypatch):
    monkeypatch.setattr(
        ai_practice_speaking_application,
        'build_learner_profile_payload',
        lambda user_id: {'memory_system': {}, 'next_actions': ['review errors']},
    )
    monkeypatch.setattr(
        ai_practice_speaking_application,
        'fetch_learning_core_wrong_word_count',
        lambda user_id: 9,
    )
    monkeypatch.setattr(ai_practice_speaking_application, 'track_metric', lambda *args, **kwargs: None)

    with app.app_context():
        response, status = ai_practice_speaking_application.review_plan_response(SimpleNamespace(id=52))

    assert status == 200
    assert response.get_json()['wrong_words'] == 9


def test_quick_memory_sync_uses_learning_core_internal_client(monkeypatch):
    monkeypatch.setattr(
        ai_progress_sync_application,
        'sync_learning_core_quick_memory',
        lambda user_id, payload: {'ok': True, 'user_id': user_id, 'records': len(payload.get('records') or [])},
    )
    monkeypatch.setattr(
        ai_progress_sync_application,
        'build_learning_core_quick_memory_sync_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )

    response, status = ai_progress_sync_application.sync_quick_memory_response(
        61,
        {'records': [{'word': 'alpha'}]},
    )

    assert status == 200
    assert response == {'ok': True, 'user_id': 61, 'records': 1}


def test_quick_memory_sync_returns_503_when_strict_boundary_blocks_local_fallback(monkeypatch):
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'ai-execution-service')
    monkeypatch.delenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', raising=False)
    monkeypatch.setattr(
        ai_progress_sync_application,
        'sync_learning_core_quick_memory',
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('learning-core unavailable')),
    )
    monkeypatch.setattr(
        ai_progress_sync_application,
        'build_learning_core_quick_memory_sync_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should stay disabled')),
    )

    response, status = ai_progress_sync_application.sync_quick_memory_response(61, {'records': [{'word': 'alpha'}]})

    assert status == 503
    assert response['boundary'] == 'strict-internal-contract'
    assert response['upstream'] == 'learning-core-service'
    assert response['action'] == 'quick-memory-sync'


def test_quick_memory_sync_uses_local_fallback_only_when_explicitly_enabled(monkeypatch):
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'ai-execution-service')
    monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'true')
    monkeypatch.setattr(
        ai_progress_sync_application,
        'sync_learning_core_quick_memory',
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('learning-core unavailable')),
    )
    monkeypatch.setattr(
        ai_progress_sync_application,
        'build_learning_core_quick_memory_sync_response',
        lambda user_id, payload: ({'ok': True, 'source': 'legacy-fallback', 'user_id': user_id}, 200),
    )

    response, status = ai_progress_sync_application.sync_quick_memory_response(61, {'records': [{'word': 'alpha'}]})

    assert status == 200
    assert response == {'ok': True, 'source': 'legacy-fallback', 'user_id': 61}


def test_smart_stats_routes_use_learning_core_internal_client(monkeypatch):
    monkeypatch.setattr(
        ai_progress_sync_application,
        'fetch_learning_core_smart_stats_response',
        lambda user_id: {'stats': [{'word': 'alpha'}], 'user_id': user_id},
    )
    monkeypatch.setattr(
        ai_progress_sync_application,
        'sync_learning_core_smart_stats',
        lambda user_id, payload: {'ok': True, 'user_id': user_id, 'count': len(payload.get('stats') or [])},
    )
    monkeypatch.setattr(
        ai_progress_sync_application,
        'build_learning_core_smart_stats_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )
    monkeypatch.setattr(
        ai_progress_sync_application,
        'build_learning_core_smart_stats_sync_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )

    get_response, get_status = ai_progress_sync_application.build_smart_stats_response(62)
    sync_response, sync_status = ai_progress_sync_application.sync_smart_stats_response(
        62,
        {'stats': [{'word': 'alpha'}]},
    )

    assert get_status == 200
    assert get_response['user_id'] == 62
    assert sync_status == 200
    assert sync_response == {'ok': True, 'user_id': 62, 'count': 1}


def test_wrong_word_routes_use_learning_core_internal_client(monkeypatch):
    monkeypatch.setattr(
        ai_wrong_words_application,
        'fetch_learning_core_wrong_words_response',
        lambda user_id, **kwargs: {'words': [{'word': 'abandon'}], 'user_id': user_id, **kwargs},
    )
    monkeypatch.setattr(
        ai_wrong_words_application,
        'sync_learning_core_wrong_words',
        lambda user_id, payload: {'updated': len(payload.get('words') or []), 'user_id': user_id},
    )
    monkeypatch.setattr(
        ai_wrong_words_application,
        'clear_learning_core_wrong_words',
        lambda user_id, word=None: {'message': 'ok', 'user_id': user_id, 'word': word},
    )
    monkeypatch.setattr(
        ai_wrong_words_application,
        'build_learning_core_wrong_words_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )
    monkeypatch.setattr(
        ai_wrong_words_application,
        'sync_learning_core_wrong_words_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )
    monkeypatch.setattr(
        ai_wrong_words_application,
        'clear_learning_core_wrong_word_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )
    monkeypatch.setattr(
        ai_wrong_words_application,
        'clear_learning_core_wrong_words_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )

    list_response, list_status = ai_wrong_words_application.build_wrong_words_response(
        63,
        search_value='aban',
        detail_mode='compact',
    )
    sync_response, sync_status = ai_wrong_words_application.sync_wrong_words_response(
        63,
        {'words': [{'word': 'abandon'}]},
    )
    clear_one_response, clear_one_status = ai_wrong_words_application.clear_wrong_word_response(63, 'abandon')
    clear_all_response, clear_all_status = ai_wrong_words_application.clear_wrong_words_response(63)

    assert list_status == 200
    assert list_response['user_id'] == 63
    assert list_response['search_value'] == 'aban'
    assert sync_status == 200
    assert sync_response == {'updated': 1, 'user_id': 63}
    assert clear_one_status == 200
    assert clear_one_response == {'message': 'ok', 'user_id': 63, 'word': 'abandon'}
    assert clear_all_status == 200
    assert clear_all_response == {'message': 'ok', 'user_id': 63, 'word': None}


def test_study_session_routes_use_learning_core_internal_client(monkeypatch):
    monkeypatch.setattr(
        ai_learning_stats_application,
        'start_learning_core_study_session_response',
        lambda user_id, payload: ({'sessionId': f'session-{user_id}', 'mode': payload.get('mode')}, 201),
    )
    monkeypatch.setattr(
        ai_learning_stats_application,
        'build_learning_core_start_session_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )
    monkeypatch.setattr(
        ai_session_application,
        'log_learning_core_study_session_response',
        lambda user_id, payload: ({'id': f'log-{user_id}', 'words': payload.get('wordsStudied')}, 200),
    )
    monkeypatch.setattr(
        ai_session_application,
        'cancel_learning_core_study_session_response',
        lambda user_id, session_id: ({'deleted': True, 'sessionId': session_id, 'user_id': user_id}, 200),
    )
    monkeypatch.setattr(
        ai_session_application,
        'build_learning_core_log_session_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )
    monkeypatch.setattr(
        ai_session_application,
        'build_learning_core_cancel_session_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should not run')),
    )

    start_response, start_status = ai_learning_stats_application.start_session_response(71, {'mode': 'smart'})
    log_response, log_status = ai_session_application.log_session_response(71, {'wordsStudied': 5})
    cancel_response, cancel_status = ai_session_application.cancel_session_response(71, 'session-71')

    assert start_status == 201
    assert start_response == {'sessionId': 'session-71', 'mode': 'smart'}
    assert log_status == 200
    assert log_response == {'id': 'log-71', 'words': 5}
    assert cancel_status == 200
    assert cancel_response == {'deleted': True, 'sessionId': 'session-71', 'user_id': 71}
