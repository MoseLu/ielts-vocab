from __future__ import annotations

from datetime import datetime
from typing import Iterable

from models import (
    EXAM_OBJECTIVE_QUESTION_TYPES,
    ExamAnswerKey,
    ExamAttempt,
    ExamIngestionJob,
    ExamPaper,
    ExamQuestion,
    ExamResponse,
    db,
)
from services.exam_feedback_service import build_writing_feedback


def _normalize_answer(value: str | None) -> str:
    return ''.join(char.lower() for char in str(value or '').strip() if char.isalnum())


def _serialize_choice(choice) -> dict:
    return {
        'id': choice.id,
        'key': choice.choice_key,
        'label': choice.label,
        'contentHtml': choice.content_html,
    }


def _serialize_question(question, response_by_question_id: dict[int, ExamResponse] | None = None) -> dict:
    response = response_by_question_id.get(question.id) if response_by_question_id else None
    return {
        'id': question.id,
        'questionNumber': question.question_number,
        'sortOrder': question.sort_order,
        'questionType': question.question_type,
        'promptHtml': question.prompt_html,
        'groupKey': question.group_key,
        'confidence': float(question.confidence or 0),
        'choices': [_serialize_choice(choice) for choice in question.choices],
        'acceptedAnswers': [answer.answer_text for answer in question.answer_keys],
        'response': _serialize_response(response) if response else None,
    }


def _serialize_passage(passage) -> dict:
    return {
        'id': passage.id,
        'title': passage.title,
        'htmlContent': passage.html_content,
        'sourcePageFrom': passage.source_page_from,
        'sourcePageTo': passage.source_page_to,
        'confidence': float(passage.confidence or 0),
    }


def _serialize_section(section, response_by_question_id: dict[int, ExamResponse] | None = None) -> dict:
    metadata = section.metadata_dict()
    return {
        'id': section.id,
        'sectionType': section.section_type,
        'title': section.title,
        'instructionsHtml': section.instructions_html,
        'htmlContent': section.html_content,
        'confidence': float(section.confidence or 0),
        'audioAssetId': section.audio_asset_id,
        'audioTracks': metadata.get('audioTracks') or [],
        'passages': [_serialize_passage(passage) for passage in section.passages],
        'questions': [_serialize_question(question, response_by_question_id) for question in section.questions],
    }


def _serialize_review_item(review_item) -> dict:
    return {
        'id': review_item.id,
        'itemType': review_item.item_type,
        'severity': review_item.severity,
        'status': review_item.status,
        'message': review_item.message,
        'sectionId': review_item.section_id,
        'questionId': review_item.question_id,
        'metadata': review_item.metadata_dict(),
    }


def _serialize_response(response: ExamResponse | None) -> dict | None:
    if response is None:
        return None
    return {
        'id': response.id,
        'questionId': response.question_id,
        'responseText': response.response_text,
        'selectedChoices': response.selected_choices(),
        'attachmentUrl': response.attachment_url,
        'durationSeconds': response.duration_seconds,
        'isCorrect': response.is_correct,
        'score': response.score,
        'feedback': response.feedback_dict(),
    }


def _serialize_attempt(attempt: ExamAttempt) -> dict:
    return {
        'id': attempt.id,
        'paperId': attempt.paper_id,
        'status': attempt.status,
        'objectiveCorrect': int(attempt.objective_correct or 0),
        'objectiveTotal': int(attempt.objective_total or 0),
        'autoScore': float(attempt.auto_score or 0),
        'maxScore': float(attempt.max_score or 0),
        'feedback': attempt.feedback_dict(),
        'startedAt': attempt.started_at.isoformat() if attempt.started_at else None,
        'submittedAt': attempt.submitted_at.isoformat() if attempt.submitted_at else None,
        'responses': [_serialize_response(response) for response in attempt.responses],
    }


