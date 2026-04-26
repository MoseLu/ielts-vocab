from __future__ import annotations

from services.word_mastery_service import (
    build_game_practice_state,
    start_game_campaign_session,
    update_game_campaign_attempt,
)
from services.game_theme_catalog_service import build_game_theme_catalog
from services.study_sessions import normalize_chapter_id


def build_learning_core_game_state_response(user_id: int, args) -> tuple[dict, int]:
    payload = build_game_practice_state(
        user_id,
        book_id=str(args.get('bookId') or args.get('book_id') or '').strip() or None,
        chapter_id=normalize_chapter_id(args.get('chapterId', args.get('chapter_id'))),
        day=args.get('day'),
        theme_id=str(args.get('themeId') or args.get('theme_id') or '').strip() or None,
        theme_chapter_id=str(args.get('themeChapterId') or args.get('theme_chapter_id') or '').strip() or None,
        task=str(args.get('task') or '').strip() or None,
        dimension=str(args.get('dimension') or '').strip() or None,
    )
    return payload, 200


def build_learning_core_game_themes_response(args) -> tuple[dict, int]:
    return build_game_theme_catalog(
        theme_id=str(args.get('themeId') or args.get('theme_id') or '').strip() or None,
        page=args.get('page'),
    ), 200


def post_learning_core_game_session_start_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    try:
        game_state = start_game_campaign_session(
            user_id,
            book_id=str(payload.get('bookId') or payload.get('book_id') or '').strip() or None,
            chapter_id=normalize_chapter_id(payload.get('chapterId', payload.get('chapter_id'))),
            day=payload.get('day'),
            theme_id=str(payload.get('themeId') or payload.get('theme_id') or '').strip() or None,
            theme_chapter_id=str(payload.get('themeChapterId') or payload.get('theme_chapter_id') or '').strip() or None,
            task=str(payload.get('task') or '').strip() or None,
            dimension=str(payload.get('taskDimension') or payload.get('task_dimension') or payload.get('dimension') or '').strip() or None,
            enabled_boosts=payload.get('enabledBoosts') if isinstance(payload.get('enabledBoosts'), dict) else None,
        )
    except ValueError as exc:
        return {'error': str(exc)}, 400
    return {'game_state': game_state}, 200


def _normalize_game_attempt_state(result: dict | None, *, node_type: str) -> dict:
    payload = result if isinstance(result, dict) else {}
    failed_dimensions = payload.get('failedDimensions')
    if not isinstance(failed_dimensions, list):
        failed_dimensions = payload.get('failed_dimensions')
    if not isinstance(failed_dimensions, list):
        dimension_states = payload.get('dimension_states')
        if isinstance(dimension_states, dict):
            failed_dimensions = [
                dimension
                for dimension, state in dimension_states.items()
                if isinstance(dimension, str)
                and isinstance(state, dict)
                and int(state.get('history_wrong') or 0) > 0
                and int(state.get('pass_streak') or 0) < 4
            ]
    if not isinstance(failed_dimensions, list):
        failed_dimensions = payload.get('pending_dimensions')
    if not isinstance(failed_dimensions, list):
        failed_dimensions = []

    return {
        'nodeType': str(payload.get('nodeType') or payload.get('node_type') or node_type or 'word'),
        'status': str(payload.get('status') or payload.get('overall_status') or 'pending'),
        'failedDimensions': [str(item) for item in failed_dimensions if isinstance(item, str)],
        'bossFailures': int(payload.get('bossFailures') or payload.get('boss_failures') or 0),
        'rewardFailures': int(payload.get('rewardFailures') or payload.get('reward_failures') or 0),
    }


def post_learning_core_word_mastery_attempt_response(user_id: int, body: dict | None) -> tuple[dict, int]:
    payload = body or {}
    node_type = str(payload.get('nodeType') or payload.get('node_type') or 'word').strip().lower() or 'word'
    word = str(payload.get('word') or '').strip()
    dimension = str(payload.get('dimension') or '').strip().lower()
    if node_type == 'word':
        if not word:
            return {'error': 'word is required'}, 400
        if not dimension:
            return {'error': 'dimension is required'}, 400
    elif node_type not in {'speaking_boss', 'speaking_reward'}:
        return {'error': 'invalid nodeType'}, 400

    try:
        state = update_game_campaign_attempt(
            user_id,
            node_type=node_type,
            word=word,
            dimension=dimension,
            passed=bool(payload.get('passed')),
            source_mode=str(payload.get('sourceMode') or payload.get('source_mode') or '').strip() or None,
            book_id=str(payload.get('bookId') or payload.get('book_id') or '').strip() or None,
            chapter_id=normalize_chapter_id(payload.get('chapterId', payload.get('chapter_id'))),
            day=payload.get('day'),
            word_payload=payload.get('wordPayload') if isinstance(payload.get('wordPayload'), dict) else payload,
            segment_index=payload.get('segmentIndex', payload.get('segment_index')),
            hint_used=bool(payload.get('hintUsed', payload.get('hint_used'))),
            input_mode=str(payload.get('inputMode') or payload.get('input_mode') or '').strip() or None,
            boost_type=str(payload.get('boostType') or payload.get('boost_type') or '').strip() or None,
        )
    except ValueError as exc:
        return {'error': str(exc)}, 400

    game_state = build_game_practice_state(
        user_id,
        book_id=str(payload.get('bookId') or payload.get('book_id') or '').strip() or None,
        chapter_id=normalize_chapter_id(payload.get('chapterId', payload.get('chapter_id'))),
        day=payload.get('day'),
        theme_id=str(payload.get('themeId') or payload.get('theme_id') or '').strip() or None,
        theme_chapter_id=str(payload.get('themeChapterId') or payload.get('theme_chapter_id') or '').strip() or None,
        task=str(payload.get('task') or '').strip() or None,
        dimension=str(payload.get('taskDimension') or payload.get('task_dimension') or '').strip() or None,
    )
    return {
        'state': _normalize_game_attempt_state(state, node_type=node_type),
        'mastery_state': state if node_type == 'word' else None,
        'scoreDelta': int(state.get('scoreDelta') or 0),
        'hits': int(state.get('hits') or 0),
        'bestHits': int(state.get('bestHits') or 0),
        'resultOverlay': state.get('resultOverlay'),
        'game_state': game_state,
    }, 200
