from services.notes_query_service import (
    export_notes_response,
    get_notes_response,
    get_summaries_response,
)
from services.notes_summary_job_service import (
    create_summary_job as _create_summary_job_service,
    find_running_summary_job as _find_running_summary_job_service,
    generate_summary_response,
    get_generate_summary_job_response,
    get_summary_job as _get_summary_job_service,
    run_summary_job as _run_summary_job_service,
    start_generate_summary_job_response,
    update_summary_job as _update_summary_job_service,
)


def _get_summary_job(job_id: str) -> dict | None:
    return _get_summary_job_service(job_id)


def _update_summary_job(job_id: str, **fields) -> dict | None:
    return _update_summary_job_service(job_id, **fields)


def _find_running_summary_job(user_id: int, target_date: str) -> dict | None:
    return _find_running_summary_job_service(user_id, target_date)


def _create_summary_job(user_id: int, target_date: str) -> dict:
    return _create_summary_job_service(user_id, target_date)


def _run_summary_job(app, job_id: str, user_id: int, target_date: str) -> None:
    _run_summary_job_service(app, job_id, user_id, target_date)


@notes_bp.route('', methods=['GET'])
@token_required
def get_notes(current_user):
    return get_notes_response(current_user.id, request.args)


@notes_bp.route('/summaries', methods=['GET'])
@token_required
def get_summaries(current_user):
    return get_summaries_response(current_user.id, request.args)


@notes_bp.route('/summaries/generate', methods=['POST'])
@token_required
def generate_summary(current_user):
    return generate_summary_response(current_user.id, request.get_json() or {})


@notes_bp.route('/summaries/generate-jobs', methods=['POST'])
@token_required
def start_generate_summary_job(current_user):
    app = current_app._get_current_object()
    return start_generate_summary_job_response(current_user.id, request.get_json() or {}, app)


@notes_bp.route('/summaries/generate-jobs/<job_id>', methods=['GET'])
@token_required
def get_generate_summary_job(current_user, job_id: str):
    return get_generate_summary_job_response(current_user.id, job_id)


@notes_bp.route('/export', methods=['GET'])
@token_required
def export_notes(current_user):
    return export_notes_response(current_user.id, request.args)
