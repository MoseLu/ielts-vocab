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
