from sqlalchemy.pool import NullPool

from platform_sdk.database_readiness import make_sqlalchemy_readiness_check


def test_database_readiness_uses_nullpool_for_postgres():
    check = make_sqlalchemy_readiness_check('postgresql://demo:secret@127.0.0.1:5432/ielts_demo')

    assert isinstance(check.engine.pool, NullPool)


def test_database_readiness_keeps_default_pool_for_sqlite(tmp_path):
    check = make_sqlalchemy_readiness_check(f"sqlite:///{(tmp_path / 'app.sqlite').as_posix()}")

    assert not isinstance(check.engine.pool, NullPool)
