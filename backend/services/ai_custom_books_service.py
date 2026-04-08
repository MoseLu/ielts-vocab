from __future__ import annotations

import json
import re
import uuid
from datetime import datetime

from flask import jsonify

from models import (
    WRONG_WORD_DIMENSIONS,
    WRONG_WORD_PENDING_REVIEW_TARGET,
    _empty_wrong_word_dimension_state,
    _normalize_wrong_word_dimension_state,
)
from services import ai_custom_book_repository
from services.ai_route_support_service import _get_context_data
from services.llm import chat


GENERATE_BOOK_PROMPT = """你是一个 IELTS 词汇专家。用户希望生成一份自定义词汇书，请根据以下信息生成词表。

要求：
1. 返回 JSON 格式，包含 title、description、chapters（数组）、words（数组）
2. 每个 word 必须包含：word（单词）、phonetic（音标，如 /əˈbdev/）、pos（词性，如 n.、v.、adj.）、definition（中文释义）
3. 章节数建议 3-5 章，每章 15-30 个词
4. 词汇要真实存在，是 IELTS 考试常见词汇
5. 不要与用户已掌握的词重复
6. 如果用户指定了 focusAreas（focusAreas），优先选择对应领域的词汇
7. 如果用户指定了 userLevel，按对应难度选词：
   - beginner：大学英语四级水平词汇为主
   - intermediate：六级到雅思核心词汇
   - advanced：雅思高分段学术词汇

输出格式（只需要 JSON，不要其他文字）：
{{
  "title": "词书标题",
  "description": "词书描述（20字内）",
  "chapters": [
    {{ "id": "ch1", "title": "第一章标题", "wordCount": 25 }}
  ],
  "words": [
    {{ "chapterId": "ch1", "word": "abdicate", "phonetic": "/ˈæbdɪkeɪt/", "pos": "v.", "definition": "退位；放弃（职位）" }}
  ]
}}
"""


def generate_book_response(current_user, body):
    body = body or {}
    target_words = body.get('targetWords', 100)
    user_level = body.get('userLevel', 'intermediate')
    focus_areas = body.get('focusAreas', [])
    exclude_words = body.get('excludeWords', [])

    try:
        ctx = _get_context_data(current_user.id)
        wrong_words = ctx.get('wrongWords', [])
        wrong_word_list = [word['word'] for word in wrong_words[:30]]
        all_exclude = list(set(exclude_words + wrong_word_list))
    except Exception:
        all_exclude = exclude_words

    user_message = (
        f"请生成一份约 {target_words} 词的自定义词书。\n"
        f"用户水平：{user_level}\n"
        f"重点领域：{', '.join(focus_areas) if focus_areas else '综合'}"
    )
    if all_exclude:
        user_message += f"\n以下词汇已掌握，请排除：{', '.join(all_exclude[:50])}"

    messages = [
        {"role": "system", "content": GENERATE_BOOK_PROMPT},
        {"role": "user", "content": user_message},
    ]

    try:
        raw = chat(messages, max_tokens=8192)
        raw_text = raw.get('text', '') if isinstance(raw, dict) else str(raw)
        json_match = re.search(r'\{[\s\S]*\}', raw_text)
        if not json_match:
            return jsonify({'error': 'Failed to parse generated book data'}), 500

        data = json.loads(json_match.group())
        book_id = f"custom_{uuid.uuid4().hex[:12]}"
        book = ai_custom_book_repository.create_custom_book(
            book_id=book_id,
            user_id=current_user.id,
            title=data.get('title', '自定义词书'),
            description=data.get('description', ''),
            word_count=len(data.get('words', [])),
        )

        chapter_map = {}
        chapters = data.get('chapters', [])
        for index, chapter_data in enumerate(chapters):
            chapter = ai_custom_book_repository.create_custom_book_chapter(
                chapter_id=chapter_data.get('id', f"ch_{uuid.uuid4().hex[:6]}"),
                book_id=book_id,
                title=chapter_data.get('title', '未命名章节'),
                word_count=chapter_data.get('wordCount', 0),
                sort_order=index,
            )
            chapter_map[chapter.id] = chapter

        for word_data in data.get('words', []):
            ai_custom_book_repository.create_custom_book_word(
                chapter_id=word_data.get('chapterId', next(iter(chapter_map.keys()), 'ch1')),
                word=word_data.get('word', ''),
                phonetic=word_data.get('phonetic', ''),
                pos=word_data.get('pos', ''),
                definition=word_data.get('definition', ''),
            )

        ai_custom_book_repository.commit()
        words = ai_custom_book_repository.list_custom_book_words_for_chapter_ids(
            [chapter.id for chapter in book.chapters]
        )
        return jsonify({
            'bookId': book_id,
            'title': book.title,
            'description': book.description,
            'chapters': [chapter.to_dict() for chapter in book.chapters],
            'words': [word.to_dict() for word in words],
        })
    except json.JSONDecodeError as exc:
        return jsonify({'error': f'Failed to parse generated book: {exc}'}), 500
    except Exception as exc:
        ai_custom_book_repository.rollback()
        return jsonify({'error': f'Book generation failed: {exc}'}), 500


def list_custom_books_response(current_user):
    books = ai_custom_book_repository.list_custom_books(current_user.id)
    return jsonify({'books': [book.to_dict() for book in books]})


def get_custom_book_response(current_user, book_id: str):
    book = ai_custom_book_repository.get_custom_book(current_user.id, book_id)
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    return jsonify(book.to_dict())


def normalize_wrong_word_counter(value, default: int = 0) -> int:
    try:
        return max(0, int(value or default))
    except Exception:
        return default


