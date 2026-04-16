from io import BytesIO

from models import User
from platform_sdk import ai_speaking_assessment_application
from services.learner_profile import build_learner_profile
from services.local_time import current_local_date


def register_and_login(client, username='speaking-monolith-user', password='password123'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@example.com',
    })
    response = client.post('/api/auth/login', json={
        'email': username,
        'password': password,
    })
    assert response.status_code == 200


def test_monolith_speaking_routes_support_prompt_evaluate_and_history(client, app, monkeypatch):
    register_and_login(client)

    monkeypatch.setattr(
        ai_speaking_assessment_application,
        '_transcribe_audio_bytes',
        lambda **kwargs: 'Dynamic planning needs coherent examples.',
    )
    monkeypatch.setattr(
        ai_speaking_assessment_application,
        '_run_speaking_assessment',
        lambda **kwargs: ({
            'raw_scores': {
                'fluency': 62,
                'lexical': 62,
                'grammar': 62,
                'pronunciation': 69,
            },
            'feedback': {
                'summary': 'The answer is understandable with room to expand.',
                'strengths': ['Relevant response'],
                'priorities': ['Add more precise detail'],
                'dimensionFeedback': {
                    'fluency': 'Mostly steady with some hesitation.',
                    'lexical': 'Adequate range for the task.',
                    'grammar': 'Some control of sentence patterns.',
                    'pronunciation': 'Generally understandable.',
                },
            },
        }, 'qwen-audio-turbo'),
    )
    monkeypatch.setattr(
        ai_speaking_assessment_application,
        'record_learning_core_event',
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError('force-local-fallback')),
    )
    monkeypatch.setattr(
        ai_speaking_assessment_application,
        'record_ai_prompt_run_completion',
        lambda **kwargs: None,
    )

    prompts_response = client.post('/api/ai/speaking/prompts', json={
        'part': 2,
        'topic': 'education',
        'targetWords': ['dynamic'],
    })
    assert prompts_response.status_code == 200
    assert 'dynamic' in prompts_response.get_json()['promptText']

    evaluate_response = client.post('/api/ai/speaking/evaluate', data={
        'part': '2',
        'topic': 'education',
        'promptText': 'Describe an education experience.',
        'targetWords[]': 'dynamic',
        'bookId': 'ielts_speaking',
        'chapterId': '2',
        'durationSeconds': '48',
        'audio': (BytesIO(b'RIFFtest'), 'sample.wav'),
    }, content_type='multipart/form-data')
    assert evaluate_response.status_code == 200
    evaluate_payload = evaluate_response.get_json()
    assert evaluate_payload['overallBand'] == 6.5
    assert evaluate_payload['dimensionBands']['pronunciation'] == 7.0

    history_response = client.get('/api/ai/speaking/history?limit=5')
    assert history_response.status_code == 200
    history_payload = history_response.get_json()
    assert history_payload['items'][0]['topic'] == 'education'
    assert history_payload['items'][0]['targetWords'] == ['dynamic']

    detail_response = client.get(f"/api/ai/speaking/history/{evaluate_payload['assessmentId']}")
    assert detail_response.status_code == 200
    detail_payload = detail_response.get_json()
    assert detail_payload['topic'] == 'education'
    assert detail_payload['transcript'] == 'Dynamic planning needs coherent examples.'

    with app.app_context():
        user = User.query.filter_by(username='speaking-monolith-user').one()
        profile = build_learner_profile(user.id, current_local_date().isoformat())
        assert profile['activity_summary']['speaking_assessments'] == 1
        assert any(item['title'] == '口语估分 Part 2 education 6.5分' for item in profile['recent_activity'])
