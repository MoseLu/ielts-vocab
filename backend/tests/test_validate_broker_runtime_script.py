from __future__ import annotations

import os
from pathlib import Path
import shutil
import stat
import subprocess

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'cloud-deploy'
    / 'validate-broker-runtime.sh'
)


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


def _setup_fake_cloud_dir(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    cloud_dir = tmp_path / 'cloud-deploy'
    app_home = tmp_path / 'app-home'
    current_link = tmp_path / 'current'
    validator_path = current_link / 'scripts' / 'validate_wave5_broker_runtime.py'
    fake_bin = tmp_path / 'fake-bin'

    _write_file(app_home / 'backend.env', 'SECRET_KEY=test\n')
    _write_file(
        app_home / 'microservices.env',
        'REDIS_HOST=127.0.0.1\nRABBITMQ_HOST=127.0.0.1\n',
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
log() {{ printf '%s\\n' "$*" >> "$APP_HOME/log.txt"; }}
fail() {{ log "FAIL:$*"; exit 1; }}
require_command() {{ command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"; }}
require_file() {{ [[ -f "$1" ]] || fail "Missing required file: $1"; }}
""",
        executable=True,
    )
    _write_file(
        cloud_dir / 'validate-broker-runtime.sh',
        SCRIPT_PATH.read_text(encoding='utf-8'),
        executable=True,
    )
    _write_file(validator_path, '# placeholder\n')
    _write_file(
        fake_bin / 'systemctl',
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$APP_HOME/systemctl.log"
""",
        executable=True,
    )
    _write_file(
        fake_bin / 'python',
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$APP_HOME/python.log"
""",
        executable=True,
    )
    return cloud_dir, app_home, current_link, validator_path


def test_validate_broker_runtime_script_checks_units_and_runs_validator(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home, current_link, validator_path = _setup_fake_cloud_dir(tmp_path)
    fake_bin = tmp_path / 'fake-bin'

    result = subprocess.run(
        [bash, str(cloud_dir / 'validate-broker-runtime.sh')],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': _as_msys_path(app_home),
            'CURRENT_LINK': _as_msys_path(current_link),
            'PYTHON_BIN': _as_msys_path(fake_bin / 'python'),
            'SYSTEMCTL_BIN': _as_msys_path(fake_bin / 'systemctl'),
            'VALIDATOR_PATH': _as_msys_path(validator_path),
            'PATH': f"{_as_msys_path(fake_bin)}{os.pathsep}{os.environ['PATH']}",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert (app_home / 'systemctl.log').read_text(encoding='utf-8').splitlines() == [
        'is-active --quiet redis',
        'is-active --quiet rabbitmq-server',
    ]
    python_calls = (app_home / 'python.log').read_text(encoding='utf-8').splitlines()
    assert python_calls == [
        f'{_as_msys_path(validator_path)} --env-file {_as_msys_path(app_home / "microservices.env")}',
    ]
    log_text = (app_home / 'log.txt').read_text(encoding='utf-8')
    assert 'Validating remote broker systemd baseline' in log_text
    assert 'Running Wave 5 broker runtime validation' in log_text
    assert 'Wave 5 broker runtime validation passed' in log_text
