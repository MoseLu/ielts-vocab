from __future__ import annotations

from types import SimpleNamespace

from platform_sdk import ai_practice_speaking_application


def test_pronunciation_check_uses_learning_core_internal_event(app, monkeypatch):
    recorded: dict[str, object] = {}

    monkeypatch.setattr(
        ai_practice_speaking_application,
        'record_learning_core_event',
        lambda user_id, **kwargs: recorded.setdefault('event', {'user_id': user_id, **kwargs}),
    )
    monkeypatch.setattr(
        ai_practice_speaking_application,
        'post_learning_core_game_attempt',
        lambda user_id, payload: {
            'state': {'nodeType': 'word', 'status': 'pending', 'failedDimensions': []},
            'mastery_state': {
                'overall_status': 'unlocked',
                'current_round': 0,
                'pending_dimensions': ['dictation'],
                'dimension_states': {
                    'speaking': {'status': 'passed', 'pass_streak': 1, 'attempt_count': 1},
                },
            },
        },
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
    assert response.get_json()['mastery_state']['dimension_states']['speaking']['pass_streak'] == 1


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
