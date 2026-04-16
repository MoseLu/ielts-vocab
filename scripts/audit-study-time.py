from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = REPO_ROOT / 'backend'
SDK_PATH = REPO_ROOT / 'packages' / 'platform-sdk'
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from app import create_app
from models import User
from platform_sdk.learning_repository_adapters import learning_event_repository, learning_stats_repository
from platform_sdk.learning_stats_modes_support import stats_mode_candidates
from platform_sdk.local_time_support import build_time_audit_report, resolve_local_day_window, utc_now_naive
from platform_sdk.study_session_repository_adapter import (
    find_recent_open_placeholder_session,
    newer_analytics_session_exists,
)
from platform_sdk.study_session_support import get_live_pending_session_snapshot


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description='Audit one user/day study-time accounting with raw, deduped, and event-backed checks.',
    )
    identity_group = parser.add_mutually_exclusive_group(required=True)
    identity_group.add_argument('--user-id', type=int, help='Numeric user id.')
    identity_group.add_argument('--username', help='Username to resolve to a user id.')
    parser.add_argument('--date', required=True, help='Local date in YYYY-MM-DD.')
    parser.add_argument('--book-id', help='Optional book filter.')
    parser.add_argument('--mode', help='Optional mode filter.')
    parser.add_argument('--format', choices=('text', 'json'), default='text', help='Output format.')
    return parser.parse_args()


def resolve_user_id(*, user_id: int | None, username: str | None) -> int:
    if user_id is not None:
        return user_id
    user = User.query.filter_by(username=username).first()
    if user is None:
        raise SystemExit(f'User not found: {username!r}')
    return int(user.id)


def build_audit_summary(args: argparse.Namespace) -> dict:
    user_id = resolve_user_id(user_id=args.user_id, username=args.username)
    now_utc = utc_now_naive()
    _date_str, day_start, day_end = resolve_local_day_window(args.date, now_utc)
    sessions = learning_stats_repository.list_user_analytics_sessions(
        user_id,
        before=day_end,
        book_id=args.book_id or None,
        mode_candidates=stats_mode_candidates(args.mode) if args.mode else None,
    )
    live_pending = get_live_pending_session_snapshot(
        user_id,
        find_recent_open_placeholder_session=find_recent_open_placeholder_session,
        newer_analytics_session_exists=newer_analytics_session_exists,
        find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
        mode=args.mode or None,
        book_id=args.book_id or None,
        since=day_start,
        now=now_utc,
    )
    audit = build_time_audit_report(
        user_id=user_id,
        sessions=sessions,
        live_pending=live_pending,
        now=now_utc,
        window_start=day_start,
        window_end=day_end,
        find_latest_session_activity_at=learning_event_repository.find_latest_session_activity_at,
        list_learning_events_in_window=learning_event_repository.list_user_learning_events_in_window,
    )
    return {
        'user_id': user_id,
        'date': args.date,
        'book_id': args.book_id or None,
        'mode': args.mode or None,
        'window_start_utc': day_start.isoformat(),
        'window_end_utc': day_end.isoformat(),
        'audit': audit.to_dict(),
    }


def render_text(summary: dict) -> str:
    audit = summary['audit']
    lines = [
        f"user_id={summary['user_id']} date={summary['date']}",
        f"window={summary['window_start_utc']} -> {summary['window_end_utc']}",
        (
            'seconds: '
            f"raw={audit['raw_session_seconds']} "
            f"deduped={audit['deduped_session_seconds']} "
            f"live_pending={audit['live_pending_seconds']} "
            f"audited_total={audit['audited_total_seconds']} "
            f"excluded_zero_activity={audit['excluded_session_seconds']}"
        ),
        (
            'counts: '
            f"sessions={audit['session_count']} "
            f"overlaps={len(audit['overlap_pairs'])} "
            f"zero_activity={len(audit['zero_activity_sessions'])} "
            f"event_backed={len(audit['event_backed_sessions'])} "
            f"event_gaps={len(audit['event_gaps'])}"
        ),
    ]
    if audit['overlap_pairs']:
        lines.append('overlap_pairs:')
        for pair in audit['overlap_pairs'][:20]:
            lines.append(
                f"  - {pair['left_session_id']}:{pair['left_mode']} vs "
                f"{pair['right_session_id']}:{pair['right_mode']} "
                f"=> {pair['overlap_seconds']}s"
            )
    if audit['zero_activity_sessions']:
        lines.append('zero_activity_sessions:')
        for row in audit['zero_activity_sessions'][:20]:
            lines.append(
                f"  - {row['session_id']}:{row['mode']} "
                f"{row['window_duration_seconds']}s "
                f"event={row['event_activity_at'] or 'none'}"
            )
    if audit['event_gaps']:
        lines.append('event_gaps:')
        for row in audit['event_gaps'][:20]:
            lines.append(
                f"  - {row['occurred_at']} {row['source']} {row['event_type']} {row['mode'] or ''}".rstrip()
            )
    return '\n'.join(lines)


def main() -> int:
    args = parse_args()
    app = create_app()
    with app.app_context():
        summary = build_audit_summary(args)

    if args.format == 'json':
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(render_text(summary))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
