from __future__ import annotations

import re
from datetime import datetime, timedelta

from flask import jsonify

from platform_sdk.local_time_support import format_event_time_for_ai
from platform_sdk.notes_summary_runtime_support import (
    GENERATE_COOLDOWN_SECONDS,
    SUMMARY_JOB_TTL_SECONDS,
    SUMMARY_MODE_LABELS,
    _summary_jobs,
    _summary_jobs_lock,
)
from platform_sdk.notes_repository_adapters import (
    daily_summary_repository,
    learning_note_repository,
    notes_summary_context_repository,
)


def parse_int_param(value: str | None, default: int, min_val: int, max_val: int) -> tuple[int, str | None]:
    if value is None:
        return default, None
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        return default, f"参数必须是整数，收到：{value!r}"
    return max(min_val, min(max_val, parsed)), None


def parse_date_param(value: str | None, name: str) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None, f"{name} 格式错误，应为 YYYY-MM-DD"
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        return None, f"{name} 不是有效日期"
    return value, None


def utc_now() -> datetime:
    return datetime.utcnow()


def date_bounds(target_date: str) -> tuple[datetime, datetime]:
    start_dt = datetime.strptime(target_date, '%Y-%m-%d')
    return start_dt, start_dt + timedelta(days=1)


def check_generate_cooldown(user_id: int, target_date: str):
    existing = daily_summary_repository.get_daily_summary(user_id, target_date)
    if existing and existing.generated_at:
        elapsed = (utc_now() - existing.generated_at).total_seconds()
        if elapsed < GENERATE_COOLDOWN_SECONDS:
            retry_after = max(1, int(GENERATE_COOLDOWN_SECONDS - elapsed))
            wait_min = max(1, (retry_after + 59) // 60)
            return existing, (
                jsonify({
                    'error': f'生成过于频繁，请 {wait_min} 分钟后再试',
                    'cooldown': True,
                    'retry_after': retry_after,
                }),
                429,
            )
    return existing, None


def collect_summary_source_data(user_id: int, target_date: str):
    start_dt, end_dt = date_bounds(target_date)
    learning_notes = learning_note_repository.list_learning_notes(
        user_id,
        start_at=start_dt,
        end_before=end_dt,
        descending=False,
        order_by='created_at',
    )
    sessions = notes_summary_context_repository.list_study_sessions_in_window(
        user_id,
        start_at=start_dt,
        end_before=end_dt,
        descending=False,
    )
    wrong_words = notes_summary_context_repository.list_wrong_words(user_id, limit=50)
    return learning_notes, sessions, wrong_words


def format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds or 0))
    if seconds >= 60:
        return f"{seconds // 60}分{seconds % 60}秒"
    return f"{seconds}秒"


def summary_streak_days(user_id: int, target_date: str) -> int:
    _start_dt, end_dt = date_bounds(target_date)
    rows = notes_summary_context_repository.list_study_sessions_before(
        user_id,
        end_before=end_dt,
        descending=True,
        require_words_studied=True,
    )
    if not rows:
        return 0

    date_set = {
        row.started_at.strftime('%Y-%m-%d')
        for row in rows
        if row.started_at is not None
    }
    if not date_set:
        return 0

    reference = datetime.strptime(target_date, '%Y-%m-%d').date()
    if reference.strftime('%Y-%m-%d') not in date_set:
        previous_day = (reference - timedelta(days=1)).strftime('%Y-%m-%d')
        if previous_day not in date_set:
            return 0
        reference = reference - timedelta(days=1)

    streak = 0
    while reference.strftime('%Y-%m-%d') in date_set:
        streak += 1
        reference -= timedelta(days=1)
    return streak


