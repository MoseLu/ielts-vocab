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
    / 'provision-broker-runtime.sh'
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


def _setup_fake_bin(tmp_path: Path) -> Path:
    fake_bin = tmp_path / 'fake-bin'
    _write_file(
        fake_bin / 'dnf',
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$APP_HOME/dnf.log"
""",
        executable=True,
    )
    _write_file(
        fake_bin / 'systemctl',
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$APP_HOME/systemctl.log"
""",
        executable=True,
    )
    _write_file(
        fake_bin / 'redis-cli',
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$APP_HOME/redis-cli.log"
printf 'PONG\n'
""",
        executable=True,
    )
    _write_file(
        fake_bin / 'rabbitmq-diagnostics',
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$APP_HOME/rabbitmq-diagnostics.log"
""",
        executable=True,
    )
    _write_file(
        fake_bin / 'rabbitmqctl',
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "$*" >> "$APP_HOME/rabbitmqctl.log"
case "${1:-}" in
  list_vhosts)
    printf 'Listing vhosts ...\n/\n'
    ;;
  list_users)
    printf 'Listing users ...\nguest [administrator]\n'
    ;;
esac
""",
        executable=True,
    )
    return fake_bin


def test_provision_broker_runtime_script_provisions_local_baseline(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    app_home = tmp_path / 'app-home'
    env_file = app_home / 'microservices.env'
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(
        '\n'.join([
            'REDIS_HOST=127.0.0.1',
            'REDIS_PORT=6379',
            'RABBITMQ_HOST=127.0.0.1',
            'RABBITMQ_PORT=5672',
            'RABBITMQ_USER=ielts_vocab',
            'RABBITMQ_PASSWORD=secret',
            'RABBITMQ_VHOST=/ielts-vocab',
        ]),
        encoding='utf-8',
    )
    fake_bin = _setup_fake_bin(tmp_path)

    result = subprocess.run(
        [bash, str(SCRIPT_PATH), _as_msys_path(env_file)],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': _as_msys_path(app_home),
            'PYTHON_BIN': _as_msys_path(Path(sys.executable)),
            'DNF_BIN': _as_msys_path(fake_bin / 'dnf'),
            'SYSTEMCTL_BIN': _as_msys_path(fake_bin / 'systemctl'),
            'REDIS_CLI_BIN': _as_msys_path(fake_bin / 'redis-cli'),
            'RABBITMQCTL_BIN': _as_msys_path(fake_bin / 'rabbitmqctl'),
            'RABBITMQ_DIAGNOSTICS_BIN': _as_msys_path(fake_bin / 'rabbitmq-diagnostics'),
            'PATH': f"{_as_msys_path(fake_bin)}{os.pathsep}{os.environ['PATH']}",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert (app_home / 'dnf.log').read_text(encoding='utf-8').splitlines() == [
        'install -y redis rabbitmq-server',
    ]
    assert (app_home / 'systemctl.log').read_text(encoding='utf-8').splitlines() == [
        'enable --now redis rabbitmq-server',
    ]
    rabbitmqctl_calls = (app_home / 'rabbitmqctl.log').read_text(encoding='utf-8').splitlines()
    assert rabbitmqctl_calls == [
        'list_vhosts',
        'add_vhost /ielts-vocab',
        'list_users',
        'add_user ielts_vocab secret',
        'set_permissions -p /ielts-vocab ielts_vocab .* .* .*',
    ]
    assert (app_home / 'redis-cli.log').read_text(encoding='utf-8').splitlines() == [
        '-h 127.0.0.1 -p 6379 PING',
    ]
    assert (app_home / 'rabbitmq-diagnostics.log').read_text(encoding='utf-8').splitlines() == [
        '-q ping',
    ]


def test_provision_broker_runtime_script_rejects_nonlocal_hosts(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    app_home = tmp_path / 'app-home'
    env_file = app_home / 'microservices.env'
    env_file.parent.mkdir(parents=True, exist_ok=True)
    env_file.write_text(
        '\n'.join([
            'REDIS_HOST=10.0.0.5',
            'RABBITMQ_HOST=127.0.0.1',
        ]),
        encoding='utf-8',
    )
    fake_bin = _setup_fake_bin(tmp_path)

    result = subprocess.run(
        [bash, str(SCRIPT_PATH), _as_msys_path(env_file)],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': _as_msys_path(app_home),
            'PYTHON_BIN': _as_msys_path(Path(sys.executable)),
            'DNF_BIN': _as_msys_path(fake_bin / 'dnf'),
            'SYSTEMCTL_BIN': _as_msys_path(fake_bin / 'systemctl'),
            'REDIS_CLI_BIN': _as_msys_path(fake_bin / 'redis-cli'),
            'RABBITMQCTL_BIN': _as_msys_path(fake_bin / 'rabbitmqctl'),
            'RABBITMQ_DIAGNOSTICS_BIN': _as_msys_path(fake_bin / 'rabbitmq-diagnostics'),
            'PATH': f"{_as_msys_path(fake_bin)}{os.pathsep}{os.environ['PATH']}",
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode != 0
    assert 'This script only provisions a local Redis baseline' in result.stderr
    assert not (app_home / 'dnf.log').exists()
