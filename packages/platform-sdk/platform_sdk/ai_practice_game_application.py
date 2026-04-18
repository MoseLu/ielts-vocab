from __future__ import annotations

import logging

from flask import jsonify

from platform_sdk.ai_word_image_application import enrich_game_state_with_word_image
from platform_sdk.learning_core_internal_client import (
    fetch_learning_core_game_state_response,
    post_learning_core_game_attempt,
)
from platform_sdk.study_session_support import normalize_chapter_id


def game_state_response(current_user, args) -> tuple:
    try:
        payload = enrich_game_state_with_word_image(
            fetch_learning_core_game_state_response(current_user.id, args)
        )
        return jsonify(payload), 200
    except Exception as exc:
        logging.warning('[AI] Failed to fetch game state: %s', exc)
        return jsonify({'error': 'game state unavailable'}), 503


def game_attempt_response(current_user, body: dict | None) -> tuple:
    payload = body or {}
    node_type = str(payload.get('nodeType') or payload.get('node_type') or 'word').strip().lower() or 'word'
    word = str(payload.get('word') or '').strip()
    dimension = str(payload.get('dimension') or '').strip().lower()
    if node_type == 'word':
        if not word:
            return jsonify({'error': 'word is required'}), 400
        if not dimension:
            return jsonify({'error': 'dimension is required'}), 400
    elif node_type not in {'speaking_boss', 'speaking_reward'}:
        return jsonify({'error': 'invalid nodeType'}), 400

    request_payload = {
        'nodeType': node_type,
        'word': word,
        'dimension': dimension,
        'passed': bool(payload.get('passed')),
        'segmentIndex': payload.get('segmentIndex', payload.get('segment_index')),
        'promptText': str(payload.get('promptText') or payload.get('prompt_text') or '').strip() or None,
        'sourceMode': str(payload.get('sourceMode') or '').strip() or 'game',
        'bookId': str(payload.get('bookId') or '').strip() or None,
        'chapterId': normalize_chapter_id(payload.get('chapterId')),
        'day': payload.get('day'),
        'wordPayload': payload.get('wordPayload') if isinstance(payload.get('wordPayload'), dict) else None,
    }
    try:
        result = post_learning_core_game_attempt(current_user.id, request_payload)
        if isinstance(result.get('game_state'), dict):
            result['game_state'] = enrich_game_state_with_word_image(result['game_state'])
        return jsonify(result), 200
    except Exception as exc:
        logging.warning('[AI] Failed to submit game attempt: %s', exc)
        return jsonify({'error': 'game attempt unavailable'}), 503
