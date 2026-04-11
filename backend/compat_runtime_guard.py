from __future__ import annotations

import os


MONOLITH_COMPAT_RUNTIME_ENV = 'ALLOW_MONOLITH_COMPAT_RUNTIME'
MONOLITH_COMPAT_RUNTIME_VALUE = '1'


def require_explicit_monolith_compat_runtime(*, runtime_label: str, startup_hint: str) -> None:
    if os.environ.get(MONOLITH_COMPAT_RUNTIME_ENV) == MONOLITH_COMPAT_RUNTIME_VALUE:
        return

    raise SystemExit(
        f'{runtime_label} is compatibility-only and no longer starts by default. '
        f'Use {startup_hint} or set {MONOLITH_COMPAT_RUNTIME_ENV}=1 for a controlled rollback drill.'
    )
