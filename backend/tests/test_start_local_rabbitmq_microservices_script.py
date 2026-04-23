from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_start_local_rabbitmq_microservices_script_uses_project_owned_runtime_dirs():
    script = _read('scripts/start-local-rabbitmq-microservices.sh')

    assert 'rabbitmq-server' in script
    assert 'rabbitmq-diagnostics' in script
    assert 'listeners.tcp.default = ${port}' in script
    assert 'management.tcp.port = 15679' in script
    assert 'RABBITMQ_NODE_PORT' in script
    assert 'RABBITMQ_CONFIG_FILE="${config_base}"' in script
    assert 'rabbitmq-server -detached' in script
    assert 'rabbitmq-diagnostics -q ping' in script
