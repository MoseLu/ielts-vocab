import logging
import re

from flask import jsonify

from platform_sdk.ai_word_image_application import enrich_game_state_with_word_image
from platform_sdk.learning_repository_adapters import (
    learning_event_repository,
    learning_stats_repository,
)
from platform_sdk.learner_profile_builder_adapter import build_learner_profile
from services.game_campaign_session import start_game_campaign_session
from services.word_mastery_service import (
    build_game_practice_state,
    update_game_campaign_attempt,
)
from services.ai_route_support_service import _normalize_chapter_id, _normalize_word_list, _track_metric
from services.ai_vocab_catalog_service import _get_global_vocab_pool
from services.learning_events import record_learning_event


_NON_WORD_PATTERN = re.compile(r"[^a-zA-Z'\-]+")


def _normalize_pronunciation_text(value):
    return _NON_WORD_PATTERN.sub(' ', str(value or '').lower()).strip()


def _transcript_matches_word(word, transcript):
    normalized_word = _normalize_pronunciation_text(word)
    normalized_transcript = _normalize_pronunciation_text(transcript)
    if not normalized_word or not normalized_transcript:
        return False
    if normalized_transcript == normalized_word:
        return True
    return f' {normalized_word} ' in f' {normalized_transcript} '


def pronunciation_check_response(current_user, body):
    body = body or {}
    word = str(body.get('word') or '').strip()
    transcript = str(body.get('transcript') or '').strip()
    sentence = str(body.get('sentence') or '').strip()
    book_id = str(body.get('bookId') or '').strip() or None
    chapter_id = _normalize_chapter_id(body.get('chapterId'))
    if not word:
        return jsonify({'error': 'word is required'}), 400

    score = 85 if _transcript_matches_word(word, transcript) else 65
    passed = score >= 80
    result = {
        'word': word,
        'score': score,
        'passed': passed,
        'stress_feedback': '重音位置基本正确，建议再拉长重读音节。',
        'vowel_feedback': '元音饱满度中等，可再放慢语速。',
        'speed_feedback': '语速可接受，注意词尾清晰度。',
    }
    try:
        record_learning_event(
            user_id=current_user.id,
            event_type='pronunciation_check',
            source='assistant',
            mode='speaking',
            book_id=book_id,
            chapter_id=chapter_id,
            word=word,
            item_count=1,
            correct_count=1 if passed else 0,
            wrong_count=0 if passed else 1,
            payload={
                'score': score,
                'passed': passed,
                'transcript': transcript[:160],
                'sentence': sentence[:300] if sentence else None,
            },
        )
        learning_event_repository.commit()
    except Exception as exc:
        learning_event_repository.rollback()
        logging.warning("[AI] Failed to record pronunciation check: %s", exc)
    try:
        mastery_state = update_game_campaign_attempt(
            current_user.id,
            node_type='word',
            word=word,
            dimension='speaking',
            passed=passed,
            source_mode='speaking',
            book_id=book_id,
            chapter_id=chapter_id,
            word_payload={'word': word},
        )
        result['mastery_state'] = mastery_state
    except Exception as exc:
        logging.warning("[AI] Failed to sync speaking mastery: %s", exc)
    _track_metric(current_user.id, 'pronunciation_check_used', {'word': word, 'score': score})
    return jsonify(result), 200


def speaking_simulate_response(current_user, body):
    body = body or {}
    part = int(body.get('part', 1))
    topic = str(body.get('topic') or 'education').strip()
    target_words = _normalize_word_list(
        body.get('targetWords')
        or body.get('target_words')
        or body.get('words')
        or body.get('word')
    )
    response_text = str(
        body.get('responseText')
        or body.get('response_text')
        or body.get('transcript')
        or ''
    ).strip()
    book_id = str(body.get('bookId') or '').strip() or None
    chapter_id = _normalize_chapter_id(body.get('chapterId'))
    question_map = {
        1: f"Part 1: Do you enjoy learning vocabulary about {topic}?",
        2: f"Part 2: Describe a time when {topic} vocabulary helped your IELTS performance.",
        3: f"Part 3: How can schools improve students' {topic} related lexical resources?",
    }
    question = question_map.get(part, question_map[1])
    try:
        record_learning_event(
            user_id=current_user.id,
            event_type='speaking_simulation',
            source='assistant',
            mode='speaking',
            book_id=book_id,
            chapter_id=chapter_id,
            word=target_words[0] if len(target_words) == 1 else None,
            item_count=max(1, len(target_words)),
            correct_count=1 if response_text else 0,
            wrong_count=0,
            payload={
                'part': part,
                'topic': topic,
                'question': question,
                'target_words': target_words,
                'response_text': response_text[:500] if response_text else None,
            },
        )
        learning_event_repository.commit()
    except Exception as exc:
        learning_event_repository.rollback()
        logging.warning("[AI] Failed to record speaking simulation: %s", exc)
    _track_metric(current_user.id, 'speaking_simulation_used', {'part': part, 'topic': topic})
    return jsonify({
        'part': part,
        'topic': topic,
        'question': question,
        'follow_ups': ['请给出一个具体例子。', '能否用更学术的表达重述？'],
    }), 200


