from __future__ import annotations

import os

from fastapi import APIRouter, Request, Response

from platform_sdk.http_proxy import proxy_browser_request


DEFAULT_IDENTITY_SERVICE_URL = 'http://127.0.0.1:8101'
DEFAULT_LEARNING_CORE_SERVICE_URL = 'http://127.0.0.1:8102'
DEFAULT_CATALOG_CONTENT_SERVICE_URL = 'http://127.0.0.1:8103'
DEFAULT_AI_EXECUTION_SERVICE_URL = 'http://127.0.0.1:8104'
DEFAULT_NOTES_SERVICE_URL = 'http://127.0.0.1:8107'
DEFAULT_ADMIN_OPS_SERVICE_URL = 'http://127.0.0.1:8108'

browser_compat_router = APIRouter()


def identity_service_url() -> str:
    return (os.environ.get('IDENTITY_SERVICE_URL') or DEFAULT_IDENTITY_SERVICE_URL).rstrip('/')


def learning_core_service_url() -> str:
    return (os.environ.get('LEARNING_CORE_SERVICE_URL') or DEFAULT_LEARNING_CORE_SERVICE_URL).rstrip('/')


def catalog_content_service_url() -> str:
    return (os.environ.get('CATALOG_CONTENT_SERVICE_URL') or DEFAULT_CATALOG_CONTENT_SERVICE_URL).rstrip('/')


def ai_execution_service_url() -> str:
    return (os.environ.get('AI_EXECUTION_SERVICE_URL') or DEFAULT_AI_EXECUTION_SERVICE_URL).rstrip('/')


def notes_service_url() -> str:
    return (os.environ.get('NOTES_SERVICE_URL') or DEFAULT_NOTES_SERVICE_URL).rstrip('/')


def admin_ops_service_url() -> str:
    return (os.environ.get('ADMIN_OPS_SERVICE_URL') or DEFAULT_ADMIN_OPS_SERVICE_URL).rstrip('/')


def resolve_browser_service_name(base_url: str) -> str:
    normalized_base_url = base_url.rstrip('/')
    service_urls = (
        ('identity-service', identity_service_url()),
        ('learning-core-service', learning_core_service_url()),
        ('catalog-content-service', catalog_content_service_url()),
        ('ai-execution-service', ai_execution_service_url()),
        ('notes-service', notes_service_url()),
        ('admin-ops-service', admin_ops_service_url()),
    )
    for service_name, service_url in service_urls:
        if normalized_base_url == service_url:
            return service_name
    return 'gateway-upstream'


async def _proxy_service_request(
    *,
    request: Request,
    base_url: str,
    path: str,
    unavailable_detail: str,
) -> Response:
    return await proxy_browser_request(
        request=request,
        service_name=resolve_browser_service_name(base_url),
        base_url=base_url,
        path=path,
        unavailable_detail=unavailable_detail,
    )


@browser_compat_router.api_route('/api/auth/{auth_path:path}', methods=['GET', 'POST', 'PUT'])
async def auth_proxy(auth_path: str, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=identity_service_url(),
        path=f'/api/auth/{auth_path}',
        unavailable_detail='identity service unavailable',
    )


@browser_compat_router.api_route('/api/progress', methods=['GET', 'POST'])
async def progress_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path='/api/progress',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.get('/api/progress/{day}')
async def day_progress_proxy(day: int, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path=f'/api/progress/{day}',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.api_route('/api/books/progress', methods=['GET', 'POST'])
async def book_progress_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path='/api/books/progress',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.get('/api/books/progress/{book_id}')
async def single_book_progress_proxy(book_id: str, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path=f'/api/books/progress/{book_id}',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.get('/api/books/{book_id}/chapters/progress')
async def chapter_progress_proxy(book_id: str, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path=f'/api/books/{book_id}/chapters/progress',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.post('/api/books/{book_id}/chapters/{chapter_id}/progress')
async def save_chapter_progress_proxy(book_id: str, chapter_id: str, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path=f'/api/books/{book_id}/chapters/{chapter_id}/progress',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.post('/api/books/{book_id}/chapters/{chapter_id}/mode-progress')
async def save_chapter_mode_progress_proxy(book_id: str, chapter_id: str, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path=f'/api/books/{book_id}/chapters/{chapter_id}/mode-progress',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.api_route('/api/books/my', methods=['GET', 'POST'])
async def my_books_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path='/api/books/my',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.delete('/api/books/my/{book_id}')
async def remove_my_book_proxy(book_id: str, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path=f'/api/books/my/{book_id}',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.post('/api/books/favorites/status')
async def favorite_status_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path='/api/books/favorites/status',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.api_route('/api/books/favorites', methods=['POST', 'DELETE'])
async def favorites_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path='/api/books/favorites',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.post('/api/books/familiar/status')
async def familiar_status_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path='/api/books/familiar/status',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.api_route('/api/books/familiar', methods=['POST', 'DELETE'])
async def familiar_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=learning_core_service_url(),
        path='/api/books/familiar',
        unavailable_detail='learning core service unavailable',
    )


@browser_compat_router.post('/api/books/word-feedback')
async def word_feedback_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=admin_ops_service_url(),
        path='/api/books/word-feedback',
        unavailable_detail='admin ops service unavailable',
    )


@browser_compat_router.api_route('/api/exams', methods=['GET'])
async def exams_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=admin_ops_service_url(),
        path='/api/exams',
        unavailable_detail='admin ops service unavailable',
    )


@browser_compat_router.api_route('/api/exams/{paper_id}', methods=['GET'])
async def exam_detail_proxy(paper_id: int, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=admin_ops_service_url(),
        path=f'/api/exams/{paper_id}',
        unavailable_detail='admin ops service unavailable',
    )


@browser_compat_router.post('/api/exams/{paper_id}/attempts')
async def exam_attempt_proxy(paper_id: int, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=admin_ops_service_url(),
        path=f'/api/exams/{paper_id}/attempts',
        unavailable_detail='admin ops service unavailable',
    )


@browser_compat_router.patch('/api/exam-attempts/{attempt_id}/responses')
async def exam_attempt_responses_proxy(attempt_id: int, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=admin_ops_service_url(),
        path=f'/api/exam-attempts/{attempt_id}/responses',
        unavailable_detail='admin ops service unavailable',
    )


@browser_compat_router.post('/api/exam-attempts/{attempt_id}/submit')
async def exam_attempt_submit_proxy(attempt_id: int, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=admin_ops_service_url(),
        path=f'/api/exam-attempts/{attempt_id}/submit',
        unavailable_detail='admin ops service unavailable',
    )


@browser_compat_router.get('/api/exam-attempts/{attempt_id}/result')
async def exam_attempt_result_proxy(attempt_id: int, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=admin_ops_service_url(),
        path=f'/api/exam-attempts/{attempt_id}/result',
        unavailable_detail='admin ops service unavailable',
    )


@browser_compat_router.put('/api/books/word-details/note')
async def word_detail_note_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=notes_service_url(),
        path='/api/books/word-details/note',
        unavailable_detail='notes service unavailable',
    )


@browser_compat_router.get('/api/books')
async def books_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=catalog_content_service_url(),
        path='/api/books',
        unavailable_detail='catalog content service unavailable',
    )


@browser_compat_router.get('/api/books/search')
async def books_search_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=catalog_content_service_url(),
        path='/api/books/search',
        unavailable_detail='catalog content service unavailable',
    )


