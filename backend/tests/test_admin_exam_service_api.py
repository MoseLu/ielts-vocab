from __future__ import annotations

import importlib.util
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from models import (
    ExamAnswerKey,
    ExamIngestionJob,
    ExamPaper,
    ExamPassage,
    ExamQuestion,
    ExamReviewItem,
    ExamSection,
    ExamSource,
    User,
    db,
)
from platform_sdk.internal_service_auth import create_internal_auth_headers_for_user


SERVICE_PATH = (
    Path(__file__).resolve().parents[2]
    / 'services'
    / 'admin-ops-service'
    / 'main.py'
)


def _load_admin_ops_service_module(module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, SERVICE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _configure_admin_env(monkeypatch, tmp_path: Path) -> None:
    database_path = tmp_path / 'admin-exams.sqlite'
    database_uri = f'sqlite:///{database_path.as_posix()}'
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    monkeypatch.setenv('COOKIE_SECURE', 'false')
    monkeypatch.setenv('EMAIL_CODE_DELIVERY_MODE', 'mock')
    monkeypatch.setenv('SQLITE_DB_PATH', str(database_path))
    monkeypatch.setenv('SQLALCHEMY_DATABASE_URI', database_uri)
    monkeypatch.setenv('ADMIN_OPS_SERVICE_SQLITE_DB_PATH', str(database_path))
    monkeypatch.setenv('ADMIN_OPS_SERVICE_SQLALCHEMY_DATABASE_URI', database_uri)
    monkeypatch.setenv('DB_BACKUP_ENABLED', 'false')
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'admin-ops-service')


