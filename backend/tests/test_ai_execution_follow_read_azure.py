from __future__ import annotations

import json

from fastapi.testclient import TestClient

from platform_sdk import ai_follow_read_assessment_application
from platform_sdk import follow_read_azure_assessment
from test_ai_execution_speaking_api import (
    _auth_headers,
    _build_tone_wav,
    _configure_ai_env,
    _create_user_and_token,
    _load_ai_execution_service_module,
)


def _enable_language_pilot(monkeypatch, tmp_path):
    pilot_path = tmp_path / 'pilot.json'
    pilot_path.write_text(json.dumps({'words': ['language']}), encoding='utf-8')
    monkeypatch.setenv('FOLLOW_READ_AZURE_PILOT_ENABLED', 'true')
    monkeypatch.setenv('FOLLOW_READ_AZURE_PILOT_WORDS_PATH', str(pilot_path))
    follow_read_azure_assessment.reset_azure_follow_read_pilot_cache()


def test_ai_execution_follow_read_uses_azure_for_pilot_words(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    _enable_language_pilot(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_follow_read_azure')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-follow-read-azure')
    recorded: dict[str, dict] = {}

    def _fake_azure(**kwargs):
        assert kwargs['word'] == 'language'
        assert kwargs['segments'] == [
            {'text': 'lan', 'phonetic': 'læŋ'},
            {'text': 'guage', 'phonetic': 'gwɪdʒ'},
        ]
        return ({
            'score': 86,
            'transcript': 'language',
            'feedback': {
                'summary': '发音整体清晰，继续保持。',
                'stress': '重音稳定。',
                'vowel': '元音稳定。',
                'consonant': '辅音稳定。',
                'ending': '收音完整。',
                'rhythm': '韵律仅供参考。',
            },
            'segment_feedback': [
                {'text': 'lan', 'phonetic': 'læŋ', 'score': 90, 'status': 'good', 'comment': 'lan 稳定。'},
                {'text': 'guage', 'phonetic': 'gwɪdʒ', 'score': 82, 'status': 'ok', 'comment': 'guage 接近。'},
            ],
            'phoneme_feedback': [
                {'expectedPhoneme': 'l', 'score': 92, 'status': 'good', 'candidatePhonemes': []},
                {'expectedPhoneme': 'æ', 'score': 88, 'status': 'good', 'candidatePhonemes': []},
            ],
            'dimensions': {'phonemeAccuracy': 86, 'completeness': 92, 'fluency': 81, 'prosody': 75},
            'weak_segments': [],
            'provider': 'azure-pronunciation-dual-locale',
            'assessment_version': 'azure-pilot-v1',
        }, 'azure-rest:en-GB+en-US')

    monkeypatch.setattr(ai_follow_read_assessment_application, 'run_azure_follow_read_assessment', _fake_azure)
    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        '_run_follow_read_assessment',
        lambda **kwargs: (_ for _ in ()).throw(AssertionError('DashScope should not run')),
    )
    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        'record_learning_core_event',
        lambda user_id, **kwargs: recorded.setdefault('event', {'user_id': user_id, **kwargs}),
    )
    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        'post_learning_core_game_attempt',
        lambda user_id, data: recorded.setdefault('attempt', {'user_id': user_id, 'data': data}) or {'mastery_state': {'overall_status': 'mastered'}},
    )

    response = client.post(
        '/api/ai/follow-read/evaluate',
        data={
            'word': 'language',
            'phonetic': '/ˈlæŋɡwɪdʒ/',
            'segments': '[{"text":"lan","phonetic":"læŋ"},{"text":"guage","phonetic":"gwɪdʒ"}]',
        },
        files={'audio': ('user.wav', _build_tone_wav(), 'audio/wav')},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['score'] == 86
    assert payload['band'] == 'pass'
    assert payload['scoringProvider'] == 'azure-pronunciation-dual-locale'
    assert payload['assessmentVersion'] == 'azure-pilot-v1'
    assert payload['dimensions']['prosody'] == 75
    assert payload['phonemeFeedback'][0]['expectedPhoneme'] == 'l'
    assert payload['explanationToken']
    assert recorded['event']['payload']['score'] == 86
    assert recorded['attempt']['data']['passed'] is True


def test_ai_execution_follow_read_azure_failure_does_not_record_attempt(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    _enable_language_pilot(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_follow_read_azure_failure')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-follow-read-azure-fail')
    recorded = {'event': False, 'attempt': False}

    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        'run_azure_follow_read_assessment',
        lambda **kwargs: (_ for _ in ()).throw(
            follow_read_azure_assessment.AzureFollowReadAssessmentError('逐音素评分对齐失败，请重新跟读')
        ),
    )
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
        data={
            'word': 'language',
            'phonetic': '/ˈlæŋɡwɪdʒ/',
            'segments': '[{"text":"lan","phonetic":"læŋ"},{"text":"guage","phonetic":"gwɪdʒ"}]',
        },
        files={'audio': ('user.wav', _build_tone_wav(), 'audio/wav')},
        headers=_auth_headers(token),
    )

    assert response.status_code == 503
    assert response.json() == {'error': '逐音素评分对齐失败，请重新跟读'}
    assert recorded == {'event': False, 'attempt': False}


def test_ai_execution_follow_read_explain_route(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_follow_read_explain')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-follow-read-explain')

    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        'generate_follow_read_explanation',
        lambda token: f'建议已生成：{token}',
    )

    response = client.post(
        '/api/ai/follow-read/explain',
        json={'token': 'signed-token'},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == {'summary': '建议已生成：signed-token'}
