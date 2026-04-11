from datetime import datetime

from platform_sdk import notes_internal_client


def test_list_recent_daily_summaries_uses_internal_notes_endpoint(monkeypatch):
    captured: dict[str, object] = {}

    def fake_request_json(method: str, path: str, *, user_id: int, params=None, json_body=None):
        captured.update({
            'method': method,
            'path': path,
            'user_id': user_id,
            'params': params,
            'json_body': json_body,
        })
        return {
            'summaries': [{
                'id': 4,
                'date': '2026-04-11',
                'content': '# 2026-04-11 学习总结',
                'generated_at': '2026-04-11T08:00:00',
            }],
        }, 200

    monkeypatch.setattr(notes_internal_client, '_request_json', fake_request_json)

    summaries = notes_internal_client.list_recent_daily_summaries(15, limit=5)

    assert captured == {
        'method': 'GET',
        'path': '/internal/notes/summaries',
        'user_id': 15,
        'params': {'limit': 5, 'descending': 'true'},
        'json_body': None,
    }
    assert summaries == [
        notes_internal_client.DailySummarySnapshot(
            id=4,
            date='2026-04-11',
            content='# 2026-04-11 学习总结',
            generated_at=datetime(2026, 4, 11, 8, 0, 0),
        )
    ]
