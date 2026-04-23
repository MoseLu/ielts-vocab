from __future__ import annotations

import os
import time
from collections.abc import Callable, Sequence

from platform_sdk.service_worker_app_context import worker_app_context


BATCH_LIMIT_ENV = 'DOMAIN_EVENT_WORKER_BATCH_LIMIT'
IDLE_SLEEP_ENV = 'DOMAIN_EVENT_WORKER_IDLE_SECONDS'
ERROR_SLEEP_ENV = 'DOMAIN_EVENT_WORKER_ERROR_SECONDS'
StepCallable = Callable[[int], int]
StepSpec = tuple[str, StepCallable] | tuple[str, str, StepCallable]


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


def _normalize_step(step_spec: StepSpec) -> tuple[str, str | None, StepCallable]:
    if len(step_spec) == 2:
        step_name, step = step_spec
        return step_name, None, step
    step_name, service_name, step = step_spec
    return step_name, service_name, step


def _run_step_once(step: StepCallable, batch_limit: int, *, service_name: str | None = None) -> int:
    with worker_app_context(service_name=service_name):
        return step(batch_limit)


def _run_step_chain_once(
    *,
    worker_name: str,
    steps: Sequence[StepSpec],
    batch_limit: int,
) -> tuple[int, bool]:
    processed = 0
    had_error = False
    for step_name, service_name, step in map(_normalize_step, steps):
        try:
            processed += _run_step_once(step, batch_limit, service_name=service_name)
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            had_error = True
            print(f'[{worker_name}] step {step_name} failed: {exc}')
    return processed, had_error


def run_polling_worker(
    *,
    worker_name: str,
    step: StepCallable,
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
        processed = _run_step_once(step, batch_limit)
        print(f'[{worker_name}] processed {processed} item(s) in one-shot mode.')
        return processed

    print(f'[{worker_name}] starting with batch_limit={batch_limit}.')
    while True:
        try:
            processed = _run_step_once(step, batch_limit)
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


def run_multi_step_polling_worker(
    *,
    worker_name: str,
    steps: Sequence[StepSpec],
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
        processed, _ = _run_step_chain_once(
            worker_name=worker_name,
            steps=steps,
            batch_limit=batch_limit,
        )
        print(f'[{worker_name}] processed {processed} item(s) in one-shot mode.')
        return processed

    print(f'[{worker_name}] starting with batch_limit={batch_limit}.')
    while True:
        try:
            processed, had_error = _run_step_chain_once(
                worker_name=worker_name,
                steps=steps,
                batch_limit=batch_limit,
            )
        except KeyboardInterrupt:
            print(f'[{worker_name}] stopping on keyboard interrupt.')
            return 0

        if processed > 0:
            print(f'[{worker_name}] processed {processed} item(s).')
            continue
        if had_error:
            time.sleep(error_sleep_seconds)
            continue
        time.sleep(idle_sleep_seconds)