def review_plan_response(current_user):
    profile = build_learner_profile(current_user.id)
    memory_system = profile.get('memory_system') or {}
    dimensions = memory_system.get('dimensions') or []
    plan = profile.get('next_actions') or []
    if not plan:
        plan = ['先补当前优先维度 10 分钟，再安排错词辨析和巩固复现。']

    response = {
        'level': 'five-dimensional',
        'wrong_words': learning_stats_repository.count_user_wrong_words(current_user.id),
        'mastery_rule': memory_system.get('mastery_rule'),
        'priority_dimension': memory_system.get('priority_dimension_label'),
        'priority_reason': memory_system.get('priority_reason'),
        'plan': plan[:4],
        'dimensions': [
            {
                'key': item.get('key'),
                'label': item.get('label'),
                'status': item.get('status'),
                'status_label': item.get('status_label'),
                'schedule_label': item.get('schedule_label'),
                'next_action': item.get('next_action'),
            }
            for item in dimensions
        ],
    }
    _track_metric(
        current_user.id,
        'adaptive_plan_generated',
        {
            'level': 'five-dimensional',
            'priority_dimension': memory_system.get('priority_dimension'),
        },
    )
    return jsonify(response), 200


def game_state_response(current_user, args):
    payload = enrich_game_state_with_word_image(build_game_practice_state(
        current_user.id,
        book_id=str(args.get('bookId') or args.get('book_id') or '').strip() or None,
        chapter_id=_normalize_chapter_id(args.get('chapterId', args.get('chapter_id'))),
        day=args.get('day'),
    ))
    return jsonify(payload), 200


def game_session_start_response(current_user, body):
    payload = body or {}
    try:
        game_state = start_game_campaign_session(
            current_user.id,
            book_id=str(payload.get('bookId') or payload.get('book_id') or '').strip() or None,
            chapter_id=_normalize_chapter_id(payload.get('chapterId', payload.get('chapter_id'))),
            day=payload.get('day'),
            enabled_boosts=payload.get('enabledBoosts') if isinstance(payload.get('enabledBoosts'), dict) else None,
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400
    return jsonify({'game_state': enrich_game_state_with_word_image(game_state)}), 200


def game_attempt_response(current_user, body):
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

    try:
        state = update_game_campaign_attempt(
            current_user.id,
            node_type=node_type,
            word=word,
            dimension=dimension,
            passed=bool(payload.get('passed')),
            source_mode=str(payload.get('sourceMode') or payload.get('source_mode') or '').strip() or 'game',
            book_id=str(payload.get('bookId') or payload.get('book_id') or '').strip() or None,
            chapter_id=_normalize_chapter_id(payload.get('chapterId', payload.get('chapter_id'))),
            day=payload.get('day'),
            word_payload=payload.get('wordPayload') if isinstance(payload.get('wordPayload'), dict) else payload,
            segment_index=payload.get('segmentIndex', payload.get('segment_index')),
            hint_used=bool(payload.get('hintUsed', payload.get('hint_used'))),
            input_mode=str(payload.get('inputMode') or payload.get('input_mode') or '').strip() or None,
            boost_type=str(payload.get('boostType') or payload.get('boost_type') or '').strip() or None,
        )
    except ValueError as exc:
        return jsonify({'error': str(exc)}), 400

    game_state = enrich_game_state_with_word_image(build_game_practice_state(
        current_user.id,
        book_id=str(payload.get('bookId') or payload.get('book_id') or '').strip() or None,
        chapter_id=_normalize_chapter_id(payload.get('chapterId', payload.get('chapter_id'))),
        day=payload.get('day'),
    ))
    failed_dimensions = state.get('failedDimensions')
    if not isinstance(failed_dimensions, list):
        failed_dimensions = state.get('failed_dimensions')
    if not isinstance(failed_dimensions, list):
        dimension_states = state.get('dimension_states')
        if isinstance(dimension_states, dict):
            failed_dimensions = [
                dimension
                for dimension, item in dimension_states.items()
                if isinstance(dimension, str)
                and isinstance(item, dict)
                and int(item.get('history_wrong') or 0) > 0
                and int(item.get('pass_streak') or 0) < 4
            ]
    if not isinstance(failed_dimensions, list):
        failed_dimensions = state.get('pending_dimensions')
    if not isinstance(failed_dimensions, list):
        failed_dimensions = []
    return jsonify({
        'state': {
            'nodeType': str(state.get('nodeType') or state.get('node_type') or node_type),
            'status': str(state.get('status') or state.get('overall_status') or 'pending'),
            'failedDimensions': [str(item) for item in failed_dimensions if isinstance(item, str)],
            'bossFailures': int(state.get('bossFailures') or state.get('boss_failures') or 0),
            'rewardFailures': int(state.get('rewardFailures') or state.get('reward_failures') or 0),
        },
        'scoreDelta': int(state.get('scoreDelta') or 0),
        'hits': int(state.get('hits') or 0),
        'bestHits': int(state.get('bestHits') or 0),
        'resultOverlay': state.get('resultOverlay'),
        'game_state': game_state,
    }), 200


def vocab_assessment_response(current_user, args):
    count = min(max(int(args.get('count', 20)), 5), 50)
    pool = _get_global_vocab_pool()
    import random

    random.shuffle(pool)
    questions = [{
        'word': word.get('word'),
        'definition': word.get('definition'),
        'pos': word.get('pos'),
    } for word in pool[:count]]
    _track_metric(current_user.id, 'vocab_assessment_generated', {'count': count})
    return jsonify({'count': len(questions), 'questions': questions}), 200
