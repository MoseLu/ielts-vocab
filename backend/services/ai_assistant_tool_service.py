from __future__ import annotations

import json
import logging
import re

from services import learning_stats_repository
from services.ai_route_support_service import (
    _QUICK_MEMORY_MASTERY_TARGET,
    _decorate_wrong_words_with_quick_memory_progress,
    _load_vocab_books,
)
from services.ai_tool_input_service import validate_tool_input
from services.books_catalog_query_service import load_book_vocabulary
from services.books_structure_service import load_book_chapters
from services.llm import TOOL_HANDLERS, chat, stream_chat_events


def make_get_wrong_words(user_id: int):
    def handler(limit: int = 100, book_id: str | None = None) -> str:
        limit_value = min(int(limit), 300)
        words = learning_stats_repository.list_user_wrong_words_for_stats(
            user_id,
            limit=limit_value,
        )
        if not words:
            return "暂无错词记录。"

        decorated = _decorate_wrong_words_with_quick_memory_progress(user_id, words)
        prefix = ''
        if book_id:
            prefix = "当前错词记录暂不支持按词书过滤，以下返回全部错词。\n"
        lines = [
            (
                f"{word['word']}（{word.get('phonetic') or ''}，{word.get('pos') or ''}）"
                f"{word.get('definition') or ''}  错误{word.get('wrong_count', 0)}次"
                f"  艾宾浩斯{word.get('ebbinghaus_streak', 0)}/{word.get('ebbinghaus_target', _QUICK_MEMORY_MASTERY_TARGET)}"
            )
            for word in decorated
        ]
        return prefix + f"共{len(lines)}个错词：\n" + "\n".join(lines)

    return handler


def make_get_chapter_words(user_id: int):
    def handler(book_id: str, chapter_id: int) -> str:
        book = next((item for item in _load_vocab_books() if item['id'] == book_id), None)
        if not book:
            return f"找不到词书 '{book_id}'，请检查 book_id 是否正确。"

        vocabulary = load_book_vocabulary(book_id)
        if not vocabulary:
            return f"词书 '{book['title']}' 的单词数据加载失败。"

        chapter_words = [word for word in vocabulary if word.get('chapter_id') == chapter_id]
        if not chapter_words:
            return f"词书 '{book['title']}' 中找不到第{chapter_id}章，或该章无单词。"

        chapter_title = chapter_words[0].get('chapter_title', f'第{chapter_id}章')
        lines = [
            f"{word['word']}  {word.get('phonetic', '')}  [{word.get('pos', '')}]  {word.get('definition', '')}"
            for word in chapter_words
        ]
        return f"{book['title']} — {chapter_title}（共{len(lines)}词）：\n" + "\n".join(lines)

    return handler


def make_get_book_chapters(user_id: int):
    def handler(book_id: str) -> str:
        book = next((item for item in _load_vocab_books() if item['id'] == book_id), None)
        if not book:
            return f"找不到词书 '{book_id}'，请检查 book_id 是否正确。"

        structure = load_book_chapters(book_id)
        if not structure:
            return f"词书 '{book['title']}' 的章节数据加载失败。"

        chapter_progress = {
            str(record.chapter_id): record
            for record in learning_stats_repository.list_user_chapter_progress_rows(
                user_id,
                book_id=book_id,
            )
        }
        lines = []
        for chapter in structure.get('chapters', []):
            chapter_id = str(chapter.get('id', ''))
            progress = chapter_progress.get(chapter_id)
            if progress:
                total = progress.correct_count + progress.wrong_count
                accuracy = round(progress.correct_count / total * 100) if total > 0 else 0
                if progress.is_completed:
                    status = f"已完成 正确率{accuracy}%"
                else:
                    status = f"进行中 已答{total}题 正确率{accuracy}%"
            else:
                status = "未开始"
            lines.append(
                f"  第{chapter['id']}章《{chapter.get('title', '')}》 {chapter.get('word_count', '?')}词 — {status}"
            )

        total_words = structure.get('total_words', 0)
        total_chapters = structure.get('total_chapters', len(lines))
        done_count = sum(1 for record in chapter_progress.values() if record.is_completed)
        return (
            f"{book['title']}（共{total_chapters}章、{total_words}词，已完成{done_count}章）：\n"
            + "\n".join(lines)
        )

    return handler


