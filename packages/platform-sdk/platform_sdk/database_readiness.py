from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool


def make_sqlalchemy_readiness_check(sqlalchemy_uri: str):
    engine_options = {'future': True, 'pool_pre_ping': True}
    if sqlalchemy_uri.startswith('postgresql://'):
        engine_options['poolclass'] = NullPool
    engine = create_engine(sqlalchemy_uri, **engine_options)

    def check() -> bool:
        try:
            with engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            return True
        except Exception:
            return False

    check.engine = engine
    return check
