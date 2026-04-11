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
    / 'wave4-storage-drill.sh'
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


def _write_file(path: Path, content: str, *, executable: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding='utf-8')
    if executable:
        path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _setup_fake_cloud_deploy_dir(tmp_path: Path) -> tuple[Path, Path, Path]:
    cloud_dir = tmp_path / 'cloud-deploy'
    app_home = tmp_path / 'app-home'
    current_release = app_home / 'releases' / '20260411-current'
    current_release.mkdir(parents=True)

    _write_file(app_home / 'backend.env', 'SECRET_KEY=test\n')
    _write_file(app_home / 'microservices.env', 'IDENTITY_SERVICE_DATABASE_URL=postgresql://demo\n')
    _write_file(
        app_home / 'fake-python.sh',
        """#!/usr/bin/env bash
set -euo pipefail
printf '[python] %s\\n' "$*"
""",
        executable=True,
    )

    _write_file(
        cloud_dir / 'release-common.sh',
        f"""#!/usr/bin/env bash
set -euo pipefail
APP_HOME="${{APP_HOME:-{app_home.as_posix()}}}"
CURRENT_LINK="${{CURRENT_LINK:-{current_release.as_posix()}}}"
BACKEND_ENV_FILE="${{BACKEND_ENV_FILE:-$APP_HOME/backend.env}}"
MICROSERVICES_ENV_FILE="${{MICROSERVICES_ENV_FILE:-$APP_HOME/microservices.env}}"
log() {{ printf '[%s] %s\\n' "2026-04-11T03:00:00Z" "$*"; }}
fail() {{ log "ERROR: $*"; exit 1; }}
require_command() {{ :; }}
require_file() {{ [[ -f "$1" ]] || fail "Missing required file: $1"; }}
current_target_path() {{ printf '%s\\n' "$CURRENT_LINK"; }}
""",
        executable=True,
    )

    for relative_path in (
        'scripts/validate_microservice_storage_parity.py',
        'scripts/repair_microservice_storage_parity.py',
        'scripts/validate_notes_export_oss_reference.py',
        'scripts/repair_notes_export_oss_reference.py',
        'scripts/validate_example_audio_oss_parity.py',
        'scripts/backfill_example_audio_to_oss.py',
        'scripts/validate_word_audio_oss_parity.py',
        'scripts/backfill_word_audio_to_oss.py',
    ):
        _write_file(current_release / relative_path, '# placeholder\n')

    drill_script = cloud_dir / 'wave4-storage-drill.sh'
    drill_script.write_text(SCRIPT_PATH.read_text(encoding='utf-8'), encoding='utf-8')
    return cloud_dir, app_home, current_release


