import logging
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
from services.notes_summary_service import (
    build_learning_snapshot as _build_learning_snapshot,
    build_summary_prompt as _build_summary_prompt,
    check_generate_cooldown as _check_generate_cooldown,
    collect_summary_source_data as _collect_summary_source_data,
    date_bounds as _date_bounds,
    estimate_summary_target_chars as _estimate_summary_target_chars,
    fallback_summary_content as _fallback_summary_content,
    format_duration as _format_duration,
    parse_date_param as _parse_date_param,
    parse_int_param as _parse_int_param,
    prune_summary_jobs as _prune_summary_jobs,
    save_summary as _save_summary,
    serialize_summary_job as _serialize_summary_job,
    summary_streak_days as _summary_streak_days,
    utc_now as _utc_now,
)

notes_bp = Blueprint('notes', __name__)

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

_SUMMARY_MODE_LABELS = {
    'smart': '智能练习',
    'listening': '听音选义',
    'meaning': '释义拼词',
    'dictation': '听写',
    'radio': '随身听',
    'quickmemory': '速记',
    'errors': '错词强化',
}


def _stream_summary_text(user_content: str):
    messages = [{'role': 'user', 'content': user_content}]
    yield from stream_text(messages, system=SUMMARY_SYSTEM_PROMPT, max_tokens=2000)
