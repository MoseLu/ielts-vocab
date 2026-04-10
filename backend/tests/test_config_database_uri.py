import importlib


def _clear_database_env(monkeypatch):
    for name in (
        'CURRENT_SERVICE_NAME',
        'SQLALCHEMY_DATABASE_URI',
        'DATABASE_URL',
        'SQLITE_DB_PATH',
        'POSTGRES_HOST',
        'POSTGRES_PORT',
        'POSTGRES_DB',
        'POSTGRES_DATABASE',
        'POSTGRES_USER',
        'POSTGRES_PASSWORD',
        'POSTGRES_SSLMODE',
        'IDENTITY_SERVICE_DATABASE_URL',
        'IDENTITY_SERVICE_SQLALCHEMY_DATABASE_URI',
        'IDENTITY_SERVICE_SQLITE_DB_PATH',
        'LEARNING_CORE_SERVICE_POSTGRES_HOST',
        'LEARNING_CORE_SERVICE_POSTGRES_PORT',
        'LEARNING_CORE_SERVICE_POSTGRES_DB',
        'LEARNING_CORE_SERVICE_POSTGRES_USER',
        'LEARNING_CORE_SERVICE_POSTGRES_PASSWORD',
        'LEARNING_CORE_SERVICE_POSTGRES_SSLMODE',
    ):
        monkeypatch.delenv(name, raising=False)


def _reload_config(monkeypatch):
    monkeypatch.setenv('SECRET_KEY', 'test-secret')
    monkeypatch.setenv('JWT_SECRET_KEY', 'test-jwt-secret')
    import config
    return importlib.reload(config)


def test_config_defaults_to_sqlite_when_no_database_env_is_set(monkeypatch):
    _clear_database_env(monkeypatch)

    config = _reload_config(monkeypatch)

    assert config.Config.DATABASE_BACKEND == 'sqlite'
    assert config.Config.SQLALCHEMY_DATABASE_URI.startswith('sqlite:///')


def test_config_uses_generic_database_url(monkeypatch):
    _clear_database_env(monkeypatch)
    monkeypatch.setenv('DATABASE_URL', 'postgres://demo:secret@127.0.0.1:5432/ielts_demo')

    config = _reload_config(monkeypatch)

    assert config.Config.DATABASE_BACKEND == 'postgresql'
    assert config.Config.SQLALCHEMY_DATABASE_URI == 'postgresql://demo:secret@127.0.0.1:5432/ielts_demo'


def test_config_prefers_service_specific_database_url(monkeypatch):
    _clear_database_env(monkeypatch)
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'identity-service')
    monkeypatch.setenv('DATABASE_URL', 'postgres://shared:secret@127.0.0.1:5432/shared_db')
    monkeypatch.setenv(
        'IDENTITY_SERVICE_DATABASE_URL',
        'postgresql://identity:secret@127.0.0.1:5432/identity_db',
    )

    config = _reload_config(monkeypatch)

    assert config.Config.SQLALCHEMY_DATABASE_URI == 'postgresql://identity:secret@127.0.0.1:5432/identity_db'


def test_config_builds_service_specific_postgres_uri_from_parts(monkeypatch):
    _clear_database_env(monkeypatch)
    monkeypatch.setenv('CURRENT_SERVICE_NAME', 'learning-core-service')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_POSTGRES_HOST', '127.0.0.1')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_POSTGRES_PORT', '5432')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_POSTGRES_DB', 'ielts_learning_core_service')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_POSTGRES_USER', 'learning_core')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_POSTGRES_PASSWORD', 'p@ss word')
    monkeypatch.setenv('LEARNING_CORE_SERVICE_POSTGRES_SSLMODE', 'disable')

    config = _reload_config(monkeypatch)

    assert config.Config.DATABASE_BACKEND == 'postgresql'
    assert config.Config.SQLALCHEMY_DATABASE_URI == (
        'postgresql://learning_core:p%40ss+word@127.0.0.1:5432/'
        'ielts_learning_core_service?sslmode=disable'
    )