def _serialize_paper_summary(paper: ExamPaper, user_id: int | None = None) -> dict:
    latest_attempt = None
    if user_id is not None:
        latest_attempt = (
            ExamAttempt.query
            .filter_by(user_id=user_id, paper_id=paper.id)
            .order_by(ExamAttempt.updated_at.desc(), ExamAttempt.id.desc())
            .first()
        )
    return {
        'id': paper.id,
        'collectionTitle': paper.collection_title,
        'title': paper.title,
        'seriesNumber': paper.series_number,
        'testNumber': paper.test_number,
        'examKind': paper.exam_kind,
        'publishStatus': paper.publish_status,
        'rightsStatus': paper.rights_status,
        'importConfidence': float(paper.import_confidence or 0),
        'answerKeyConfidence': float(paper.answer_key_confidence or 0),
        'hasListeningAudio': bool(paper.has_listening_audio),
        'reviewCount': len(paper.review_items),
        'sections': [
            {
                'id': section.id,
                'sectionType': section.section_type,
                'title': section.title,
                'audioTracks': section.metadata_dict().get('audioTracks') or [],
                'questionCount': len(section.questions),
            }
            for section in paper.sections
        ],
        'latestAttempt': _serialize_attempt(latest_attempt) if latest_attempt else None,
    }


def _paper_query(*, include_draft: bool) -> Iterable[ExamPaper]:
    query = ExamPaper.query.order_by(
        ExamPaper.series_number.desc().nullslast(),
        ExamPaper.test_number.asc().nullslast(),
        ExamPaper.id.desc(),
    )
    if include_draft:
        return query.all()
    return query.filter_by(publish_status='published_internal').all()


def list_exam_papers(*, user_id: int, include_draft: bool = False) -> dict:
    return {'items': [_serialize_paper_summary(paper, user_id=user_id) for paper in _paper_query(include_draft=include_draft)]}


def get_exam_paper_detail(*, paper_id: int, user_id: int, include_draft: bool = False) -> dict:
    paper = ExamPaper.query.get_or_404(paper_id)
    if not include_draft and paper.publish_status != 'published_internal':
        raise LookupError('Exam paper is not published')
    latest_attempt = (
        ExamAttempt.query
        .filter_by(user_id=user_id, paper_id=paper.id)
        .order_by(ExamAttempt.updated_at.desc(), ExamAttempt.id.desc())
        .first()
    )
    response_by_question_id = {
        response.question_id: response
        for response in latest_attempt.responses
    } if latest_attempt else {}
    return {
        'paper': {
            'id': paper.id,
            'collectionTitle': paper.collection_title,
            'title': paper.title,
            'seriesNumber': paper.series_number,
            'testNumber': paper.test_number,
            'examKind': paper.exam_kind,
            'publishStatus': paper.publish_status,
            'rightsStatus': paper.rights_status,
            'importConfidence': float(paper.import_confidence or 0),
            'answerKeyConfidence': float(paper.answer_key_confidence or 0),
            'hasListeningAudio': bool(paper.has_listening_audio),
            'sections': [_serialize_section(section, response_by_question_id) for section in paper.sections],
            'reviewItems': [_serialize_review_item(item) for item in paper.review_items] if include_draft else [],
        },
        'latestAttempt': _serialize_attempt(latest_attempt) if latest_attempt else None,
    }


def create_exam_attempt(*, paper_id: int, user_id: int) -> dict:
    paper = ExamPaper.query.get_or_404(paper_id)
    if paper.publish_status != 'published_internal':
        raise ValueError('Only published papers can be attempted')
    attempt = ExamAttempt(user_id=user_id, paper_id=paper.id, status='in_progress')
    db.session.add(attempt)
    db.session.commit()
    return {'attempt': _serialize_attempt(attempt)}


def _response_for_question(*, attempt: ExamAttempt, question_id: int) -> ExamResponse:
    response = next((item for item in attempt.responses if item.question_id == question_id), None)
    if response is None:
        response = ExamResponse(attempt_id=attempt.id, question_id=question_id)
        db.session.add(response)
        db.session.flush()
    return response


def save_exam_attempt_responses(*, attempt_id: int, user_id: int, body: dict | None) -> dict:
    body = body or {}
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.user_id != user_id:
        raise PermissionError('Attempt does not belong to the current user')
    for item in body.get('responses') or []:
        question_id = int(item.get('questionId'))
        response = _response_for_question(attempt=attempt, question_id=question_id)
        response.response_text = str(item.get('responseText') or '').strip() or None
        response.set_selected_choices(item.get('selectedChoices') or [])
        response.attachment_url = str(item.get('attachmentUrl') or '').strip() or None
        response.duration_seconds = item.get('durationSeconds')
        response.is_correct = item.get('isCorrect')
        response.score = item.get('score')
        response.set_feedback(item.get('feedback') or {})
    db.session.commit()
    return {'attempt': _serialize_attempt(attempt)}


