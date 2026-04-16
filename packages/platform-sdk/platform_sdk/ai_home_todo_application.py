from __future__ import annotations

from datetime import datetime

from platform_sdk.cross_service_boundary import run_with_legacy_cross_service_fallback
from platform_sdk.learning_core_home_todo_signals_application import (
    build_learning_core_home_todo_signals_payload,
)
from platform_sdk.learning_core_internal_client import fetch_learning_core_home_todo_signals
from platform_sdk.ai_home_todo_task_builders import (
    TASK_ORDER,
    TASK_PRIORITY,
    build_due_review_task,
    build_error_review_task,
    build_mainline_task,
    build_speaking_task,
    ranked_items,
)
from service_models.ai_execution_models import UserHomeTodoItem, UserHomeTodoPlan, db


def _validate_target_date(target_date: str | None) -> str | None:
    if not target_date:
        return None
    try:
        datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        return None
    return target_date


def _serialize_summary(plan: UserHomeTodoPlan) -> dict:
    return {
        'pending_count': int(plan.pending_count or 0),
        'completed_count': int(plan.completed_count or 0),
        'carry_over_count': int(plan.carry_over_count or 0),
        'last_generated_at': plan.last_generated_at.isoformat() if plan.last_generated_at else None,
    }


def _select_primary_items(items: list[UserHomeTodoItem]) -> tuple[list[UserHomeTodoItem], list[UserHomeTodoItem]]:
    return ranked_items(items), []


def _roll_over_pending_items(user_id: int, *, plan_date: str, now_utc: datetime) -> dict[str, int]:
    rows = (
        db.session.query(UserHomeTodoItem, UserHomeTodoPlan)
        .join(UserHomeTodoPlan, UserHomeTodoItem.plan_id == UserHomeTodoPlan.id)
        .filter(UserHomeTodoPlan.user_id == user_id)
        .filter(UserHomeTodoPlan.plan_date < plan_date)
        .filter(UserHomeTodoItem.status == 'pending')
        .filter(UserHomeTodoItem.rolled_over_at.is_(None))
        .order_by(UserHomeTodoPlan.plan_date.desc(), UserHomeTodoItem.id.desc())
        .all()
    )
    carry_over_by_key: dict[str, int] = {}
    seen_keys: set[str] = set()
    for item, _plan in rows:
        if item.task_key not in seen_keys:
            carry_over_by_key[item.task_key] = max(0, int(item.carry_over_count or 0)) + 1
            seen_keys.add(item.task_key)
        item.status = 'rolled_over'
        item.rolled_over_at = now_utc
    return carry_over_by_key


def _build_task_specs(
    signals: dict,
    *,
    carry_over_by_key: dict[str, int],
    existing_items: dict[str, UserHomeTodoItem],
) -> list[dict]:
    specs = [
        build_due_review_task(signals, carry_over_count=carry_over_by_key.get('due-review', 0)),
        build_mainline_task(signals, carry_over_by_key=carry_over_by_key),
        build_error_review_task(signals, carry_over_count=carry_over_by_key.get('error-review', 0)),
    ]
    speaking_spec = build_speaking_task(
        signals,
        carry_over_count=carry_over_by_key.get('speaking', 0),
        existing_item=existing_items.get('speaking'),
    )
    if speaking_spec is not None:
        specs.append(speaking_spec)
    return sorted(
        specs,
        key=lambda item: (
            TASK_PRIORITY.get(item['kind'], 100),
            TASK_ORDER.index(item['kind']) if item['kind'] in TASK_ORDER else 999,
        ),
    )


def _upsert_plan_item(plan_id: int, existing_item: UserHomeTodoItem | None, spec: dict, *, now_utc: datetime) -> UserHomeTodoItem:
    item = existing_item or UserHomeTodoItem(plan_id=plan_id, task_key=spec['task_key'])
    item.kind = spec['kind']
    item.status = spec['status']
    item.priority = int(spec['priority'] or 100)
    item.title = spec['title']
    item.description = spec['description']
    item.badge = spec['badge']
    item.carry_over_count = int(spec['carry_over_count'] or 0)
    item.set_action(spec.get('action'))
    item.set_steps(spec.get('steps'))
    item.set_evidence(spec.get('evidence'))
    if item.status == 'completed':
        item.completed_at = item.completed_at or now_utc
    else:
        item.completed_at = None
    if existing_item is None:
        db.session.add(item)
    return item


def _serialize_plan_payload(plan: UserHomeTodoPlan, items: list[UserHomeTodoItem]) -> dict:
    primary_items, overflow_items = _select_primary_items(items)
    return {
        'date': plan.plan_date,
        'summary': _serialize_summary(plan),
        'primary_items': [item.to_dict() for item in primary_items],
        'overflow_items': [item.to_dict() for item in overflow_items],
    }


def _refresh_home_todo_plan(user_id: int, signals: dict) -> tuple[dict, int]:
    plan_date = str(signals.get('date') or '').strip()
    if not plan_date:
        return {'error': 'missing plan date'}, 500

    now_utc = datetime.utcnow()
    try:
        plan = UserHomeTodoPlan.query.filter_by(user_id=user_id, plan_date=plan_date).one_or_none()
        is_new_plan = plan is None
        if plan is None:
            plan = UserHomeTodoPlan(user_id=user_id, plan_date=plan_date)
            db.session.add(plan)
            db.session.flush()

        existing_items = {item.task_key: item for item in list(plan.items)}
        carry_over_by_key = (
            _roll_over_pending_items(user_id, plan_date=plan_date, now_utc=now_utc)
            if is_new_plan
            else {item.task_key: int(item.carry_over_count or 0) for item in existing_items.values()}
        )
        specs = _build_task_specs(
            signals,
            carry_over_by_key=carry_over_by_key,
            existing_items=existing_items,
        )
        desired_keys = {spec['task_key'] for spec in specs}
        for task_key, item in list(existing_items.items()):
            if task_key not in desired_keys:
                db.session.delete(item)

        for spec in specs:
            _upsert_plan_item(
                plan.id,
                existing_items.get(spec['task_key']),
                spec,
                now_utc=now_utc,
            )

        db.session.flush()
        items = ranked_items(UserHomeTodoItem.query.filter_by(plan_id=plan.id).all())
        plan.pending_count = sum(1 for item in items if item.status == 'pending')
        plan.completed_count = sum(1 for item in items if item.status == 'completed')
        plan.carry_over_count = sum(max(0, int(item.carry_over_count or 0)) for item in items)
        plan.last_generated_at = now_utc
        db.session.commit()
        return _serialize_plan_payload(plan, items), 200
    except Exception:
        db.session.rollback()
        raise


def build_home_todos_response(
    user_id: int,
    *,
    target_date: str | None = None,
) -> tuple[dict, int]:
    normalized_date = _validate_target_date(target_date)
    if target_date and not normalized_date:
        return {'error': 'date must be YYYY-MM-DD'}, 400

    def primary() -> tuple[dict, int]:
        signals = fetch_learning_core_home_todo_signals(
            user_id,
            target_date=normalized_date,
        )
        return _refresh_home_todo_plan(user_id, signals)

    def fallback() -> tuple[dict, int]:
        signals = build_learning_core_home_todo_signals_payload(
            user_id,
            target_date=normalized_date,
        )
        return _refresh_home_todo_plan(user_id, signals)

    return run_with_legacy_cross_service_fallback(
        upstream_name='learning-core-service',
        action='home-todo-signals-read',
        primary=primary,
        fallback=fallback,
    )
