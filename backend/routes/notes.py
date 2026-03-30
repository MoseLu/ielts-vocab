import logging
import re
import threading
import uuid
from datetime import date as date_type
from datetime import datetime, timedelta

from flask import Blueprint, current_app, jsonify, request

from models import db, UserDailySummary, UserLearningNote, UserStudySession, UserWrongWord
from routes.middleware import token_required
from services.learner_profile import build_learner_profile
from services.llm import chat, stream_text
from services.memory_topics import build_memory_topics

notes_bp = Blueprint('notes', __name__)


def _parse_int_param(value: str | None, default: int, min_val: int, max_val: int) -> tuple[int, str | None]:
    if value is None:
        return default, None
    try:
        parsed = int(value)
    except (ValueError, TypeError):
        return default, f"参数必须是整数，收到：{value!r}"
    return max(min_val, min(max_val, parsed)), None


def _parse_date_param(value: str | None, name: str) -> tuple[str | None, str | None]:
    if not value:
        return None, None
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None, f"{name} 格式错误，应为 YYYY-MM-DD"
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        return None, f"{name} 不是有效日期"
    return value, None


SUMMARY_SYSTEM_PROMPT = """你是一个 IELTS 英语词汇学习助手。请根据用户当天的学习数据和 AI 问答记录，生成一份简洁、可读的每日学习总结，使用 Markdown 格式。

总结结构请尽量包含：
1. 学习概况
2. AI 问答记录
3. 薄弱点与建议
4. 今日亮点

要求：
- 使用中文
- 内容具体，不要空泛
- 如果当天学习记录很少，也要明确指出并给出下一步建议
"""

_GENERATE_COOLDOWN_SECONDS = 300
_SUMMARY_JOB_TTL_SECONDS = 3600
_summary_jobs: dict[str, dict] = {}
_summary_jobs_lock = threading.Lock()


def _utc_now() -> datetime:
    return datetime.utcnow()


def _date_bounds(target_date: str) -> tuple[datetime, datetime]:
    start_dt = datetime.strptime(target_date, '%Y-%m-%d')
    return start_dt, start_dt + timedelta(days=1)


def _check_generate_cooldown(user_id: int, target_date: str) -> tuple[UserDailySummary | None, tuple | None]:
    existing = UserDailySummary.query.filter_by(user_id=user_id, date=target_date).first()
    if existing and existing.generated_at:
        elapsed = (_utc_now() - existing.generated_at).total_seconds()
        if elapsed < _GENERATE_COOLDOWN_SECONDS:
            retry_after = max(1, int(_GENERATE_COOLDOWN_SECONDS - elapsed))
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


def _collect_summary_source_data(user_id: int, target_date: str):
    start_dt, end_dt = _date_bounds(target_date)
    notes = (
        UserLearningNote.query
        .filter_by(user_id=user_id)
        .filter(UserLearningNote.created_at >= start_dt, UserLearningNote.created_at < end_dt)
        .order_by(UserLearningNote.created_at.asc())
        .all()
    )
    sessions = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.started_at >= start_dt, UserStudySession.started_at < end_dt)
        .order_by(UserStudySession.started_at.asc())
        .all()
    )
    wrong_words = (
        UserWrongWord.query
        .filter_by(user_id=user_id)
        .limit(50)
        .all()
    )
    return notes, sessions, wrong_words


_SUMMARY_MODE_LABELS = {
    'smart': '智能练习',
    'listening': '听音选义',
    'meaning': '看词选义',
    'dictation': '听写',
    'radio': '随身听',
    'quickmemory': '速记',
    'errors': '错词强化',
}

def _format_duration(seconds: int) -> str:
    seconds = max(0, int(seconds or 0))
    if seconds >= 60:
        return f"{seconds // 60}分{seconds % 60}秒"
    return f"{seconds}秒"
def _summary_streak_days(user_id: int, target_date: str) -> int:
    start_dt, end_dt = _date_bounds(target_date)
    rows = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.started_at < end_dt, UserStudySession.words_studied > 0)
        .order_by(UserStudySession.started_at.desc())
        .all()
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


