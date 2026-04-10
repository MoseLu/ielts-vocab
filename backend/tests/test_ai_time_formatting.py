from datetime import datetime

from services.ai_learning_context_service import build_learning_context_msg
from services.local_time import format_event_time_for_ai
from services.notes_summary_service_parts.prompt_building import build_summary_prompt


def test_format_event_time_for_ai_converts_utc_to_local_clock():
    stamp = format_event_time_for_ai(
        '2026-04-09T08:11:00',
        now_utc=datetime(2026, 4, 9, 9, 0, 0),
        reference_date='2026-04-09',
    )

    assert stamp == '16:11'


def test_format_event_time_for_ai_includes_date_for_non_reference_day():
    stamp = format_event_time_for_ai(
        '2026-04-08T08:11:00',
        now_utc=datetime(2026, 4, 9, 7, 0, 0),
        reference_date='2026-04-09',
    )

    assert stamp == '04-08 16:11'


def test_learning_context_uses_local_today_and_safe_event_stamp(monkeypatch):
    monkeypatch.setattr('services.local_time.utc_now_naive', lambda: datetime(2026, 4, 9, 16, 30, 0))

    rendered = build_learning_context_msg(
        {
            'learnerProfile': {
                'activity_summary': {'total_events': 1},
                'recent_activity': [{
                    'occurred_at': '2026-04-09T17:11:00',
                    'title': '听力检查 thus 待强化',
                }],
            },
        },
        {},
    )

    assert '【今日日期】2026年04月10日' in rendered
    assert '01:11 听力检查 thus 待强化' in rendered


def test_summary_prompt_uses_local_event_stamp():
    prompt = build_summary_prompt(
        target_date='2026-04-09',
        notes_list=[],
        sessions=[],
        wrong_words=[],
        learner_profile={
            'activity_summary': {'total_events': 1},
            'recent_activity': [{
                'occurred_at': '2026-04-09T08:11:00',
                'title': '听力检查 thus 待强化',
            }],
        },
    )

    assert '16:11 听力检查 thus 待强化' in prompt
