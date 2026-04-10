from __future__ import annotations

from datetime import datetime

from models import SearchCache, db


def prune_search_cache_older_than(cutoff: datetime) -> None:
    SearchCache.query.filter(SearchCache.created_at < cutoff).delete(
        synchronize_session=False
    )


def get_search_cache(query: str):
    return SearchCache.query.filter_by(query=query).first()


def create_search_cache(query: str, result: str):
    record = SearchCache(query=query, result=result)
    db.session.add(record)
    return record


def commit() -> None:
    db.session.commit()


def rollback() -> None:
    db.session.rollback()
