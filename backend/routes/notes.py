import re
import json
import logging
from datetime import datetime, timedelta, date as date_type

from flask import Blueprint, jsonify, request
from models import db, UserLearningNote, UserDailySummary, UserStudySession, UserWrongWord
from routes.middleware import token_required
from services.llm import chat

notes_bp = Blueprint('notes', __name__)

# ── Parameter helpers ──────────────────────────────────────────────────────────

def _parse_int_param(value: str | None, default: int, min_val: int, max_val: int) -> tuple[int, str | None]:
    """Parse an integer query param with range clamp. Returns (value, error_msg)."""
    if value is None:
        return default, None
    try:
        n = int(value)
    except (ValueError, TypeError):
        return default, f"参数必须为整数，收到：{value!r}"
    return max(min_val, min(max_val, n)), None


def _parse_date_param(value: str | None, name: str) -> tuple[str | None, str | None]:
    """Validate YYYY-MM-DD date string. Returns (value, error_msg)."""
    if not value:
        return None, None
    if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return None, f"{name} 格式错误，应为 YYYY-MM-DD"
    try:
        datetime.strptime(value, '%Y-%m-%d')
    except ValueError:
        return None, f"{name} 不是有效日期"
    return value, None


# ── GET /api/notes ─────────────────────────────────────────────────────────────

