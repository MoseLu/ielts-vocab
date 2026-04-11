from __future__ import annotations

from platform_sdk.admin_word_feedback_adapter import admin_word_feedback_repository


WORD_FEEDBACK_TYPE_LABELS = {
    'audio_pronunciation': '音频发音问题',
    'spelling': '单词拼写错误',
    'translation': '翻译不准',
    'other': '其他',
}
WORD_FEEDBACK_SOURCES = {'global_search', 'word_detail'}


def _normalize_text(value, *, max_length: int | None = None) -> str:
    text = ' '.join(str(value or '').split())
    if max_length is not None:
        return text[:max_length]
    return text


def _normalize_feedback_types(value) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        key = _normalize_text(item, max_length=40).lower()
        if not key or key in seen or key not in WORD_FEEDBACK_TYPE_LABELS:
            continue
        seen.add(key)
        normalized.append(key)
    return normalized


def build_word_feedback_list_response(*, limit: int) -> tuple[dict, int]:
    safe_limit = min(max(int(limit or 50), 1), 100)
    rows = admin_word_feedback_repository.list_recent_word_feedback_rows(limit=safe_limit)
    items = []
    for row in rows:
        payload = row.to_dict()
        payload['feedback_type_labels'] = [
            WORD_FEEDBACK_TYPE_LABELS.get(item, item)
            for item in payload['feedback_types']
        ]
        items.append(payload)
    return {
        'items': items,
        'total': admin_word_feedback_repository.count_word_feedback_rows(),
        'feedback_type_labels': WORD_FEEDBACK_TYPE_LABELS,
    }, 200


def submit_word_feedback_response(current_user, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    word = _normalize_text(payload.get('word'), max_length=100)
    if not word:
        return {'error': '缺少单词信息'}, 400

    feedback_types = _normalize_feedback_types(payload.get('feedback_types'))
    if not feedback_types:
        return {'error': '至少选择一个问题类型'}, 400

    source = _normalize_text(payload.get('source'), max_length=40).lower() or 'global_search'
    if source not in WORD_FEEDBACK_SOURCES:
        source = 'global_search'

    comment = _normalize_text(payload.get('comment'), max_length=500)
    record = admin_word_feedback_repository.create_word_feedback(
        user_id=int(current_user.id),
        username=_normalize_text(current_user.username, max_length=100) or f'user-{current_user.id}',
        email=_normalize_text(current_user.email, max_length=255) or None,
        word=word,
        normalized_word=word.lower(),
        phonetic=_normalize_text(payload.get('phonetic'), max_length=100),
        pos=_normalize_text(payload.get('pos'), max_length=50),
        definition=_normalize_text(payload.get('definition'), max_length=500),
        example_en=_normalize_text(payload.get('example_en'), max_length=1000),
        example_zh=_normalize_text(payload.get('example_zh'), max_length=1000),
        source_book_id=_normalize_text(payload.get('book_id'), max_length=100) or None,
        source_book_title=_normalize_text(payload.get('book_title'), max_length=200) or None,
        source_chapter_id=_normalize_text(payload.get('chapter_id'), max_length=100) or None,
        source_chapter_title=_normalize_text(payload.get('chapter_title'), max_length=200) or None,
        feedback_types=feedback_types,
        source=source,
        comment=comment,
    )
    response = record.to_dict()
    response['feedback_type_labels'] = [
        WORD_FEEDBACK_TYPE_LABELS.get(item, item)
        for item in response['feedback_types']
    ]
    return {
        'message': '反馈已提交',
        'feedback': response,
    }, 201