@browser_compat_router.get('/api/books/categories')
async def books_categories_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=catalog_content_service_url(),
        path='/api/books/categories',
        unavailable_detail='catalog content service unavailable',
    )


@browser_compat_router.get('/api/books/levels')
async def books_levels_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=catalog_content_service_url(),
        path='/api/books/levels',
        unavailable_detail='catalog content service unavailable',
    )


@browser_compat_router.get('/api/books/stats')
async def books_stats_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=catalog_content_service_url(),
        path='/api/books/stats',
        unavailable_detail='catalog content service unavailable',
    )


@browser_compat_router.get('/api/books/examples')
async def books_examples_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=catalog_content_service_url(),
        path='/api/books/examples',
        unavailable_detail='catalog content service unavailable',
    )


@browser_compat_router.get('/api/books/word-details')
async def word_details_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=catalog_content_service_url(),
        path='/api/books/word-details',
        unavailable_detail='catalog content service unavailable',
    )


@browser_compat_router.api_route('/api/books/{book_path:path}', methods=['GET', 'POST', 'PUT'])
async def catalog_books_catchall_proxy(book_path: str, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=catalog_content_service_url(),
        path=f'/api/books/{book_path}',
        unavailable_detail='catalog content service unavailable',
    )


@browser_compat_router.get('/api/vocabulary')
async def vocabulary_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=catalog_content_service_url(),
        path='/api/vocabulary',
        unavailable_detail='catalog content service unavailable',
    )


@browser_compat_router.get('/api/vocabulary/stats')
async def vocabulary_stats_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=catalog_content_service_url(),
        path='/api/vocabulary/stats',
        unavailable_detail='catalog content service unavailable',
    )


@browser_compat_router.get('/api/vocabulary/day/{day}')
async def vocabulary_day_proxy(day: int, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=catalog_content_service_url(),
        path=f'/api/vocabulary/day/{day}',
        unavailable_detail='catalog content service unavailable',
    )


@browser_compat_router.api_route('/api/ai/{ai_path:path}', methods=['GET', 'POST', 'DELETE'])
async def ai_proxy(ai_path: str, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=ai_execution_service_url(),
        path=f'/api/ai/{ai_path}',
        unavailable_detail='ai execution service unavailable',
    )


@browser_compat_router.get('/api/notes')
async def notes_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=notes_service_url(),
        path='/api/notes',
        unavailable_detail='notes service unavailable',
    )


@browser_compat_router.get('/api/notes/summaries')
async def notes_summaries_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=notes_service_url(),
        path='/api/notes/summaries',
        unavailable_detail='notes service unavailable',
    )


@browser_compat_router.post('/api/notes/summaries/generate')
async def notes_generate_summary_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=notes_service_url(),
        path='/api/notes/summaries/generate',
        unavailable_detail='notes service unavailable',
    )


@browser_compat_router.post('/api/notes/summaries/generate-jobs')
async def notes_generate_summary_jobs_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=notes_service_url(),
        path='/api/notes/summaries/generate-jobs',
        unavailable_detail='notes service unavailable',
    )


@browser_compat_router.get('/api/notes/summaries/generate-jobs/{job_id}')
async def notes_generate_summary_job_proxy(job_id: str, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=notes_service_url(),
        path=f'/api/notes/summaries/generate-jobs/{job_id}',
        unavailable_detail='notes service unavailable',
    )


@browser_compat_router.get('/api/notes/export')
async def notes_export_proxy(request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=notes_service_url(),
        path='/api/notes/export',
        unavailable_detail='notes service unavailable',
    )


@browser_compat_router.api_route('/api/admin/{admin_path:path}', methods=['GET', 'POST'])
async def admin_proxy(admin_path: str, request: Request):
    return await _proxy_service_request(
        request=request,
        base_url=admin_ops_service_url(),
        path=f'/api/admin/{admin_path}',
        unavailable_detail='admin ops service unavailable',
    )
