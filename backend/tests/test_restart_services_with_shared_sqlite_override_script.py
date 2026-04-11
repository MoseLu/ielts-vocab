from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'cloud-deploy'
    / 'restart-services-with-shared-sqlite-override.sh'
)
REPO_ROOT = Path(__file__).resolve().parents[2]


def _find_bash() -> str | None:
    candidates = [
        r'C:\Program Files\Git\bin\bash.exe',
        r'C:\Program Files\Git\usr\bin\bash.exe',
        shutil.which('bash'),
    ]
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            normalized = str(candidate).replace('/', '\\').lower()
            if normalized.endswith(r'windows\system32\bash.exe'):
                continue
            return candidate
    return None


def _as_msys_path(path: Path) -> str:
    value = path.resolve().as_posix()
    if len(value) >= 3 and value[1:3] == ':/':
        return f'/{value[0].lower()}/{value[3:]}'
    return value


def _write_file(path: Path, content: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _setup_fake_cloud_dir(tmp_path: Path) -> tuple[Path, Path, Path]:
    cloud_dir = tmp_path / 'cloud-deploy'
    app_home = tmp_path / 'app-home'
    current_link = REPO_ROOT
    python_wrapper = tmp_path / 'bin' / 'python-wrapper.sh'

    _write_file(app_home / 'backend.env', 'SECRET_KEY=test\n')
    _write_file(app_home / 'microservices.env', 'IDENTITY_SERVICE_DATABASE_URL=postgresql://demo\n')
    _write_file(
        python_wrapper,
        """#!/usr/bin/env bash
set -euo pipefail
service_name="${@: -1}"
case "${service_name}" in
  identity-service|learning-core-service|catalog-content-service|ai-execution-service|notes-service|tts-media-service|asr-service|admin-ops-service)
    exit 0
    ;;
  *)
    echo "Unknown service storage boundary plan: ${service_name}" >&2
    exit 1
    ;;
esac
""",
        executable=True,
    )

    _write_file(
        cloud_dir / 'release-common.sh',
        f"""#!/usr/bin/env bash
set -euo pipefail
APP_HOME="${{APP_HOME:-{app_home.as_posix()}}}"
CURRENT_LINK="${{CURRENT_LINK:-{current_link.as_posix()}}}"
VENV_DIR="${{VENV_DIR:-{(tmp_path / 'venv').as_posix()}}}"
BACKEND_ENV_FILE="${{BACKEND_ENV_FILE:-$APP_HOME/backend.env}}"
MICROSERVICES_ENV_FILE="${{MICROSERVICES_ENV_FILE:-$APP_HOME/microservices.env}}"
log() {{
  local line=""
  line="$(printf '[%s] %s' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*")"
  printf '%s\\n' "$line" | tee -a "$APP_HOME/log.txt"
}}
fail() {{ log "FAIL:$*"; exit 1; }}
require_command() {{ command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"; }}
require_file() {{ [[ -f "$1" ]] || fail "Missing required file: $1"; }}
current_target_path() {{ printf '%s\\n' '{REPO_ROOT.as_posix()}'; }}
""",
        executable=True,
    )

    _write_file(
        cloud_dir / 'restart-services-with-shared-sqlite-override.sh',
        SCRIPT_PATH.read_text(encoding='utf-8'),
        executable=True,
    )

    fake_bin = tmp_path / 'fake-bin'
    _write_file(
        fake_bin / 'systemctl',
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$APP_HOME/systemctl.log"
""",
        executable=True,
    )
    _write_file(
        fake_bin / 'curl',
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$APP_HOME/curl.log"
exit 0
""",
        executable=True,
    )

    return cloud_dir, app_home, python_wrapper


def test_restart_services_with_shared_sqlite_override_sets_manager_env_and_cleans_up(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home, python_wrapper = _setup_fake_cloud_dir(tmp_path)
    fake_bin = tmp_path / 'fake-bin'
    record_path = app_home / 'shared-override.log'

    result = subprocess.run(
        [
            bash,
            str(cloud_dir / 'restart-services-with-shared-sqlite-override.sh'),
            'notes-service',
            'asr-service',
            'notes-service',
        ],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': _as_msys_path(app_home),
            'CURRENT_LINK': _as_msys_path(REPO_ROOT),
            'PYTHON_BIN': _as_msys_path(python_wrapper),
            'SYSTEMCTL_BIN': _as_msys_path(fake_bin / 'systemctl'),
            'CURL_BIN': _as_msys_path(fake_bin / 'curl'),
            'SHARED_SQLITE_OVERRIDE_RECORD_PATH': _as_msys_path(record_path),
            'PATH': f"{_as_msys_path(fake_bin)}{os.pathsep}{os.environ['PATH']}",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    systemctl_calls = (app_home / 'systemctl.log').read_text(encoding='utf-8').splitlines()
    assert systemctl_calls == [
        'set-environment ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES=notes-service,asr-service',
        'restart ielts-service@notes-service',
        'restart ielts-service@asr-service',
        'unset-environment ALLOW_SHARED_SPLIT_SERVICE_SQLITE_SERVICES',
    ]
    curl_calls = (app_home / 'curl.log').read_text(encoding='utf-8').splitlines()
    assert curl_calls == [
        '-fsS http://127.0.0.1:8107/ready',
        '-fsS http://127.0.0.1:8106/ready',
    ]
    log_text = (app_home / 'log.txt').read_text(encoding='utf-8')
    record_text = record_path.read_text(encoding='utf-8')
    assert 'Wave 4 shared SQLite override restart' in log_text
    assert f'Current release: {REPO_ROOT.as_posix()}' in log_text
    assert 'Target services: notes-service,asr-service' in log_text
    assert 'Ready timeout seconds: 45' in log_text
    assert 'Applying scoped shared SQLite override for: notes-service,asr-service' in log_text
    assert 'Wave 4 shared SQLite override restart completed for: notes-service,asr-service' in log_text
    assert 'Recording Wave 4 shared SQLite override restart output to' in record_text
    assert 'Waiting for ready URL: http://127.0.0.1:8107/ready' in record_text
    assert 'Ready URL responded: http://127.0.0.1:8106/ready' in record_text


def test_restart_services_with_shared_sqlite_override_rejects_unknown_service(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home, python_wrapper = _setup_fake_cloud_dir(tmp_path)
    fake_bin = tmp_path / 'fake-bin'

    result = subprocess.run(
        [
            bash,
            str(cloud_dir / 'restart-services-with-shared-sqlite-override.sh'),
            'gateway-bff',
        ],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': _as_msys_path(app_home),
            'CURRENT_LINK': _as_msys_path(REPO_ROOT),
            'PYTHON_BIN': _as_msys_path(python_wrapper),
            'SYSTEMCTL_BIN': _as_msys_path(fake_bin / 'systemctl'),
            'CURL_BIN': _as_msys_path(fake_bin / 'curl'),
            'PATH': f"{_as_msys_path(fake_bin)}{os.pathsep}{os.environ['PATH']}",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    log_text = (app_home / 'log.txt').read_text(encoding='utf-8')
    assert 'Unknown guarded split service: gateway-bff' in log_text
    assert not (app_home / 'systemctl.log').exists()
