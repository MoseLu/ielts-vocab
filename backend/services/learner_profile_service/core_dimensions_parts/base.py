from datetime import datetime, timedelta

from models import UserQuickMemoryRecord
from services import learner_profile_repository
from services.learning_events import build_learning_activity_timeline
from services.local_time import resolve_local_day_window, utc_naive_to_epoch_ms, utc_naive_to_local_date_key, utc_now_naive
from services.memory_topics import build_memory_topics
from services.quick_memory_schedule import load_user_quick_memory_records
from services.study_sessions import get_live_pending_session_snapshot, get_session_window_metrics

MODE_LABELS = {
    'smart': '智能练习',
    'listening': '听音选义',
    'meaning': '默写模式',
    'dictation': '听写',
    'radio': '随身听',
    'quickmemory': '速记',
    'errors': '错词强化',
}

DIMENSION_LABELS = {
    'listening': '听音辨义',
    'meaning': '默写模式',
    'dictation': '拼写默写',
}

FOUR_DIMENSION_CONFIG = {
    'recognition': {
        'label': '认读',
        'definition': '看到英文单词后，1 秒内说出核心中文义。',
        'schedule_days': [1, 3, 7, 30],
        'mastery_rule': '按第1/3/7/30天节点连续答对，才算认读维度稳定。',
        'evidence_label': '速记记录 + 默写模式',
    },
    'listening': {
        'label': '听力',
        'definition': '听到发音后，不看拼写也能立刻反应词义。',
        'schedule_days': [1, 2, 4, 7, 14],
        'mastery_rule': '按第1/2/4/7/14天多次快速识别，才算听力维度稳定。',
        'evidence_label': '听音辨义练习',
    },
    'speaking': {
        'label': '口语',
        'definition': '能正确发音，并能主动用该词造简单句。',
        'schedule_days': [1, 3, 7, 15, 30],
        'mastery_rule': '按第1/3/7/15/30天完成发音和造句复现，才算口语维度稳定。',
        'evidence_label': '发音检查 + 口语模拟',
    },
    'writing': {
        'label': '书写',
        'definition': '看到中文提示后，能零错误拼出英文单词。',
        'schedule_days': [1, 2, 5, 9, 21],
        'mastery_rule': '按第1/2/5/9/21天多轮零错误拼写，才算书写维度稳定。',
        'evidence_label': '听写练习',
    },
}

DIMENSION_STATUS_LABELS = {
    'due': '有到期复习',
    'strengthen': '需要强化',
    'building': '持续巩固',
    'mastered': '阶段稳定',
    'not_started': '尚未开始',
    'needs_setup': '证据不足',
}

def _resolve_target_date(target_date: str | None) -> tuple[str, datetime, datetime]:
    return resolve_local_day_window(target_date)


def _calc_streak_days(user_id: int, target_date: str) -> int:
    rows = learner_profile_repository.list_user_study_sessions_with_words(
        user_id,
        descending=True,
    )
    if not rows:
        return 0

    date_set = {
        utc_naive_to_local_date_key(row.started_at)
        for row in rows
        if row.started_at is not None
    }
    date_set.discard(None)
    if not date_set:
        return 0

    reference = datetime.strptime(target_date, '%Y-%m-%d').date()
    if reference.isoformat() not in date_set:
        previous = (reference - timedelta(days=1)).isoformat()
        if previous not in date_set:
            return 0
        reference = reference - timedelta(days=1)

    streak = 0
    while reference.isoformat() in date_set:
        streak += 1
        reference -= timedelta(days=1)
    return streak


