from __future__ import annotations

import logging
import os
from collections.abc import Callable


_TRUE_VALUES = frozenset({'1', 'true', 'yes', 'on'})
_FALSE_VALUES = frozenset({'0', 'false', 'no', 'off'})
_LEGACY_FALLBACK_SERVICE_NAMES = frozenset({'', 'backend-monolith'})


def current_service_name() -> str:
    return (os.environ.get('CURRENT_SERVICE_NAME') or '').strip()


def legacy_cross_service_fallback_enabled() -> bool:
    raw_value = (os.environ.get('ALLOW_LEGACY_CROSS_SERVICE_FALLBACK') or '').strip().lower()
    if raw_value in _TRUE_VALUES:
        return True
    if raw_value in _FALSE_VALUES:
        return False
    return current_service_name() in _LEGACY_FALLBACK_SERVICE_NAMES


def build_strict_internal_contract_error(
    *,
    upstream_name: str,
    action: str,
) -> tuple[dict, int]:
    return {
        'error': f'{upstream_name} unavailable',
        'boundary': 'strict-internal-contract',
        'action': action,
        'upstream': upstream_name,
    }, 503


def run_with_legacy_cross_service_fallback(
    *,
    upstream_name: str,
    action: str,
    primary: Callable[[], tuple[dict, int]],
    fallback: Callable[[], tuple[dict, int]],
) -> tuple[dict, int]:
    try:
        return primary()
    except Exception as exc:
        if legacy_cross_service_fallback_enabled():
            logging.warning(
                '[Boundary] using legacy local fallback: current_service=%s upstream=%s action=%s error=%s',
                current_service_name() or '<unset>',
                upstream_name,
                action,
                exc,
            )
            return fallback()
        logging.warning(
            '[Boundary] strict internal contract blocked local fallback: current_service=%s upstream=%s action=%s error=%s',
            current_service_name() or '<unset>',
            upstream_name,
            action,
            exc,
        )
        return build_strict_internal_contract_error(
            upstream_name=upstream_name,
            action=action,
        )