def build_learning_snapshot(user_id: int, target_date: str, sessions, wrong_words) -> dict:
    _start_dt, end_dt = date_bounds(target_date)
    today_words = sum(session.words_studied or 0 for session in sessions)
    today_duration = sum(session.duration_seconds or 0 for session in sessions)
    today_correct = sum(session.correct_count or 0 for session in sessions)
    today_wrong = sum(session.wrong_count or 0 for session in sessions)
    today_attempted = today_correct + today_wrong
    today_accuracy = round(today_correct / today_attempted * 100) if today_attempted > 0 else 0

    today_mode_breakdown = []
    for session in sessions:
        mode_label = SUMMARY_MODE_LABELS.get(session.mode or '', session.mode or '未知模式')
        correct = session.correct_count or 0
        wrong = session.wrong_count or 0
        attempted = correct + wrong
        accuracy = round(correct / attempted * 100) if attempted > 0 else 0
        today_mode_breakdown.append({
            'mode': session.mode or '',
            'label': mode_label,
            'accuracy': accuracy,
            'words': session.words_studied or 0,
            'duration_seconds': session.duration_seconds or 0,
        })

    all_sessions = notes_summary_context_repository.list_study_sessions_before(
        user_id,
        end_before=end_dt,
        descending=False,
    )
    mode_totals: dict[str, dict] = {}
    for session in all_sessions:
        mode = (session.mode or '').strip()
        if not mode:
            continue
        bucket = mode_totals.setdefault(mode, {
            'label': SUMMARY_MODE_LABELS.get(mode, mode),
            'correct': 0,
            'wrong': 0,
            'words': 0,
        })
        bucket['correct'] += session.correct_count or 0
        bucket['wrong'] += session.wrong_count or 0
        bucket['words'] += session.words_studied or 0

    weakest_mode = None
    for mode, bucket in mode_totals.items():
        attempted = bucket['correct'] + bucket['wrong']
        if attempted < 5:
            continue
        accuracy = round(bucket['correct'] / attempted * 100) if attempted > 0 else 0
        if weakest_mode is None or accuracy < weakest_mode['accuracy']:
            weakest_mode = {
                'mode': mode,
                'label': bucket['label'],
                'accuracy': accuracy,
                'attempts': attempted,
            }

    return {
        'today_words': today_words,
        'today_duration': today_duration,
        'today_accuracy': today_accuracy,
        'today_sessions': len(sessions),
        'today_mode_breakdown': today_mode_breakdown,
        'streak_days': summary_streak_days(user_id, target_date),
        'weakest_mode': weakest_mode,
        'wrong_words': [word.word for word in wrong_words[:8] if word.word],
    }


def estimate_summary_target_chars(notes_list, sessions, wrong_words) -> int:
    estimate = 420 + len(notes_list) * 150 + len(sessions) * 110 + min(len(wrong_words), 20) * 18
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
    return daily_summary_repository.save_daily_summary(
        existing,
        user_id=user_id,
        target_date=target_date,
        summary_content=summary_content,
        generated_at=utc_now(),
    )


def prune_summary_jobs() -> None:
    cutoff = utc_now() - timedelta(seconds=SUMMARY_JOB_TTL_SECONDS)
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