def clamp_wrong_word_pass_streak(value) -> int:
    return min(normalize_wrong_word_counter(value), WRONG_WORD_PENDING_REVIEW_TARGET)


def normalize_wrong_word_iso(value) -> str | None:
    if not isinstance(value, str):
        return None
    text_value = value.strip()
    if not text_value:
        return None
    try:
        return datetime.fromisoformat(text_value.replace('Z', '+00:00')).isoformat()
    except Exception:
        return None


def pick_later_wrong_word_iso(*values) -> str | None:
    picked = None
    for value in values:
        normalized = normalize_wrong_word_iso(value)
        if normalized is None:
            continue
        if picked is None or normalized > picked:
            picked = normalized
    return picked


def build_incoming_wrong_word_dimension_states(payload: dict) -> dict:
    states = {
        dimension: _empty_wrong_word_dimension_state()
        for dimension in WRONG_WORD_DIMENSIONS
    }

    raw_dimension_state = payload.get('dimension_states') or payload.get('dimensionStates')
    if isinstance(raw_dimension_state, str):
        try:
            raw_dimension_state = json.loads(raw_dimension_state)
        except Exception:
            raw_dimension_state = {}
    if not isinstance(raw_dimension_state, dict):
        raw_dimension_state = {}

    for dimension in WRONG_WORD_DIMENSIONS:
        states[dimension] = _normalize_wrong_word_dimension_state(raw_dimension_state.get(dimension))

    recognition_wrong = normalize_wrong_word_counter(
        payload.get('recognition_wrong', payload.get('recognitionWrong'))
    )
    if recognition_wrong > states['recognition']['history_wrong']:
        states['recognition']['history_wrong'] = recognition_wrong
    states['recognition']['pass_streak'] = max(
        states['recognition']['pass_streak'],
        clamp_wrong_word_pass_streak(
            payload.get(
                'recognition_pass_streak',
                payload.get('recognitionPassStreak', payload.get('ebbinghaus_streak', payload.get('ebbinghausStreak'))),
            )
        ),
    )

    for dimension in ('meaning', 'listening', 'dictation'):
        history_wrong = normalize_wrong_word_counter(
            payload.get(f'{dimension}_wrong', payload.get(f'{dimension}Wrong'))
        )
        if history_wrong > states[dimension]['history_wrong']:
            states[dimension]['history_wrong'] = history_wrong
        states[dimension]['pass_streak'] = max(
            states[dimension]['pass_streak'],
            clamp_wrong_word_pass_streak(
                payload.get(
                    f'{dimension}_pass_streak',
                    payload.get(
                        f'{dimension}PassStreak',
                        payload.get(f'{dimension}_review_streak', payload.get(f'{dimension}ReviewStreak')),
                    ),
                )
            ),
        )

    fallback_wrong_count = normalize_wrong_word_counter(
        payload.get('wrong_count', payload.get('wrongCount'))
    )
    total_history_wrong = sum(states[dimension]['history_wrong'] for dimension in WRONG_WORD_DIMENSIONS)
    if fallback_wrong_count > 0 and total_history_wrong == 0:
        states['recognition']['history_wrong'] = fallback_wrong_count
    elif fallback_wrong_count > total_history_wrong:
        states['recognition']['history_wrong'] += fallback_wrong_count - total_history_wrong

    normalized_total = sum(states[dimension]['history_wrong'] for dimension in WRONG_WORD_DIMENSIONS)
    word_value = str(payload.get('word') or '').strip()
    if normalized_total == 0 and word_value:
        states['recognition']['history_wrong'] = 1

    return states


def merge_wrong_word_dimension_states(existing_states: dict, incoming_states: dict) -> dict:
    merged = {}

    for dimension in WRONG_WORD_DIMENSIONS:
        base_state = _normalize_wrong_word_dimension_state(existing_states.get(dimension))
        incoming_state = _normalize_wrong_word_dimension_state(incoming_states.get(dimension))
        latest_wrong_at = pick_later_wrong_word_iso(
            base_state.get('last_wrong_at'),
            incoming_state.get('last_wrong_at'),
        )
        latest_pass_at = pick_later_wrong_word_iso(
            base_state.get('last_pass_at'),
            incoming_state.get('last_pass_at'),
        )
        if latest_pass_at and (latest_wrong_at is None or latest_pass_at > latest_wrong_at):
            pass_source = incoming_state if latest_pass_at == incoming_state.get('last_pass_at') else base_state
            pass_streak = clamp_wrong_word_pass_streak(pass_source.get('pass_streak'))
            if pass_streak <= 0:
                pass_streak = max(
                    clamp_wrong_word_pass_streak(base_state.get('pass_streak')),
                    clamp_wrong_word_pass_streak(incoming_state.get('pass_streak')),
                )
        elif latest_wrong_at:
            pass_streak = 0
        else:
            pass_streak = max(
                clamp_wrong_word_pass_streak(base_state.get('pass_streak')),
                clamp_wrong_word_pass_streak(incoming_state.get('pass_streak')),
            )

        merged[dimension] = {
            'history_wrong': max(
                normalize_wrong_word_counter(base_state.get('history_wrong')),
                normalize_wrong_word_counter(incoming_state.get('history_wrong')),
            ),
            'pass_streak': pass_streak,
            'last_wrong_at': latest_wrong_at,
            'last_pass_at': latest_pass_at,
        }

    return merged


def max_wrong_word_counter(*values) -> int:
    return max(normalize_wrong_word_counter(value) for value in values)
