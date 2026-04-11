from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
BACKEND_PATH = REPO_ROOT / 'backend'
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))

from platform_sdk.learning_core_outbox_publisher_runtime import run_learning_core_outbox_publisher
from platform_sdk.runtime_env import load_split_service_env


load_split_service_env(service_name='learning-core-service')


if __name__ == '__main__':
    raise SystemExit(run_learning_core_outbox_publisher(sys.argv[1:]))
