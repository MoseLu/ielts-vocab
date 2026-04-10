from __future__ import annotations

import logging

from flask import Response, current_app, jsonify, stream_with_context

from platform_sdk.notes_repository_adapters import learning_note_repository
from services import ai_assistant_repository
from services.ai_assistant_memory_service import (
    add_memory_note,
    load_history,
    maybe_summarize_history,
    save_turn,
)
from services.ai_assistant_tool_service import (
    chat_with_tools,
    encode_sse_event,
    make_get_book_chapters,
    make_get_chapter_words,
    make_get_wrong_words,
    stream_chat_with_tools,
    strip_options_for_stream,
)
from services.ai_learning_context_service import build_learning_context_msg
from services.ai_prompt_context_service import parse_options, strip_options
from services.ai_related_notes_service import (
    build_related_notes_msg,
    collect_related_learning_notes,
)
from services.ai_route_support_service import SYSTEM_PROMPT, _get_context_data
from services.learning_events import record_learning_event
from services.llm import TOOLS, web_search
from services.runtime_async import maybe_timeout, spawn_background


def build_ask_messages(current_user, user_message: str, frontend_context: dict) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    try:
        ctx_data = _get_context_data(current_user.id)
        context_msg = build_learning_context_msg(ctx_data, frontend_context)
        messages.append({"role": "user", "content": f"[学习数据]\n{context_msg}"})
    except Exception as exc:
        logging.warning("[AI] Failed to fetch user context: %s", exc)
        messages.append({"role": "user", "content": "[学习数据]\n数据加载失败，请根据用户当前状态回复。"})
        if frontend_context:
            from services.ai_prompt_context_service import build_context_msg

            context_text = build_context_msg(frontend_context)
            messages.append({"role": "user", "content": f"[当前学习状态]\n{context_text}"})

    messages.extend(load_history(current_user.id))

    related_notes_msg = build_related_notes_msg(
        collect_related_learning_notes(current_user.id, user_message, frontend_context)
    )
    if related_notes_msg:
        messages.append({"role": "user", "content": related_notes_msg})

    search_trigger_keywords = ['例句', '例 子', 'example', '怎么 用', '用法', '这个词', '这个词的', '这个单词']
    needs_search = any(keyword in user_message for keyword in search_trigger_keywords)
    if needs_search and frontend_context.get('currentWord'):
        word = frontend_context['currentWord']
        search_query = f"{word} example sentences IELTS context"
        try:
            search_results = web_search(search_query)
            messages.append({
                "role": "user",
                "content": (
                    f"[网页搜索结果 for '{word}']\n{search_results}\n\n"
                    "请根据搜索结果，为用户解释这个单词的用法并给出例句。"
                ),
            })
        except Exception:
            messages.append({"role": "user", "content": user_message})
    else:
        messages.append({"role": "user", "content": user_message})

    return messages


def build_ask_extra_handlers(current_user) -> dict[str, callable]:
    def handle_remember(note: str, category: str = 'other') -> str:
        return add_memory_note(current_user.id, note, category)

    return {
        'remember_user_note': handle_remember,
        'get_wrong_words': make_get_wrong_words(current_user.id),
        'get_chapter_words': make_get_chapter_words(current_user.id),
        'get_book_chapters': make_get_book_chapters(current_user.id),
    }


def persist_ask_response(current_user, user_message: str, frontend_context: dict, clean_reply: str) -> None:
    save_turn(current_user.id, user_message, clean_reply)
    try:
        word_context = frontend_context.get('currentWord') if frontend_context else None
        learning_note_repository.create_learning_note(
            current_user.id,
            question=user_message,
            answer=clean_reply,
            word_context=word_context,
        )
        record_learning_event(
            user_id=current_user.id,
            event_type='assistant_question',
            source='assistant',
            mode=(frontend_context.get('practiceMode') if isinstance(frontend_context, dict) else None),
            word=word_context,
            payload={
                'question': user_message[:500],
                'answer_excerpt': clean_reply[:500],
            },
        )
        ai_assistant_repository.commit()
    except Exception as exc:
        ai_assistant_repository.rollback()
        logging.warning("[AI] Failed to save learning note: %s", exc)

    try:
        app = current_app._get_current_object()

        def summarize_history_in_app():
            with app.app_context():
                maybe_summarize_history(current_user.id)

        spawn_background(summarize_history_in_app)
    except Exception:
        pass


def ask_response(current_user, body):
    body = body or {}
    user_message = str(body.get('message', '') or '').strip()
    frontend_context = body.get('context') if isinstance(body.get('context'), dict) else {}

    logging.warning(
        "[AI] ask from user=%s: msg='%s' ctx=%s",
        current_user.id,
        user_message[:50],
        frontend_context,
    )
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    messages = build_ask_messages(current_user, user_message, frontend_context)
    extra_handlers = build_ask_extra_handlers(current_user)
    try:
        with maybe_timeout(90, RuntimeError('LLM timeout')):
            response = chat_with_tools(messages, tools=TOOLS, extra_handlers=extra_handlers)
        final_text = response.get("text", str(response))
        options = parse_options(final_text)
        clean_reply = strip_options(final_text)
        persist_ask_response(current_user, user_message, frontend_context, clean_reply)
        return jsonify({
            'reply': clean_reply,
            'options': options,
        })
    except Exception as exc:
        logging.error("[AI] /ask error for user=%s: %s", current_user.id, exc, exc_info=True)
        return jsonify({'error': 'AI 服务暂时不可用，请稍后重试'}), 500


def ask_stream_response(current_user, body):
    body = body or {}
    user_message = str(body.get('message', '') or '').strip()
    frontend_context = body.get('context') if isinstance(body.get('context'), dict) else {}

    logging.warning(
        "[AI] ask/stream from user=%s: msg='%s' ctx=%s",
        current_user.id,
        user_message[:50],
        frontend_context,
    )
    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    messages = build_ask_messages(current_user, user_message, frontend_context)
    extra_handlers = build_ask_extra_handlers(current_user)

    @stream_with_context
    def generate():
        raw_reply = ''
        visible_reply = ''
        try:
            yield encode_sse_event({'type': 'status', 'stage': 'start', 'message': 'AI 正在思考...'})
            with maybe_timeout(90, RuntimeError('LLM timeout')):
                for event in stream_chat_with_tools(messages, tools=TOOLS, extra_handlers=extra_handlers):
                    event_type = event.get('type')
                    if event_type == 'status':
                        yield encode_sse_event(event)
                        continue
                    if event_type != 'text_delta':
                        continue
                    raw_reply += str(event.get('text', '') or '')
                    next_visible_reply = strip_options_for_stream(raw_reply)
                    if next_visible_reply.startswith(visible_reply):
                        visible_delta = next_visible_reply[len(visible_reply):]
                    else:
                        visible_delta = next_visible_reply
                    if visible_delta:
                        visible_reply = next_visible_reply
                        yield encode_sse_event({'type': 'text', 'delta': visible_delta})

            clean_reply = strip_options(raw_reply)
            options = parse_options(raw_reply) or []
            persist_ask_response(current_user, user_message, frontend_context, clean_reply)
            if options:
                yield encode_sse_event({'type': 'options', 'options': options})
            yield encode_sse_event({'type': 'done', 'reply': clean_reply, 'options': options})
        except Exception as exc:
            logging.error("[AI] /ask/stream error for user=%s: %s", current_user.id, exc, exc_info=True)
            yield encode_sse_event({'type': 'error', 'error': 'AI 服务暂时不可用，请稍后重试'})

    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache, no-transform'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response
