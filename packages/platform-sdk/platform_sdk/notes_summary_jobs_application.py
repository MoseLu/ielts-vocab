from __future__ import annotations

import logging
import threading
import uuid
from datetime import date as date_type

from flask import jsonify

from platform_sdk.cross_service_boundary import build_strict_internal_contract_error
from platform_sdk.memory_topics_support import build_memory_topics
from platform_sdk.notes_summary_runtime_support import (
    SUMMARY_SYSTEM_PROMPT,
    _summary_jobs,
    _summary_jobs_lock,
    stream_summary_text,
)
from platform_sdk.notes_summary_service_support import (
    build_learning_snapshot,
    build_summary_prompt,
    check_generate_cooldown,
    collect_summary_source_data,
    estimate_summary_target_chars,
    fallback_summary_content,
    parse_date_param,
    prune_summary_jobs,
    save_summary,
    serialize_summary_job,
    utc_now,
)
from platform_sdk.learner_profile_application_support import build_learner_profile_payload
from platform_sdk.llm_provider_adapter import chat
from platform_sdk.notes_repository_adapters import (
    daily_summary_repository,
    notes_summary_context_repository,
)


def _validate_target_date(raw_target_date):
    target_date = raw_target_date or date_type.today().strftime('%Y-%m-%d')
    target_date, error = parse_date_param(target_date, 'date')
    if error or not target_date:
        return None, (jsonify({'error': error or '日期格式错误'}), 400)
    if target_date > date_type.today().strftime('%Y-%m-%d'):
        return None, (jsonify({'error': '不能为未来日期生成总结'}), 400)
    return target_date, None


def _build_summary_context(user_id: int, target_date: str) -> dict:
    learning_notes, sessions, wrong_words, prompt_runs = collect_summary_source_data(user_id, target_date)
    learning_snapshot = build_learning_snapshot(
        user_id,
        target_date,
        sessions,
        wrong_words,
        prompt_runs=prompt_runs,
    )
    topic_insights = build_memory_topics(learning_notes, limit=5, include_singletons=True)
    learner_profile = build_learner_profile_payload(user_id, target_date=target_date)
    estimated_chars = estimate_summary_target_chars(learning_notes, sessions, wrong_words, prompt_runs=prompt_runs)
    user_content = build_summary_prompt(
        target_date,
        learning_notes,
        sessions,
        wrong_words,
        learning_snapshot=learning_snapshot,
        topic_insights=topic_insights,
        learner_profile=learner_profile,
        prompt_runs=prompt_runs,
    )
    return {
        'learning_notes': learning_notes,
        'sessions': sessions,
        'wrong_words': wrong_words,
        'prompt_runs': prompt_runs,
        'estimated_chars': estimated_chars,
        'user_content': user_content,
    }


def _build_notes_summary_boundary_error(action: str):
    return build_strict_internal_contract_error(
        upstream_name='learning-core-service',
        action=action,
    )


def get_summary_job(job_id: str):
    prune_summary_jobs()
    with _summary_jobs_lock:
        job = _summary_jobs.get(job_id)
        return dict(job) if job else None


def update_summary_job(job_id: str, **fields):
    with _summary_jobs_lock:
        job = _summary_jobs.get(job_id)
        if not job:
            return None
        job.update(fields)
        job['updated_at'] = utc_now()
        return dict(job)


def find_running_summary_job(user_id: int, target_date: str):
    prune_summary_jobs()
    with _summary_jobs_lock:
        for job in _summary_jobs.values():
            if (
                job['user_id'] == user_id and
                job['date'] == target_date and
                job['status'] in {'queued', 'running'}
            ):
                return dict(job)
    return None


def create_summary_job(user_id: int, target_date: str):
    job = {
        'job_id': uuid.uuid4().hex,
        'user_id': user_id,
        'date': target_date,
        'status': 'queued',
        'progress': 1,
        'message': '准备生成总结...',
        'estimated_chars': 0,
        'generated_chars': 0,
        'summary': None,
        'error': None,
        'created_at': utc_now(),
        'updated_at': utc_now(),
    }
    with _summary_jobs_lock:
        _summary_jobs[job['job_id']] = job
    return dict(job)