def _build_learning_snapshot(user_id: int, target_date: str, sessions, wrong_words) -> dict:
    _start_dt, end_dt = _date_bounds(target_date)
    today_words = sum(session.words_studied or 0 for session in sessions)
    today_duration = sum(session.duration_seconds or 0 for session in sessions)
    today_correct = sum(session.correct_count or 0 for session in sessions)
    today_wrong = sum(session.wrong_count or 0 for session in sessions)
    today_attempted = today_correct + today_wrong
    today_accuracy = round(today_correct / today_attempted * 100) if today_attempted > 0 else 0

    today_mode_breakdown = []
    for session in sessions:
        mode_label = _SUMMARY_MODE_LABELS.get(session.mode or '', session.mode or '未知模式')
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

    all_sessions = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.started_at < end_dt)
        .all()
    )
    mode_totals: dict[str, dict] = {}
    for session in all_sessions:
        mode = (session.mode or '').strip()
        if not mode:
            continue
        bucket = mode_totals.setdefault(mode, {
            'label': _SUMMARY_MODE_LABELS.get(mode, mode),
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
        'streak_days': _summary_streak_days(user_id, target_date),
        'weakest_mode': weakest_mode,
        'wrong_words': [word.word for word in wrong_words[:8] if word.word],
    }


def _estimate_summary_target_chars(notes, sessions, wrong_words) -> int:
    estimate = 420 + len(notes) * 150 + len(sessions) * 110 + min(len(wrong_words), 20) * 18
    return max(480, min(1800, estimate))


def _build_summary_prompt(
    target_date: str,
    notes,
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
        prompt_parts.append(f"- 今日用时：{_format_duration(learning_snapshot['today_duration'])}")
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
                f"{item['label']} {item['accuracy']}% / {item['words']}词 / { _format_duration(item['duration_seconds']) }"
                for item in learning_snapshot['today_mode_breakdown']
            )
            prompt_parts.append(f"- 今日模式表现：{mode_summary}")

    if sessions:
        prompt_parts.append("### 当天练习记录")
        for session in sessions:
            mode_label = _SUMMARY_MODE_LABELS.get(session.mode or '', session.mode or '未知模式')
            duration_text = _format_duration(session.duration_seconds or 0)
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

    if notes:
        prompt_parts.append("")
        prompt_parts.append("### 当天 AI 问答记录")
        for index, note in enumerate(notes, start=1):
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

    return '\n'.join(prompt_parts)


def _fallback_summary_content(target_date: str) -> str:
    return (
        f"# {target_date} 学习总结\n\n"
        "## 学习概况\n\n"
        "今天暂时没有足够的学习数据可供总结。\n\n"
        "## 建议\n\n"
        "- 先完成一轮词汇练习或向 AI 提一个问题，再回来生成总结。"
    )


def _save_summary(existing: UserDailySummary | None, user_id: int, target_date: str, summary_content: str) -> UserDailySummary:
    if existing:
        existing.content = summary_content
        existing.generated_at = _utc_now()
        db.session.commit()
        return existing

    summary = UserDailySummary(
        user_id=user_id,
        date=target_date,
        content=summary_content,
    )
    db.session.add(summary)
    db.session.commit()
    return summary


def _stream_summary_text(user_content: str):
    messages = [{'role': 'user', 'content': user_content}]
    yield from stream_text(messages, system=SUMMARY_SYSTEM_PROMPT, max_tokens=2000)


def _prune_summary_jobs() -> None:
    cutoff = _utc_now() - timedelta(seconds=_SUMMARY_JOB_TTL_SECONDS)
    with _summary_jobs_lock:
        stale_job_ids = [
            job_id
            for job_id, job in _summary_jobs.items()
            if job['updated_at'] < cutoff and job['status'] in {'completed', 'failed'}
        ]
        for job_id in stale_job_ids:
            _summary_jobs.pop(job_id, None)


def _serialize_summary_job(job: dict) -> dict:
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


def _get_summary_job(job_id: str) -> dict | None:
    _prune_summary_jobs()
    with _summary_jobs_lock:
        job = _summary_jobs.get(job_id)
        return dict(job) if job else None


def _update_summary_job(job_id: str, **fields) -> dict | None:
    with _summary_jobs_lock:
        job = _summary_jobs.get(job_id)
        if not job:
            return None
        job.update(fields)
        job['updated_at'] = _utc_now()
        return dict(job)


def _find_running_summary_job(user_id: int, target_date: str) -> dict | None:
    _prune_summary_jobs()
    with _summary_jobs_lock:
        for job in _summary_jobs.values():
            if (
                job['user_id'] == user_id and
                job['date'] == target_date and
                job['status'] in {'queued', 'running'}
            ):
                return dict(job)
    return None


def _create_summary_job(user_id: int, target_date: str) -> dict:
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
        'created_at': _utc_now(),
        'updated_at': _utc_now(),
    }
    with _summary_jobs_lock:
        _summary_jobs[job['job_id']] = job
    return dict(job)


