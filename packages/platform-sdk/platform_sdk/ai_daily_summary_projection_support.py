from __future__ import annotations

from service_models.ai_execution_models import AIProjectedDailySummary
from service_models.notes_models import UserDailySummary


def projected_daily_summaries_ready(user_id: int) -> bool:
    projected_total = AIProjectedDailySummary.query.filter_by(user_id=user_id).count()
    shared_total = UserDailySummary.query.filter_by(user_id=user_id).count()
    if shared_total <= 0:
        return True
    return projected_total >= shared_total


def list_projected_daily_summaries_for_ai(
    user_id: int,
    *,
    limit: int = 7,
    start_date: str | None = None,
    end_date: str | None = None,
) -> tuple[bool, list[dict]]:
    query = AIProjectedDailySummary.query.filter_by(user_id=user_id)
    if start_date:
        query = query.filter(AIProjectedDailySummary.date >= start_date)
    if end_date:
        query = query.filter(AIProjectedDailySummary.date <= end_date)

    summaries = (
        query
        .order_by(AIProjectedDailySummary.generated_at.desc(), AIProjectedDailySummary.id.desc())
        .limit(max(1, min(30, int(limit or 7))))
        .all()
    )
    return projected_daily_summaries_ready(user_id), [summary.to_dict() for summary in summaries]