def _create_access_token(flask_app, *, user_id: int, is_admin: bool, username: str, email: str) -> str:
    return jwt.encode(
        {
            'user_id': user_id,
            'type': 'access',
            'is_admin': is_admin,
            'username': username,
            'email': email,
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
        is_admin=bool(payload.get('is_admin')),
        username=str(payload.get('username') or ''),
        email=str(payload.get('email') or ''),
        env={'INTERNAL_SERVICE_JWT_SECRET_KEY': 'test-jwt-secret'},
    )


def _seed_users(flask_app) -> tuple[dict[str, object], dict[str, object]]:
    with flask_app.app_context():
        db.create_all()
        admin = User(username='exam-admin', email='exam-admin@example.com', is_admin=True)
        admin.set_password('password123')
        learner = User(username='exam-learner', email='exam-learner@example.com', is_admin=False)
        learner.set_password('password123')
        db.session.add_all([admin, learner])
        db.session.commit()
        return (
            {'id': admin.id, 'username': admin.username, 'email': admin.email},
            {'id': learner.id, 'username': learner.username, 'email': learner.email},
        )


def _seed_exam_paper(flask_app, *, publish_status: str = 'published_internal') -> int:
    with flask_app.app_context():
        source = ExamSource(
            source_type='github',
            source_url='https://github.com/vaakian/IELTS/tree/main',
            owner='vaakian',
            repo='IELTS',
            ref='main',
            root_path='',
            rights_status='restricted_internal',
        )
        db.session.add(source)
        db.session.flush()
        paper = ExamPaper(
            source_id=source.id,
            external_key='github:vaakian/IELTS:s20:t1',
            collection_key='cambridge-20',
            collection_title='剑雅20 IELTS ACADEMIC',
            title='Test 1',
            exam_kind='academic',
            series_number=20,
            test_number=1,
            rights_status='restricted_internal',
            publish_status=publish_status,
            parser_strategy='multimodal',
            has_listening_audio=True,
        )
        db.session.add(paper)
        db.session.flush()
        section = ExamSection(
            paper_id=paper.id,
            section_type='reading',
            sort_order=1,
            title='Reading',
            html_content='<p>Read the passage.</p>',
            confidence=0.91,
        )
        db.session.add(section)
        db.session.flush()
        passage = ExamPassage(
            section_id=section.id,
            sort_order=1,
            title='Passage 1',
            html_content='<p>The library opens at 9 am.</p>',
            source_page_from=1,
            source_page_to=1,
            confidence=0.95,
        )
        db.session.add(passage)
        db.session.flush()
        question = ExamQuestion(
            section_id=section.id,
            passage_id=passage.id,
            group_key='reading-1',
            question_number=1,
            sort_order=1,
            question_type='fill_blank',
            prompt_html='<p>What time does the library open?</p>',
            confidence=0.92,
        )
        db.session.add(question)
        db.session.flush()
        db.session.add(ExamAnswerKey(
            question_id=question.id,
            sort_order=1,
            answer_kind='accepted_answer',
            answer_text='9 am',
            normalized_text='9am',
        ))
        db.session.commit()
        return paper.id


def _seed_reviewable_exam_paper(flask_app) -> tuple[int, int, int, int]:
    with flask_app.app_context():
        source = ExamSource(
            source_type='github',
            source_url='https://github.com/vaakian/IELTS/tree/main/Cambridge 20',
            owner='vaakian',
            repo='IELTS',
            ref='main',
            root_path='Cambridge 20',
            rights_status='restricted_internal',
        )
        db.session.add(source)
        db.session.flush()
        paper = ExamPaper(
            source_id=source.id,
            external_key='github:vaakian/IELTS:s20:t2',
            collection_key='cambridge-20',
            collection_title='剑雅20 IELTS ACADEMIC',
            title='Draft Test 2',
            exam_kind='academic',
            series_number=20,
            test_number=2,
            rights_status='restricted_internal',
            publish_status='in_review',
            parser_strategy='multimodal',
            has_listening_audio=False,
        )
        db.session.add(paper)
        db.session.flush()
        section = ExamSection(
            paper_id=paper.id,
            section_type='unknown',
            sort_order=1,
            title='Section 1',
            html_content='<p>Needs cleanup.</p>',
            confidence=0.61,
        )
        section.set_metadata({'audioTracks': []})
        db.session.add(section)
        db.session.flush()
        passage = ExamPassage(
            section_id=section.id,
            sort_order=1,
            title='Draft passage',
            html_content='<p>Draft text.</p>',
            source_page_from=1,
            source_page_to=1,
            confidence=0.62,
        )
        db.session.add(passage)
        db.session.flush()
        question = ExamQuestion(
            section_id=section.id,
            passage_id=passage.id,
            group_key='unknown-1',
            question_number=1,
            sort_order=1,
            question_type='short_answer',
            prompt_html='<p>Draft prompt</p>',
            confidence=0.6,
        )
        db.session.add(question)
        db.session.flush()
        review_item = ExamReviewItem(
            paper_id=paper.id,
            section_id=section.id,
            question_id=question.id,
            item_type='missing_answer_key',
            severity='warning',
            status='open',
            message='Missing answer key',
        )
        db.session.add(review_item)
        job = ExamIngestionJob(
            source_id=source.id,
            status='completed',
            repo_url=source.source_url,
            audio_repo_url='https://github.com/vaakian/IELTS/tree/main/雅思真题音频',
            parser_model='qwen3-omni-flash',
            stitch_model='qwen3.5-omni-plus',
            started_at=datetime.utcnow() - timedelta(minutes=5),
            finished_at=datetime.utcnow(),
        )
        job.set_summary({'paperCount': 1, 'audioCount': 4})
        db.session.add(job)
        db.session.commit()
        return paper.id, passage.id, question.id, job.id


def test_admin_ops_service_supports_exam_attempt_flow(monkeypatch, tmp_path):
    _configure_admin_env(monkeypatch, tmp_path)
    module = _load_admin_ops_service_module('admin_ops_service_exam_routes')
    client = TestClient(module.app)
    _, learner = _seed_users(module.admin_ops_flask_app)
    paper_id = _seed_exam_paper(module.admin_ops_flask_app)
    learner_token = _create_access_token(
        module.admin_ops_flask_app,
        user_id=int(learner['id']),
        is_admin=False,
        username=str(learner['username']),
        email=str(learner['email']),
    )

    list_response = client.get('/api/exams', headers=_auth_headers(learner_token))
    detail_response = client.get(f'/api/exams/{paper_id}', headers=_auth_headers(learner_token))
    create_attempt_response = client.post(f'/api/exams/{paper_id}/attempts', headers=_auth_headers(learner_token))

    assert list_response.status_code == 200
    assert list_response.json()['items'][0]['title'] == 'Test 1'
    assert detail_response.status_code == 200
    assert detail_response.json()['paper']['sections'][0]['questions'][0]['questionNumber'] == 1
    assert create_attempt_response.status_code == 201

    attempt_id = create_attempt_response.json()['attempt']['id']
    save_response = client.patch(
        f'/api/exam-attempts/{attempt_id}/responses',
        headers=_auth_headers(learner_token),
        json={'responses': [{'questionId': detail_response.json()['paper']['sections'][0]['questions'][0]['id'], 'responseText': '9 am'}]},
    )
    submit_response = client.post(
        f'/api/exam-attempts/{attempt_id}/submit',
        headers=_auth_headers(learner_token),
    )
    result_response = client.get(
        f'/api/exam-attempts/{attempt_id}/result',
        headers=_auth_headers(learner_token),
    )

    assert save_response.status_code == 200
    assert submit_response.status_code == 200
    assert submit_response.json()['result']['summary']['objectiveCorrect'] == 1
    assert result_response.status_code == 200
    assert result_response.json()['summary']['autoScore'] == 1.0


def test_admin_ops_service_supports_exam_review_and_publish(monkeypatch, tmp_path):
    _configure_admin_env(monkeypatch, tmp_path)
    module = _load_admin_ops_service_module('admin_ops_service_admin_exam_review')
    client = TestClient(module.app)
    admin, _ = _seed_users(module.admin_ops_flask_app)
    paper_id, passage_id, question_id, job_id = _seed_reviewable_exam_paper(module.admin_ops_flask_app)
    admin_token = _create_access_token(
        module.admin_ops_flask_app,
        user_id=int(admin['id']),
        is_admin=True,
        username=str(admin['username']),
        email=str(admin['email']),
    )

    list_jobs_response = client.get('/api/admin/exam-import-jobs', headers=_auth_headers(admin_token))
    get_job_response = client.get(f'/api/admin/exam-import-jobs/{job_id}', headers=_auth_headers(admin_token))

    assert list_jobs_response.status_code == 200
    assert list_jobs_response.json()['items'][0]['summary']['audioCount'] == 4
    assert get_job_response.status_code == 200
    assert get_job_response.json()['job']['id'] == job_id

    detail_response = client.get(
        f'/api/exams/{paper_id}?include_draft=1',
        headers=_auth_headers(admin_token),
    )
    review_item_id = detail_response.json()['paper']['reviewItems'][0]['id']

    review_response = client.post(
        f'/api/admin/exam-papers/{paper_id}/review',
        headers=_auth_headers(admin_token),
        json={
            'publishStatus': 'in_review',
            'sections': [{
                'id': detail_response.json()['paper']['sections'][0]['id'],
                'sectionType': 'listening',
                'title': 'Listening',
                'htmlContent': '<p>Cleaned section text.</p>',
                'audioTracks': [{'partNumber': 1, 'title': 'Part 1', 'sourceUrl': 'https://cdn.example.com/test1-part1.mp3'}],
            }],
            'passages': [{
                'id': passage_id,
                'title': 'Repaired passage',
                'htmlContent': '<p>Repaired HTML.</p>',
            }],
            'questions': [{
                'id': question_id,
                'questionType': 'fill_blank',
                'promptHtml': '<p>Final prompt</p>',
                'acceptedAnswers': ['library'],
            }],
            'resolvedReviewItemIds': [review_item_id],
        },
    )
    publish_response = client.post(
        f'/api/admin/exam-papers/{paper_id}/publish',
        headers=_auth_headers(admin_token),
    )

    assert review_response.status_code == 200
    assert review_response.json()['paper']['sections'][0]['sectionType'] == 'listening'
    assert review_response.json()['paper']['sections'][0]['passages'][0]['title'] == 'Repaired passage'
    assert review_response.json()['paper']['sections'][0]['questions'][0]['acceptedAnswers'] == ['library']
    assert review_response.json()['paper']['reviewItems'][0]['status'] == 'resolved'
    assert publish_response.status_code == 200
    assert publish_response.json()['publishStatus'] == 'published_internal'


def test_admin_ops_service_can_start_import_jobs_via_exam_admin_route(monkeypatch, tmp_path):
    _configure_admin_env(monkeypatch, tmp_path)
    module = _load_admin_ops_service_module('admin_ops_service_admin_exam_import')
    client = TestClient(module.app)
    admin, _ = _seed_users(module.admin_ops_flask_app)
    admin_token = _create_access_token(
        module.admin_ops_flask_app,
        user_id=int(admin['id']),
        is_admin=True,
        username=str(admin['username']),
        email=str(admin['email']),
    )
    monkeypatch.setattr(
        'platform_sdk.exam_transport.create_exam_import_job_response',
        lambda body: ({'job_id': 99, 'summary': {'paperCount': 2}}, 201),
    )

    response = client.post(
        '/api/admin/exam-import-jobs',
        headers=_auth_headers(admin_token),
        json={
            'repoUrl': 'https://github.com/vaakian/IELTS/tree/main',
            'audioRepoUrl': 'https://github.com/vaakian/IELTS/tree/main/雅思真题音频',
        },
    )

    assert response.status_code == 201
    assert response.json()['summary']['paperCount'] == 2
