from __future__ import annotations

from services.exam_api_service import (
    create_exam_attempt,
    get_exam_attempt_result,
    get_exam_import_job,
    get_exam_paper_detail,
    list_exam_import_jobs,
    list_exam_papers,
    publish_exam_paper,
    review_exam_paper,
    save_exam_attempt_responses,
    submit_exam_attempt,
)


def _error_payload(message: str, status: int):
    return {'error': message}, status


def create_exam_import_job_response(body: dict | None):
    try:
        from services.exam_import_service import run_exam_import_job
        return run_exam_import_job(body), 201
    except ModuleNotFoundError as exc:
        return _error_payload(f'Missing exam import dependency: {exc.name}', 500)
    except ValueError as exc:
        return _error_payload(str(exc), 400)
    except Exception as exc:
        return _error_payload(str(exc) or 'Exam import failed', 500)


def list_exam_import_jobs_response(*, limit: int):
    return list_exam_import_jobs(limit=limit), 200


def get_exam_import_job_response(job_id: int):
    try:
        return get_exam_import_job(job_id=job_id), 200
    except Exception:
        return _error_payload('Exam import job not found', 404)


def list_exam_papers_response(*, user_id: int, include_draft: bool = False):
    return list_exam_papers(user_id=user_id, include_draft=include_draft), 200


def get_exam_paper_response(*, user_id: int, paper_id: int, include_draft: bool = False):
    try:
        return get_exam_paper_detail(paper_id=paper_id, user_id=user_id, include_draft=include_draft), 200
    except LookupError as exc:
        return _error_payload(str(exc), 404)
    except Exception:
        return _error_payload('Exam paper not found', 404)


def create_exam_attempt_response(*, user_id: int, paper_id: int):
    try:
        return create_exam_attempt(paper_id=paper_id, user_id=user_id), 201
    except ValueError as exc:
        return _error_payload(str(exc), 400)
    except Exception:
        return _error_payload('Exam paper not found', 404)


def save_exam_attempt_responses_response(*, user_id: int, attempt_id: int, body: dict | None):
    try:
        return save_exam_attempt_responses(attempt_id=attempt_id, user_id=user_id, body=body), 200
    except PermissionError as exc:
        return _error_payload(str(exc), 403)
    except Exception:
        return _error_payload('Exam attempt not found', 404)


def submit_exam_attempt_response(*, user_id: int, attempt_id: int):
    try:
        return submit_exam_attempt(attempt_id=attempt_id, user_id=user_id), 200
    except PermissionError as exc:
        return _error_payload(str(exc), 403)
    except Exception:
        return _error_payload('Exam attempt not found', 404)


def get_exam_attempt_result_response(*, user_id: int, attempt_id: int):
    try:
        return get_exam_attempt_result(attempt_id=attempt_id, user_id=user_id), 200
    except PermissionError as exc:
        return _error_payload(str(exc), 403)
    except Exception:
        return _error_payload('Exam attempt not found', 404)


def review_exam_paper_response(*, paper_id: int, body: dict | None):
    try:
        return review_exam_paper(paper_id=paper_id, body=body), 200
    except Exception:
        return _error_payload('Exam paper not found', 404)


def publish_exam_paper_response(*, paper_id: int):
    try:
        return publish_exam_paper(paper_id=paper_id), 200
    except Exception:
        return _error_payload('Exam paper not found', 404)
