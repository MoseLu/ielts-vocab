from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CANONICAL_WORKERS = (
    'core-eventing-worker',
    'notes-domain-worker',
    'ai-execution-domain-worker',
    'admin-ops-domain-worker',
)


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_start_microservices_boots_canonical_worker_set():
    script = _read('start-microservices.sh')

    for worker_name in CANONICAL_WORKERS:
        assert worker_name in script

    assert 'apps/gateway-bff/main.py' in script
    assert 'services/identity-service/eventing_worker.py' in script
    assert 'services/notes-service/domain_worker.py' in script
    assert 'replaced_worker_names=(' in script
    assert 'stop_pidfile_process "${runtime_dir}/${worker_name}.pid"' in script
    assert 'exited during startup' in script
    assert 'Core worker:' in script
    assert 'AI worker:' in script
    assert 'Notes worker:' in script
    assert 'Admin worker:' in script
    assert 'scripts/start-local-postgres-microservices.sh' in script
    assert 'scripts/start-local-redis-microservices.sh' in script
    assert 'scripts/start-local-rabbitmq-microservices.sh' in script
    assert '"identity-outbox-publisher|services/identity-service|' not in script
    assert '"learning-core-outbox-publisher|services/learning-core-service|' not in script
    assert '"tts-media-outbox-publisher|services/tts-media-service|' not in script
    assert '"ai-execution-outbox-publisher|' not in script
    assert '"notes-outbox-publisher|' not in script
    assert '"admin-user-projection-worker|' not in script


def test_canonical_worker_entrypoints_load_split_service_env():
    core_worker = _read('services/identity-service/eventing_worker.py')
    notes_worker = _read('services/notes-service/domain_worker.py')
    ai_worker = _read('services/ai-execution-service/domain_worker.py')
    admin_worker = _read('services/admin-ops-service/domain_worker.py')

    assert 'load_split_service_env()' in core_worker
    assert 'run_core_eventing_worker' in core_worker
    assert "load_split_service_env(service_name='notes-service')" in notes_worker
    assert 'run_notes_domain_worker' in notes_worker
    assert "load_split_service_env(service_name='ai-execution-service')" in ai_worker
    assert 'run_ai_execution_domain_worker' in ai_worker
    assert "load_split_service_env(service_name='admin-ops-service')" in admin_worker
    assert 'run_admin_ops_domain_worker' in admin_worker
