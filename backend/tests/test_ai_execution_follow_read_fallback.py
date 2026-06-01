from __future__ import annotations

from fastapi.testclient import TestClient

from platform_sdk import ai_follow_read_assessment_application
from test_ai_execution_speaking_api import (
    _auth_headers,
    _build_tone_wav,
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
        files={'audio': ('user.wav', _build_tone_wav(), 'audio/wav')},
        headers=_auth_headers(token),
    )

    assert response.status_code == 503
    assert 'DashScope 控制台' in response.json()['error']


def test_ai_execution_service_follow_read_rejects_too_short_audio(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_follow_read_short_audio')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-follow-read-short')
    run_model = False

    def _record_model_call(**kwargs):
        nonlocal run_model
        run_model = True
        return {}, 'qwen-audio-turbo'

    monkeypatch.setattr(ai_follow_read_assessment_application, '_run_follow_read_assessment', _record_model_call)

    response = client.post(
        '/api/ai/follow-read/evaluate',
        data={'word': 'demonstrate', 'phonetic': '/ˈdemənstreɪt/'},
        files={'audio': ('user.wav', _build_tone_wav(seconds=0.2), 'audio/wav')},
        headers=_auth_headers(token),
    )

    assert response.status_code == 422
    assert response.json() == {'error': '没有检测到有效跟读，请重试'}
    assert run_model is False


def test_ai_execution_service_follow_read_evaluate_does_not_fake_score_when_ai_unavailable(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_follow_read_fallback')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-follow-read-fallback')

    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        '_run_follow_read_assessment',
        _fail_with_runtime_error,
    )
    recorded = {'event': False, 'attempt': False}
    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        'record_learning_core_event',
        lambda *args, **kwargs: recorded.__setitem__('event', True),
    )
    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        'post_learning_core_game_attempt',
        lambda *args, **kwargs: recorded.__setitem__('attempt', True),
    )

    response = client.post(
        '/api/ai/follow-read/evaluate',
        data={'word': 'demonstrate', 'phonetic': '/ˈdemənstreɪt/'},
        files={
            'audio': ('user.wav', _build_tone_wav(), 'audio/wav'),
            'referenceAudio': ('reference.wav', _build_tone_wav(), 'audio/wav'),
        },
        headers=_auth_headers(token),
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload == {'error': '跟读评分暂时不可用，请稍后重试'}
    assert recorded == {'event': False, 'attempt': False}
