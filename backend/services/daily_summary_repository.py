from __future__ import annotations

from datetime import datetime

from models import UserDailySummary, db


def get_daily_summary(user_id: int, target_date: str):
    return UserDailySummary.query.filter_by(user_id=user_id, date=target_date).first()


def list_daily_summaries(
    user_id: int,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    descending: bool = True,
):
    query = UserDailySummary.query.filter_by(user_id=user_id)
    if start_date:
        query = query.filter(UserDailySummary.date >= start_date)
    if end_date:
        query = query.filter(UserDailySummary.date <= end_date)
    order_clause = UserDailySummary.date.desc() if descending else UserDailySummary.date.asc()
    return query.order_by(order_clause).all()


def save_daily_summary(
    existing,
    *,
    user_id: int,
    target_date: str,
    summary_content: str,
    generated_at: datetime,
):
    if existing:
        existing.content = summary_content
        existing.generated_at = generated_at
        db.session.commit()
        return existing

    summary = UserDailySummary(
        user_id=user_id,
        date=target_date,
        content=summary_content,
        generated_at=generated_at,
    )
    db.session.add(summary)
    db.session.commit()
    return summary


def rollback() -> None:
    db.session.rollback()
