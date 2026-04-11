from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess

import pytest


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'cloud-deploy'
    / 'wave4-rollback-rehearsal.sh'
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


def _write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')


def _setup_fake_cloud_deploy_dir(tmp_path: Path) -> tuple[Path, Path]:
    cloud_dir = tmp_path / 'cloud-deploy'
    app_home = tmp_path / 'app-home'
    current_release = app_home / 'releases' / '20260411-current'
    target_release = app_home / 'releases' / '20260410-target'
    invalid_release = app_home / 'releases' / '20260409-invalid'
    current_release.mkdir(parents=True)
    target_release.mkdir(parents=True)
    invalid_release.mkdir(parents=True)
    (current_release / 'dist').mkdir()
    (target_release / 'dist').mkdir()

    _write_file(app_home / 'backend.env', 'SECRET_KEY=test\n')
    _write_file(app_home / 'microservices.env', 'IDENTITY_SERVICE_DATABASE_URL=postgresql://demo\n')
    _write_file(app_home / 'current-release.txt', str(current_release))

    _write_file(
        cloud_dir / 'release-common.sh',
        f"""#!/usr/bin/env bash
set -euo pipefail
APP_HOME="${{APP_HOME:-{app_home.as_posix()}}}"
BACKEND_ENV_FILE="${{BACKEND_ENV_FILE:-$APP_HOME/backend.env}}"
MICROSERVICES_ENV_FILE="${{MICROSERVICES_ENV_FILE:-$APP_HOME/microservices.env}}"
log() {{ printf '%s\\n' "$*" | tee -a "$APP_HOME/log.txt"; }}
fail() {{ log "FAIL:$*"; exit 1; }}
require_command() {{ :; }}
require_file() {{ [[ -f "$1" ]] || fail "Missing required file: $1"; }}
current_target_path() {{ cat "$APP_HOME/current-release.txt"; }}
list_release_dirs() {{
  printf '%s\\n' "{invalid_release.as_posix()}" "{target_release.as_posix()}" "{current_release.as_posix()}"
}}
""",
    )
    _write_file(
        cloud_dir / 'rollback-release.sh',
        """#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "${script_dir}/release-common.sh"
printf '%s\n' "$1" >> "$APP_HOME/rollback-calls.txt"
printf '%s' "$1" > "$APP_HOME/current-release.txt"
""",
    )
    _write_file(
        cloud_dir / 'wave4-storage-drill.sh',
        """#!/usr/bin/env bash
set -euo pipefail
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
source "${script_dir}/release-common.sh"
log "storage-drill"
""",
    )
    rehearsal_script = cloud_dir / 'wave4-rollback-rehearsal.sh'
    rehearsal_script.write_text(SCRIPT_PATH.read_text(encoding='utf-8'), encoding='utf-8')
    return cloud_dir, app_home


def test_wave4_rollback_rehearsal_dry_run_reports_plan(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home = _setup_fake_cloud_deploy_dir(tmp_path)

    result = subprocess.run(
        [bash, str(cloud_dir / 'wave4-rollback-rehearsal.sh')],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': str(app_home),
            'REHEARSAL_RUN_STORAGE_DRILL': 'false',
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    log_text = (app_home / 'log.txt').read_text(encoding='utf-8')
    assert 'Wave 4 rollback rehearsal' in log_text
    assert 'Dry-run only; set REHEARSAL_EXECUTE=true to run the real rollback rehearsal' in log_text
    assert not (app_home / 'rollback-calls.txt').exists()


def test_wave4_rollback_rehearsal_execute_rolls_to_target_and_restores(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home = _setup_fake_cloud_deploy_dir(tmp_path)

    result = subprocess.run(
        [bash, str(cloud_dir / 'wave4-rollback-rehearsal.sh')],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': str(app_home),
            'REHEARSAL_EXECUTE': 'true',
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    rollback_calls = (app_home / 'rollback-calls.txt').read_text(encoding='utf-8').splitlines()
    current_release = app_home / 'releases' / '20260411-current'
    target_release = app_home / 'releases' / '20260410-target'
    assert [Path(item) for item in rollback_calls] == [target_release, current_release]
    assert Path((app_home / 'current-release.txt').read_text(encoding='utf-8')) == current_release
    log_text = (app_home / 'log.txt').read_text(encoding='utf-8')
    assert 'storage-drill' in log_text
    assert 'Wave 4 rollback rehearsal completed successfully' in log_text


def test_wave4_rollback_rehearsal_recording_writes_log_file(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home = _setup_fake_cloud_deploy_dir(tmp_path)
    record_path = app_home / 'records' / 'wave4-rollback-rehearsal.log'

    result = subprocess.run(
        [bash, str(cloud_dir / 'wave4-rollback-rehearsal.sh')],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': str(app_home),
            'REHEARSAL_RUN_STORAGE_DRILL': 'false',
            'REHEARSAL_RECORD_PATH': str(record_path),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    record_text = record_path.read_text(encoding='utf-8')
    assert 'Recording Wave 4 rollback rehearsal output to' in record_text
    assert 'Wave 4 rollback rehearsal' in record_text
    assert 'Dry-run only; set REHEARSAL_EXECUTE=true to run the real rollback rehearsal' in record_text


def test_wave4_rollback_rehearsal_skips_non_release_directories_without_dist(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home = _setup_fake_cloud_deploy_dir(tmp_path)

    result = subprocess.run(
        [bash, str(cloud_dir / 'wave4-rollback-rehearsal.sh')],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': str(app_home),
            'REHEARSAL_RUN_STORAGE_DRILL': 'false',
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    log_text = (app_home / 'log.txt').read_text(encoding='utf-8')
    assert (app_home / 'releases' / '20260410-target').as_posix() in log_text
    assert (app_home / 'releases' / '20260409-invalid').as_posix() not in log_text
