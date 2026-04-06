def fallback_summary_content(target_date: str) -> str:
    return (
        f"# {target_date} 学习总结\n\n"
        "## 学习概况\n\n"
        "今天暂时没有足够的学习数据可供总结。\n\n"
        "## 建议\n\n"
        "- 先完成一轮词汇练习或向 AI 提一个问题，再回来生成总结。"
    )


def save_summary(existing, user_id: int, target_date: str, summary_content: str):
    notes = _notes_module()
    if existing:
        existing.content = summary_content
        existing.generated_at = utc_now()
        notes.db.session.commit()
        return existing

    summary = notes.UserDailySummary(
        user_id=user_id,
        date=target_date,
        content=summary_content,
    )
    notes.db.session.add(summary)
    notes.db.session.commit()
    return summary


def prune_summary_jobs() -> None:
    notes = _notes_module()
    cutoff = utc_now() - timedelta(seconds=notes._SUMMARY_JOB_TTL_SECONDS)
    with notes._summary_jobs_lock:
        stale_job_ids = [
            job_id
            for job_id, job in notes._summary_jobs.items()
            if job['updated_at'] < cutoff and job['status'] in {'completed', 'failed'}
        ]
        for job_id in stale_job_ids:
            notes._summary_jobs.pop(job_id, None)


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
