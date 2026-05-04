from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TypeVar

from service_models.learning_core_models import db


T = TypeVar('T')
DEADLOCK_SQLSTATE = '40P01'
DEFAULT_DEADLOCK_ATTEMPTS = 3


def _is_deadlock_error(exc: BaseException) -> bool:
    checked: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in checked:
        checked.add(id(current))
        original = getattr(current, 'orig', None)
        if getattr(original, 'pgcode', None) == DEADLOCK_SQLSTATE:
            return True
        original_text = str(original).lower()
        current_text = str(current).lower()
        if 'deadlock detected' in original_text or 'deadlock detected' in current_text:
            return True
        current = current.__cause__
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
            if not _is_deadlock_error(exc) or is_last_attempt:
                raise
            db.session.rollback()
            logging.warning(
                '[LEARNING_CORE] deadlock during %s; retrying attempt %s/%s',
                operation,
                attempt_index + 2,
                attempts,
            )
            time.sleep(0.05 * (2 ** attempt_index))
    return action()


__all__ = ['run_learning_core_deadlock_retry']
