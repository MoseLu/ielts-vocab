from datetime import datetime
from io import BytesIO

from models import User, UserLearningEvent, db
from services.learning_events import record_learning_event
from services.learner_profile import build_learner_profile
from services import ai_assistant_ask_service as ask_service
from services import ai_practice_support_service as practice_support_service
from services.local_time import current_local_date
from platform_sdk import ai_speaking_assessment_application
from werkzeug.datastructures import FileStorage, MultiDict


def register_and_login(client, username='event-user', password='password123'):
    client.post('/api/auth/register', json={
        'username': username,
        'password': password,
        'email': f'{username}@example.com',
    })
    res = client.post('/api/auth/login', json={
        'email': username,
        'password': password,
    })
    assert res.status_code == 200


def test_record_learning_event_normalizes_registered_mode_alias(app):
    with app.app_context():
        user = User(username='event-mode-user', email='event-mode-user@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()

        event = record_learning_event(
            user_id=user.id,
            event_type='wrong_word_recorded',
            source='wrong_words',
            mode='quick_memory',
            word='effect',
        )
        db.session.commit()

        assert event.mode == 'quickmemory'
        assert UserLearningEvent.query.filter_by(mode='quickmemory').count() == 1


def test_learner_profile_activity_summary_merges_events_from_multiple_sources(client, app, monkeypatch):
    register_and_login(client)

    start_res = client.post('/api/ai/start-session', json={
        'mode': 'listening',
        'bookId': 'ielts_reading_premium',
        'chapterId': '3',
    })
    assert start_res.status_code == 201
    session_id = start_res.get_json()['sessionId']

    log_res = client.post('/api/ai/log-session', json={
        'sessionId': session_id,
        'mode': 'listening',
        'bookId': 'ielts_reading_premium',
        'chapterId': '3',
        'wordsStudied': 12,
        'correctCount': 9,
        'wrongCount': 3,
        'durationSeconds': 180,
        'startedAt': int(datetime.utcnow().timestamp() * 1000),
    })
    assert log_res.status_code == 200

    qm_res = client.post('/api/ai/quick-memory/sync', json={
        'source': 'quickmemory',
        'records': [{
            'word': 'kind',
            'bookId': 'ielts_reading_premium',
            'chapterId': '3',
            'status': 'known',
            'firstSeen': 1,
            'lastSeen': 2,
            'knownCount': 1,
            'unknownCount': 0,
            'nextReview': 3,
            'fuzzyCount': 0,
        }],
    })
    assert qm_res.status_code == 200

    wrong_res = client.post('/api/ai/wrong-words/sync', json={
        'sourceMode': 'listening',
        'bookId': 'ielts_reading_premium',
        'chapterId': '3',
        'words': [{
            'word': 'effect',
            'definition': 'result',
            'wrongCount': 1,
            'listeningWrong': 1,
        }],
    })
    assert wrong_res.status_code == 200

    monkeypatch.setattr(ask_service, 'chat_with_tools', lambda *args, **kwargs: {'text': '已回答'})
    ask_res = client.post('/api/ai/ask', json={
        'message': 'kind 和 effect 有什么区别？',
        'context': {
            'currentWord': 'kind',
            'practiceMode': 'listening',
        },
    })
    assert ask_res.status_code == 200

    today = current_local_date().isoformat()
    profile_res = client.get(f'/api/ai/learner-profile?date={today}')
    assert profile_res.status_code == 200
    data = profile_res.get_json()

    assert data['activity_summary']['total_events'] >= 4
    assert data['activity_summary']['study_sessions'] >= 1
    assert data['activity_summary']['quick_memory_reviews'] >= 1
    assert data['activity_summary']['wrong_word_records'] >= 1
    assert data['activity_summary']['assistant_questions'] >= 1
    assert any(item['source'] == 'quickmemory' for item in data['activity_source_breakdown'])
    assert any('向助手提问' in item['title'] for item in data['recent_activity'])

    with app.app_context():
        assert UserLearningEvent.query.count() >= 4


def test_speaking_routes_record_learning_events_and_timeline_titles(client, app):
    register_and_login(client, username='speaking-event-user')

    pronunciation_res = client.post('/api/ai/pronunciation-check', json={
        'word': 'dynamic',
        'transcript': 'dynamic',
        'sentence': 'Dynamic pricing can confuse users.',
        'bookId': 'ielts_speaking',
        'chapterId': '2',
    })
    assert pronunciation_res.status_code == 200
    assert pronunciation_res.get_json()['passed'] is True

    speaking_res = client.post('/api/ai/speaking-simulate', json={
        'part': 2,
        'topic': 'education',
        'targetWords': ['dynamic', 'coherent'],
        'responseText': 'Dynamic activities need coherent planning.',
        'bookId': 'ielts_speaking',
        'chapterId': '2',
    })
    assert speaking_res.status_code == 200

    with app.app_context():
        pronunciation_event = UserLearningEvent.query.filter_by(event_type='pronunciation_check').first()
        assert pronunciation_event is not None
        assert pronunciation_event.word == 'dynamic'
        assert pronunciation_event.mode == 'speaking'
        assert pronunciation_event.correct_count == 1
        assert pronunciation_event.payload_dict()['sentence'] == 'Dynamic pricing can confuse users.'

        simulation_event = UserLearningEvent.query.filter_by(event_type='speaking_simulation').first()
        assert simulation_event is not None
        assert simulation_event.mode == 'speaking'
        assert simulation_event.payload_dict()['target_words'] == ['dynamic', 'coherent']
        assert simulation_event.payload_dict()['response_text'] == 'Dynamic activities need coherent planning.'

    today = current_local_date().isoformat()
    profile_res = client.get(f'/api/ai/learner-profile?date={today}')
    assert profile_res.status_code == 200
    data = profile_res.get_json()

    assert data['activity_summary']['pronunciation_checks'] == 1
    assert data['activity_summary']['speaking_simulations'] == 1
    assert any(item['title'] == '发音检查 dynamic 通过' for item in data['recent_activity'])
    assert any(item['title'] == '口语模拟 Part 2 education 已作答' for item in data['recent_activity'])


def test_pronunciation_check_accepts_normalized_single_word_transcript(client):
    register_and_login(client, username='pronunciation-normalize-user')

    response = client.post('/api/ai/pronunciation-check', json={
        'word': 'dynamic',
        'transcript': 'Dynamic, please.',
        'bookId': 'ielts_reading_premium',
        'chapterId': '1',
    })

    assert response.status_code == 200
    assert response.get_json()['passed'] is True


def test_speaking_assessment_route_records_learning_event_and_profile_summary(client, app, monkeypatch):
    register_and_login(client, username='speaking-assessment-user')

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
                'pronunciation': 62,
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
        'record_ai_prompt_run_completion',
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        ai_speaking_assessment_application,
        'record_learning_core_event',
        lambda user_id, **kwargs: record_learning_event(user_id=user_id, **kwargs),
    )

    with app.app_context():
        user = User.query.filter_by(username='speaking-assessment-user').one()
        form = MultiDict([
            ('part', '2'),
            ('topic', 'education'),
            ('promptText', 'Describe an education experience.'),
            ('targetWords[]', 'dynamic'),
            ('bookId', 'ielts_speaking'),
            ('chapterId', '2'),
            ('durationSeconds', '48'),
        ])
        files = MultiDict({
            'audio': FileStorage(
                stream=BytesIO(b'RIFFtest'),
                filename='sample.wav',
                content_type='audio/wav',
            ),
        })
        response, status = ai_speaking_assessment_application.evaluate_speaking_response(user, form, files)
        assert status == 200
        assert response.get_json()['overallBand'] == 6.5

        event = UserLearningEvent.query.filter_by(event_type='speaking_assessment_completed').one()
        assert event.mode == 'speaking'
        assert event.payload_dict()['overall_band'] == 6.5
        assert event.payload_dict()['target_words'] == ['dynamic']
        data = build_learner_profile(user.id, current_local_date().isoformat())
        assert data['activity_summary']['speaking_assessments'] == 1
        assert any(item['title'] == '口语估分 Part 2 education 6.5分' for item in data['recent_activity'])


