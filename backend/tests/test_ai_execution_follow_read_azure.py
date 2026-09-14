from __future__ import annotations

import json
import threading

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
    monkeypatch.setenv('AZURE_SPEECH_KEY', 'test-azure-key')
    monkeypatch.setenv('AZURE_SPEECH_REGION', 'eastus')
    follow_read_azure_assessment.reset_azure_follow_read_pilot_cache()


def test_ai_execution_follow_read_uses_azure_for_non_pilot_words_with_phonetics(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    _enable_language_pilot(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_follow_read_azure')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-follow-read-azure')
    recorded: dict[str, dict] = {}

    def _fake_azure(**kwargs):
        assert kwargs['word'] == 'attention'
        assert kwargs['segments'] == [
            {'text': 'at', 'phonetic': 'ə'},
            {'text': 'ten', 'phonetic': 'ten'},
        ]
        return ({
            'score': 86,
            'transcript': 'attention',
            'feedback': {
                'summary': '发音整体清晰，继续保持。',
                'stress': '重音稳定。',
                'vowel': '元音稳定。',
                'consonant': '辅音稳定。',
                'ending': '收音完整。',
                'rhythm': '韵律仅供参考。',
            },
            'segment_feedback': [
                {'text': 'at', 'phonetic': 'ə', 'score': 90, 'status': 'good', 'comment': 'at 稳定。'},
                {'text': 'ten', 'phonetic': 'ten', 'score': 82, 'status': 'ok', 'comment': 'ten 接近。'},
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
            'word': 'attention',
            'phonetic': '/əˈtenʃn/',
            'segments': '[{"text":"at","phonetic":"ə"},{"text":"ten","phonetic":"ten"}]',
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


def test_azure_follow_read_requests_gb_and_us_concurrently(monkeypatch, tmp_path):
    wav_path = tmp_path / 'sample.wav'
    wav_path.write_bytes(b'RIFF')
    started: list[str] = []
    both_started = threading.Event()

    def _payload(locale: str) -> dict:
        return {
            'RecognitionStatus': 'Success',
            'NBest': [{
                'Display': 'la',
                'PronunciationAssessment': {'CompletenessScore': 90, 'FluencyScore': 80, 'ProsodyScore': 70},
                'Words': [{
                    'PronunciationAssessment': {},
                    'Phonemes': [
                        {'Phoneme': 'l', 'PronunciationAssessment': {'AccuracyScore': 90}},
                        {'Phoneme': 'æ', 'PronunciationAssessment': {'AccuracyScore': 80}},
                    ],
                }],
            }],
        }

    def _fake_request(_wav_path, *, word: str, locale: str):
        assert word == 'la'
        started.append(locale)
        if len(started) == 2:
            both_started.set()
        assert both_started.wait(1), 'Azure locale requests should overlap'
        return _payload(locale)

    monkeypatch.setattr(follow_read_azure_assessment, '_write_pcm_wav', lambda _audio_path: str(wav_path))
    monkeypatch.setattr(follow_read_azure_assessment, '_request_assessment', _fake_request)

    result, model = follow_read_azure_assessment.run_azure_follow_read_assessment(
        audio_path='input.webm',
        word='la',
        segments=[{'text': 'la', 'phonetic': 'l æ'}],
    )

    assert set(started) == {'en-GB', 'en-US'}
    assert model == 'azure-rest:en-GB+en-US'
    assert result['provider'] == 'azure-pronunciation-dual-locale'


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
