from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from service_models.learning_core_models import db


T = TypeVar('T')
DEADLOCK_SQLSTATE = '40P01'
UNIQUE_VIOLATION_SQLSTATE = '23505'
RETRYABLE_UNIQUE_CONSTRAINTS = {'unique_user_scope_word_mastery_state'}
DEFAULT_DEADLOCK_ATTEMPTS = 3


def _iter_exception_chain(exc: BaseException):
    checked: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in checked:
        checked.add(id(current))
        yield current
        current = current.__cause__ or current.__context__


def _is_retryable_write_conflict(exc: BaseException) -> bool:
    for current in _iter_exception_chain(exc):
        original = getattr(current, 'orig', None)
        if getattr(original, 'pgcode', None) == DEADLOCK_SQLSTATE:
            return True
        if getattr(original, 'pgcode', None) == UNIQUE_VIOLATION_SQLSTATE:
            constraint = getattr(getattr(original, 'diag', None), 'constraint_name', '')
            if constraint in RETRYABLE_UNIQUE_CONSTRAINTS:
                return True
        original_text = str(original).lower()
        current_text = str(current).lower()
        if 'deadlock detected' in original_text or 'deadlock detected' in current_text:
            return True
        if (
            'unique_user_scope_word_mastery_state' in original_text
            or 'unique_user_scope_word_mastery_state' in current_text
        ):
            return True
    return False


def run_learning_core_deadlock_retry(
    action: Callable[[], T],
    *,
    operation: str,
    attempts: int = DEFAULT_DEADLOCK_ATTEMPTS,
) -> T:
    for attempt_index in range(max(1, attempts)):
        try:
            return action()
        except Exception as exc:
            is_last_attempt = attempt_index >= attempts - 1
            if not _is_retryable_write_conflict(exc) or is_last_attempt:
                raise
            db.session.rollback()
            logging.warning(
                '[LEARNING_CORE] retryable write conflict during %s; retrying attempt %s/%s',
                operation,
                attempt_index + 2,
                attempts,
            )
            time.sleep(0.05 * (2 ** attempt_index))
    return action()


__all__ = ['run_learning_core_deadlock_retry']
