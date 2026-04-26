from __future__ import annotations

import json
import re
from datetime import timedelta

from service_models.learning_core_models import (
    UserGameEnergyState,
    UserGameSessionState,
    db,
)
from services.word_mastery_support import normalize_word_text, utc_now

GAME_ENERGY_MAX = 5
GAME_SEGMENT_START_COST = 2
GAME_ENERGY_RECOVERY_HOURS = 5
GAME_SEGMENT_PASS_SCORE = 70
GAME_HINTS_PER_SEGMENT = 2
GAME_SCORE_WEIGHTS = {
    'recognition': 10,
    'meaning': 20,
    'listening': 20,
    'speaking': 20,
    'dictation': 30,
}

_WHITESPACE_RE = re.compile(r'\s+')
_GAME_SESSION_TABLES_READY = False


def ensure_game_session_tables() -> None:
    global _GAME_SESSION_TABLES_READY
    if _GAME_SESSION_TABLES_READY:
        return
    UserGameEnergyState.__table__.create(bind=db.engine, checkfirst=True)
    UserGameSessionState.__table__.create(bind=db.engine, checkfirst=True)
    _GAME_SESSION_TABLES_READY = True


def _json_loads(value, default):
    try:
        parsed = json.loads(value) if value else default
    except Exception:
        return default
    return parsed if isinstance(parsed, type(default)) else default


def _json_dumps(value) -> str:
    return json.dumps(value, ensure_ascii=False)


def _normalize_enabled_boosts(value: dict | None) -> dict:
    payload = value if isinstance(value, dict) else {}
    return {
        'spellingBoost': bool(payload.get('spellingBoost', True)),
        'applicationBoost': bool(payload.get('applicationBoost', True)),
        'rewardEligible': bool(payload.get('rewardEligible', True)),
    }


def _normalize_example_sentence(value: str | None) -> str:
    text = _WHITESPACE_RE.sub(' ', str(value or '')).strip()
    return text


def _next_energy_time(base_time):
    return base_time + timedelta(hours=GAME_ENERGY_RECOVERY_HOURS)


def _recover_energy(record: UserGameEnergyState, *, now_utc):
    changed = False
    energy = max(0, int(record.energy or 0))
    energy_max = max(1, int(record.energy_max or GAME_ENERGY_MAX))
    next_energy_at = record.next_energy_at
    while energy < energy_max and next_energy_at is not None and next_energy_at <= now_utc:
        energy += 1
        changed = True
        next_energy_at = None if energy >= energy_max else _next_energy_time(next_energy_at)
    if energy >= energy_max:
        next_energy_at = None
    if changed:
        record.energy = energy
        record.next_energy_at = next_energy_at
        record.updated_at = now_utc


def get_or_create_energy_state(user_id: int) -> UserGameEnergyState:
    ensure_game_session_tables()
    record = UserGameEnergyState.query.filter_by(user_id=user_id).first()
    if record is None:
        record = UserGameEnergyState(
            user_id=user_id,
            energy=GAME_ENERGY_MAX,
            energy_max=GAME_ENERGY_MAX,
        )
        db.session.add(record)
        db.session.flush()
    _recover_energy(record, now_utc=utc_now())
    return record


def get_scope_game_session(user_id: int, *, scope_key: str) -> UserGameSessionState | None:
    ensure_game_session_tables()
    return UserGameSessionState.query.filter_by(user_id=user_id, scope_key=scope_key).first()


def _build_result_overlay(session: UserGameSessionState, game_state: dict) -> dict:
    passed = int(session.score or 0) >= int(session.pass_score or GAME_SEGMENT_PASS_SCORE)
    segment = game_state.get('segment') or {}
    return {
        'title': '试炼达线' if passed else '试炼待补强',
        'tone': 'success' if passed else 'warning',
        'score': int(session.score or 0),
        'passScore': int(session.pass_score or GAME_SEGMENT_PASS_SCORE),
        'passed': passed,
        'bestHits': int(session.best_hits or 0),
        'hintUsage': int(session.hint_usage or 0),
        'bossCompleted': bool(session.boss_completed),
        'rewardCompleted': bool(session.reward_completed),
        'segmentTitle': str(segment.get('title') or f'第 {int(session.segment_index or 0) + 1} 试炼段'),
    }


