from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime

from platform_sdk.redis_runtime import build_redis_client, resolve_redis_key_prefix
from service_models.ai_execution_models import SearchCache, db


SEARCH_CACHE_SERVICE_NAME = 'ai-execution-service'
SEARCH_CACHE_TTL_SECONDS = 7 * 24 * 60 * 60


@dataclass(slots=True)
class SearchCacheSnapshot:
    query: str
    result: str
    created_at: datetime | None = None


def _search_cache_redis_key(query: str) -> str:
    digest = hashlib.sha256(query.encode('utf-8')).hexdigest()
    prefix = resolve_redis_key_prefix(service_name=SEARCH_CACHE_SERVICE_NAME)
    return f'{prefix}:search-cache:{digest}'


def _build_redis_snapshot(query: str, result: str) -> SearchCacheSnapshot:
    return SearchCacheSnapshot(
        query=query,
        result=result,
        created_at=datetime.utcnow(),
    )


def _serialize_redis_snapshot(snapshot: SearchCacheSnapshot) -> str:
    return json.dumps(
        {
            'query': snapshot.query,
            'result': snapshot.result,
            'created_at': snapshot.created_at.isoformat() if snapshot.created_at else None,
        },
        ensure_ascii=False,
    )


def _deserialize_redis_snapshot(raw_value) -> SearchCacheSnapshot | None:
    if raw_value is None:
        return None

    payload = raw_value.decode('utf-8') if isinstance(raw_value, bytes) else str(raw_value)
    data = json.loads(payload)
    created_at_value = str(data.get('created_at') or '').strip()
    try:
        created_at = datetime.fromisoformat(created_at_value) if created_at_value else None
    except ValueError:
        created_at = None
    return SearchCacheSnapshot(
        query=str(data.get('query') or ''),
        result=str(data.get('result') or ''),
        created_at=created_at,
    )


def _get_redis_client():
    try:
        return build_redis_client(service_name=SEARCH_CACHE_SERVICE_NAME)
    except Exception:
        return None


def prune_search_cache_older_than(cutoff: datetime) -> None:
    db.session.query(SearchCache).filter(SearchCache.created_at < cutoff).delete(
        synchronize_session=False
    )


def get_search_cache(query: str):
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            cached = _deserialize_redis_snapshot(
                redis_client.get(_search_cache_redis_key(query))
            )
        except Exception:
            cached = None
        if cached is not None:
            return cached
    return db.session.query(SearchCache).filter_by(query=query).first()


def create_search_cache(query: str, result: str):
    snapshot = _build_redis_snapshot(query, result)
    redis_client = _get_redis_client()
    if redis_client is not None:
        try:
            redis_client.setex(
                _search_cache_redis_key(query),
                SEARCH_CACHE_TTL_SECONDS,
                _serialize_redis_snapshot(snapshot),
            )
            return snapshot
        except Exception:
            pass

    record = SearchCache(query=query, result=result)
    db.session.add(record)
    return record


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
