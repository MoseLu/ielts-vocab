from __future__ import annotations

from models import SearchCache, db
from services import search_cache_repository


class FakeRedisSearchCacheClient:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.expirations: dict[str, int] = {}

    def get(self, key: str):
        return self.values.get(key)

    def setex(self, key: str, ttl_seconds: int, value: str) -> bool:
        self.values[key] = value
        self.expirations[key] = int(ttl_seconds)
        return True


def test_search_cache_uses_redis_when_available(app, monkeypatch):
    fake_redis = FakeRedisSearchCacheClient()
    monkeypatch.setattr(
        search_cache_repository,
        'build_redis_client',
        lambda service_name=None: fake_redis,
    )
    monkeypatch.setattr(
        search_cache_repository,
        'resolve_redis_key_prefix',
        lambda service_name=None: 'test-ai-execution',
    )

    with app.app_context():
        search_cache_repository.create_search_cache('compile meaning', 'cached summary')
        search_cache_repository.commit()
        cached = search_cache_repository.get_search_cache('compile meaning')

        assert cached is not None
        assert cached.result == 'cached summary'
        assert db.session.query(SearchCache).count() == 0
        assert len(fake_redis.values) == 1
        redis_key = next(iter(fake_redis.values))
        assert redis_key.startswith('test-ai-execution:search-cache:')
        assert fake_redis.expirations[redis_key] == search_cache_repository.SEARCH_CACHE_TTL_SECONDS


def test_search_cache_falls_back_to_database_when_redis_is_unavailable(app, monkeypatch):
    def _raise_unavailable(*args, **kwargs):
        raise RuntimeError('redis unavailable')

    monkeypatch.setattr(search_cache_repository, 'build_redis_client', _raise_unavailable)

    with app.app_context():
        search_cache_repository.create_search_cache('abandon meaning', 'database summary')
        search_cache_repository.commit()
        cached = search_cache_repository.get_search_cache('abandon meaning')

        assert cached is not None
        assert cached.result == 'database summary'
        assert db.session.query(SearchCache).count() == 1
