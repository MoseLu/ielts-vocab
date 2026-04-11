from platform_sdk import ai_learning_stats_application


def test_build_learning_stats_response_prefers_learning_core_internal_route(monkeypatch):
    monkeypatch.setattr(
        ai_learning_stats_application,
        'fetch_learning_core_learning_stats_response',
        lambda user_id, *, days, book_id_filter, mode_filter_raw: (
            {'summary': {'source': 'learning-core', 'days': days}},
            200,
        ),
    )

    payload, status = ai_learning_stats_application.build_learning_stats_response(
        12,
        days=14,
        book_id_filter=None,
        mode_filter_raw=None,
    )

    assert status == 200
    assert payload == {'summary': {'source': 'learning-core', 'days': 14}}


def test_build_learning_stats_response_uses_local_fallback_when_explicitly_enabled(monkeypatch):
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'ai-execution-service')
    monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'true')
    monkeypatch.setattr(
        ai_learning_stats_application,
        'fetch_learning_core_learning_stats_response',
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('learning-core unavailable')),
    )
    monkeypatch.setattr(
        ai_learning_stats_application,
        'build_learning_core_learning_stats_response',
        lambda user_id, *, days, book_id_filter, mode_filter_raw: (
            {'summary': {'source': 'legacy-fallback', 'days': days, 'user_id': user_id}},
            200,
        ),
    )

    payload, status = ai_learning_stats_application.build_learning_stats_response(
        12,
        days=30,
        book_id_filter='book-1',
        mode_filter_raw='smart',
    )

    assert status == 200
    assert payload == {
        'summary': {
            'source': 'legacy-fallback',
            'days': 30,
            'user_id': 12,
        }
    }
