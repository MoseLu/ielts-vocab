from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


WAVE5_WORKER_CASES = {
    'core-eventing-worker': ('services/identity-service', 'eventing_worker.py'),
    'notes-domain-worker': ('services/notes-service', 'domain_worker.py'),
    'ai-execution-domain-worker': ('services/ai-execution-service', 'domain_worker.py'),
    'admin-ops-domain-worker': ('services/admin-ops-service', 'domain_worker.py'),
}
REPLACED_GROUP_WORKERS = (
    'identity-outbox-publisher',
    'learning-core-outbox-publisher',
    'tts-media-outbox-publisher',
    'ai-execution-outbox-publisher',
    'ai-wrong-word-projection-worker',
    'ai-daily-summary-projection-worker',
    'notes-outbox-publisher',
    'notes-study-session-projection-worker',
    'notes-wrong-word-projection-worker',
    'notes-prompt-run-projection-worker',
    'admin-user-projection-worker',
    'admin-study-session-projection-worker',
    'admin-daily-summary-projection-worker',
    'admin-prompt-run-projection-worker',
    'admin-tts-media-projection-worker',
    'admin-wrong-word-projection-worker',
)


def test_run_service_routes_wave5_worker_units_to_python_entrypoints():
    script = _read('scripts/cloud-deploy/run-service.sh')

    assert 'run_python_script()' in script
    for worker_name, (workdir, script_name) in WAVE5_WORKER_CASES.items():
        assert f'  {worker_name})' in script
        assert f'run_python_script "{workdir}" "{script_name}"' in script


def test_release_common_enables_workers_only_for_worker_aware_releases():
    script = _read('scripts/cloud-deploy/release-common.sh')

    assert 'CORE_SERVICE_UNITS=(' in script
    assert 'WAVE5_WORKER_UNITS=(' in script
    assert 'REPLACED_GROUP_WORKER_UNITS=(' in script
    assert 'release_supports_wave5_workers()' in script
    assert 'grep -Fq "  ${worker})"' in script
    assert 'disable_replaced_group_workers()' in script
    assert 'systemctl enable "ielts-service@${worker}"' in script
    assert 'systemctl disable --now "ielts-service@${worker}"' in script
    assert 'disable_replaced_group_workers' in script
    for worker_name in WAVE5_WORKER_CASES:
        assert f'"{worker_name}"' in script
    for worker_name in REPLACED_GROUP_WORKERS:
        assert f'"{worker_name}"' in script


def test_smoke_check_gates_on_worker_unit_health_when_release_supports_them():
    script = _read('scripts/cloud-deploy/smoke-check.sh')

    assert 'require_command systemctl' in script
    assert 'wait_for_systemd_unit()' in script
    assert 'release_supports_wave5_workers "${current_release}"' in script
    assert 'wait_for_systemd_unit "ielts-service@${worker}" "${worker} active"' in script
    assert 'Skipping canonical worker unit smoke because current release does not support worker units' in script