def _run_summary_job(app, job_id: str, user_id: int, target_date: str) -> None:
    try:
        with app.app_context():
            _update_summary_job(job_id, status='running', progress=8, message='正在收集学习记录...')
            existing = UserDailySummary.query.filter_by(user_id=user_id, date=target_date).first()
            notes, sessions, wrong_words = _collect_summary_source_data(user_id, target_date)
            learning_snapshot = _build_learning_snapshot(user_id, target_date, sessions, wrong_words)
            topic_insights = build_memory_topics(notes, limit=5, include_singletons=True)
            learner_profile = build_learner_profile(user_id, target_date)
            estimated_chars = _estimate_summary_target_chars(notes, sessions, wrong_words)
            _update_summary_job(
                job_id,
                progress=18,
                message='正在整理总结结构...',
                estimated_chars=estimated_chars,
            )

            user_content = _build_summary_prompt(
                target_date,
                notes,
                sessions,
                wrong_words,
                learning_snapshot=learning_snapshot,
                topic_insights=topic_insights,
                learner_profile=learner_profile,
            )
            _update_summary_job(job_id, progress=26, message='AI 正在生成正文...')

            chunks: list[str] = []
            generated_chars = 0
            for chunk in _stream_summary_text(user_content):
                if not chunk:
                    continue
                chunks.append(chunk)
                generated_chars += len(chunk)
                ratio = min(generated_chars / max(estimated_chars, 1), 1.0)
                progress = min(94, 26 + int(ratio * 64))
                _update_summary_job(
                    job_id,
                    progress=progress,
                    message='AI 正在生成正文...',
                    generated_chars=generated_chars,
                )

            summary_content = ''.join(chunks).strip() or _fallback_summary_content(target_date)
            _update_summary_job(
                job_id,
                progress=96,
                message='正在保存总结...',
                generated_chars=max(generated_chars, len(summary_content)),
            )
            saved_summary = _save_summary(existing, user_id, target_date, summary_content)
            _update_summary_job(
                job_id,
                status='completed',
                progress=100,
                message='生成完成',
                generated_chars=max(generated_chars, len(summary_content)),
                summary=saved_summary.to_dict(),
                error=None,
            )
    except Exception as exc:
        logging.exception("[Notes] Summary job failed for user=%s date=%s", user_id, target_date)
        _update_summary_job(
            job_id,
            status='failed',
            message='生成失败，请重试',
            error=str(exc) or '生成失败，请重试',
        )