def _build_application_boost(word_payload: dict | None) -> dict | None:
    payload = word_payload if isinstance(word_payload, dict) else {}
    word = normalize_word_text(payload.get('word'))
    if not word:
        return None
    examples = payload.get('examples') if isinstance(payload.get('examples'), list) else []
    example = next((item for item in examples if isinstance(item, dict) and item.get('en')), None)
    sentence = _normalize_example_sentence(example.get('en') if isinstance(example, dict) else None)
    answer = word
    if sentence and re.search(re.escape(word), sentence, re.IGNORECASE):
        blank_sentence = re.sub(re.escape(word), '____', sentence, count=1, flags=re.IGNORECASE)
    else:
        blank_sentence = f'The explorer used ____ in a natural sentence.'
    options = [answer]
    confusables = payload.get('listening_confusables') if isinstance(payload.get('listening_confusables'), list) else []
    for item in confusables:
        if not isinstance(item, dict):
            continue
        candidate = normalize_word_text(item.get('word'))
        if candidate and candidate not in options:
            options.append(candidate)
        if len(options) >= 4:
            break
    while len(options) < 4:
        filler = ['focus', 'signal', 'route', 'scope'][len(options) - 1]
        if filler not in options:
            options.append(filler)
    return {
        'kind': 'application',
        'status': 'pending',
        'title': f'{word} 应用强化',
        'promptText': '根据句子语境，选出最合适的词补全句子。',
        'sentence': blank_sentence,
        'answer': answer,
        'options': options[:4],
        'translation': (example or {}).get('zh') if isinstance(example, dict) else None,
    }


def _scene_theme(game_state: dict) -> str:
    current_node = game_state.get('currentNode') or {}
    if current_node.get('nodeType') == 'speaking_boss':
        return 'boss'
    if current_node.get('nodeType') == 'speaking_reward':
        return 'reward'
    level_kind = current_node.get('levelKind')
    if level_kind in {'spelling', 'pronunciation', 'definition', 'speaking', 'example'}:
        return str(level_kind)
    dimension = current_node.get('dimension')
    if dimension in {'meaning', 'listening', 'speaking', 'dictation', 'recognition'}:
        return str(dimension)
    return 'launcher'


def _mascot_state(game_state: dict, session_payload: dict) -> str:
    boost_module = session_payload.get('boostModule')
    if session_payload.get('status') == 'result':
        overlay = session_payload.get('resultOverlay') or {}
        return 'correct' if overlay.get('passed') else 'wrong'
    if isinstance(boost_module, dict) and boost_module.get('status') == 'pending':
        return 'encourage'
    current_node = game_state.get('currentNode') or {}
    node_type = current_node.get('nodeType')
    if node_type == 'speaking_boss':
        return 'boss'
    if node_type == 'speaking_reward':
        return 'encourage'
    dimension = current_node.get('dimension')
    if dimension == 'listening':
        return 'listen'
    if dimension == 'speaking':
        return 'encourage'
    return 'idle'


def _score_delta(dimension: str | None, *, passed: bool, hint_used: bool, boost_type: str | None) -> int:
    if boost_type == 'application':
        return -10 if hint_used else 0
    base = GAME_SCORE_WEIGHTS.get(str(dimension or '').strip().lower(), 0) if passed else 0
    penalty = 10 if hint_used else 0
    return base - penalty


def _session_payload(
    session: UserGameSessionState | None,
    *,
    energy_state: UserGameEnergyState,
) -> dict:
    session_dict = session.to_dict() if session is not None else {}
    boost_module = session_dict.get('active_boost_module')
    return {
        'status': str(session_dict.get('status') or 'launcher'),
        'score': int(session_dict.get('score') or 0),
        'hits': int(session_dict.get('hits') or 0),
        'bestHits': int(session_dict.get('best_hits') or 0),
        'hintsRemaining': int(session_dict.get('hints_remaining') or GAME_HINTS_PER_SEGMENT),
        'hintUsage': int(session_dict.get('hint_usage') or 0),
        'energy': int(energy_state.energy or 0),
        'energyMax': int(energy_state.energy_max or GAME_ENERGY_MAX),
        'nextEnergyAt': energy_state.to_dict().get('next_energy_at'),
        'enabledBoosts': _normalize_enabled_boosts(session_dict.get('enabled_boosts')),
        'resultOverlay': session_dict.get('result_overlay'),
        'boostModule': boost_module if isinstance(boost_module, dict) else None,
    }