def _score_response(question: ExamQuestion, response: ExamResponse) -> tuple[bool | None, float]:
    if question.question_type not in EXAM_OBJECTIVE_QUESTION_TYPES:
        return None, 0
    expected = [_normalize_answer(answer.answer_text) for answer in question.answer_keys if answer.answer_text]
    if question.question_type in {'single_choice', 'multiple_choice'}:
        actual = sorted(_normalize_answer(choice) for choice in response.selected_choices())
        is_correct = bool(actual and sorted(expected) == actual)
        return is_correct, 1.0 if is_correct else 0.0
    actual_text = _normalize_answer(response.response_text)
    is_correct = bool(actual_text and actual_text in expected)
    return is_correct, 1.0 if is_correct else 0.0


def _apply_writing_feedback(attempt: ExamAttempt) -> dict:
    feedback: dict[str, dict] = {}
    for response in attempt.responses:
        question = response.question
        if question.question_type != 'writing_prompt':
            continue
        generated = build_writing_feedback(
            prompt_html=question.prompt_html,
            answer_text=response.response_text,
        )
        if not generated:
            continue
        response.set_feedback(generated)
        feedback[str(question.id)] = generated
    return feedback


def _validate_publishable(paper: ExamPaper) -> tuple[list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    if paper.rights_status not in {'restricted_internal', 'approved_public'}:
        blockers.append('rights_status')
    if not paper.sections:
        blockers.append('empty_paper')
    for section in paper.sections:
        if section.section_type == 'listening' and not (section.metadata_dict().get('audioTracks') or []):
            warnings.append(f'section:{section.id}:missing_audio')
        for question in section.questions:
            if question.question_type in EXAM_OBJECTIVE_QUESTION_TYPES and not question.answer_keys:
                warnings.append(f'question:{question.id}:missing_answer')
    return blockers, warnings


def submit_exam_attempt(*, attempt_id: int, user_id: int) -> dict:
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.user_id != user_id:
        raise PermissionError('Attempt does not belong to the current user')
    objective_correct = 0
    objective_total = 0
    auto_score = 0.0
    max_score = 0.0
    for response in attempt.responses:
        is_correct, score = _score_response(response.question, response)
        response.is_correct = is_correct
        response.score = score if is_correct is not None else None
        if is_correct is not None:
            objective_total += 1
            max_score += 1.0
            auto_score += score
            if is_correct:
                objective_correct += 1
    writing_feedback = _apply_writing_feedback(attempt)
    attempt.objective_correct = objective_correct
    attempt.objective_total = objective_total
    attempt.auto_score = auto_score
    attempt.max_score = max_score
    attempt.status = 'submitted'
    attempt.submitted_at = datetime.utcnow()
    attempt.set_feedback({'writing': writing_feedback})
    db.session.commit()
    return {'attempt': _serialize_attempt(attempt), 'result': get_exam_attempt_result(attempt_id=attempt.id, user_id=user_id)}


def get_exam_attempt_result(*, attempt_id: int, user_id: int) -> dict:
    attempt = ExamAttempt.query.get_or_404(attempt_id)
    if attempt.user_id != user_id:
        raise PermissionError('Attempt does not belong to the current user')
    return {
        'attempt': _serialize_attempt(attempt),
        'summary': {
            'objectiveCorrect': int(attempt.objective_correct or 0),
            'objectiveTotal': int(attempt.objective_total or 0),
            'autoScore': float(attempt.auto_score or 0),
            'maxScore': float(attempt.max_score or 0),
            'feedback': attempt.feedback_dict(),
        },
    }


def list_exam_import_jobs(*, limit: int = 20) -> dict:
    rows = (
        ExamIngestionJob.query
        .order_by(ExamIngestionJob.created_at.desc(), ExamIngestionJob.id.desc())
        .limit(max(1, min(limit, 50)))
        .all()
    )
    return {
        'items': [
            {
                'id': row.id,
                'status': row.status,
                'repoUrl': row.repo_url,
                'audioRepoUrl': row.audio_repo_url,
                'parserModel': row.parser_model,
                'stitchModel': row.stitch_model,
                'summary': row.summary_dict(),
                'errorMessage': row.error_message,
                'startedAt': row.started_at.isoformat() if row.started_at else None,
                'finishedAt': row.finished_at.isoformat() if row.finished_at else None,
                'createdAt': row.created_at.isoformat() if row.created_at else None,
            }
            for row in rows
        ]
    }


def get_exam_import_job(*, job_id: int) -> dict:
    job = ExamIngestionJob.query.get_or_404(job_id)
    return {
        'job': {
            'id': job.id,
            'status': job.status,
            'repoUrl': job.repo_url,
            'audioRepoUrl': job.audio_repo_url,
            'parserModel': job.parser_model,
            'stitchModel': job.stitch_model,
            'summary': job.summary_dict(),
            'errorMessage': job.error_message,
            'startedAt': job.started_at.isoformat() if job.started_at else None,
            'finishedAt': job.finished_at.isoformat() if job.finished_at else None,
            'createdAt': job.created_at.isoformat() if job.created_at else None,
        }
    }


def review_exam_paper(*, paper_id: int, body: dict | None) -> dict:
    body = body or {}
    paper = ExamPaper.query.get_or_404(paper_id)
    if 'title' in body:
        paper.title = str(body.get('title') or '').strip() or paper.title
    if 'collectionTitle' in body:
        paper.collection_title = str(body.get('collectionTitle') or '').strip() or paper.collection_title
    if 'rightsStatus' in body:
        paper.rights_status = str(body.get('rightsStatus') or paper.rights_status)
    for section_patch in body.get('sections') or []:
        section = next((item for item in paper.sections if item.id == int(section_patch.get('id'))), None)
        if not section:
            continue
        if 'sectionType' in section_patch:
            section.section_type = str(section_patch.get('sectionType') or section.section_type).strip() or section.section_type
        if 'title' in section_patch:
            section.title = str(section_patch.get('title') or '').strip() or section.title
        if 'instructionsHtml' in section_patch:
            section.instructions_html = str(section_patch.get('instructionsHtml') or '').strip() or None
        if 'htmlContent' in section_patch:
            section.html_content = str(section_patch.get('htmlContent') or '').strip() or None
        if 'audioTracks' in section_patch:
            metadata = section.metadata_dict()
            metadata['audioTracks'] = section_patch.get('audioTracks') or []
            section.set_metadata(metadata)
    for passage_patch in body.get('passages') or []:
        passage = next((item for section in paper.sections for item in section.passages if item.id == int(passage_patch.get('id'))), None)
        if passage is None:
            continue
        if 'title' in passage_patch:
            passage.title = str(passage_patch.get('title') or '').strip() or None
        if 'htmlContent' in passage_patch:
            passage.html_content = str(passage_patch.get('htmlContent') or '').strip()
        if 'sourcePageFrom' in passage_patch:
            passage.source_page_from = passage_patch.get('sourcePageFrom')
        if 'sourcePageTo' in passage_patch:
            passage.source_page_to = passage_patch.get('sourcePageTo')
    for question_patch in body.get('questions') or []:
        question = ExamQuestion.query.get(int(question_patch.get('id')))
        if question is None or question.section.paper_id != paper.id:
            continue
        if 'questionType' in question_patch:
            question.question_type = str(question_patch.get('questionType') or question.question_type)
        if 'promptHtml' in question_patch:
            question.prompt_html = str(question_patch.get('promptHtml') or '').strip() or question.prompt_html
        if 'acceptedAnswers' in question_patch:
            for answer_key in list(question.answer_keys):
                db.session.delete(answer_key)
            for answer_index, answer in enumerate(question_patch.get('acceptedAnswers') or [], start=1):
                text = str(answer or '').strip()
                if not text:
                    continue
                db.session.add(ExamAnswerKey(
                    question_id=question.id,
                    sort_order=answer_index,
                    answer_kind='accepted_answer',
                    answer_text=text,
                    normalized_text=_normalize_answer(text),
                ))
    resolved_ids = {int(value) for value in body.get('resolvedReviewItemIds') or []}
    for review_item in paper.review_items:
        if review_item.id in resolved_ids:
            review_item.status = 'resolved'
    paper.publish_status = str(body.get('publishStatus') or 'in_review')
    db.session.commit()
    return get_exam_paper_detail(paper_id=paper.id, user_id=0, include_draft=True)


def publish_exam_paper(*, paper_id: int) -> dict:
    paper = ExamPaper.query.get_or_404(paper_id)
    blockers, warnings = _validate_publishable(paper)
    if blockers:
        paper.publish_status = 'blocked'
    elif warnings:
        paper.publish_status = 'in_review'
    else:
        paper.publish_status = 'published_internal'
    db.session.commit()
    return {
        'paperId': paper.id,
        'publishStatus': paper.publish_status,
        'blockers': blockers,
        'warnings': warnings,
    }