@notes_bp.route('', methods=['GET'])
@token_required
def get_notes(current_user):
    per_page, err = _parse_int_param(request.args.get('per_page'), default=20, min_val=1, max_val=100)
    if err:
        return jsonify({'error': err}), 400

    before_id_raw = request.args.get('before_id')
    before_id: int | None = None
    if before_id_raw is not None:
        before_id, err = _parse_int_param(before_id_raw, default=0, min_val=1, max_val=2_147_483_647)
        if err:
            return jsonify({'error': f'before_id: {err}'}), 400

    start_date, err = _parse_date_param(request.args.get('start_date'), 'start_date')
    if err:
        return jsonify({'error': err}), 400
    end_date, err = _parse_date_param(request.args.get('end_date'), 'end_date')
    if err:
        return jsonify({'error': err}), 400

    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    filtered_query = UserLearningNote.query.filter_by(user_id=current_user.id)
    if start_date:
        filtered_query = filtered_query.filter(UserLearningNote.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        filtered_query = filtered_query.filter(UserLearningNote.created_at < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))

    memory_source_notes = (
        filtered_query
        .order_by(UserLearningNote.created_at.desc())
        .limit(160)
        .all()
    )
    memory_topics = build_memory_topics(memory_source_notes, limit=8, include_singletons=True)

    query = filtered_query
    if before_id:
        query = query.filter(UserLearningNote.id < before_id)

    total = filtered_query.count()
    notes = query.order_by(UserLearningNote.id.desc()).limit(per_page).all()
    has_more = len(notes) == per_page
    next_cursor = notes[-1].id if has_more else None

    return jsonify({
        'notes': [note.to_dict() for note in notes],
        'memory_topics': memory_topics,
        'total': total,
        'per_page': per_page,
        'next_cursor': next_cursor,
        'has_more': has_more,
    })


@notes_bp.route('/summaries', methods=['GET'])
@token_required
def get_summaries(current_user):
    start_date, err = _parse_date_param(request.args.get('start_date'), 'start_date')
    if err:
        return jsonify({'error': err}), 400
    end_date, err = _parse_date_param(request.args.get('end_date'), 'end_date')
    if err:
        return jsonify({'error': err}), 400

    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    query = UserDailySummary.query.filter_by(user_id=current_user.id)
    if start_date:
        query = query.filter(UserDailySummary.date >= start_date)
    if end_date:
        query = query.filter(UserDailySummary.date <= end_date)

    summaries = query.order_by(UserDailySummary.date.desc()).all()
    return jsonify({'summaries': [summary.to_dict() for summary in summaries]})


@notes_bp.route('/summaries/generate', methods=['POST'])
@token_required
def generate_summary(current_user):
    body = request.get_json() or {}
    target_date = body.get('date', date_type.today().strftime('%Y-%m-%d'))

    target_date, err = _parse_date_param(target_date, 'date')
    if err or not target_date:
        return jsonify({'error': err or '日期格式错误'}), 400
    if target_date > date_type.today().strftime('%Y-%m-%d'):
        return jsonify({'error': '不能为未来日期生成总结'}), 400

    existing, cooldown_response = _check_generate_cooldown(current_user.id, target_date)
    if cooldown_response:
        return cooldown_response

    notes, sessions, wrong_words = _collect_summary_source_data(current_user.id, target_date)
    learning_snapshot = _build_learning_snapshot(current_user.id, target_date, sessions, wrong_words)
    topic_insights = build_memory_topics(notes, limit=5, include_singletons=True)
    learner_profile = build_learner_profile(current_user.id, target_date)
    user_content = _build_summary_prompt(
        target_date,
        notes,
        sessions,
        wrong_words,
        learning_snapshot=learning_snapshot,
        topic_insights=topic_insights,
        learner_profile=learner_profile,
    )

    try:
        messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        response = chat(messages, max_tokens=2000)
        summary_content = (response or {}).get('text', '').strip() or _fallback_summary_content(target_date)
    except Exception as exc:
        logging.warning("[Notes] LLM summary generation failed for user=%s: %s", current_user.id, exc)
        return jsonify({'error': 'AI 生成失败，请稍后重试'}), 500

    try:
        saved_summary = _save_summary(existing, current_user.id, target_date, summary_content)
        return jsonify({'summary': saved_summary.to_dict()})
    except Exception as exc:
        db.session.rollback()
        logging.error("[Notes] Failed to save summary for user=%s: %s", current_user.id, exc)
        return jsonify({'error': '保存失败，请重试'}), 500


