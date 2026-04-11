from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CLOUD_DIR = REPO_ROOT / 'scripts' / 'cloud-deploy'


def test_provision_postgres_writes_wave5_broker_env_baseline():
    script_text = (CLOUD_DIR / 'provision-postgres.sh').read_text(encoding='utf-8')

    for expected in (
        'REDIS_HOST=',
        'REDIS_PORT=',
        'REDIS_KEY_PREFIX=',
        'GATEWAY_BFF_REDIS_DB=0',
        'ADMIN_OPS_SERVICE_REDIS_DB=8',
        'RABBITMQ_HOST=',
        'RABBITMQ_PORT=',
        'RABBITMQ_USER=',
        'RABBITMQ_PASSWORD=',
        'RABBITMQ_VHOST=',
        'RABBITMQ_DOMAIN_EXCHANGE=',
    ):
        assert expected in script_text


def test_install_cloud_runtime_includes_broker_packages_and_provision_step():
    script_text = (CLOUD_DIR / 'install-cloud-runtime.sh').read_text(encoding='utf-8')

    assert 'redis rabbitmq-server' in script_text
    assert 'provision-broker-runtime.sh' in script_text
    assert 'systemctl enable --now postgresql nginx crond redis rabbitmq-server' in script_text


def test_preflight_check_requires_broker_env_and_units():
    script_text = (CLOUD_DIR / 'preflight-check.sh').read_text(encoding='utf-8')

    assert "grep -q '^REDIS_HOST='" in script_text
    assert "grep -q '^RABBITMQ_HOST='" in script_text
    assert "grep -q '^RABBITMQ_USER='" in script_text
    assert "grep -q '^RABBITMQ_VHOST='" in script_text
    assert 'systemctl is-active --quiet redis' in script_text
    assert 'systemctl is-active --quiet rabbitmq-server' in script_text


def test_smoke_check_runs_broker_validation_before_http_readiness():
    script_text = (CLOUD_DIR / 'smoke-check.sh').read_text(encoding='utf-8')

    validate_index = script_text.index('VALIDATE_BROKER_SCRIPT=')
    gateway_check_index = script_text.index('check_url "http://127.0.0.1:${GATEWAY_BFF_PORT}/ready"')
    assert validate_index < gateway_check_index
    assert 'validate-broker-runtime.sh' in script_text
