from __future__ import annotations

from sqlalchemy import create_engine, text


def make_sqlalchemy_readiness_check(sqlalchemy_uri: str):
    engine = create_engine(sqlalchemy_uri, future=True, pool_pre_ping=True)

    def check() -> bool:
        try:
            with engine.connect() as connection:
                connection.execute(text('SELECT 1'))
            return True
        except Exception:
            return False

    return check