@notes_bp.route('/summaries/generate-jobs', methods=['POST'])
@token_required
def start_generate_summary_job(current_user):
    body = request.get_json() or {}
    target_date = body.get('date', date_type.today().strftime('%Y-%m-%d'))

    target_date, err = _parse_date_param(target_date, 'date')
    if err or not target_date:
        return jsonify({'error': err or '日期格式错误'}), 400
    if target_date > date_type.today().strftime('%Y-%m-%d'):
        return jsonify({'error': '不能为未来日期生成总结'}), 400

    running_job = _find_running_summary_job(current_user.id, target_date)
    if running_job:
        return jsonify(_serialize_summary_job(running_job)), 202

    _existing, cooldown_response = _check_generate_cooldown(current_user.id, target_date)
    if cooldown_response:
        return cooldown_response

    job = _create_summary_job(current_user.id, target_date)
    app = current_app._get_current_object()
    threading.Thread(
        target=_run_summary_job,
        args=(app, job['job_id'], current_user.id, target_date),
        daemon=True,
    ).start()
    return jsonify(_serialize_summary_job(job)), 202


@notes_bp.route('/summaries/generate-jobs/<job_id>', methods=['GET'])
@token_required
def get_generate_summary_job(current_user, job_id: str):
    job = _get_summary_job(job_id)
    if not job or job['user_id'] != current_user.id:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify(_serialize_summary_job(job))


@notes_bp.route('/export', methods=['GET'])
@token_required
def export_notes(current_user):
    start_date, err = _parse_date_param(request.args.get('start_date'), 'start_date')
    if err:
        return jsonify({'error': err}), 400
    end_date, err = _parse_date_param(request.args.get('end_date'), 'end_date')
    if err:
        return jsonify({'error': err}), 400

    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    fmt = request.args.get('format', 'md')
    if fmt not in ('md', 'txt'):
        fmt = 'md'

    export_type = request.args.get('type', 'all')
    if export_type not in ('summaries', 'notes', 'all'):
        export_type = 'all'

    sections: list[str] = []

    if export_type in ('summaries', 'all'):
        query = UserDailySummary.query.filter_by(user_id=current_user.id)
        if start_date:
            query = query.filter(UserDailySummary.date >= start_date)
        if end_date:
            query = query.filter(UserDailySummary.date <= end_date)
        summaries = query.order_by(UserDailySummary.date.asc()).all()

        if summaries:
            sections.append("# 每日学习总结\n")
            for summary in summaries:
                sections.append(f"\n---\n\n{summary.content}\n")

    if export_type in ('notes', 'all'):
        query = UserLearningNote.query.filter_by(user_id=current_user.id)
        if start_date:
            query = query.filter(UserLearningNote.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(UserLearningNote.created_at < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        notes = query.order_by(UserLearningNote.created_at.asc()).all()

        if notes:
            sections.append("\n# AI 问答笔记\n")
            current_day = None
            for note in notes:
                day = note.created_at.strftime('%Y-%m-%d') if note.created_at else '未知日期'
                if day != current_day:
                    current_day = day
                    sections.append(f"\n## {day}\n")
                word_info = f"（{note.word_context}）" if note.word_context else ""
                sections.append(f"\n**问：** {note.question}{word_info}\n\n**答：** {note.answer}\n")

    content = '\n'.join(sections) if sections else "暂无数据。"

    if fmt == 'txt':
        content = re.sub(r'#{1,6}\s*', '', content)
        content = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', content)
        content = re.sub(r'\n{3,}', '\n\n', content)

    date_range = f"{start_date or 'all'}_{end_date or 'all'}"
    filename = f"ielts_notes_{date_range}.{'md' if fmt != 'txt' else 'txt'}"

    return jsonify({
        'content': content,
        'filename': filename,
        'format': fmt,
    })
