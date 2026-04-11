from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


WAVE5_WORKER_CASES = {
    'identity-outbox-publisher': ('services/identity-service', 'outbox_publisher.py'),
    'learning-core-outbox-publisher': ('services/learning-core-service', 'outbox_publisher.py'),
    'ai-execution-outbox-publisher': ('services/ai-execution-service', 'outbox_publisher.py'),
    'ai-wrong-word-projection-worker': ('services/ai-execution-service', 'wrong_word_projection_worker.py'),
    'ai-daily-summary-projection-worker': ('services/ai-execution-service', 'daily_summary_projection_worker.py'),
    'notes-outbox-publisher': ('services/notes-service', 'outbox_publisher.py'),
    'notes-study-session-projection-worker': ('services/notes-service', 'study_session_projection_worker.py'),
    'notes-wrong-word-projection-worker': ('services/notes-service', 'wrong_word_projection_worker.py'),
    'notes-prompt-run-projection-worker': ('services/notes-service', 'prompt_run_projection_worker.py'),
    'tts-media-outbox-publisher': ('services/tts-media-service', 'outbox_publisher.py'),
    'admin-user-projection-worker': ('services/admin-ops-service', 'user_projection_worker.py'),
    'admin-study-session-projection-worker': ('services/admin-ops-service', 'study_session_projection_worker.py'),
    'admin-daily-summary-projection-worker': ('services/admin-ops-service', 'daily_summary_projection_worker.py'),
    'admin-prompt-run-projection-worker': ('services/admin-ops-service', 'prompt_run_projection_worker.py'),
    'admin-tts-media-projection-worker': ('services/admin-ops-service', 'tts_media_projection_worker.py'),
    'admin-wrong-word-projection-worker': ('services/admin-ops-service', 'wrong_word_projection_worker.py'),
}


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
    assert 'release_supports_wave5_workers()' in script
    assert 'grep -Fq "  ${worker})"' in script
    assert 'systemctl enable "ielts-service@${worker}"' in script
    assert 'systemctl disable --now "ielts-service@${worker}"' in script
    for worker_name in WAVE5_WORKER_CASES:
        assert f'"{worker_name}"' in script


def test_smoke_check_gates_on_worker_unit_health_when_release_supports_them():
    script = _read('scripts/cloud-deploy/smoke-check.sh')

    assert 'require_command systemctl' in script
    assert 'wait_for_systemd_unit()' in script
    assert 'release_supports_wave5_workers "${current_release}"' in script
    assert 'wait_for_systemd_unit "ielts-service@${worker}" "${worker} active"' in script
    assert 'Skipping Wave 5 worker unit smoke because current release does not support worker units' in script
