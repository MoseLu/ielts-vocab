from __future__ import annotations

import json
import re

from flask import jsonify

from platform_sdk.ai_context_application import build_context_payload
from platform_sdk.catalog_content_custom_books_application import (
    create_catalog_content_custom_book_response as build_catalog_content_custom_book_response,
    get_catalog_content_custom_book_response as build_catalog_content_get_custom_book_response,
    list_catalog_content_custom_books_response as build_catalog_content_list_custom_books_response,
)
from platform_sdk.catalog_content_internal_client import (
    create_catalog_content_custom_book_internal_response,
    get_catalog_content_custom_book_internal_response,
    list_catalog_content_custom_books_internal_response,
)
from platform_sdk.llm_provider_adapter import chat


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
{
  "title": "词书标题",
  "description": "词书描述（20字内）",
  "chapters": [
    { "id": "ch1", "title": "第一章标题", "wordCount": 25 }
  ],
  "words": [
    { "chapterId": "ch1", "word": "abdicate", "phonetic": "/ˈæbdɪkeɪt/", "pos": "v.", "definition": "退位；放弃（职位）" }
  ]
}
"""


def generate_book_response(current_user, body: dict | None):
    body = body or {}
    target_words = body.get('targetWords', 100)
    user_level = body.get('userLevel', 'intermediate')
    focus_areas = body.get('focusAreas', [])
    exclude_words = body.get('excludeWords', [])

    try:
        wrong_words = build_context_payload(current_user.id).get('wrongWords', [])
        wrong_word_list = [word['word'] for word in wrong_words[:30]]
        all_exclude = list(set(exclude_words + wrong_word_list))
    except Exception:
        all_exclude = exclude_words

    user_message = (
        f'请生成一份约 {target_words} 词的自定义词书。\n'
        f'用户水平：{user_level}\n'
        f"重点领域：{', '.join(focus_areas) if focus_areas else '综合'}"
    )
    if all_exclude:
        user_message += f"\n以下词汇已掌握，请排除：{', '.join(all_exclude[:50])}"

    messages = [
        {'role': 'system', 'content': GENERATE_BOOK_PROMPT},
        {'role': 'user', 'content': user_message},
    ]

    try:
        raw = chat(messages, max_tokens=8192)
        raw_text = raw.get('text', '') if isinstance(raw, dict) else str(raw)
        json_match = re.search(r'\{[\s\S]*\}', raw_text)
        if not json_match:
            return jsonify({'error': 'Failed to parse generated book data'}), 500

        data = json.loads(json_match.group())
        try:
            payload, status = create_catalog_content_custom_book_internal_response(current_user.id, data)
        except Exception:
            payload, status = build_catalog_content_custom_book_response(current_user.id, data)
        return jsonify(payload), 200 if status == 201 else status
    except json.JSONDecodeError as exc:
        return jsonify({'error': f'Failed to parse generated book: {exc}'}), 500
    except Exception as exc:
        return jsonify({'error': f'Book generation failed: {exc}'}), 500


def list_custom_books_response(current_user):
    try:
        payload, status = list_catalog_content_custom_books_internal_response(current_user.id)
    except Exception:
        payload, status = build_catalog_content_list_custom_books_response(current_user.id)
    return jsonify(payload), status


def get_custom_book_response(current_user, book_id: str):
    try:
        payload, status = get_catalog_content_custom_book_internal_response(current_user.id, book_id)
    except Exception:
        payload, status = build_catalog_content_get_custom_book_response(current_user.id, book_id)
    return jsonify(payload), status
