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

from platform_sdk.runtime_env import load_split_service_env


load_split_service_env(service_name='ai-execution-service')

from platform_sdk.ai_runtime import create_ai_flask_app
from platform_sdk.ai_word_image_runtime import run_ai_word_image_generation_worker

ai_flask_app = create_ai_flask_app()


if __name__ == '__main__':
    with ai_flask_app.app_context():
        raise SystemExit(run_ai_word_image_generation_worker(sys.argv[1:]))
