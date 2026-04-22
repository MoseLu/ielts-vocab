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
    / 'release-closeout.sh'
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


def _setup_fake_closeout_dir(tmp_path: Path) -> tuple[Path, Path]:
    cloud_dir = tmp_path / 'cloud-deploy'
    app_home = tmp_path / 'app-home'
    current_release = app_home / 'releases' / '20260422-current'
    current_release.mkdir(parents=True)

    _write_file(app_home / 'backend.env', 'SECRET_KEY=test-secret\n')
    _write_file(app_home / 'microservices.env', 'IDENTITY_SERVICE_DATABASE_URL=postgresql://demo\n')
    _write_file(
        app_home / 'venv' / 'bin' / 'python',
        """#!/usr/bin/env bash
set -euo pipefail
if [[ \"$1\" == *\"run-wave5-projection-cutover.py\" ]]; then
  printf '[projection] secret=%s env=%s\\n' \"${SECRET_KEY:-}\" \"${MICROSERVICES_ENV_FILE:-}\"
  [[ -n \"${SECRET_KEY:-}\" ]] || exit 1
  exit 0
fi
printf '[python] %s\\n' \"$*\"
""",
        executable=True,
    )

    _write_file(
        cloud_dir / 'release-common.sh',
        f"""#!/usr/bin/env bash
set -euo pipefail
APP_HOME="${{APP_HOME:-{app_home.as_posix()}}}"
CURRENT_LINK="${{CURRENT_LINK:-{current_release.as_posix()}}}"
VENV_DIR="${{VENV_DIR:-$APP_HOME/venv}}"
BACKEND_ENV_FILE="${{BACKEND_ENV_FILE:-$APP_HOME/backend.env}}"
MICROSERVICES_ENV_FILE="${{MICROSERVICES_ENV_FILE:-$APP_HOME/microservices.env}}"
log() {{ printf '[%s] %s\\n' "2026-04-22T03:45:00Z" "$*"; }}
fail() {{ log "ERROR: $*"; exit 1; }}
require_command() {{ :; }}
require_file() {{ [[ -f "$1" ]] || fail "Missing required file: $1"; }}
current_target_path() {{ printf '%s\\n' "$CURRENT_LINK"; }}
""",
        executable=True,
    )

    _write_file(
        cloud_dir / 'smoke-check.sh',
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '[smoke] ok\\n'\n",
        executable=True,
    )
    _write_file(
        cloud_dir / 'wave4-storage-drill.sh',
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '[storage-drill] ok\\n'\n",
        executable=True,
    )
    _write_file(current_release / 'scripts' / 'run-wave5-projection-cutover.py', '# placeholder\n')

    script_copy = cloud_dir / 'release-closeout.sh'
    script_copy.write_text(SCRIPT_PATH.read_text(encoding='utf-8'), encoding='utf-8')
    script_copy.chmod(script_copy.stat().st_mode | stat.S_IXUSR)
    return cloud_dir, app_home


def test_release_closeout_sources_runtime_env_before_projection_verify(tmp_path):
    bash = _find_bash()
    if bash is None:
        pytest.skip('bash is not available')

    cloud_dir, app_home = _setup_fake_closeout_dir(tmp_path)

    result = subprocess.run(
        [bash, str(cloud_dir / 'release-closeout.sh')],
        cwd=tmp_path,
        env={
            **os.environ,
            'APP_HOME': app_home.as_posix(),
            'CLOSEOUT_LOG_DIR': (app_home / 'logs').as_posix(),
        },
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert '[projection] secret=test-secret' in result.stdout
