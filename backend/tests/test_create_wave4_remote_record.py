from __future__ import annotations

from pathlib import Path
import subprocess
import sys


SCRIPT_PATH = (
    Path(__file__).resolve().parents[2]
    / 'scripts'
    / 'create-wave4-remote-record.py'
)


def _run_script(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_create_wave4_remote_record_writes_storage_drill_summary(tmp_path):
    log_path = tmp_path / 'wave4-storage-drill.log'
    log_path.write_text(
        '\n'.join(
            (
                '[2026-04-11T02:00:00Z] Wave 4 remote storage drill starting',
                '[2026-04-11T02:00:01Z] Current release: /opt/ielts-vocab/releases/20260411-current',
                '[2026-04-11T02:00:02Z] Running scripts/validate_microservice_storage_parity.py --scope owned --env-file /etc/ielts-vocab/microservices.env',
                '[2026-04-11T02:00:03Z] Wave 4 remote storage drill completed',
            )
        )
        + '\n',
        encoding='utf-8',
    )
    output_path = tmp_path / 'record.md'

    result = _run_script(
        '--log-path',
        str(log_path),
        '--output',
        str(output_path),
        '--host',
        '119.29.182.134',
        '--command',
        'sudo APP_HOME=/opt/ielts-vocab bash /opt/ielts-vocab/current/scripts/cloud-deploy/wave4-storage-drill.sh',
        '--note',
        'Captured after remote parity rehearsal.',
    )

    assert result.returncode == 0
    record_text = output_path.read_text(encoding='utf-8')
    assert '- Kind: storage-drill' in record_text
    assert '- Status: success' in record_text
    assert '- Host: 119.29.182.134' in record_text
    assert '- Current release: /opt/ielts-vocab/releases/20260411-current' in record_text
    assert 'Captured after remote parity rehearsal.' in record_text
    assert 'Wave 4 remote storage drill completed' in record_text


def test_create_wave4_remote_record_defaults_rollback_dry_run_output_path(tmp_path):
    log_path = tmp_path / 'wave4-rollback-rehearsal.log'
    log_path.write_text(
        '\n'.join(
            (
                '[2026-04-11T03:00:00Z] Wave 4 rollback rehearsal',
                '[2026-04-11T03:00:01Z] Current release: /opt/ielts-vocab/releases/20260411-current',
                '[2026-04-11T03:00:02Z] Target release: /opt/ielts-vocab/releases/20260410-target',
                '[2026-04-11T03:00:03Z] Restore release: /opt/ielts-vocab/releases/20260411-current',
                '[2026-04-11T03:00:04Z] Execute mode: false',
                '[2026-04-11T03:00:05Z] Storage drill after restore: false',
                '[2026-04-11T03:00:06Z] Dry-run only; set REHEARSAL_EXECUTE=true to run the real rollback rehearsal',
            )
        )
        + '\n',
        encoding='utf-8',
    )
    output_path = tmp_path / '20260411-030000-wave4-rollback-rehearsal.md'

    result = _run_script('--log-path', str(log_path))

    assert result.returncode == 0
    assert output_path.exists()
    record_text = output_path.read_text(encoding='utf-8')
    assert '- Kind: rollback-rehearsal' in record_text
    assert '- Status: dry-run' in record_text
    assert '- Target release: /opt/ielts-vocab/releases/20260410-target' in record_text
    assert '- Execute mode: false' in record_text


def test_create_wave4_remote_record_writes_shared_sqlite_override_restart_summary(tmp_path):
    log_path = tmp_path / 'shared-sqlite-override.log'
    log_path.write_text(
        '\n'.join(
            (
                '[2026-04-11T04:00:00Z] Recording Wave 4 shared SQLite override restart output to /var/log/ielts-vocab/wave4/shared-sqlite-override-20260411T040000Z.log',
                '[2026-04-11T04:00:01Z] Wave 4 shared SQLite override restart',
                '[2026-04-11T04:00:02Z] Current release: /opt/ielts-vocab/releases/20260411-current',
                '[2026-04-11T04:00:03Z] Target services: notes-service,asr-service',
                '[2026-04-11T04:00:04Z] Ready timeout seconds: 45',
                '[2026-04-11T04:00:05Z] Applying scoped shared SQLite override for: notes-service,asr-service',
                '[2026-04-11T04:00:06Z] Restarting ielts-service@notes-service',
                '[2026-04-11T04:00:07Z] Waiting for ready URL: http://127.0.0.1:8107/ready',
                '[2026-04-11T04:00:08Z] Ready URL responded: http://127.0.0.1:8107/ready',
                '[2026-04-11T04:00:09Z] Restarting ielts-service@asr-service',
                '[2026-04-11T04:00:10Z] Waiting for ready URL: http://127.0.0.1:8106/ready',
                '[2026-04-11T04:00:11Z] Ready URL responded: http://127.0.0.1:8106/ready',
                '[2026-04-11T04:00:12Z] Wave 4 shared SQLite override restart completed for: notes-service,asr-service',
            )
        )
        + '\n',
        encoding='utf-8',
    )
    output_path = tmp_path / 'record.md'

    result = _run_script(
        '--log-path',
        str(log_path),
        '--output',
        str(output_path),
        '--host',
        '119.29.182.134',
        '--command',
        'sudo APP_HOME=/opt/ielts-vocab SHARED_SQLITE_OVERRIDE_RECORD_PATH=/var/log/ielts-vocab/wave4/shared-sqlite-override-20260411T040000Z.log bash /opt/ielts-vocab/current/scripts/cloud-deploy/restart-services-with-shared-sqlite-override.sh notes-service asr-service',
    )

    assert result.returncode == 0
    record_text = output_path.read_text(encoding='utf-8')
    assert '- Kind: shared-sqlite-override-restart' in record_text
    assert '- Status: success' in record_text
    assert '- Host: 119.29.182.134' in record_text
    assert '- Current release: /opt/ielts-vocab/releases/20260411-current' in record_text
    assert '- Target services: notes-service,asr-service' in record_text
    assert '- Ready timeout seconds: 45' in record_text
    assert 'Restarting ielts-service@notes-service' in record_text
