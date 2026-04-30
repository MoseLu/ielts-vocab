from __future__ import annotations

from fastapi.testclient import TestClient

from platform_sdk import ai_follow_read_assessment_application
from test_ai_execution_speaking_api import (
    _auth_headers,
    _configure_ai_env,
    _create_user_and_token,
    _load_ai_execution_service_module,
)


def _fail_with_quota_exhaustion(**kwargs):
    raise ai_follow_read_assessment_application.SpeakingAssessmentError(
        'The free tier of the model has been exhausted.',
        status_code=502,
    )


def _fail_with_runtime_error(**kwargs):
    raise RuntimeError('ai service unavailable')


def test_ai_execution_service_follow_read_evaluate_reports_quota_exhaustion(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_follow_read_quota_exhaustion')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-follow-read-quota')

    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        '_run_follow_read_assessment',
        _fail_with_quota_exhaustion,
    )

    response = client.post(
        '/api/ai/follow-read/evaluate',
        data={'word': 'demonstrate', 'phonetic': '/ˈdemənstreɪt/'},
        files={'audio': ('user.webm', b'user-audio', 'audio/webm')},
        headers=_auth_headers(token),
    )

    assert response.status_code == 503
    assert 'DashScope 控制台' in response.json()['error']


def test_ai_execution_service_follow_read_evaluate_falls_back_when_ai_unavailable(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_follow_read_fallback')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-follow-read-fallback')

    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        '_run_follow_read_assessment',
        _fail_with_runtime_error,
    )
    monkeypatch.setattr(ai_follow_read_assessment_application, 'record_learning_core_event', lambda *args, **kwargs: None)
    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        'post_learning_core_game_attempt',
        lambda user_id, data: {'mastery_state': {'overall_status': 'in_review'}},
    )
    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        'score_follow_read_acoustic_fallback',
        lambda **kwargs: {
            'score': 68,
            'transcript': '',
            'feedback': {
                'summary': '基础声学评分完成。',
                'stress': '基础评分暂不判断重音。',
                'vowel': '基础评分暂不判断元音。',
                'consonant': '基础评分暂不判断辅音。',
                'ending': '基础评分暂不判断词尾。',
                'rhythm': '节奏接近参考音频。',
            },
            'weak_segments': [],
            'provider': 'fallback-acoustic',
            'model': 'local-acoustic-v1',
            'confidence': 'low',
        },
    )

    response = client.post(
        '/api/ai/follow-read/evaluate',
        data={'word': 'demonstrate', 'phonetic': '/ˈdemənstreɪt/'},
        files={
            'audio': ('user.wav', b'user-audio', 'audio/wav'),
            'referenceAudio': ('reference.wav', b'reference-audio', 'audio/wav'),
        },
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['provider'] == 'fallback-acoustic'
    assert payload['model'] == 'local-acoustic-v1'
    assert payload['confidence'] == 'low'
