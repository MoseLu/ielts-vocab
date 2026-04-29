from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from models import AISpeakingAssessment, User, db
from platform_sdk.internal_service_auth import create_internal_auth_headers_for_user
from platform_sdk import ai_follow_read_assessment_application, ai_speaking_assessment_application


SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'ai-execution-service'
    / 'main.py'
)


def _load_ai_execution_service_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _configure_ai_env(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / 'ai-execution-speaking.sqlite'
    database_uri = f'sqlite:///{database_path.as_posix()}'
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(database_path))
    monkeypatch.setenv('SQLALCHEMY_DATABASE_URI', database_uri)
    monkeypatch.setenv('AI_EXECUTION_SERVICE_SQLITE_DB_PATH', str(database_path))
    monkeypatch.setenv('AI_EXECUTION_SERVICE_SQLALCHEMY_DATABASE_URI', database_uri)
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'ai-execution-service')
    monkeypatch.setenv('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK', 'true')


def _create_user_and_token(flask_app, username='ai-speaking-user') -> str:
    with flask_app.app_context():
        db.create_all()
        user = User(username=username, email=f'{username}@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        return jwt.encode(
            {
                'user_id': user.id,
                'type': 'access',
                'jti': str(uuid.uuid4()),
                'iat': int(datetime.utcnow().timestamp()),
                'exp': datetime.utcnow() + timedelta(seconds=flask_app.config['JWT_ACCESS_TOKEN_EXPIRES']),
            },
            flask_app.config['JWT_SECRET_KEY'],
            algorithm='HS256',
        )


def _auth_headers(token: str) -> dict[str, str]:
    payload = jwt.decode(token, options={'verify_signature': False})
    return create_internal_auth_headers_for_user(
        user_id=int(payload['user_id']),
        source_service_name='gateway-bff',
        env={'INTERNAL_SERVICE_JWT_SECRET_KEY': 'test-jwt-secret'},
    )


