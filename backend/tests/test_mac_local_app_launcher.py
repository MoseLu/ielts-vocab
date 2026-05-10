import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_dev_and_preview_scripts_launch_mac_local_app_only():
    root_manifest = json.loads(_read('package.json'))
    frontend_manifest = json.loads(_read('frontend/package.json'))

    assert root_manifest['scripts']['dev'] == 'bash scripts/run-mac-local-app.sh dev'
    assert root_manifest['scripts']['preview'] == 'bash scripts/run-mac-local-app.sh preview'
    assert root_manifest['scripts']['build'] == 'pnpm --dir frontend build'

    assert frontend_manifest['scripts']['dev'] == 'bash ../scripts/run-mac-local-app.sh dev'
    assert frontend_manifest['scripts']['preview'] == 'bash ../scripts/run-mac-local-app.sh preview'
    assert frontend_manifest['scripts']['build'] == 'pnpm run verify:repo-guards && vite build'


def test_mac_local_app_launcher_keeps_vite_inside_generated_app_bundle():
    launcher = _read('scripts/run-mac-local-app.sh')

    assert 'MacOS' in launcher
    assert 'Info.plist' in launcher
    assert 'NSAppSleepDisabled' in launcher
    assert '雅思词汇${label}.app' in launcher
    assert 'open "${app_bundle}"' in launcher
    assert 'IELTS_DISABLE_MAC_APP' in launcher
    assert 'IELTS_MAC_LOCAL_APP_DRY_RUN' in launcher
    assert 'IELTS_LOCAL_APP_NODE' in launcher
    assert '[nodeCommand, viteBin, "preview"]' in launcher
    assert 'IELTS_LOCAL_APP_API_HEALTH_URL=http://127.0.0.1:8000/ready' in launcher
    assert 'logs/runtime/mac-app' in launcher
