from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_start_local_redis_microservices_script_uses_project_owned_daemon_config():
    script = _read('scripts/start-local-redis-microservices.sh')

    assert 'redis-server' in script
    assert 'redis-cli' in script
    assert 'daemonize yes' in script
    assert 'pidfile ${pid_path}' in script
    assert 'logfile ${log_path}' in script
    assert 'redis-server "${config_path}"' in script
    assert 'redis-cli -h "${bind_host}" -p "${port}" ping' in script
