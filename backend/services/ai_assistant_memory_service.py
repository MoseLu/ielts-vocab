from __future__ import annotations

import logging
from datetime import datetime, timedelta
from importlib import import_module


HISTORY_LIMIT = 20
HISTORY_PRUNE_DAYS = 90
SUMMARIZE_THRESHOLD = 40
SUMMARIZE_CHUNK = 20


def _ai_module():
    return import_module('routes.ai')


def save_turn(user_id: int, user_message: str, assistant_reply: str) -> None:
    ai = _ai_module()
    try:
        ai.db.session.add(ai.UserConversationHistory(
            user_id=user_id,
            role='user',
            content=user_message,
        ))
        ai.db.session.add(ai.UserConversationHistory(
            user_id=user_id,
            role='assistant',
            content=assistant_reply,
        ))
        cutoff = datetime.utcnow() - timedelta(days=HISTORY_PRUNE_DAYS)
        ai.UserConversationHistory.query.filter(
            ai.UserConversationHistory.user_id == user_id,
            ai.UserConversationHistory.created_at < cutoff,
        ).delete(synchronize_session=False)
        ai.db.session.commit()
    except Exception as exc:
        ai.db.session.rollback()
        logging.warning("[AI] Failed to save conversation turn: %s", exc)


def get_or_create_memory(user_id: int):
    ai = _ai_module()
    from sqlalchemy.exc import IntegrityError

    memory = ai.UserMemory.query.filter_by(user_id=user_id).first()
    if memory:
        return memory

    try:
        memory = ai.UserMemory(user_id=user_id)
        ai.db.session.add(memory)
        ai.db.session.flush()
    except IntegrityError:
        ai.db.session.rollback()
        memory = ai.UserMemory.query.filter_by(user_id=user_id).first()

    return memory


def load_memory(user_id: int) -> dict:
    ai = _ai_module()
    memory = ai.UserMemory.query.filter_by(user_id=user_id).first()
    if not memory:
        return {}
    return {
        'goals': memory.get_goals(),
        'ai_notes': memory.get_ai_notes(),
        'conversation_summary': memory.conversation_summary or '',
    }


def add_memory_note(user_id: int, note: str, category: str) -> str:
    ai = _ai_module()
    try:
        memory = ai._get_or_create_memory(user_id)
        notes = memory.get_ai_notes()
        if not any(item.get('note') == note for item in notes):
            notes.append({
                'category': category,
                'note': note,
                'created_at': datetime.utcnow().strftime('%Y-%m-%d'),
            })
            memory.set_ai_notes(notes[-30:])
        ai.db.session.commit()
        return f"已记录：[{category}] {note}"
    except Exception as exc:
        ai.db.session.rollback()
        logging.warning("[AI] Failed to save memory note: %s", exc)
        return f"记录失败：{exc}"


def maybe_summarize_history(user_id: int) -> None:
    ai = _ai_module()
    with ai.current_app.app_context():
        total = ai.UserConversationHistory.query.filter_by(user_id=user_id).count()
        memory = ai.UserMemory.query.filter_by(user_id=user_id).first()
        summarized_count = memory.summary_turn_count if memory else 0
        unsummarized = total - summarized_count
        if unsummarized <= SUMMARIZE_THRESHOLD:
            return

        old_rows = (
            ai.UserConversationHistory.query
            .filter_by(user_id=user_id)
            .order_by(ai.UserConversationHistory.created_at.asc())
            .offset(summarized_count)
            .limit(SUMMARIZE_CHUNK)
            .all()
        )
        if not old_rows:
            return

        snippet = '\n'.join(
            f"{'用户' if row.role == 'user' else 'AI'}：{row.content[:300]}"
            for row in old_rows
        )
        existing_summary = memory.conversation_summary if memory else ''
        summary_prompt = [
            {
                "role": "system",
                "content": (
                    "你是一个摘要助手，请将以下对话压缩为一段简洁的中文摘要（100-200字），"
                    "重点保留：用户的学习目标、偏好、困难、AI给出的重要建议和用户的关键反应。"
                    "不要编造内容，只提炼对话中已有的信息。"
                ),
            },
            {
                "role": "user",
                "content": (
                    (f"【已有摘要】\n{existing_summary}\n\n" if existing_summary else '') +
                    f"【新增对话（{len(old_rows)}条）】\n{snippet}\n\n"
                    "请输出更新后的完整摘要："
                ),
            },
        ]
        try:
            response = ai.chat(summary_prompt, max_tokens=400)
            new_summary = response.get('text', '').strip()
            if new_summary:
                memory = ai._get_or_create_memory(user_id)
                memory.conversation_summary = new_summary
                memory.summary_turn_count = summarized_count + len(old_rows)
                ai.db.session.commit()
        except Exception as exc:
            logging.warning("[AI] Summarization failed for user=%s: %s", user_id, exc)


def load_history(user_id: int) -> list[dict]:
    ai = _ai_module()
    rows = (
        ai.UserConversationHistory.query
        .filter_by(user_id=user_id)
        .order_by(ai.UserConversationHistory.created_at.desc())
        .limit(HISTORY_LIMIT)
        .all()
    )
    return [{"role": row.role, "content": row.content} for row in reversed(rows)]
