from __future__ import annotations

from datetime import datetime, timedelta

from platform_sdk.notes_repository_adapters import daily_summary_repository
from platform_sdk.notes_summary_event_application import queue_summary_generated_event
from platform_sdk.notes_summary_runtime_support import (
    SUMMARY_JOB_TTL_SECONDS,
    _summary_jobs,
    _summary_jobs_lock,
)


def estimate_summary_target_chars(notes_list, sessions, wrong_words, prompt_runs=None) -> int:
    prompt_runs = list(prompt_runs or [])
    estimate = (
        420
        + len(notes_list) * 150
        + len(sessions) * 110
        + min(len(wrong_words), 20) * 18
        + len(prompt_runs) * 70
    )
    return max(480, min(1800, estimate))


def fallback_summary_content(target_date: str) -> str:
    return (
        f"# {target_date} 学习总结\n\n"
        "## 学习概况\n\n"
        "今天暂时没有足够的学习数据可供总结。\n\n"
        "## 建议\n\n"
        "- 先完成一轮词汇练习或向 AI 提一个问题，再回来生成总结。"
    )


def save_summary(existing, user_id: int, target_date: str, summary_content: str):
    summary = daily_summary_repository.save_daily_summary(
        existing,
        user_id=user_id,
        target_date=target_date,
        summary_content=summary_content,
        generated_at=datetime.utcnow(),
    )
    queue_summary_generated_event(summary)
    daily_summary_repository.commit()
    return summary


def prune_summary_jobs() -> None:
    cutoff = datetime.utcnow() - timedelta(seconds=SUMMARY_JOB_TTL_SECONDS)
    with _summary_jobs_lock:
        stale_job_ids = [
            job_id
            for job_id, job in _summary_jobs.items()
            if job['updated_at'] < cutoff and job['status'] in {'completed', 'failed'}
        ]
        for job_id in stale_job_ids:
            _summary_jobs.pop(job_id, None)


def serialize_summary_job(job: dict) -> dict:
    return {
        'job_id': job['job_id'],
        'date': job['date'],
        'status': job['status'],
        'progress': job['progress'],
        'message': job['message'],
        'estimated_chars': job['estimated_chars'],
        'generated_chars': job['generated_chars'],
        'summary': job.get('summary'),
        'error': job.get('error'),
    }


__all__ = [
    'estimate_summary_target_chars',
    'fallback_summary_content',
    'prune_summary_jobs',
    'save_summary',
    'serialize_summary_job',
]