def build_summary_prompt(
    target_date: str,
    notes_list,
    sessions,
    wrong_words,
    learning_snapshot: dict | None = None,
    topic_insights: list[dict] | None = None,
    learner_profile: dict | None = None,
) -> str:
    prompt_parts = [f"请为 {target_date} 生成学习总结。", ""]

    if learning_snapshot:
        prompt_parts.append("### 学习指标总览")
        prompt_parts.append(f"- 今日学习词数：{learning_snapshot['today_words']}")
        prompt_parts.append(f"- 今日练习次数：{learning_snapshot['today_sessions']}")
        prompt_parts.append(f"- 今日用时：{format_duration(learning_snapshot['today_duration'])}")
        prompt_parts.append(f"- 今日准确率：{learning_snapshot['today_accuracy']}%")
        prompt_parts.append(f"- 连续学习：{learning_snapshot['streak_days']} 天")

        weakest_mode = learning_snapshot.get('weakest_mode')
        if weakest_mode:
            prompt_parts.append(
                f"- 最弱模式：{weakest_mode['label']}（累计准确率 {weakest_mode['accuracy']}%，样本 {weakest_mode['attempts']} 题）"
            )
        else:
            prompt_parts.append("- 最弱模式：样本不足，暂不判断")

        if learning_snapshot.get('today_mode_breakdown'):
            mode_summary = '；'.join(
                f"{item['label']} {item['accuracy']}% / {item['words']}词 / {format_duration(item['duration_seconds'])}"
                for item in learning_snapshot['today_mode_breakdown']
            )
            prompt_parts.append(f"- 今日模式表现：{mode_summary}")

    if sessions:
        prompt_parts.append("### 当天练习记录")
        for session in sessions:
            mode_label = SUMMARY_MODE_LABELS.get(session.mode or '', session.mode or '未知模式')
            duration_text = format_duration(session.duration_seconds or 0)
            correct = session.correct_count or 0
            wrong = session.wrong_count or 0
            total = correct + wrong
            accuracy = round(correct / total * 100) if total > 0 else 0
            prompt_parts.append(
                f"- {mode_label}：学习 {session.words_studied or 0} 词，准确率 {accuracy}%，用时 {duration_text}"
            )
    else:
        prompt_parts.append("### 当天练习记录")
        prompt_parts.append("- 暂无练习记录。")

    if notes_list:
        prompt_parts.append("")
        prompt_parts.append("### 当天 AI 问答记录")
        for index, note in enumerate(notes_list, start=1):
            word_info = f"（关联单词：{note.word_context}）" if note.word_context else ""
            prompt_parts.append(f"{index}. 问题{word_info}：{note.question[:200]}")
            prompt_parts.append(f"   回答要点：{note.answer[:500]}")
    else:
        prompt_parts.append("")
        prompt_parts.append("### 当天 AI 问答记录")
        prompt_parts.append("- 暂无提问记录。")

    if topic_insights:
        prompt_parts.append("")
        prompt_parts.append("### AI 对话主题洞察")
        for topic in topic_insights[:5]:
            prompt_parts.append(
                f"- {topic['title']}：今天相关提问 {topic['count']} 次；最近一次回答重点：{topic['latest_answer']}"
            )

    if wrong_words:
        prompt_parts.append("")
        prompt_parts.append("### 近期易错词")
        prompt_parts.append("- " + "、".join(word.word for word in wrong_words[:20]))

    prompt_parts.append("")
    prompt_parts.append("### 生成要求")
    prompt_parts.append("- 请把当天学习内容、学习指标、重复提问主题和易错词联系起来分析。")
    prompt_parts.append("- 后续建议必须具体到下一步动作，优先结合最弱模式、重复困惑点和错词。")

    if learner_profile:
        prompt_parts.append("")
        prompt_parts.append("### 统一学习画像")
        profile_summary = learner_profile.get('summary') or {}
        dimensions = learner_profile.get('dimensions') or []
        focus_words = learner_profile.get('focus_words') or []
        repeated_topics = learner_profile.get('repeated_topics') or []
        next_actions = learner_profile.get('next_actions') or []
        activity_summary = learner_profile.get('activity_summary') or {}
        activity_sources = learner_profile.get('activity_source_breakdown') or []
        recent_activity = learner_profile.get('recent_activity') or []

        weakest_mode_label = profile_summary.get('weakest_mode_label') or profile_summary.get('weakest_mode')
        weakest_mode_accuracy = profile_summary.get('weakest_mode_accuracy')
        if weakest_mode_label:
            accuracy_suffix = f"（{weakest_mode_accuracy}%）" if weakest_mode_accuracy is not None else ""
            prompt_parts.append(f"- 最弱模式：{weakest_mode_label}{accuracy_suffix}")
        if dimensions:
            dimension_text = '、'.join(
                f"{item.get('label', item.get('dimension'))} {item.get('accuracy')}%"
                for item in dimensions[:3]
            )
            prompt_parts.append(f"- 薄弱维度：{dimension_text}")
        if focus_words:
            focus_text = '、'.join(item.get('word', '') for item in focus_words[:5] if item.get('word'))
            if focus_text:
                prompt_parts.append(f"- 重点突破词：{focus_text}")
        if repeated_topics:
            topic_text = '；'.join(
                f"{topic.get('title', '')}（{topic.get('count', 0)}次）"
                for topic in repeated_topics[:3]
            )
            prompt_parts.append(f"- 重复困惑主题：{topic_text}")
        if next_actions:
            prompt_parts.append("- 建议动作：")
            for action in next_actions[:4]:
                prompt_parts.append(f"  - {action}")
        if activity_summary.get('total_events'):
            prompt_parts.append(
                "- 今日统一行为流："
                f"记录了 {activity_summary.get('total_events', 0)} 个事件，"
                f"涉及 {activity_summary.get('books_touched', 0)} 本词书、"
                f"{activity_summary.get('chapters_touched', 0)} 个章节、"
                f"{activity_summary.get('words_touched', 0)} 个单词"
            )
            if activity_sources:
                source_text = '；'.join(
                    f"{item.get('label', item.get('source'))} {item.get('count', 0)} 次"
                    for item in activity_sources[:5]
                )
                if source_text:
                    prompt_parts.append(f"- 行为来源分布：{source_text}")
            if recent_activity:
                prompt_parts.append("- 近期关键动作：")
                for item in recent_activity[:8]:
                    stamp = format_event_time_for_ai(
                        item.get('occurred_at'),
                        reference_date=target_date,
                    )
                    title = item.get('title') or item.get('label') or '学习行为'
                    if stamp:
                        prompt_parts.append(f"  - {stamp} {title}")
                    else:
                        prompt_parts.append(f"  - {title}")

    return '\n'.join(prompt_parts)