def _launcher_payload(game_state: dict, *, session_payload: dict) -> dict:
    segment = game_state.get('segment') or {}
    enabled_boosts = _normalize_enabled_boosts(session_payload.get('enabledBoosts'))
    segment_index = max(0, int(segment.get('index') or 1) - 1)
    return {
        'lessonId': f'lesson-{segment_index + 1}',
        'title': str(segment.get('title') or f'第 {segment_index + 1} 试炼段'),
        'estimatedMinutes': 5,
        'energyCost': GAME_SEGMENT_START_COST,
        'passScore': GAME_SEGMENT_PASS_SCORE,
        'segmentIndex': segment_index,
        'boosts': enabled_boosts,
    }


def build_game_session_bundle(
    user_id: int,
    *,
    scope_key: str,
    game_state: dict,
    book_id: str | None,
    chapter_id: str | None,
    day: int | None,
) -> dict:
    ensure_game_session_tables()
    energy_state = get_or_create_energy_state(user_id)
    session = get_scope_game_session(user_id, scope_key=scope_key)
    changed = False
    if session is not None and session.status == 'active':
        current_segment_index = max(0, int((game_state.get('segment') or {}).get('index') or 1) - 1)
        boost_module = session.to_dict().get('active_boost_module')
        if current_segment_index != int(session.segment_index or 0) and not isinstance(boost_module, dict):
            session.status = 'result'
            session.result_overlay = _json_dumps(_build_result_overlay(session, game_state))
            changed = True
        elif game_state.get('currentNode') is None and not isinstance(boost_module, dict):
            session.status = 'result'
            session.result_overlay = _json_dumps(_build_result_overlay(session, game_state))
            changed = True
    if changed:
        db.session.commit()
    payload = _session_payload(session, energy_state=energy_state)
    launcher = _launcher_payload(game_state, session_payload=payload)
    return {
        'session': payload,
        'launcher': launcher,
        'animationPayload': {
            'sceneTheme': _scene_theme(game_state),
            'mascotState': _mascot_state(game_state, payload),
            'feedbackTone': ((payload.get('resultOverlay') or {}).get('tone') if isinstance(payload.get('resultOverlay'), dict) else None),
            'showResultLayer': payload.get('status') == 'result',
        },
        'boostModule': payload.get('boostModule'),
    }


def start_game_session(
    user_id: int,
    *,
    scope_key: str,
    book_id: str | None,
    chapter_id: str | None,
    day: int | None,
    lesson_id: str,
    segment_index: int,
    enabled_boosts: dict | None,
) -> dict:
    ensure_game_session_tables()
    now_utc = utc_now()
    energy_state = get_or_create_energy_state(user_id)
    _recover_energy(energy_state, now_utc=now_utc)
    has_reward_energy = int(energy_state.energy or 0) >= GAME_SEGMENT_START_COST
    session = get_scope_game_session(user_id, scope_key=scope_key)
    if session is None:
        session = UserGameSessionState(
            user_id=user_id,
            scope_key=scope_key,
            book_id=book_id,
            chapter_id=chapter_id,
            day=day,
            lesson_id=lesson_id,
            segment_index=max(0, int(segment_index)),
        )
        db.session.add(session)
    session.book_id = book_id
    session.chapter_id = chapter_id
    session.day = day
    session.lesson_id = lesson_id
    session.segment_index = max(0, int(segment_index))
    session.status = 'active'
    session.score = 0
    session.hits = 0
    session.best_hits = 0
    session.hints_remaining = GAME_HINTS_PER_SEGMENT
    session.hint_usage = 0
    session.pass_score = GAME_SEGMENT_PASS_SCORE
    session_boosts = _normalize_enabled_boosts(enabled_boosts)
    session_boosts['rewardEligible'] = has_reward_energy
    session.enabled_boosts = _json_dumps(session_boosts)
    session.active_boost_module = None
    session.boss_completed = False
    session.reward_completed = False
    session.last_feedback_tone = None
    session.last_feedback_message = None
    session.last_score_delta = 0
    session.result_overlay = None

    if has_reward_energy:
        energy_state.energy = max(0, int(energy_state.energy or 0) - GAME_SEGMENT_START_COST)
    if int(energy_state.energy or 0) < int(energy_state.energy_max or GAME_ENERGY_MAX):
        energy_state.next_energy_at = energy_state.next_energy_at or _next_energy_time(now_utc)
    if int(energy_state.energy or 0) >= int(energy_state.energy_max or GAME_ENERGY_MAX):
        energy_state.next_energy_at = None
    db.session.commit()
    return {
        'energy': int(energy_state.energy or 0),
        'energyMax': int(energy_state.energy_max or GAME_ENERGY_MAX),
        'nextEnergyAt': energy_state.to_dict().get('next_energy_at'),
    }