def test_smart_stats_sync_records_meaning_listening_and_writing_events(client, app):
    register_and_login(client, username='smart-event-user')

    res = client.post('/api/ai/smart-stats/sync', json={
        'context': {
            'bookId': 'ielts_listening_premium',
            'chapterId': '4',
            'mode': 'quick_memory',
        },
        'stats': [{
            'word': 'dynamic',
            'listening': {'correct': 2, 'wrong': 1},
            'meaning': {'correct': 1, 'wrong': 1},
            'dictation': {'correct': 1, 'wrong': 1},
        }],
    })

    assert res.status_code == 200

    with app.app_context():
        meaning_event = UserLearningEvent.query.filter_by(event_type='meaning_review').first()
        assert meaning_event is not None
        assert meaning_event.word == 'dynamic'
        assert meaning_event.correct_count == 1
        assert meaning_event.wrong_count == 1

        listening_event = UserLearningEvent.query.filter_by(event_type='listening_review').first()
        assert listening_event is not None
        assert listening_event.word == 'dynamic'
        assert listening_event.book_id == 'ielts_listening_premium'
        assert listening_event.chapter_id == '4'
        assert listening_event.correct_count == 2
        assert listening_event.wrong_count == 1
        assert listening_event.payload_dict()['source_mode'] == 'quickmemory'

        writing_event = UserLearningEvent.query.filter_by(event_type='writing_review').first()
        assert writing_event is not None
        assert writing_event.word == 'dynamic'
        assert writing_event.correct_count == 1
        assert writing_event.wrong_count == 1

    today = current_local_date().isoformat()
    profile_res = client.get(f'/api/ai/learner-profile?date={today}')
    assert profile_res.status_code == 200
    data = profile_res.get_json()

    assert data['activity_summary']['meaning_reviews'] == 1
    assert data['activity_summary']['listening_reviews'] == 1
    assert data['activity_summary']['writing_reviews'] == 1
    assert any(item['title'] == '释义检查 dynamic 待强化' for item in data['recent_activity'])
    assert any(item['title'] == '听力检查 dynamic 通过' for item in data['recent_activity'])
    assert any(item['title'] == '书写检查 dynamic 待强化' for item in data['recent_activity'])


