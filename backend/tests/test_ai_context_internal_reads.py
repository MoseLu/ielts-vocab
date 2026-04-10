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

    payload = ai_context_application.build_context_payload(12)

    assert payload['summary']['source'] == 'learning-core'
    assert payload['learnerProfile'] == {'summary': {'today_words': 0}}
    assert payload['memory'] == {'goals': ['7.0']}
