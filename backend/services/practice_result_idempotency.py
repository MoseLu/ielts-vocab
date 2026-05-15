from __future__ import annotations

import json
from collections.abc import Callable

from sqlalchemy.exc import IntegrityError

from service_models.learning_core_models import UserPracticeResultCommand, db
from services.learning_scope_support import resolve_learning_scope


def canonical_command_json(payload: dict | None) -> str:
    return json.dumps(payload if isinstance(payload, dict) else {}, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def load_result_json(value: str | None) -> dict:
    try:
        result = json.loads(value or '{}')
    except Exception:
        return {}
    return result if isinstance(result, dict) else {}


def scope_key_from_payload(payload: dict | None) -> str:
    return resolve_learning_scope(payload).scope_key


def resolve_attempt_metadata(payload: dict | None) -> tuple[str | None, str | None]:
    data = payload if isinstance(payload, dict) else {}
    idempotency_key = str(
        data.get('idempotencyKey')
        or data.get('idempotency_key')
        or data.get('clientAttemptId')
        or data.get('client_attempt_id')
        or ''
    ).strip() or None
    trace_id = str(data.get('traceId') or data.get('trace_id') or '').strip() or idempotency_key
    return idempotency_key, trace_id


def _existing_response(row: UserPracticeResultCommand, command_json: str) -> tuple[dict, int] | None:
    if row.command_json != command_json:
        return {'error': 'idempotency key reused with different command'}, 409
    if row.status == 'applied':
        payload = load_result_json(row.result_json)
        payload['duplicate'] = True
        payload.setdefault('traceId', row.trace_id)
        payload.setdefault('idempotencyKey', row.idempotency_key)
        return payload, 200
    return {'error': f'idempotency command is {row.status}'}, 409


def apply_idempotent_practice_result(
    *,
    user_id: int,
    payload: dict | None,
    mode: str,
    dimension: str | None,
    word: str | None,
    apply_result: Callable[[], dict],
) -> tuple[dict, int]:
    idempotency_key, trace_id = resolve_attempt_metadata(payload)
    if not idempotency_key:
        return apply_result(), 200

    command_json = canonical_command_json(payload)
    row = UserPracticeResultCommand.query.filter_by(user_id=user_id, idempotency_key=idempotency_key).first()
    if row is not None:
        existing = _existing_response(row, command_json)
        if existing is not None:
            return existing

    row = UserPracticeResultCommand(
        user_id=user_id,
        trace_id=trace_id or '',
        idempotency_key=idempotency_key,
        mode=str(mode or 'practice')[:40],
        dimension=str(dimension or '')[:40],
        scope_key=scope_key_from_payload(payload),
        word=str(word or '')[:100],
        status='processing',
        command_json=command_json,
    )
    db.session.add(row)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        row = UserPracticeResultCommand.query.filter_by(user_id=user_id, idempotency_key=idempotency_key).first()
        if row is None:
            raise
        return _existing_response(row, command_json) or ({'error': 'idempotency command conflict'}, 409)

    try:
        result = apply_result()
    except Exception:
        row.status = 'failed'
        row.result_json = canonical_command_json({'error': 'practice result application failed'})
        db.session.commit()
        raise

    result['duplicate'] = False
    result.setdefault('traceId', trace_id)
    result.setdefault('idempotencyKey', idempotency_key)
    row.status = 'applied'
    row.result_json = canonical_command_json(result)
    db.session.commit()
    return result, 200