def run_summary_job(app, job_id: str, user_id: int, target_date: str) -> None:
    try:
        with app.app_context():
            update_summary_job(job_id, status='running', progress=8, message='正在收集学习记录...')
            existing = daily_summary_repository.get_daily_summary(user_id, target_date)
            context = _build_summary_context(user_id, target_date)
            update_summary_job(
                job_id,
                progress=18,
                message='正在整理总结结构...',
                estimated_chars=context['estimated_chars'],
            )
            update_summary_job(job_id, progress=26, message='AI 正在生成正文...')

            chunks = []
            generated_chars = 0
            for chunk in stream_summary_text(context['user_content']):
                if not chunk:
                    continue
                chunks.append(chunk)
                generated_chars += len(chunk)
                ratio = min(generated_chars / max(context['estimated_chars'], 1), 1.0)
                progress = min(94, 26 + int(ratio * 64))
                update_summary_job(
                    job_id,
                    progress=progress,
                    message='AI 正在生成正文...',
                    generated_chars=generated_chars,
                )

            summary_content = ''.join(chunks).strip() or fallback_summary_content(target_date)
            update_summary_job(
                job_id,
                progress=96,
                message='正在保存总结...',
                generated_chars=max(generated_chars, len(summary_content)),
            )
            saved_summary = save_summary(existing, user_id, target_date, summary_content)
            update_summary_job(
                job_id,
                status='completed',
                progress=100,
                message='生成完成',
                generated_chars=max(generated_chars, len(summary_content)),
                summary=saved_summary.to_dict(),
                error=None,
            )
    except Exception as exc:
        daily_summary_repository.rollback()
        logging.exception("[Notes] Summary job failed for user=%s date=%s", user_id, target_date)
        update_summary_job(
            job_id,
            status='failed',
            message='生成失败，请重试',
            error=str(exc) or '生成失败，请重试',
        )


def generate_summary_response(user_id: int, body):
    target_date, error_response = _validate_target_date((body or {}).get('date'))
    if error_response:
        return error_response

    existing, cooldown_response = check_generate_cooldown(user_id, target_date)
    if cooldown_response:
        return cooldown_response

    try:
        context = _build_summary_context(user_id, target_date)
    except notes_summary_context_repository.LearningCoreNotesContextUnavailable as exc:
        return _build_notes_summary_boundary_error(exc.action)
    try:
        response = chat(
            [
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {"role": "user", "content": context['user_content']},
            ],
            max_tokens=2000,
        )
        summary_content = (response or {}).get('text', '').strip() or fallback_summary_content(target_date)
    except Exception as exc:
        logging.warning("[Notes] LLM summary generation failed for user=%s: %s", user_id, exc)
        return jsonify({'error': 'AI 生成失败，请稍后重试'}), 500

    try:
        saved_summary = save_summary(existing, user_id, target_date, summary_content)
        return jsonify({'summary': saved_summary.to_dict()})
    except Exception as exc:
        daily_summary_repository.rollback()
        logging.error("[Notes] Failed to save summary for user=%s: %s", user_id, exc)
        return jsonify({'error': '保存失败，请重试'}), 500


def start_generate_summary_job_response(user_id: int, body, app):
    target_date, error_response = _validate_target_date((body or {}).get('date'))
    if error_response:
        return error_response

    running_job = find_running_summary_job(user_id, target_date)
    if running_job:
        return jsonify(serialize_summary_job(running_job)), 202

    _existing, cooldown_response = check_generate_cooldown(user_id, target_date)
    if cooldown_response:
        return cooldown_response

    try:
        collect_summary_source_data(user_id, target_date)
    except notes_summary_context_repository.LearningCoreNotesContextUnavailable as exc:
        return _build_notes_summary_boundary_error(exc.action)

    job = create_summary_job(user_id, target_date)
    threading.Thread(
        target=run_summary_job,
        args=(app, job['job_id'], user_id, target_date),
        daemon=True,
    ).start()
    return jsonify(serialize_summary_job(job)), 202


def get_generate_summary_job_response(user_id: int, job_id: str):
    job = get_summary_job(job_id)
    if not job or job['user_id'] != user_id:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify(serialize_summary_job(job))
