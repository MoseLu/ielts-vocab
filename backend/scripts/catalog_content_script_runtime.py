from __future__ import annotations

import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_ROOT.parent
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'

for candidate in (BACKEND_ROOT, SDK_PATH):
    candidate_text = str(candidate)
    if candidate_text not in sys.path:
        sys.path.insert(0, candidate_text)

from platform_sdk.runtime_env import load_split_service_env


def create_catalog_content_script_app():
    load_split_service_env(service_name='catalog-content-service')

    from platform_sdk.catalog_content_runtime import create_catalog_content_flask_app

    return create_catalog_content_flask_app()