@notes_bp.route('', methods=['GET'])
@token_required
def get_notes(current_user):
    """List Q&A notes with cursor-based pagination (before_id) and optional date filter.

    Cursor pagination avoids OFFSET O(N) scans:
      - first page: omit before_id
      - next page:  before_id = id of the last item in previous response
    """
    per_page, err = _parse_int_param(request.args.get('per_page'), default=20, min_val=1, max_val=100)
    if err:
        return jsonify({'error': err}), 400

    before_id_raw = request.args.get('before_id')
    before_id: int | None = None
    if before_id_raw is not None:
        before_id, err = _parse_int_param(before_id_raw, default=0, min_val=1, max_val=2_147_483_647)
        if err:
            return jsonify({'error': f'before_id: {err}'}), 400

    # Validate date params
    start_date, err = _parse_date_param(request.args.get('start_date'), 'start_date')
    if err:
        return jsonify({'error': err}), 400
    end_date, err = _parse_date_param(request.args.get('end_date'), 'end_date')
    if err:
        return jsonify({'error': err}), 400

    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    query = UserLearningNote.query.filter_by(user_id=current_user.id)

    if start_date:
        query = query.filter(UserLearningNote.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(UserLearningNote.created_at < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
    if before_id:
        query = query.filter(UserLearningNote.id < before_id)

    total = query.count()
    notes = (
        query
        .order_by(UserLearningNote.id.desc())
        .limit(per_page)
        .all()
    )

    has_more = len(notes) == per_page
    next_cursor = notes[-1].id if has_more else None

    return jsonify({
        'notes': [n.to_dict() for n in notes],
        'total': total,
        'per_page': per_page,
        'next_cursor': next_cursor,
        'has_more': has_more,
    })


# ── GET /api/notes/summaries ───────────────────────────────────────────────────

@notes_bp.route('/summaries', methods=['GET'])
@token_required
def get_summaries(current_user):
    """List daily summaries with optional date range filter."""
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
    return jsonify({'summaries': [s.to_dict() for s in summaries]})


# ── POST /api/notes/summaries/generate ────────────────────────────────────────

SUMMARY_SYSTEM_PROMPT = """你是一个 IELTS 英语词汇学习助手。请根据用户今日的学习数据和 AI 问答记录，生成一份简洁、可读的每日学习总结，使用 Markdown 格式。

总结结构（按需包含）：
1. **学习概况** — 今日学习词书/章节、总词数、准确率
2. **AI 问答记录** — 列出今日向 AI 提问的重要知识点（每条包含问题摘要和要点答案）
3. **薄弱点与建议** — 基于错词和准确率给出下次学习建议
4. **今日亮点** — 值得记住的单词或规律

要求：
- 语言用中文，格式用 Markdown
- 知识点要具体（列出单词、发音规律、例句要点等）
- 总结要实用，用户可随时查阅复习
- 如果没有数据，说明当日无学习记录
"""

# Rate limit: max 1 generation per date per user per hour
_GENERATE_COOLDOWN_SECONDS = 3600


@notes_bp.route('/summaries/generate', methods=['POST'])
@token_required
def generate_summary(current_user):
    """Generate or regenerate an AI summary for a given date."""
    body = request.get_json() or {}
    target_date = body.get('date', date_type.today().strftime('%Y-%m-%d'))

    # Validate date format
    target_date, err = _parse_date_param(target_date, 'date')
    if err or not target_date:
        return jsonify({'error': err or '日期格式错误'}), 400

    # Reject future dates (no study data exists yet)
    if target_date > date_type.today().strftime('%Y-%m-%d'):
        return jsonify({'error': '不能为未来日期生成总结'}), 400

    # Rate limiting: check last generated_at
    existing = UserDailySummary.query.filter_by(
        user_id=current_user.id, date=target_date
    ).first()
    if existing and existing.generated_at:
        elapsed = (datetime.utcnow() - existing.generated_at).total_seconds()
        if elapsed < _GENERATE_COOLDOWN_SECONDS:
            wait_min = int((_GENERATE_COOLDOWN_SECONDS - elapsed) / 60) + 1
            return jsonify({
                'error': f'生成过于频繁，请 {wait_min} 分钟后再试',
                'cooldown': True,
            }), 429

    start_dt = datetime.strptime(target_date, '%Y-%m-%d')
    end_dt = start_dt + timedelta(days=1)

    # Fetch data for this date
    notes = (
        UserLearningNote.query
        .filter_by(user_id=current_user.id)
        .filter(UserLearningNote.created_at >= start_dt, UserLearningNote.created_at < end_dt)
        .order_by(UserLearningNote.created_at.asc())
        .all()
    )
    sessions = (
        UserStudySession.query
        .filter_by(user_id=current_user.id)
        .filter(UserStudySession.started_at >= start_dt, UserStudySession.started_at < end_dt)
        .order_by(UserStudySession.started_at.asc())
        .all()
    )
    wrong_words = (
        UserWrongWord.query
        .filter_by(user_id=current_user.id)
        .limit(50).all()
    )

    # Build prompt
    prompt_parts = [f"请为 {target_date} 生成学习总结。\n"]

    if sessions:
        prompt_parts.append("**今日练习记录：**")
        mode_zh = {
            'smart': '智能', 'listening': '听音选义', 'meaning': '看词选义',
            'dictation': '听写', 'radio': '随身听', 'quickmemory': '速记',
        }
        for s in sessions:
            mode_label = mode_zh.get(s.mode or '', s.mode or '未知')
            dur = s.duration_seconds or 0
            dur_str = f"{dur // 60}分{dur % 60}秒" if dur >= 60 else f"{dur}秒"
            cc = s.correct_count or 0
            wc = s.wrong_count or 0
            tot = cc + wc
            acc_pct = round(cc / tot * 100) if tot > 0 else 0
            prompt_parts.append(
                f"- {mode_label}模式：{s.words_studied or 0}词，"
                f"准确率{acc_pct}%，用时{dur_str}"
            )
    else:
        prompt_parts.append("今日无练习记录。")

    if notes:
        prompt_parts.append("\n**今日 AI 问答记录：**")
        for i, n in enumerate(notes, 1):
            q_short = n.question[:200]
            a_short = n.answer[:500]
            word_info = f"（学习单词：{n.word_context}）" if n.word_context else ""
            prompt_parts.append(f"\n问题 {i}{word_info}：\n用户：{q_short}\nAI：{a_short}")
    else:
        prompt_parts.append("\n今日无 AI 问答记录。")

    if wrong_words:
        words_str = '、'.join(w.word for w in wrong_words[:20])
        prompt_parts.append(f"\n**近期错词（最多20个）：**{words_str}")

    user_content = '\n'.join(prompt_parts)

    # Call LLM
    try:
        messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        response = chat(messages, max_tokens=2000)
        summary_content = (response or {}).get('text', '').strip()
        if not summary_content:
            summary_content = f"# {target_date} 学习总结\n\n暂无足够数据生成总结。"
    except Exception as e:
        logging.warning(f"[Notes] LLM summary generation failed for user={current_user.id}: {e}")
        return jsonify({'error': 'AI 生成失败，请稍后重试'}), 500

    # Save or update summary
    try:
        if existing:
            existing.content = summary_content
            existing.generated_at = datetime.utcnow()
            db.session.commit()
            return jsonify({'summary': existing.to_dict()})
        else:
            new_summary = UserDailySummary(
                user_id=current_user.id,
                date=target_date,
                content=summary_content,
            )
            db.session.add(new_summary)
            db.session.commit()
            return jsonify({'summary': new_summary.to_dict()})
    except Exception as e:
        db.session.rollback()
        logging.error(f"[Notes] Failed to save summary for user={current_user.id}: {e}")
        return jsonify({'error': '保存失败，请重试'}), 500


# ── GET /api/notes/export ──────────────────────────────────────────────────────

@notes_bp.route('/export', methods=['GET'])
@token_required
def export_notes(current_user):
    """
    Export notes and/or summaries as plain text or markdown.

    Query params:
      start_date  YYYY-MM-DD
      end_date    YYYY-MM-DD
      format      'md' | 'txt'  (default 'md')
      type        'summaries' | 'notes' | 'all'  (default 'all')
    """
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

    sections = []

    # ── Summaries ──────────────────────────────────────────────────────────────
    if export_type in ('summaries', 'all'):
        q = UserDailySummary.query.filter_by(user_id=current_user.id)
        if start_date:
            q = q.filter(UserDailySummary.date >= start_date)
        if end_date:
            q = q.filter(UserDailySummary.date <= end_date)
        summaries = q.order_by(UserDailySummary.date.asc()).all()

        if summaries:
            sections.append("# 每日学习总结\n")
            for s in summaries:
                sections.append(f"\n---\n\n{s.content}\n")

    # ── Q&A Notes ──────────────────────────────────────────────────────────────
    if export_type in ('notes', 'all'):
        q = UserLearningNote.query.filter_by(user_id=current_user.id)
        if start_date:
            q = q.filter(UserLearningNote.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            q = q.filter(UserLearningNote.created_at < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        notes = q.order_by(UserLearningNote.created_at.asc()).all()

        if notes:
            sections.append("\n# AI 问答笔记\n")
            current_day_str = None
            for n in notes:
                day_str = (n.created_at.strftime('%Y-%m-%d') if n.created_at else '未知日期')
                if day_str != current_day_str:
                    current_day_str = day_str
                    sections.append(f"\n## {day_str}\n")
                word_info = f" *（{n.word_context}）*" if n.word_context else ""
                sections.append(f"\n**问：** {n.question}{word_info}\n\n**答：** {n.answer}\n")

    content = '\n'.join(sections) if sections else "暂无数据。"

    # Strip markdown for plain text export
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
