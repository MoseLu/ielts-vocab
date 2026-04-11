from __future__ import annotations

from collections.abc import Sequence

from platform_sdk.admin_user_projection_application import drain_identity_user_registered_queue
from platform_sdk.domain_worker_runtime import run_polling_worker
from platform_sdk.rabbitmq_runtime import rabbitmq_is_configured


ADMIN_USER_PROJECTION_WORKER = 'admin-ops-service.user-projection-worker'


def drain_admin_user_projection_once(*, limit: int = 50) -> int:
    if not rabbitmq_is_configured(service_name='admin-ops-service'):
        return 0
    return drain_identity_user_registered_queue(limit=limit)


def run_admin_user_projection_worker(argv: Sequence[str] | None = None) -> int:
    return run_polling_worker(
        worker_name=ADMIN_USER_PROJECTION_WORKER,
        step=lambda batch_limit: drain_admin_user_projection_once(limit=batch_limit),
        argv=argv,
    )