def apply_game_attempt_meta(
    user_id: int,
    *,
    scope_key: str,
    book_id: str | None,
    chapter_id: str | None,
    day: int | None,
    node_type: str,
    dimension: str | None,
    passed: bool,
    hint_used: bool,
    input_mode: str | None,
    boost_type: str | None,
    word_payload: dict | None,
    game_state: dict,
) -> dict:
    ensure_game_session_tables()
    session = get_scope_game_session(user_id, scope_key=scope_key)
    if session is None:
        session = UserGameSessionState(
            user_id=user_id,
            scope_key=scope_key,
            book_id=book_id,
            chapter_id=chapter_id,
            day=day,
            lesson_id=f'lesson-{max(0, int((game_state.get("segment") or {}).get("index") or 1) - 1) + 1}',
            segment_index=max(0, int((game_state.get('segment') or {}).get('index') or 1) - 1),
            status='active',
            hints_remaining=GAME_HINTS_PER_SEGMENT,
            pass_score=GAME_SEGMENT_PASS_SCORE,
            enabled_boosts=_json_dumps(_normalize_enabled_boosts(None)),
        )
        db.session.add(session)
        db.session.flush()

    normalized_boost_type = str(boost_type or '').strip().lower() or None
    if hint_used and int(session.hints_remaining or 0) > 0:
        session.hints_remaining = max(0, int(session.hints_remaining or 0) - 1)
        session.hint_usage = int(session.hint_usage or 0) + 1
    score_delta = _score_delta(dimension, passed=passed, hint_used=hint_used, boost_type=normalized_boost_type)
    session.score = max(0, int(session.score or 0) + score_delta)
    if normalized_boost_type == 'application':
        session.active_boost_module = None
    elif passed:
        if not hint_used:
            session.hits = int(session.hits or 0) + 1
            session.best_hits = max(int(session.best_hits or 0), int(session.hits or 0))
        if (
            node_type == 'word'
            and str(dimension or '').strip().lower() == 'speaking'
            and _normalize_enabled_boosts(_json_loads(session.enabled_boosts, {})).get('applicationBoost')
        ):
            boost_module = _build_application_boost(word_payload)
            if boost_module is not None:
                session.active_boost_module = _json_dumps(boost_module)
        if node_type == 'speaking_boss':
            session.boss_completed = True
        if node_type == 'speaking_reward':
            session.reward_completed = True
    else:
        session.hits = 0
        if node_type == 'speaking_boss':
            session.boss_completed = False
        if node_type == 'speaking_reward':
            session.reward_completed = False

    session.status = 'active'
    session.last_feedback_tone = 'success' if passed else 'warning'
    session.last_feedback_message = '链路推进成功。' if passed else '当前节点已记入待补强。'
    session.last_score_delta = score_delta
    session.result_overlay = None
    db.session.commit()

    overlay = {
        'tone': 'success' if passed else 'warning',
        'title': '判定成功' if passed else '判定失败',
        'message': session.last_feedback_message,
        'scoreDelta': score_delta,
        'score': int(session.score or 0),
        'hits': int(session.hits or 0),
        'bestHits': int(session.best_hits or 0),
        'hintUsed': bool(hint_used),
        'inputMode': str(input_mode or 'pointer'),
    }
    return {
        'scoreDelta': score_delta,
        'hits': int(session.hits or 0),
        'bestHits': int(session.best_hits or 0),
        'resultOverlay': overlay,
    }