def test_wave4_storage_drill_recording_writes_log_file(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home, current_release = _setup_fake_cloud_deploy_dir(tmp_path)
    record_path = app_home / 'records' / 'wave4-storage-drill.log'

    result = subprocess.run(
        [bash, str(cloud_dir / 'wave4-storage-drill.sh')],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': app_home.as_posix(),
            'PYTHON_BIN': (app_home / 'fake-python.sh').as_posix(),
            'DRILL_RUN_SMOKE': 'false',
            'DRILL_RECORD_PATH': record_path.as_posix(),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    record_text = record_path.read_text(encoding='utf-8')
    assert 'Recording Wave 4 storage drill output to' in record_text
    assert 'Wave 4 remote storage drill starting' in record_text
    assert f'Current release: {current_release.as_posix()}' in record_text
    assert 'Wave 4 remote storage drill completed' in record_text


def test_wave4_storage_drill_can_run_notes_export_repair(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home, _ = _setup_fake_cloud_deploy_dir(tmp_path)

    result = subprocess.run(
        [bash, str(cloud_dir / 'wave4-storage-drill.sh')],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': app_home.as_posix(),
            'PYTHON_BIN': (app_home / 'fake-python.sh').as_posix(),
            'DRILL_RUN_SMOKE': 'false',
            'DRILL_RUN_NOTES_EXPORT_REPAIR': 'true',
            'DRILL_NOTES_USER_ID': '7',
            'DRILL_NOTES_START_DATE': '2026-03-30',
            'DRILL_NOTES_END_DATE': '2026-03-30',
            'AXI_ALIYUN_OSS_ACCESS_KEY_ID': 'key',
            'AXI_ALIYUN_OSS_ACCESS_KEY_SECRET': 'secret',
            'AXI_ALIYUN_OSS_PRIVATE_BUCKET': 'bucket',
            'AXI_ALIYUN_OSS_REGION': 'oss-cn-shanghai',
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert 'repair_notes_export_oss_reference.py --user-id 7 --format md --type all --start-date 2026-03-30 --end-date 2026-03-30' in result.stdout
    assert 'validate_notes_export_oss_reference.py --user-id 7' not in result.stdout


def test_wave4_storage_drill_can_run_word_audio_repair(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home, _ = _setup_fake_cloud_deploy_dir(tmp_path)

    result = subprocess.run(
        [bash, str(cloud_dir / 'wave4-storage-drill.sh')],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': app_home.as_posix(),
            'PYTHON_BIN': (app_home / 'fake-python.sh').as_posix(),
            'DRILL_RUN_SMOKE': 'false',
            'DRILL_RUN_WORD_AUDIO_REPAIR': 'true',
            'DRILL_WORD_AUDIO_BOOK_ID': 'ielts_core',
            'DRILL_WORD_AUDIO_LIMIT': '5',
            'AXI_ALIYUN_OSS_ACCESS_KEY_ID': 'key',
            'AXI_ALIYUN_OSS_ACCESS_KEY_SECRET': 'secret',
            'AXI_ALIYUN_OSS_PRIVATE_BUCKET': 'bucket',
            'AXI_ALIYUN_OSS_REGION': 'oss-cn-shanghai',
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert 'backfill_word_audio_to_oss.py --repair-size-mismatch --repair-content-type-mismatch --book-id ielts_core --limit 5' in result.stdout
    assert 'validate_word_audio_oss_parity.py --book-id ielts_core --limit 5' in result.stdout


def test_wave4_storage_drill_can_run_example_audio_repair(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home, _ = _setup_fake_cloud_deploy_dir(tmp_path)

    result = subprocess.run(
        [bash, str(cloud_dir / 'wave4-storage-drill.sh')],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': app_home.as_posix(),
            'PYTHON_BIN': (app_home / 'fake-python.sh').as_posix(),
            'DRILL_RUN_SMOKE': 'false',
            'DRILL_RUN_EXAMPLE_AUDIO_REPAIR': 'true',
            'DRILL_EXAMPLE_AUDIO_BOOK_ID': 'ielts_reading_premium',
            'DRILL_EXAMPLE_AUDIO_LIMIT': '5',
            'AXI_ALIYUN_OSS_ACCESS_KEY_ID': 'key',
            'AXI_ALIYUN_OSS_ACCESS_KEY_SECRET': 'secret',
            'AXI_ALIYUN_OSS_PRIVATE_BUCKET': 'bucket',
            'AXI_ALIYUN_OSS_REGION': 'oss-cn-shanghai',
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert 'backfill_example_audio_to_oss.py --generate-missing --repair-size-mismatch --repair-content-type-mismatch --book-id ielts_reading_premium --limit 5' in result.stdout
    assert 'validate_example_audio_oss_parity.py --book-id ielts_reading_premium --limit 5' in result.stdout


def test_wave4_storage_drill_continues_into_repair_when_initial_parity_validation_fails(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home, _ = _setup_fake_cloud_deploy_dir(tmp_path)
    fake_python = app_home / 'fake-python.sh'
    fake_python.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '[python] %s\\n' "$*"
case "$1" in
  */validate_microservice_storage_parity.py)
    exit 1
    ;;
  *)
    exit 0
    ;;
esac
""",
        encoding='utf-8',
    )
    fake_python.chmod(fake_python.stat().st_mode | stat.S_IXUSR)

    result = subprocess.run(
        [bash, str(cloud_dir / 'wave4-storage-drill.sh')],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': app_home.as_posix(),
            'PYTHON_BIN': fake_python.as_posix(),
            'DRILL_RUN_SMOKE': 'false',
            'DRILL_RUN_REPAIR': 'true',
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert 'Initial storage parity validation reported drift; continuing into repair because DRILL_RUN_REPAIR=true' in result.stdout
    assert 'repair_microservice_storage_parity.py --scope owned --env-file' in result.stdout
