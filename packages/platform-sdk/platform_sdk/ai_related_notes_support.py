from __future__ import annotations

import re
from datetime import datetime

from services import learner_profile_repository
from platform_sdk.memory_topics_support import build_memory_topics


_QUERY_STOPWORDS = {
    'the', 'and', 'for', 'with', 'that', 'this', 'have', 'what', 'when', 'where',
    'which', 'from', 'into', 'your', 'about', 'please', 'could', 'would', 'should',
    'kind',
}


def _extract_query_tokens(text: str) -> set[str]:
    english = {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z'-]{1,}", text or '')
        if token.lower() not in _QUERY_STOPWORDS
    }
    chinese = {
        chunk
        for chunk in re.findall(r'[\u4e00-\u9fff]{2,}', text or '')
        if len(chunk.strip()) >= 2
    }
    return english | chinese


def _normalize_question_signature(text: str) -> str:
    lowered = (text or '').lower()
    lowered = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', ' ', lowered)
    return re.sub(r'\s+', ' ', lowered).strip()


def collect_related_learning_notes(
    user_id: int,
    user_message: str,
    frontend_context: dict | None = None,
    limit: int = 3,
) -> dict | None:
    query_tokens = _extract_query_tokens(user_message)
    normalized_message = _normalize_question_signature(user_message)
    current_word = ((frontend_context or {}).get('currentWord') or '').strip().lower()

    recent_notes = learner_profile_repository.list_user_learning_notes(
        user_id,
        limit=80,
        descending=True,
    )
    if not recent_notes:
        return None

    topic_matches = []
    memory_topics = build_memory_topics(
        recent_notes,
        limit=12,
        include_singletons=True,
        related_note_limit=max(limit + 2, 4),
    )
    for topic in memory_topics:
        related_notes = topic.get('related_notes') or []
        topic_text = ' '.join([
            str(topic.get('title') or ''),
            ' '.join(str(item.get('question') or '') for item in related_notes),
        ]).strip()
        topic_signature = _normalize_question_signature(topic_text)
        topic_tokens = _extract_query_tokens(topic_text)
        overlap = query_tokens & topic_tokens
        topic_word = str(topic.get('word_context') or '').strip().lower()

        score = len(overlap) * 2
        if current_word and topic_word == current_word:
            score += 4
        if topic_signature and normalized_message and (
            topic_signature in normalized_message or normalized_message in topic_signature
        ):
            score += 4
        if current_word and current_word in topic_signature:
            score += 1
        if score < 3:
            continue

        items = []
        for item in related_notes[:limit]:
            created_at = item.get('created_at')
            created_at_dt = _parse_optional_datetime(created_at)
            items.append({
                'question': item.get('question') or '',
                'answer': item.get('answer') or '',
                'word_context': item.get('word_context') or '',
                'created_at': created_at_dt or created_at,
            })

        latest_at = _parse_optional_datetime(topic.get('latest_at')) or datetime.min
        topic_matches.append({
            'score': score,
            'repeat_count': int(topic.get('count') or len(items)),
            'items': items,
            'follow_up_hint': topic.get('follow_up_hint') or '',
            'latest_at': latest_at,
        })

    if not topic_matches:
        return None

    topic_matches.sort(
        key=lambda item: (item['score'], item['repeat_count'], item['latest_at']),
        reverse=True,
    )
    best = topic_matches[0]
    return {
        'repeat_count': best['repeat_count'],
        'items': best['items'][:limit],
        'follow_up_hint': best['follow_up_hint'],
    }


def _parse_optional_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except ValueError:
            return None
    return None


def build_related_notes_msg(related_notes: dict | None) -> str | None:
    if not related_notes:
        return None

    repeat_count = int(related_notes.get('repeat_count') or 0)
    items = related_notes.get('items') or []
    follow_up_hint = str(related_notes.get('follow_up_hint') or '').strip()
    if not items:
        return None

    lines = ['[相关历史问答]']
    if repeat_count >= 2:
        lines.append(f'这个主题用户已重复询问 {repeat_count} 次，说明这里可能还没有真正吃透。')
    else:
        lines.append('下面是和当前问题最相关的历史问答，请优先利用。')

    for index, item in enumerate(items, start=1):
        created_at = item.get('created_at')
        date_text = created_at.strftime('%Y-%m-%d') if isinstance(created_at, datetime) else '最近'
        question = str(item.get('question') or '').strip()[:180]
        answer = str(item.get('answer') or '').strip().replace('\n', ' ')[:220]
        word_context = str(item.get('word_context') or '').strip()
        suffix = f'（关联单词：{word_context}）' if word_context else ''
        lines.append(f'{index}. {date_text} | 问：{question}{suffix}')
        lines.append(f'   答：{answer}')

    if repeat_count >= 2:
        lines.append('回答要求：先承认用户之前问过这个点，换一种解释角度，并主动询问是否需要进一步辨析、例句或小测。')
    if follow_up_hint:
        lines.append(f'[Follow-up hint] {follow_up_hint}')
    return '\n'.join(lines)
