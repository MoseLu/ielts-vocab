from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timedelta
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import or_

from service_models.eventing_models import FrontendErrorLog, db


SENSITIVE_QUERY_KEYS = {
    'code',
    'email',
    'password',
    'secret',
    'token',
    'access_token',
    'refresh_token',
}
SENSITIVE_VALUE_KEYS = SENSITIVE_QUERY_KEYS | {
    'authorization',
    'cookie',
    'set-cookie',
    'jwt',
}
ALLOWED_SOURCES = {
    'http',
    'network',
    'window-error',
    'unhandledrejection',
    'react-error-boundary',
    'manual',
}
ALLOWED_SEVERITIES = {'info', 'warning', 'error'}
MAX_CONTEXT_KEYS = 24


def _truncate(value, max_length: int) -> str | None:
    if value is None:
        return None
    text = str(value)
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + '...'


def _clean_token(value, *, max_length: int = 64) -> str:
    text = str(value or '').strip()
    return re.sub(r'[^A-Za-z0-9_-]', '', text)[:max_length]


def _is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(sensitive_key in normalized for sensitive_key in SENSITIVE_VALUE_KEYS)


def _redact_text(value: str) -> str:
    return re.sub(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', '[redacted-email]', value, flags=re.IGNORECASE)


def _clean_source(value) -> str:
    source = str(value or '').strip().lower()
    return source if source in ALLOWED_SOURCES else 'http'


def _clean_severity(value, *, status_code: int | None) -> str:
    severity = str(value or '').strip().lower()
    if severity in ALLOWED_SEVERITIES:
        return severity
    if status_code is not None and status_code >= 500:
        return 'error'
    return 'warning'


def _clean_status(value) -> int | None:
    try:
        status = int(value)
    except (TypeError, ValueError):
        return None
    return status if 100 <= status <= 599 else None


def _sanitize_url(raw_url) -> str | None:
    text = str(raw_url or '').strip()
    if not text:
        return None
    try:
        parts = urlsplit(text)
    except ValueError:
        return _truncate(text, 2048)

    safe_pairs = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        replacement = '[redacted]' if _is_sensitive_key(key) else value
        safe_pairs.append((key, replacement))
    query = urlencode(safe_pairs, doseq=True)
    return _truncate(urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment)), 2048)


def _sanitize_value(key: str, value, *, depth: int = 0):
    if _is_sensitive_key(key):
        return '[redacted]'
    if depth > 2:
        return _truncate(value, 500)
    if isinstance(value, dict):
        return {
            str(child_key)[:80]: _sanitize_value(str(child_key), child_value, depth=depth + 1)
            for child_key, child_value in list(value.items())[:MAX_CONTEXT_KEYS]
        }
    if isinstance(value, list):
        return [
            _sanitize_value(key, item, depth=depth + 1)
            for item in value[:MAX_CONTEXT_KEYS]
        ]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return _truncate(_redact_text(value), 500) if isinstance(value, str) else value
    return _truncate(value, 500)


def _sanitize_context(value) -> dict:
    if not isinstance(value, dict):
        return {}
    return {
        str(key)[:80]: _sanitize_value(str(key), item)
        for key, item in list(value.items())[:MAX_CONTEXT_KEYS]
    }


def _json_dumps(value: dict) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(',', ':'))


def _serialize_log(row: FrontendErrorLog) -> dict:
    return row.to_dict()


def create_frontend_error_log_response(current_user, body: dict | None, *, user_agent: str = '') -> tuple[dict, int]:
    payload = body if isinstance(body, dict) else {}
    status_code = _clean_status(payload.get('status_code'))
    source = _clean_source(payload.get('source'))
    severity = _clean_severity(payload.get('severity'), status_code=status_code)
    event_id = _clean_token(payload.get('event_id')) or uuid.uuid4().hex
    existing = FrontendErrorLog.query.filter_by(event_id=event_id).first()
    if existing:
        return {'ok': True, 'event_id': existing.event_id}, 200

    user_id = int(current_user.id) if current_user is not None else None
    username = str(getattr(current_user, 'username', '') or '') if current_user is not None else None
    row = FrontendErrorLog(
        event_id=event_id,
        source=source,
        severity=severity,
        status_code=status_code,
        method=_truncate(str(payload.get('method') or '').upper() or None, 12),
        request_url=_sanitize_url(payload.get('request_url')),
        route_path=_truncate(payload.get('route_path'), 255),
        message=_truncate(_redact_text(str(payload.get('message') or 'Frontend error')), 2000) or 'Frontend error',
        error_name=_truncate(payload.get('error_name'), 120),
        stack=_truncate(_redact_text(str(payload.get('stack') or '')), 8000),
        component_stack=_truncate(_redact_text(str(payload.get('component_stack') or '')), 8000),
        response_excerpt=_truncate(_redact_text(str(payload.get('response_excerpt') or '')), 2000),
        fingerprint=_clean_token(payload.get('fingerprint'), max_length=128) or event_id,
        browser_session_id=_clean_token(payload.get('browser_session_id'), max_length=80) or None,
        app_version=_truncate(payload.get('app_version'), 80),
        user_agent=_truncate(user_agent or payload.get('user_agent'), 500),
        user_id=user_id,
        username=_truncate(username, 100),
        context_json=_json_dumps(_sanitize_context(payload.get('context'))),
    )
    db.session.add(row)
    db.session.commit()
    return {'ok': True, 'event_id': row.event_id}, 201


def list_frontend_error_logs_response(args) -> tuple[dict, int]:
    page = max(1, int(args.get('page', 1) or 1))
    per_page = min(max(1, int(args.get('per_page', 20) or 20)), 100)
    query = FrontendErrorLog.query

    source = str(args.get('source') or '').strip().lower()
    if source:
        query = query.filter(FrontendErrorLog.source == source)
    severity = str(args.get('severity') or '').strip().lower()
    if severity:
        query = query.filter(FrontendErrorLog.severity == severity)
    status_code = _clean_status(args.get('status_code'))
    if status_code is not None:
        query = query.filter(FrontendErrorLog.status_code == status_code)
    try:
        since_hours = float(args.get('since_hours') or 0)
    except (TypeError, ValueError):
        since_hours = 0
    if since_hours > 0:
        query = query.filter(FrontendErrorLog.created_at >= datetime.utcnow() - timedelta(hours=since_hours))

    search = str(args.get('q') or '').strip()
    if search:
        pattern = f'%{search}%'
        query = query.filter(or_(
            FrontendErrorLog.message.ilike(pattern),
            FrontendErrorLog.request_url.ilike(pattern),
            FrontendErrorLog.route_path.ilike(pattern),
            FrontendErrorLog.fingerprint.ilike(pattern),
        ))

    total = query.count()
    rows = (
        query
        .order_by(FrontendErrorLog.created_at.desc(), FrontendErrorLog.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
        .all()
    )
    return {
        'items': [_serialize_log(row) for row in rows],
        'total': total,
        'page': page,
        'per_page': per_page,
    }, 200
