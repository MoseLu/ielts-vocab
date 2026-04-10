from __future__ import annotations

import logging
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy.exc import IntegrityError

from services import ai_assistant_repository
from services.llm import chat


HISTORY_LIMIT = 20
HISTORY_PRUNE_DAYS = 90
SUMMARIZE_THRESHOLD = 40
SUMMARIZE_CHUNK = 20
GREET_TURN_MARKER = '[用户打开了AI助手]'


def save_turn(user_id: int, user_message: str, assistant_reply: str) -> None:
    try:
        ai_assistant_repository.add_conversation_turn(
            user_id,
            user_message=user_message,
            assistant_reply=assistant_reply,
        )
        cutoff = datetime.utcnow() - timedelta(days=HISTORY_PRUNE_DAYS)
        ai_assistant_repository.prune_conversation_history_before(
            user_id,
            cutoff=cutoff,
        )
        ai_assistant_repository.commit()
    except Exception as exc:
        ai_assistant_repository.rollback()
        logging.warning("[AI] Failed to save conversation turn: %s", exc)


def get_or_create_memory(user_id: int):
    memory = ai_assistant_repository.get_user_memory(user_id)
    if memory:
        return memory

    try:
        memory = ai_assistant_repository.create_user_memory(user_id)
        ai_assistant_repository.flush()
    except IntegrityError:
        ai_assistant_repository.rollback()
        memory = ai_assistant_repository.get_user_memory(user_id)

    return memory


def load_memory(user_id: int) -> dict:
    memory = ai_assistant_repository.get_user_memory(user_id)
    if not memory:
        return {}
    return {
        'goals': memory.get_goals(),
        'ai_notes': memory.get_ai_notes(),
        'conversation_summary': memory.conversation_summary or '',
    }


def add_memory_note(user_id: int, note: str, category: str) -> str:
    try:
        memory = get_or_create_memory(user_id)
        notes = memory.get_ai_notes()
        if not any(item.get('note') == note for item in notes):
            notes.append({
                'category': category,
                'note': note,
                'created_at': datetime.utcnow().strftime('%Y-%m-%d'),
            })
            memory.set_ai_notes(notes[-30:])
        ai_assistant_repository.commit()
        return f"已记录：[{category}] {note}"
    except Exception as exc:
        ai_assistant_repository.rollback()
        logging.warning("[AI] Failed to save memory note: %s", exc)
        return f"记录失败：{exc}"


def maybe_summarize_history(user_id: int) -> None:
    with current_app.app_context():
        total = ai_assistant_repository.count_conversation_history(user_id)
        memory = ai_assistant_repository.get_user_memory(user_id)
        summarized_count = memory.summary_turn_count if memory else 0
        unsummarized = total - summarized_count
        if unsummarized <= SUMMARIZE_THRESHOLD:
            return

        old_rows = ai_assistant_repository.list_conversation_history(
            user_id,
            limit=SUMMARIZE_CHUNK,
            offset=summarized_count,
            descending=False,
        )
        if not old_rows:
            return

        filtered_rows = _filter_greet_turn_rows(old_rows)
        if not filtered_rows:
            memory = get_or_create_memory(user_id)
            memory.summary_turn_count = summarized_count + len(old_rows)
            ai_assistant_repository.commit()
            return

        snippet = '\n'.join(
            f"{'用户' if row.role == 'user' else 'AI'}：{row.content[:300]}"
            for row in filtered_rows
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
            response = chat(summary_prompt, max_tokens=400)
            new_summary = response.get('text', '').strip()
            if new_summary:
                memory = get_or_create_memory(user_id)
                memory.conversation_summary = new_summary
                memory.summary_turn_count = summarized_count + len(old_rows)
                ai_assistant_repository.commit()
        except Exception as exc:
            logging.warning("[AI] Summarization failed for user=%s: %s", user_id, exc)


def load_history(user_id: int) -> list[dict]:
    rows = ai_assistant_repository.list_conversation_history(
        user_id,
        limit=HISTORY_LIMIT,
        descending=True,
    )
    filtered_rows = _filter_greet_turn_rows(reversed(rows))
    return [{"role": row.role, "content": row.content} for row in filtered_rows]


def _filter_greet_turn_rows(rows) -> list:
    filtered = []
    skip_next_assistant = False

    for row in rows:
        if skip_next_assistant and row.role == 'assistant':
            skip_next_assistant = False
            continue

        if row.role == 'user' and row.content == GREET_TURN_MARKER:
            skip_next_assistant = True
            continue

        skip_next_assistant = False
        filtered.append(row)

    return filtered
