from __future__ import annotations

from services.word_mastery_service import (
    build_game_practice_state,
    update_word_mastery_attempt,
)
from services.study_sessions import normalize_chapter_id


def build_learning_core_game_state_response(user_id: int, args) -> tuple[dict, int]:
    payload = build_game_practice_state(
        user_id,
        book_id=str(args.get('bookId') or args.get('book_id') or '').strip() or None,
        chapter_id=normalize_chapter_id(args.get('chapterId', args.get('chapter_id'))),
        day=args.get('day'),
    )
    return payload, 200


def post_learning_core_word_mastery_attempt_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    word = str(payload.get('word') or '').strip()
    dimension = str(payload.get('dimension') or '').strip().lower()
    if not word:
        return {'error': 'word is required'}, 400
    if not dimension:
        return {'error': 'dimension is required'}, 400

    try:
        state = update_word_mastery_attempt(
            user_id,
            word=word,
            dimension=dimension,
            passed=bool(payload.get('passed')),
            source_mode=str(payload.get('sourceMode') or payload.get('source_mode') or '').strip() or None,
            book_id=str(payload.get('bookId') or payload.get('book_id') or '').strip() or None,
            chapter_id=normalize_chapter_id(payload.get('chapterId', payload.get('chapter_id'))),
            day=payload.get('day'),
            word_payload=payload.get('wordPayload') if isinstance(payload.get('wordPayload'), dict) else payload,
        )
    except ValueError as exc:
        return {'error': str(exc)}, 400

    game_state = build_game_practice_state(
        user_id,
        book_id=str(payload.get('bookId') or payload.get('book_id') or '').strip() or None,
        chapter_id=normalize_chapter_id(payload.get('chapterId', payload.get('chapter_id'))),
        day=payload.get('day'),
    )
    return {'state': state, 'game_state': game_state}, 200
