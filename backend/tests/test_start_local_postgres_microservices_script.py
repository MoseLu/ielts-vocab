from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding='utf-8')


def test_start_local_postgres_microservices_script_uses_project_owned_cluster():
    script = _read('scripts/start-local-postgres-microservices.sh')

    assert 'initdb -D "${data_dir}"' in script
    assert 'pg_ctl -D "${data_dir}"' in script
    assert 'pg_isready -h "${bind_host}" -p "${port}" -U "${admin_user}"' in script
    assert "env_path.read_text(encoding='utf-8-sig')" in script
    assert "conn = psycopg2.connect(" in script
    assert "conn.autocommit = True" in script
    assert "CREATE DATABASE {} OWNER {}" in script
