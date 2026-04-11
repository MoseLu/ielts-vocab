from __future__ import annotations

import os
import time
from collections.abc import Callable, Sequence


BATCH_LIMIT_ENV = 'DOMAIN_EVENT_WORKER_BATCH_LIMIT'
IDLE_SLEEP_ENV = 'DOMAIN_EVENT_WORKER_IDLE_SECONDS'
ERROR_SLEEP_ENV = 'DOMAIN_EVENT_WORKER_ERROR_SECONDS'


def _read_int_env(name: str, default: int) -> int:
    raw_value = (os.environ.get(name) or '').strip()
    if not raw_value:
        return default
    try:
        return max(1, int(raw_value))
    except ValueError:
        return default


def _read_float_env(name: str, default: float) -> float:
    raw_value = (os.environ.get(name) or '').strip()
    if not raw_value:
        return default
    try:
        return max(0.1, float(raw_value))
    except ValueError:
        return default


def run_polling_worker(
    *,
    worker_name: str,
    step: Callable[[int], int],
    argv: Sequence[str] | None = None,
    default_limit: int = 50,
    default_idle_sleep_seconds: float = 1.0,
    default_error_sleep_seconds: float = 5.0,
) -> int:
    args = tuple(argv or ())
    run_once = '--once' in args
    batch_limit = _read_int_env(BATCH_LIMIT_ENV, default_limit)
    idle_sleep_seconds = _read_float_env(IDLE_SLEEP_ENV, default_idle_sleep_seconds)
    error_sleep_seconds = _read_float_env(ERROR_SLEEP_ENV, default_error_sleep_seconds)

    if run_once:
        processed = step(batch_limit)
        print(f'[{worker_name}] processed {processed} item(s) in one-shot mode.')
        return processed

    print(f'[{worker_name}] starting with batch_limit={batch_limit}.')
    while True:
        try:
            processed = step(batch_limit)
        except KeyboardInterrupt:
            print(f'[{worker_name}] stopping on keyboard interrupt.')
            return 0
        except Exception as exc:
            print(f'[{worker_name}] batch failed: {exc}')
            time.sleep(error_sleep_seconds)
            continue

        if processed > 0:
            print(f'[{worker_name}] processed {processed} item(s).')
            continue

        time.sleep(idle_sleep_seconds)
