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

from platform_sdk.admin_study_session_projection_runtime import run_admin_study_session_projection_worker
from platform_sdk.runtime_env import load_split_service_env


load_split_service_env(service_name='admin-ops-service')


if __name__ == '__main__':
    raise SystemExit(run_admin_study_session_projection_worker(sys.argv[1:]))
