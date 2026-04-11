from platform_sdk import ai_context_application


def test_build_context_payload_merges_learning_core_internal_payload_with_ai_memory(monkeypatch):
    monkeypatch.setattr(
        ai_context_application,
        'fetch_learning_core_context_payload',
        lambda user_id: {'summary': {'source': 'learning-core'}, 'books': []},
    )
    monkeypatch.setattr(
        ai_context_application,
        'build_local_learner_profile_response',
        lambda user_id, *, target_date, view: ({'summary': {'today_words': 0}}, 200),
    )
    monkeypatch.setattr(
        ai_context_application,
        'load_memory',
        lambda user_id: {'goals': ['7.0']},
    )
    monkeypatch.setattr(
        ai_context_application,
        'list_recent_daily_summaries',
        lambda user_id, limit=7: [],
    )

    payload = ai_context_application.build_context_payload(12)

    assert payload['summary']['source'] == 'learning-core'
    assert payload['learnerProfile'] == {'summary': {'today_words': 0}}
    assert payload['memory'] == {'goals': ['7.0']}


def test_build_context_payload_uses_empty_learning_core_snapshot_in_strict_mode(monkeypatch):
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'ai-execution-service')
    monkeypatch.delenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', raising=False)
    monkeypatch.setattr(
        ai_context_application,
        'fetch_learning_core_context_payload',
        lambda user_id: (_ for _ in ()).throw(RuntimeError('learning-core unavailable')),
    )
    monkeypatch.setattr(
        ai_context_application,
        'build_learning_core_context_payload',
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError('fallback should stay disabled')),
    )
    monkeypatch.setattr(
        ai_context_application,
        'build_local_learner_profile_response',
        lambda user_id, *, target_date, view: ({'activity_summary': {'today_words': 0}}, 200),
    )
    monkeypatch.setattr(
        ai_context_application,
        'load_memory',
        lambda user_id: {'goals': ['7.5']},
    )
    monkeypatch.setattr(
        ai_context_application,
        'list_recent_daily_summaries',
        lambda user_id, limit=7: [],
    )

    payload = ai_context_application.build_context_payload(12)

    assert payload['books'] == []
    assert payload['totalLearned'] == 0
    assert payload['totalSessions'] == 0
    assert payload['learnerProfile'] == {'activity_summary': {'today_words': 0}}
    assert payload['memory'] == {'goals': ['7.5']}


def test_build_context_payload_uses_projected_daily_summaries_when_notes_service_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        ai_context_application,
        'fetch_learning_core_context_payload',
        lambda user_id: {'books': [], 'wrongWords': [], 'recentSessions': []},
    )
    monkeypatch.setattr(
        ai_context_application,
        'build_local_learner_profile_response',
        lambda user_id, *, target_date, view: ({'activity_summary': {'today_words': 1}}, 200),
    )
    monkeypatch.setattr(
        ai_context_application,
        'load_memory',
        lambda user_id: {'goals': ['7.0']},
    )
    monkeypatch.setattr(
        ai_context_application,
        'list_recent_daily_summaries',
        lambda user_id, limit=7: (_ for _ in ()).throw(RuntimeError('notes unavailable')),
    )
    monkeypatch.setattr(
        ai_context_application,
        'list_projected_daily_summaries_for_ai',
        lambda user_id, limit=7: (True, [{
            'id': 3,
            'date': '2026-04-11',
            'content': '# 2026-04-11 学习总结 今天复盘了错词。',
            'generated_at': '2026-04-11T09:00:00',
        }]),
    )

    payload = ai_context_application.build_context_payload(12)

    assert payload['recentSummaries'][0]['date'] == '2026-04-11'
    assert '错词' in payload['recentSummaries'][0]['content']


def test_build_learner_profile_response_returns_empty_snapshot_when_local_builder_crashes(monkeypatch):
    monkeypatch.setattr(
        ai_context_application,
        'build_local_learner_profile_response',
        lambda user_id, *, target_date, view: (_ for _ in ()).throw(RuntimeError('profile failed')),
    )

    payload, status = ai_context_application.build_learner_profile_response(
        12,
        target_date='2026-04-11',
        view='full',
    )

    assert status == 200
    assert payload['date'] == '2026-04-11'
    assert payload['summary']['due_reviews'] == 0
    assert payload['dimensions'] == []
    assert payload['daily_plan'] is None
    assert payload['recent_activity'] == []


def test_build_context_payload_uses_empty_learner_profile_snapshot_when_local_builder_crashes(monkeypatch):
    monkeypatch.setattr(
        ai_context_application,
        'fetch_learning_core_context_payload',
        lambda user_id: {'books': [], 'wrongWords': [], 'recentSessions': [], 'totalSessions': 0},
    )
    monkeypatch.setattr(
        ai_context_application,
        'build_local_learner_profile_response',
        lambda user_id, *, target_date, view: (_ for _ in ()).throw(RuntimeError('profile failed')),
    )
    monkeypatch.setattr(
        ai_context_application,
        'load_memory',
        lambda user_id: {'goals': ['7.0']},
    )
    monkeypatch.setattr(
        ai_context_application,
        'list_recent_daily_summaries',
        lambda user_id, limit=7: [],
    )

    payload = ai_context_application.build_context_payload(12)

    assert payload['learnerProfile']['summary']['due_reviews'] == 0
    assert payload['learnerProfile']['daily_plan'] is None
    assert payload['activityTimeline']['recent_events'] == []
    assert payload['memory'] == {'goals': ['7.0']}