def test_ai_tool_metrics_are_exposed_via_profile_and_context(client, monkeypatch):
    register_and_login(client, username='ai-tool-event-user')

    monkeypatch.setattr(practice_support_service, 'correct_text', lambda text: {
        'is_valid_english': True,
        'original_text': text,
        'corrected_text': text,
        'explanation': 'ok',
    })

    correction_res = client.post('/api/ai/correct-text', json={'text': 'This is a sample sentence.'})
    assert correction_res.status_code == 200

    feedback_res = client.post('/api/ai/correction-feedback', json={'adopted': True})
    assert feedback_res.status_code == 200

    today = current_local_date().isoformat()
    profile_res = client.get(f'/api/ai/learner-profile?date={today}')
    assert profile_res.status_code == 200
    profile = profile_res.get_json()

    assert profile['activity_summary']['assistant_tool_uses'] == 2
    assert any(item['event_type'] == 'writing_correction_used' for item in profile['activity_event_breakdown'])
    assert any(item['event_type'] == 'writing_correction_adoption' for item in profile['activity_event_breakdown'])
    assert any('写作纠错' in item['title'] for item in profile['recent_activity'])

    context_res = client.get('/api/ai/context')
    assert context_res.status_code == 200
    context_data = context_res.get_json()

    assert context_data['activityTimeline']['summary']['assistant_tool_uses'] == 2
    assert any(
        item['event_type'] == 'writing_correction_used'
        for item in context_data['activityTimeline']['event_breakdown']
    )
