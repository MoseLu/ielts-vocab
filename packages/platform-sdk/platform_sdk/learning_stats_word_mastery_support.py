from __future__ import annotations

from models import UserWordMasteryState


def build_word_mastery_summary(user_id: int) -> tuple[dict, list[dict]]:
    rows = UserWordMasteryState.query.filter_by(user_id=user_id).all()
    dimension_totals = {
        'recognition': {'passed': 0, 'pending': 0},
        'meaning': {'passed': 0, 'pending': 0},
        'listening': {'passed': 0, 'pending': 0},
        'speaking': {'passed': 0, 'pending': 0},
        'dictation': {'passed': 0, 'pending': 0},
    }
    summary = {
        'total_words': len(rows),
        'new_words': 0,
        'unlocked_words': 0,
        'in_review_words': 0,
        'passed_words': 0,
    }
    for row in rows:
        payload = row.to_dict()
        status = payload.get('overall_status') or 'new'
        if status == 'passed':
            summary['passed_words'] += 1
        elif status == 'in_review':
            summary['in_review_words'] += 1
        elif status == 'unlocked':
            summary['unlocked_words'] += 1
        else:
            summary['new_words'] += 1

        states = payload.get('dimension_states') or {}
        for dimension, totals in dimension_totals.items():
            state = states.get(dimension) or {}
            if int(state.get('pass_streak') or 0) >= 4:
                totals['passed'] += 1
            else:
                totals['pending'] += 1

    dimension_mastery = [
        {
            'dimension': dimension,
            'passed_words': totals['passed'],
            'pending_words': totals['pending'],
        }
        for dimension, totals in dimension_totals.items()
    ]
    return summary, dimension_mastery