def _build_dimension_breakdown(smart_rows, wrong_words) -> list[dict]:
    dimension_totals = {
        'listening': {'correct': 0, 'wrong': 0},
        'meaning': {'correct': 0, 'wrong': 0},
        'dictation': {'correct': 0, 'wrong': 0},
    }

    for row in smart_rows:
        dimension_totals['listening']['correct'] += row.listening_correct or 0
        dimension_totals['listening']['wrong'] += row.listening_wrong or 0
        dimension_totals['meaning']['correct'] += row.meaning_correct or 0
        dimension_totals['meaning']['wrong'] += row.meaning_wrong or 0
        dimension_totals['dictation']['correct'] += row.dictation_correct or 0
        dimension_totals['dictation']['wrong'] += row.dictation_wrong or 0

    if not smart_rows:
        for row in wrong_words:
            dimension_totals['listening']['wrong'] += row.listening_wrong or 0
            dimension_totals['meaning']['wrong'] += row.meaning_wrong or 0
            dimension_totals['dictation']['wrong'] += row.dictation_wrong or 0

    dimensions = []
    for dimension, totals in dimension_totals.items():
        attempts = totals['correct'] + totals['wrong']
        accuracy = round(totals['correct'] / attempts * 100) if attempts > 0 else None
        weakness = (totals['wrong'] / attempts) if attempts > 0 else 0
        dimensions.append({
            'dimension': dimension,
            'label': DIMENSION_LABELS.get(dimension, dimension),
            'correct': totals['correct'],
            'wrong': totals['wrong'],
            'attempts': attempts,
            'accuracy': accuracy,
            'weakness': round(weakness, 4),
        })

    dimensions.sort(key=lambda item: (item['weakness'], item['wrong']), reverse=True)
    return dimensions


def _build_focus_words(wrong_words) -> list[dict]:
    focus_words = []
    for row in wrong_words:
        dimension_wrong_map = {
            'listening': row.listening_wrong or 0,
            'meaning': row.meaning_wrong or 0,
            'dictation': row.dictation_wrong or 0,
        }
        dominant_dimension, dominant_wrong = max(
            dimension_wrong_map.items(),
            key=lambda item: item[1],
        )
        focus_score = (row.wrong_count or 0) * 2 + dominant_wrong
        focus_words.append({
            'word': row.word,
            'definition': row.definition or '',
            'wrong_count': row.wrong_count or 0,
            'dominant_dimension': dominant_dimension,
            'dominant_dimension_label': DIMENSION_LABELS.get(dominant_dimension, dominant_dimension),
            'dominant_wrong': dominant_wrong,
            'focus_score': focus_score,
        })

    focus_words.sort(key=lambda item: (item['focus_score'], item['wrong_count']), reverse=True)
    return focus_words[:8]


def _format_schedule_label(days: list[int]) -> str:
    return '第' + '/'.join(str(day) for day in days) + '天'


def _schedule_intervals(days: list[int]) -> list[int]:
    intervals: list[int] = []
    previous = 0
    for day in days:
        intervals.append(max(1, int(day) - previous))
        previous = int(day)
    return intervals


def _coerce_word_list(values) -> list[str]:
    if isinstance(values, str):
        candidates = values.replace('，', ',').split(',')
    elif isinstance(values, list):
        candidates = values
    elif values in (None, ''):
        candidates = []
    else:
        candidates = [values]

    seen: set[str] = set()
    words: list[str] = []
    for item in candidates:
        word = str(item or '').strip()
        key = word.lower()
        if not key or key in seen:
            continue
        seen.add(key)
        words.append(word)
    return words


def _build_dimension_word_stats(rows, correct_attr: str, wrong_attr: str) -> list[dict]:
    stats: list[dict] = []
    for row in rows:
        word = (getattr(row, 'word', None) or '').strip()
        if not word:
            continue
        correct = int(getattr(row, correct_attr, 0) or 0)
        wrong = int(getattr(row, wrong_attr, 0) or 0)
        attempts = correct + wrong
        if attempts <= 0:
            continue
        stats.append({
            'word': word,
            'word_key': word.lower(),
            'correct': correct,
            'wrong': wrong,
            'attempts': attempts,
            'accuracy': round(correct / attempts * 100) if attempts > 0 else None,
        })
    return stats


def _pick_focus_words(word_stats: list[dict], limit: int = 5) -> list[str]:
    ranked = sorted(
        word_stats,
        key=lambda item: (
            item.get('wrong', 0),
            -1 * (item.get('accuracy') if item.get('accuracy') is not None else 101),
            item.get('attempts', 0),
        ),
        reverse=True,
    )
    return [item['word'] for item in ranked[:limit]]