def chat_with_tools(
    messages: list[dict],
    tools: list | None = None,
    max_iterations: int = 5,
    extra_handlers: dict | None = None,
) -> dict:
    handlers = {**TOOL_HANDLERS, **(extra_handlers or {})}
    for index in range(max_iterations):
        response = chat(messages, tools=tools, max_tokens=4096)
        if response.get("type") != "tool_call":
            return response

        tool_name = response.get("tool")
        raw_input = response.get("input", {})
        tool_call_id = response.get("tool_call_id", f"call_{index}")
        handler = handlers.get(tool_name)
        tool_input = validate_tool_input(tool_name, raw_input) if isinstance(raw_input, dict) else None

        if handler and tool_input is not None:
            try:
                result = handler(**tool_input)
            except Exception as exc:
                result = f"Tool error: {exc}"
            messages.append({
                "role": "assistant",
                "content": [{
                    "type": "tool_use",
                    "id": tool_call_id,
                    "name": tool_name,
                    "input": tool_input,
                }],
            })
            messages.append({
                "role": "user",
                "content": [{
                    "type": "tool_result",
                    "tool_use_id": tool_call_id,
                    "content": result,
                }],
            })
        elif handler and tool_input is None:
            logging.warning("[AI] Tool '%s' input validation failed: %r", tool_name, raw_input)
            messages.append({
                "role": "assistant",
                "content": f"[Tool '{tool_name}' input validation failed]",
            })
        else:
            messages.append({
                "role": "assistant",
                "content": f"[Tool '{tool_name}' not available]",
            })

    return {"type": "text", "text": "[对话轮次过多，已停止]"}


def strip_options_for_stream(text: str) -> str:
    stripped = re.sub(r'\[options\][\s\S]*?\[/options\]\s*', '', text)
    open_tag_index = stripped.find('[options]')
    if open_tag_index >= 0:
        stripped = stripped[:open_tag_index]
    return stripped.rstrip()


def encode_sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_tool_status_message(tool_name: str, tool_input: dict | None = None) -> str:
    safe_input = tool_input if isinstance(tool_input, dict) else {}

    if tool_name == 'web_search':
        return 'AI 正在检索相关资料...'
    if tool_name == 'remember_user_note':
        category = str(safe_input.get('category', '') or '').strip()
        if category == 'goal':
            return 'AI 正在记录你的学习目标...'
        if category == 'habit':
            return 'AI 正在记录你的学习习惯...'
        if category == 'weakness':
            return 'AI 正在记录你的薄弱点...'
        if category == 'preference':
            return 'AI 正在记录你的学习偏好...'
        if category == 'achievement':
            return 'AI 正在记录你的学习进展...'
        return 'AI 正在记录你的学习信息...'
    if tool_name == 'get_wrong_words':
        return 'AI 正在分析你的错词记录...'
    if tool_name == 'get_chapter_words':
        chapter_id = safe_input.get('chapter_id')
        if chapter_id not in (None, ''):
            return f'AI 正在读取第 {chapter_id} 章词表...'
        return 'AI 正在读取章节词表...'
    if tool_name == 'get_book_chapters':
        return 'AI 正在读取词书章节结构...'
    return 'AI 正在处理学习数据...'


def stream_chat_with_tools(
    messages: list[dict],
    *,
    tools: list | None = None,
    max_iterations: int = 5,
    extra_handlers: dict | None = None,
):
    handlers = {**TOOL_HANDLERS, **(extra_handlers or {})}

    for index in range(max_iterations):
        tool_called = False
        for event in stream_chat_events(messages, tools=tools, max_tokens=4096):
            event_type = event.get('type')
            if event_type == 'text_delta':
                yield {'type': 'text_delta', 'text': str(event.get('text', '') or '')}
                continue
            if event_type != 'tool_call':
                continue

            tool_called = True
            tool_name = str(event.get('tool', '') or '')
            raw_input = event.get('input', {})
            tool_call_id = str(event.get('tool_call_id', f"call_{index}") or f"call_{index}")
            handler = handlers.get(tool_name)
            tool_input = validate_tool_input(tool_name, raw_input) if isinstance(raw_input, dict) else None

            if handler and tool_input is not None:
                status_message = build_tool_status_message(tool_name, tool_input)
                yield {'type': 'status', 'stage': 'tool', 'tool': tool_name, 'message': status_message}
                try:
                    result = handler(**tool_input)
                except Exception as exc:
                    result = f"Tool error: {exc}"

                messages.append({
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": tool_call_id,
                        "name": tool_name,
                        "input": tool_input,
                    }],
                })
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": result,
                    }],
                })
            elif handler and tool_input is None:
                logging.warning("[AI] Tool '%s' input validation failed: %r", tool_name, raw_input)
                messages.append({
                    "role": "assistant",
                    "content": f"[Tool '{tool_name}' input validation failed]",
                })
            else:
                messages.append({
                    "role": "assistant",
                    "content": f"[Tool '{tool_name}' not available]",
                })

        if not tool_called:
            return

    yield {'type': 'text_delta', 'text': '[对话轮次过多，已停止]'}