def test_ai_execution_service_speaking_prompts_route(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_speaking_prompts')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-speaking-prompts')

    response = client.post(
        '/api/ai/speaking/prompts',
        json={'part': 2, 'topic': 'education', 'targetWords': ['dynamic']},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['recommendedDurationSeconds'] == 120
    assert 'dynamic' in payload['promptText']


def test_ai_execution_service_speaking_evaluate_persists_assessment(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_speaking_evaluate')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-speaking-evaluate')
    recorded: dict[str, dict] = {}

    monkeypatch.setattr(
        ai_speaking_assessment_application,
        '_transcribe_audio_bytes',
        lambda **kwargs: 'Dynamic planning requires coherent examples.',
    )
    monkeypatch.setattr(
        ai_speaking_assessment_application,
        '_run_speaking_assessment',
        lambda **kwargs: ({
            'raw_scores': {
                'fluency': 78,
                'lexical': 73,
                'grammar': 70,
                'pronunciation': 81,
            },
            'feedback': {
                'summary': 'The response is generally clear and relevant.',
                'strengths': ['Relevant answer'],
                'priorities': ['Add more precise detail'],
                'dimensionFeedback': {
                    'fluency': 'Reasonably fluent overall.',
                    'lexical': 'Shows some range with minor repetition.',
                    'grammar': 'Uses a mix of sentence types with some slips.',
                    'pronunciation': 'Mostly easy to understand.',
                },
            },
        }, 'qwen-audio-turbo'),
    )
    monkeypatch.setattr(
        ai_speaking_assessment_application,
        'record_learning_core_event',
        lambda user_id, **kwargs: recorded.setdefault('event', {'user_id': user_id, **kwargs}),
    )
    monkeypatch.setattr(
        ai_speaking_assessment_application,
        'record_ai_prompt_run_completion',
        lambda **kwargs: recorded.setdefault('prompt_run', kwargs),
    )

    response = client.post(
        '/api/ai/speaking/evaluate',
        data={
            'part': '2',
            'topic': 'education',
            'promptText': 'Describe an education experience.',
            'targetWords[]': 'dynamic',
            'bookId': 'book-1',
            'chapterId': '2',
            'durationSeconds': '64',
        },
        files={'audio': ('sample.wav', b'RIFFtest', 'audio/wav')},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['overallBand'] == 7.5
    assert payload['dimensionBands']['pronunciation'] == 7.5
    assert payload['metrics']['wordCount'] > 0

    with module.ai_flask_app.app_context():
        assessment = AISpeakingAssessment.query.one()
        assert assessment.topic == 'education'
        assert assessment.target_words() == ['dynamic']
        assert assessment.metrics_dict()['durationSeconds'] == 64

    assert recorded['event']['event_type'] == 'speaking_assessment_completed'
    assert recorded['event']['payload']['overall_band'] == 7.5
    assert recorded['prompt_run']['run_kind'] == 'speaking.assessment.evaluate'


def test_ai_execution_service_speaking_evaluate_returns_model_validation_error(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_speaking_invalid')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-speaking-invalid')

    monkeypatch.setattr(
        ai_speaking_assessment_application,
        '_transcribe_audio_bytes',
        lambda **kwargs: 'Hello world',
    )
    monkeypatch.setattr(
        ai_speaking_assessment_application,
        '_run_speaking_assessment',
        lambda **kwargs: (_ for _ in ()).throw(
            ai_speaking_assessment_application.SpeakingAssessmentError(
                '评分模型返回了无效 JSON',
                status_code=502,
            )
        ),
    )

    response = client.post(
        '/api/ai/speaking/evaluate',
        data={'part': '1', 'topic': 'music'},
        files={'audio': ('sample.wav', b'RIFFtest', 'audio/wav')},
        headers=_auth_headers(token),
    )

    assert response.status_code == 502
    assert response.json() == {'error': '评分模型返回了无效 JSON'}


def test_ai_execution_service_follow_read_evaluate_records_speaking_attempt(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_follow_read_evaluate')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-follow-read')
    recorded: dict[str, dict] = {}

    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        '_run_follow_read_assessment',
        lambda **kwargs: ({
            'score': 76,
            'transcript': 'phenomenon',
            'feedback': {
                'summary': 'Close but not passed.',
                'stress': 'Stress is close.',
                'vowel': 'Open the middle vowel.',
                'consonant': 'Consonants are clear.',
                'ending': 'Finish the final sound.',
                'rhythm': 'Rhythm is steady.',
            },
            'weak_segments': ['no'],
        }, 'qwen-audio-turbo'),
    )
    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        'record_learning_core_event',
        lambda user_id, **kwargs: recorded.setdefault('event', {'user_id': user_id, **kwargs}),
    )
    monkeypatch.setattr(
        ai_follow_read_assessment_application,
        'post_learning_core_game_attempt',
        lambda user_id, data: recorded.setdefault('attempt', {'user_id': user_id, 'data': data}) or {'mastery_state': {'overall_status': 'in_review'}},
    )

    response = client.post(
        '/api/ai/follow-read/evaluate',
        data={
            'word': 'phenomenon',
            'phonetic': '/fəˈnɒmɪnən/',
            'bookId': 'book-1',
            'chapterId': '2',
            'durationSeconds': '4',
        },
        files={
            'audio': ('user.webm', b'user-audio', 'audio/webm'),
            'referenceAudio': ('reference.mp3', b'reference-audio', 'audio/mpeg'),
        },
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['score'] == 76
    assert payload['band'] == 'near_pass'
    assert payload['passed'] is False
    assert payload['weakSegments'] == ['no']
    assert recorded['event']['event_type'] == 'follow_read_pronunciation_check'
    assert recorded['event']['mode'] == 'follow'
    assert recorded['attempt']['data']['dimension'] == 'speaking'
    assert recorded['attempt']['data']['sourceMode'] == 'follow'


def test_ai_execution_service_speaking_evaluate_respects_custom_band_thresholds(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    monkeypatch.setenv(
        'SPEAKING_ASSESSMENT_BAND_THRESHOLDS_JSON',
        '[[80, 8.0], [70, 7.0], [60, 6.0], [0, 0.0]]',
    )
    module = _load_ai_execution_service_module('ai_execution_service_speaking_custom_band_thresholds')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-speaking-custom-thresholds')

    monkeypatch.setattr(
        ai_speaking_assessment_application,
        '_transcribe_audio_bytes',
        lambda **kwargs: 'Dynamic planning requires coherent examples.',
    )
    monkeypatch.setattr(
        ai_speaking_assessment_application,
        '_run_speaking_assessment',
        lambda **kwargs: ({
            'raw_scores': {
                'fluency': 78,
                'lexical': 73,
                'grammar': 70,
                'pronunciation': 81,
            },
            'feedback': {
                'summary': 'The response is generally clear and relevant.',
                'strengths': ['Relevant answer'],
                'priorities': ['Add more precise detail'],
                'dimensionFeedback': {
                    'fluency': 'Reasonably fluent overall.',
                    'lexical': 'Shows some range with minor repetition.',
                    'grammar': 'Uses a mix of sentence types with some slips.',
                    'pronunciation': 'Mostly easy to understand.',
                },
            },
        }, 'qwen-audio-turbo'),
    )
    monkeypatch.setattr(ai_speaking_assessment_application, 'record_learning_core_event', lambda *args, **kwargs: None)
    monkeypatch.setattr(ai_speaking_assessment_application, 'record_ai_prompt_run_completion', lambda **kwargs: None)

    response = client.post(
        '/api/ai/speaking/evaluate',
        data={'part': '2', 'topic': 'education'},
        files={'audio': ('sample.wav', b'RIFFtest', 'audio/wav')},
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['dimensionBands'] == {
        'fluency': 7.0,
        'lexical': 7.0,
        'grammar': 7.0,
        'pronunciation': 8.0,
    }
    assert payload['overallBand'] == 7.5


def test_ai_execution_service_speaking_history_returns_latest_rows(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_speaking_history')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-speaking-history')

    with module.ai_flask_app.app_context():
        user = User.query.filter_by(username='ai-speaking-history').one()
        assessment = AISpeakingAssessment(
            user_id=user.id,
            part=3,
            topic='technology',
            prompt_text='Why does technology matter?',
            transcript='Technology changes education quickly.',
            overall_band=6.5,
            fluency_band=6.5,
            lexical_band=6.0,
            grammar_band=6.5,
            pronunciation_band=7.0,
            provider='dashscope',
            model='qwen-audio-turbo',
        )
        assessment.set_target_words(['technology'])
        assessment.set_metrics({'wordCount': 4})
        assessment.set_feedback({'summary': 'Solid answer.'})
        db.session.add(assessment)
        db.session.commit()

    response = client.get(
        '/api/ai/speaking/history?limit=5',
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['items'][0]['topic'] == 'technology'
    assert payload['items'][0]['targetWords'] == ['technology']


def test_ai_execution_service_speaking_history_detail_returns_full_assessment(monkeypatch, tmp_path):
    _configure_ai_env(monkeypatch, tmp_path)
    module = _load_ai_execution_service_module('ai_execution_service_speaking_history_detail')
    client = TestClient(module.app)
    token = _create_user_and_token(module.ai_flask_app, username='ai-speaking-history-detail')

    with module.ai_flask_app.app_context():
        user = User.query.filter_by(username='ai-speaking-history-detail').one()
        assessment = AISpeakingAssessment(
            user_id=user.id,
            part=1,
            topic='travel',
            prompt_text='What kind of travel do you enjoy?',
            transcript='I enjoy short city trips with friends.',
            overall_band=6.0,
            fluency_band=6.0,
            lexical_band=6.0,
            grammar_band=6.0,
            pronunciation_band=6.5,
            provider='dashscope',
            model='qwen-audio-turbo',
        )
        assessment.set_target_words(['travel', 'trip'])
        assessment.set_metrics({'wordCount': 7, 'targetWordsUsed': ['travel']})
        assessment.set_feedback({
            'summary': 'Clear answer.',
            'strengths': ['Relevant response'],
            'priorities': ['Add more detail'],
            'dimensionFeedback': {
                'fluency': 'Mostly smooth.',
                'lexical': 'Adequate range.',
                'grammar': 'Simple but controlled.',
                'pronunciation': 'Easy to follow.',
            },
        })
        db.session.add(assessment)
        db.session.commit()
        assessment_id = assessment.id

    response = client.get(
        f'/api/ai/speaking/history/{assessment_id}',
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['assessmentId'] == assessment_id
    assert payload['topic'] == 'travel'
    assert payload['targetWords'] == ['travel', 'trip']
    assert payload['feedback']['summary'] == 'Clear answer.'
