from __future__ import annotations

import logging

from flask import jsonify

from services.ai_assistant_memory_service import save_turn
from services.ai_assistant_tool_service import chat_with_tools
from services.ai_learning_context_service import GREET_SYSTEM_PROMPT_V2, build_learning_context_msg
from services.ai_prompt_context_service import parse_options, strip_options
from services.ai_route_support_service import _get_context_data, _track_metric
from services.llm import correct_text


def build_greet_fallback(current_user, ctx_data: dict | None = None) -> str:
    name = (getattr(current_user, 'username', None) or '同学').strip() or '同学'
    ctx_data = ctx_data or {}

    total_learned = int(ctx_data.get('totalLearned') or 0)
    accuracy_rate = ctx_data.get('accuracyRate')
    wrong_words = ctx_data.get('wrongWords') or []
    recent_sessions = ctx_data.get('recentSessions') or []
    learner_profile = ctx_data.get('learnerProfile') or {}
    dimensions = learner_profile.get('dimensions') or []
    focus_words = learner_profile.get('focus_words') or []
    memory_system = learner_profile.get('memory_system') or {}
    repeated_topics = learner_profile.get('repeated_topics') or []
    next_actions = learner_profile.get('next_actions') or []

    if total_learned <= 0 and not recent_sessions and not repeated_topics and not focus_words and not dimensions:
        return f"你好，{name}！我是雅思小助手。你可以告诉我今天想学哪本词书，或者直接开始一章练习。"

    parts = [f"你好，{name}！我是雅思小助手。"]
    if repeated_topics:
        topic = repeated_topics[0] or {}
        topic_title = str(topic.get('title') or '').strip()
        topic_count = int(topic.get('count') or 0)
        if topic_title:
            repeat_text = f"这个点你已经反复问过 {topic_count} 次" if topic_count > 1 else "这个点你最近又问到了"
            parts.append(f"我注意到你最近在“{topic_title}”上有些卡住，{repeat_text}，这次我可以换个更容易抓住差别的讲法。")
    elif focus_words:
        focus_text = '、'.join(item.get('word', '') for item in focus_words[:3] if item.get('word'))
        if focus_text:
            parts.append(f"你这阶段的重点突破词主要集中在 {focus_text}，我可以顺着这些词继续帮你拆开辨析。")

    if total_learned > 0:
        summary = f"你已经累计学习了 {total_learned} 个词"
        if isinstance(accuracy_rate, (int, float)):
            summary += f"，整体正确率约 {int(accuracy_rate)}%"
        parts.append(summary + "。")

    priority_dimension_label = str(memory_system.get('priority_dimension_label') or '').strip()
    priority_reason = str(memory_system.get('priority_reason') or '').strip()
    if priority_dimension_label:
        reason_suffix = f"，原因是{priority_reason}" if priority_reason else ''
        parts.append(f"按四维记忆节奏，你现在最该先补的是“{priority_dimension_label}”{reason_suffix}。")
    elif dimensions:
        dimension = dimensions[0] or {}
        label = str(dimension.get('label') or dimension.get('dimension') or '').strip()
        accuracy = dimension.get('accuracy')
        if label:
            accuracy_suffix = f"，目前准确率大约 {int(accuracy)}%" if isinstance(accuracy, (int, float)) else ''
            parts.append(f"当前最值得优先补的是“{label}”{accuracy_suffix}。")
    elif wrong_words:
        focus_text = '、'.join(word.get('word', '') for word in wrong_words[:3] if word.get('word'))
        if focus_text:
            parts.append(f"近期可以优先复习：{focus_text}。")

    speaking_state = next(
        (item for item in (memory_system.get('dimensions') or []) if item.get('key') == 'speaking'),
        None,
    )
    if speaking_state and speaking_state.get('status') == 'needs_setup':
        parts.append("另外，口语维度目前还没有稳定记录，后面要补一轮跟读和造句。")

    if next_actions:
        first_action = str(next_actions[0]).strip()
        if first_action:
            parts.append(f"如果你愿意，我们可以先从“{first_action}”开始。")
    elif recent_sessions:
        latest = recent_sessions[0]
        book_title = latest.get('book_title') or latest.get('book_id') or '当前词书'
        chapter_id = latest.get('chapter_id')
        chapter_label = f"第{chapter_id}章" if chapter_id else '当前章节'
        parts.append(f"如果你愿意，我可以继续围绕 {book_title} {chapter_label} 帮你安排复习。")
    else:
        parts.append("如果你愿意，我可以根据你最近的学习情况帮你安排下一步复习。")

    return ''.join(parts)


def greet_response(current_user, body):
    body = body or {}
    frontend_context = body.get('context') or {}
    messages = [{"role": "system", "content": GREET_SYSTEM_PROMPT_V2}]
    ctx_data = {}
    try:
        ctx_data = _get_context_data(current_user.id)
        context_msg = build_learning_context_msg(ctx_data, frontend_context)
        messages.append({
            "role": "user",
            "content": (
                "补充要求：如果画像已经显示明显弱点、重复困惑主题或重点突破词，优先围绕这些点自然开场。"
                "不要默认输出选项；只有当下一步动作非常明确时，才补 1-2 个简短选项。"
            ),
        })
        messages.append({
            "role": "user",
            "content": f"[学习数据]\n{context_msg}\n\n请根据以上数据，生成一条个性化的问候。",
        })
    except Exception as exc:
        logging.warning("[AI] greet context load failed for user=%s: %s", current_user.id, exc)
        messages.append({
            "role": "user",
            "content": "补充要求：默认自然开场，不要默认输出选项。",
        })
        messages.append({
            "role": "user",
            "content": "请生成一条欢迎问候语，用户可能刚开始学习。",
        })

    try:
        response = chat_with_tools(messages, tools=None)
        final_text = response.get("text", str(response))
        options = parse_options(final_text) or []
        clean_reply = strip_options(final_text).strip()
        save_turn(current_user.id, '[用户打开了AI助手]', clean_reply)
        return jsonify({'reply': clean_reply, 'options': options})
    except Exception as exc:
        logging.warning("[AI] greet failed for user=%s: %s", current_user.id, exc)
        fallback_reply = build_greet_fallback(current_user, ctx_data)
        save_turn(current_user.id, '[用户打开了AI助手]', fallback_reply)
        return jsonify({'reply': fallback_reply, 'options': []}), 200


def correct_text_response(current_user, body):
    body = body or {}
    text_in = str(body.get('text') or '').strip()
    if not text_in:
        return jsonify({
            'is_valid_english': False,
            'message': '请输入英文句子（建议 1-50 词）。',
        }), 200
    if len(text_in.split()) > 80:
        return jsonify({'error': '句子过长，请控制在 80 词内'}), 400
    result = correct_text(text_in)
    _track_metric(current_user.id, 'writing_correction_used', {'length': len(text_in.split())})
    return jsonify(result), 200


def correction_feedback_response(current_user, body):
    adopted = bool((body or {}).get('adopted'))
    _track_metric(current_user.id, 'writing_correction_adoption', {'adopted': adopted})
    return jsonify({'ok': True}), 200
