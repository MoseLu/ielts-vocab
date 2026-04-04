from datetime import datetime, timedelta

from models import UserLearningEvent, UserLearningNote, UserQuickMemoryRecord, UserSmartWordStat, UserStudySession, UserWrongWord
from services.learning_events import build_learning_activity_timeline
from services.local_time import resolve_local_day_window, utc_naive_to_epoch_ms, utc_naive_to_local_date_key, utc_now_naive
from services.memory_topics import build_memory_topics
from services.study_sessions import get_live_pending_session_snapshot

MODE_LABELS = {
    'smart': '智能练习',
    'listening': '听音选义',
    'meaning': '汉译英',
    'dictation': '听写',
    'radio': '随身听',
    'quickmemory': '速记',
    'errors': '错词强化',
}

DIMENSION_LABELS = {
    'listening': '听音辨义',
    'meaning': '汉译英（会想）',
    'dictation': '拼写默写',
}

FOUR_DIMENSION_CONFIG = {
    'recognition': {
        'label': '认读',
        'definition': '看到英文单词后，1 秒内说出核心中文义。',
        'schedule_days': [1, 3, 7, 30],
        'mastery_rule': '按第1/3/7/30天节点连续答对，才算认读维度稳定。',
        'evidence_label': '速记记录 + 汉译英（会想）',
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
    rows = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.words_studied > 0)
        .order_by(UserStudySession.started_at.desc())
        .all()
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


def _build_recognition_dimension(recognition_rows, qm_rows, now_ms: int) -> dict:
    config = FOUR_DIMENSION_CONFIG['recognition']
    word_stats = _build_dimension_word_stats(recognition_rows, 'meaning_correct', 'meaning_wrong')

    qm_items: list[dict] = []
    tracked_keys = {item['word_key'] for item in word_stats}
    evidence_correct = sum(item['correct'] for item in word_stats)
    evidence_wrong = sum(item['wrong'] for item in word_stats)
    due_words = 0
    stable_words = 0
    latest_unknown_words = 0

    for row in qm_rows:
        word = (row.word or '').strip()
        if not word:
            continue
        word_key = word.lower()
        tracked_keys.add(word_key)
        status = (row.status or '').strip().lower()
        known_count = int(row.known_count or 0)
        unknown_count = int(row.unknown_count or 0)
        next_review = int(row.next_review or 0)
        is_due = next_review > 0 and next_review <= now_ms
        if status == 'known':
            evidence_correct += 1
        elif status == 'unknown':
            evidence_wrong += 1
            latest_unknown_words += 1
        if is_due:
            due_words += 1
        if known_count >= len(config['schedule_days']):
            stable_words += 1
        qm_items.append({
            'word': word,
            'word_key': word_key,
            'status': status or 'unknown',
            'known_count': known_count,
            'unknown_count': unknown_count,
            'next_review': next_review,
            'is_due': is_due,
        })

    tracked_words = len(tracked_keys)
    evidence_attempts = evidence_correct + evidence_wrong
    accuracy = round(evidence_correct / evidence_attempts * 100) if evidence_attempts > 0 else None

    due_focus = sorted(
        [item for item in qm_items if item['is_due']],
        key=lambda item: (
            item['next_review'],
            0 if item['status'] == 'unknown' else 1,
            -item['unknown_count'],
        ),
    )
    focus_words = [item['word'] for item in due_focus[:5]]
    if not focus_words:
        focus_words = [item['word'] for item in qm_items if item['status'] == 'unknown'][:5]
    if not focus_words:
        focus_words = _pick_focus_words(word_stats)

    if due_words > 0:
        status = 'due'
    elif tracked_words == 0 and evidence_attempts == 0:
        status = 'not_started'
    elif tracked_words > 0 and stable_words >= tracked_words and (accuracy is None or accuracy >= 90):
        status = 'mastered'
    elif accuracy is not None and accuracy < 78:
        status = 'strengthen'
    else:
        status = 'building'

    if due_words > 0:
        next_action = f"先按认读的 1/3/7/30 天节奏复习 {due_words} 个到期词，要求 1 秒内说出中文义。"
    elif focus_words:
        focus_text = '、'.join(focus_words[:3])
        next_action = f"认读维度先盯住 {focus_text}，用英译中快反重建核心词义通路。"
    else:
        next_action = '认读维度先建立首轮快反词卡，再按 1/3/7/30 天节奏复习。'

    return {
        'key': 'recognition',
        'label': config['label'],
        'definition': config['definition'],
        'schedule_days': config['schedule_days'],
        'schedule_label': _format_schedule_label(config['schedule_days']),
        'mastery_rule': config['mastery_rule'],
        'evidence_label': config['evidence_label'],
        'tracking_level': 'full',
        'tracked': tracked_words > 0,
        'status': status,
        'status_label': DIMENSION_STATUS_LABELS[status],
        'tracked_words': tracked_words,
        'stable_words': stable_words,
        'backlog_words': max(due_words, latest_unknown_words),
        'due_words': due_words,
        'accuracy': accuracy,
        'focus_words': focus_words,
        'next_action': next_action,
        'evidence_note': '当前认读维度优先依据速记复习状态与汉译英（会想）记录判断。',
    }


def _build_practice_dimension(
    *,
    key: str,
    rows,
    correct_attr: str,
    wrong_attr: str,
    stable_threshold: int,
    stable_accuracy: int,
) -> dict:
    config = FOUR_DIMENSION_CONFIG[key]
    word_stats = _build_dimension_word_stats(rows, correct_attr, wrong_attr)
    tracked_words = len(word_stats)
    correct = sum(item['correct'] for item in word_stats)
    wrong = sum(item['wrong'] for item in word_stats)
    attempts = correct + wrong
    accuracy = round(correct / attempts * 100) if attempts > 0 else None
    stable_words = sum(
        1
        for item in word_stats
        if item['attempts'] >= stable_threshold
        and item['accuracy'] is not None
        and item['accuracy'] >= stable_accuracy
    )
    backlog_words = sum(
        1
        for item in word_stats
        if item['wrong'] > 0
        and (item['accuracy'] is None or item['accuracy'] < stable_accuracy)
    )
    focus_words = _pick_focus_words(word_stats)

    if tracked_words == 0:
        status = 'not_started'
    elif tracked_words > 0 and stable_words >= tracked_words and (accuracy is None or accuracy >= stable_accuracy):
        status = 'mastered'
    elif accuracy is not None and (
        accuracy < max(stable_accuracy - 10, 60)
        or backlog_words >= max(3, tracked_words // 2)
    ):
        status = 'strengthen'
    else:
        status = 'building'

    if status == 'not_started':
        next_action = f"{config['label']}维度还没建立稳定记录，先做一轮基础训练，再按 { _format_schedule_label(config['schedule_days']) } 节奏复现。"
    elif focus_words:
        focus_text = '、'.join(focus_words[:3])
        next_action = f"{config['label']}维度先集中处理 {focus_text}，不要平均铺题。"
    else:
        next_action = f"{config['label']}维度继续按 { _format_schedule_label(config['schedule_days']) } 节奏巩固。"

    return {
        'key': key,
        'label': config['label'],
        'definition': config['definition'],
        'schedule_days': config['schedule_days'],
        'schedule_label': _format_schedule_label(config['schedule_days']),
        'mastery_rule': config['mastery_rule'],
        'evidence_label': config['evidence_label'],
        'tracking_level': 'partial',
        'tracked': tracked_words > 0,
        'status': status,
        'status_label': DIMENSION_STATUS_LABELS[status],
        'tracked_words': tracked_words,
        'stable_words': stable_words,
        'backlog_words': backlog_words,
        'due_words': 0,
        'accuracy': accuracy,
        'focus_words': focus_words,
        'next_action': next_action,
        'evidence_note': '当前主要按正确率和错词热度估算，尚未为该维度记录逐词日历节点。',
    }


def _build_timed_practice_dimension(
    *,
    key: str,
    events,
    now_utc: datetime,
    focus_words: list[dict],
    fallback_dimension: dict,
    stable_accuracy: int,
) -> dict:
    if not events:
        return fallback_dimension

    config = FOUR_DIMENSION_CONFIG[key]
    review_intervals = _schedule_intervals(config['schedule_days'])
    word_map: dict[str, dict] = {}

    for event in events:
        word = (event.word or '').strip()
        if not word:
            continue
        payload = event.payload_dict() if hasattr(event, 'payload_dict') else {}
        word_key = word.lower()
        bucket = word_map.setdefault(word_key, {
            'word': word,
            'attempts': 0,
            'correct': 0,
            'wrong': 0,
            'success_days': set(),
            'last_pass_at': None,
        })

        correct = int(event.correct_count or 0)
        wrong = int(event.wrong_count or 0)
        bucket['attempts'] += max(1, correct + wrong)
        bucket['correct'] += correct
        bucket['wrong'] += wrong

        passed = bool(payload.get('passed')) or correct > wrong or (correct > 0 and wrong == 0)
        if passed and event.occurred_at is not None:
            bucket['success_days'].add(event.occurred_at.strftime('%Y-%m-%d'))
            if bucket['last_pass_at'] is None or event.occurred_at > bucket['last_pass_at']:
                bucket['last_pass_at'] = event.occurred_at

    word_stats: list[dict] = []
    for bucket in word_map.values():
        attempts = bucket['attempts']
        accuracy = round(bucket['correct'] / attempts * 100) if attempts > 0 else None
        review_stage = min(len(bucket['success_days']), len(config['schedule_days']))
        due = False
        if 0 < review_stage < len(review_intervals) and bucket['last_pass_at'] is not None:
            due = bucket['last_pass_at'] + timedelta(days=review_intervals[review_stage]) <= now_utc
        word_stats.append({
            'word': bucket['word'],
            'attempts': attempts,
            'correct': bucket['correct'],
            'wrong': bucket['wrong'],
            'review_stage': review_stage,
            'due': due,
            'accuracy': accuracy,
        })

    tracked_words = len(word_stats)
    correct = sum(item['correct'] for item in word_stats)
    wrong = sum(item['wrong'] for item in word_stats)
    attempts = correct + wrong
    accuracy = round(correct / attempts * 100) if attempts > 0 else None
    stable_words = sum(
        1
        for item in word_stats
        if item['review_stage'] >= len(config['schedule_days'])
        and (item['accuracy'] is None or item['accuracy'] >= stable_accuracy)
    )
    due_words = sum(1 for item in word_stats if item['due'])
    backlog_words = sum(
        1
        for item in word_stats
        if item['wrong'] > 0 or item['due'] or item['review_stage'] < 2
    )

    ranked = sorted(
        word_stats,
        key=lambda item: (
            1 if item['due'] else 0,
            item['wrong'],
            0 if item['accuracy'] is None else 100 - item['accuracy'],
            len(config['schedule_days']) - item['review_stage'],
        ),
        reverse=True,
    )
    focus_word_list = [item['word'] for item in ranked[:5]]
    if not focus_word_list:
        focus_word_list = fallback_dimension.get('focus_words') or [item['word'] for item in focus_words[:3] if item.get('word')]

    if due_words > 0:
        status = 'due'
    elif (
        tracked_words > 0
        and stable_words >= tracked_words
        and (accuracy is None or accuracy >= stable_accuracy)
    ):
        status = 'mastered'
    elif (
        (accuracy is not None and accuracy < max(stable_accuracy - 10, 60))
        or backlog_words >= max(2, tracked_words // 2)
    ):
        status = 'strengthen'
    else:
        status = 'building'

    if status == 'due' and focus_word_list:
        focus_text = '、'.join(focus_word_list[:3])
        next_action = f"{config['label']}维度有 {due_words} 个词到了 { _format_schedule_label(config['schedule_days']) } 节点，优先复现 {focus_text}。"
    elif focus_word_list:
        focus_text = '、'.join(focus_word_list[:3])
        next_action = f"{config['label']}维度优先处理 {focus_text}，按 { _format_schedule_label(config['schedule_days']) } 节奏继续复现。"
    else:
        next_action = f"{config['label']}维度继续按 { _format_schedule_label(config['schedule_days']) } 节奏巩固。"

    return {
        'key': key,
        'label': config['label'],
        'definition': config['definition'],
        'schedule_days': config['schedule_days'],
        'schedule_label': _format_schedule_label(config['schedule_days']),
        'mastery_rule': config['mastery_rule'],
        'evidence_label': config['evidence_label'],
        'tracking_level': 'full',
        'tracked': tracked_words > 0,
        'status': status,
        'status_label': DIMENSION_STATUS_LABELS[status],
        'tracked_words': tracked_words,
        'stable_words': stable_words,
        'backlog_words': backlog_words,
        'due_words': due_words,
        'accuracy': accuracy,
        'focus_words': focus_word_list,
        'next_action': next_action,
        'evidence_note': f"当前{config['label']}维度已按逐词事件跟踪复习节点，不再只看累计正确率。",
    }


def _build_speaking_dimension(speaking_events, focus_words: list[dict], now_utc: datetime) -> dict:
    config = FOUR_DIMENSION_CONFIG['speaking']
    review_intervals = _schedule_intervals(config['schedule_days'])
    word_map: dict[str, dict] = {}

    for event in speaking_events:
        payload = event.payload_dict() if hasattr(event, 'payload_dict') else {}
        target_words = _coerce_word_list(payload.get('target_words') or payload.get('words'))
        if event.word:
            target_words = _coerce_word_list([event.word, *target_words])

        if not target_words:
            continue

        response_text = str(payload.get('response_text') or '').strip()
        sentence = str(payload.get('sentence') or '').strip()
        score = int(payload.get('score') or 0)
        passed = bool(payload.get('passed')) or (event.correct_count or 0) > 0 or score >= 80

        for word in target_words:
            word_key = word.lower()
            bucket = word_map.setdefault(word_key, {
                'word': word,
                'attempts': 0,
                'correct': 0,
                'wrong': 0,
                'sentence_uses': 0,
                'simulation_uses': 0,
                'last_pass_at': None,
            })

            if event.event_type == 'pronunciation_check':
                bucket['attempts'] += max(1, (event.correct_count or 0) + (event.wrong_count or 0))
                if passed:
                    bucket['correct'] += 1
                    if bucket['last_pass_at'] is None or (event.occurred_at and event.occurred_at > bucket['last_pass_at']):
                        bucket['last_pass_at'] = event.occurred_at
                else:
                    bucket['wrong'] += 1
                if sentence:
                    bucket['sentence_uses'] += 1
            elif event.event_type == 'speaking_simulation':
                bucket['simulation_uses'] += 1
                if response_text:
                    bucket['sentence_uses'] += 1

    word_stats: list[dict] = []
    for bucket in word_map.values():
        attempts = bucket['attempts']
        accuracy = round(bucket['correct'] / attempts * 100) if attempts > 0 else None
        review_stage = min(bucket['correct'], len(config['schedule_days']))
        sentence_ready = bucket['sentence_uses'] > 0
        due = False
        if 0 < review_stage < len(review_intervals) and bucket['last_pass_at'] is not None:
            due = bucket['last_pass_at'] + timedelta(days=review_intervals[review_stage]) <= now_utc
        word_stats.append({
            'word': bucket['word'],
            'attempts': attempts,
            'correct': bucket['correct'],
            'wrong': bucket['wrong'],
            'sentence_ready': sentence_ready,
            'simulation_uses': bucket['simulation_uses'],
            'review_stage': review_stage,
            'due': due,
            'accuracy': accuracy,
        })

    tracked_words = len(word_stats)
    correct = sum(item['correct'] for item in word_stats)
    wrong = sum(item['wrong'] for item in word_stats)
    attempts = correct + wrong
    accuracy = round(correct / attempts * 100) if attempts > 0 else None
    sentence_ready_words = sum(1 for item in word_stats if item['sentence_ready'])
    stable_words = sum(
        1
        for item in word_stats
        if item['review_stage'] >= len(config['schedule_days']) and item['sentence_ready']
    )
    due_words = sum(1 for item in word_stats if item['due'])
    missing_sentence_words = sum(1 for item in word_stats if not item['sentence_ready'])
    backlog_words = sum(
        1
        for item in word_stats
        if item['wrong'] > 0 or not item['sentence_ready'] or item['review_stage'] < 2
    )

    ranked = sorted(
        word_stats,
        key=lambda item: (
            1 if item['due'] else 0,
            1 if not item['sentence_ready'] else 0,
            item['wrong'],
            0 if item['accuracy'] is None else 100 - item['accuracy'],
            len(config['schedule_days']) - item['review_stage'],
        ),
        reverse=True,
    )
    focus_word_list = [item['word'] for item in ranked[:5]]
    if not focus_word_list:
        focus_word_list = [item['word'] for item in focus_words[:3] if item.get('word')]

    if tracked_words == 0:
        status = 'needs_setup'
    elif due_words > 0:
        status = 'due'
    elif (
        tracked_words > 0
        and stable_words >= tracked_words
        and sentence_ready_words >= tracked_words
        and (accuracy is None or accuracy >= 85)
    ):
        status = 'mastered'
    elif (
        (accuracy is not None and accuracy < 80)
        or missing_sentence_words >= max(2, tracked_words // 2)
        or wrong >= max(2, tracked_words // 2)
    ):
        status = 'strengthen'
    else:
        status = 'building'

    if status == 'needs_setup':
        if focus_word_list:
            focus_text = '、'.join(focus_word_list[:3])
            next_action = f"口语维度还没有有效证据，先拿 {focus_text} 做 1 次发音检查 + 1 句主动造句。"
        else:
            next_action = '口语维度还没有有效证据，先做 5 个词的发音检查 + 主动造句，建立首轮记录。'
    elif status == 'due':
        focus_text = '、'.join(focus_word_list[:3])
        next_action = f"口语维度有 {due_words} 个词到了第1/3/7/15/30天节点，优先复现 {focus_text} 的发音 + 造句。"
    elif missing_sentence_words > 0 and focus_word_list:
        focus_text = '、'.join(focus_word_list[:3])
        next_action = f"口语维度先补 {focus_text} 的造句证据，每个词至少说 1 句完整表达。"
    elif focus_word_list:
        focus_text = '、'.join(focus_word_list[:3])
        next_action = f"口语维度优先处理 {focus_text}，每个词完成 1 次发音检查并口头造句。"
    else:
        next_action = f"口语维度继续按 { _format_schedule_label(config['schedule_days']) } 节奏复现发音和造句。"

    evidence_note = (
        '当前口语维度依据发音检查与带回应的口语模拟事件跟踪，发音通过后仍需补主动造句证据。'
        if tracked_words > 0
        else '当前仓库里还没有口语维度的有效事件，AI 需要主动补发音和造句训练。'
    )

    return {
        'key': 'speaking',
        'label': config['label'],
        'definition': config['definition'],
        'schedule_days': config['schedule_days'],
        'schedule_label': _format_schedule_label(config['schedule_days']),
        'mastery_rule': config['mastery_rule'],
        'evidence_label': config['evidence_label'],
        'tracking_level': 'full' if tracked_words > 0 else 'missing',
        'tracked': tracked_words > 0,
        'status': status,
        'status_label': DIMENSION_STATUS_LABELS[status],
        'tracked_words': tracked_words,
        'stable_words': stable_words,
        'backlog_words': backlog_words,
        'due_words': due_words,
        'accuracy': accuracy,
        'focus_words': focus_word_list,
        'next_action': next_action,
        'evidence_note': evidence_note,
    }


def _build_memory_system(*, smart_rows, wrong_words, focus_words, qm_rows, dimension_events, now_ms: int, now_utc: datetime) -> dict:
    primary_dimension_rows = smart_rows if smart_rows else wrong_words
    listening_fallback = _build_practice_dimension(
        key='listening',
        rows=primary_dimension_rows,
        correct_attr='listening_correct',
        wrong_attr='listening_wrong',
        stable_threshold=5,
        stable_accuracy=85,
    )
    writing_fallback = _build_practice_dimension(
        key='writing',
        rows=primary_dimension_rows,
        correct_attr='dictation_correct',
        wrong_attr='dictation_wrong',
        stable_threshold=5,
        stable_accuracy=90,
    )
    listening_events = [event for event in dimension_events if event.event_type == 'listening_review']
    writing_events = [event for event in dimension_events if event.event_type == 'writing_review']
    speaking_events = [
        event
        for event in dimension_events
        if event.event_type in {'pronunciation_check', 'speaking_simulation'}
    ]
    memory_dimensions = [
        _build_recognition_dimension(primary_dimension_rows, qm_rows, now_ms),
        _build_timed_practice_dimension(
            key='listening',
            events=listening_events,
            now_utc=now_utc,
            focus_words=focus_words,
            fallback_dimension=listening_fallback,
            stable_accuracy=85,
        ),
        _build_speaking_dimension(speaking_events, focus_words, now_utc),
        _build_timed_practice_dimension(
            key='writing',
            events=writing_events,
            now_utc=now_utc,
            focus_words=focus_words,
            fallback_dimension=writing_fallback,
            stable_accuracy=90,
        ),
    ]

    status_rank = {
        'due': 0,
        'strengthen': 1,
        'needs_setup': 2,
        'not_started': 3,
        'building': 4,
        'mastered': 5,
    }
    priority_dimension = sorted(
        memory_dimensions,
        key=lambda item: (
            status_rank.get(item['status'], 99),
            -(item.get('due_words', 0)),
            -(item.get('backlog_words', 0)),
            item.get('accuracy') if item.get('accuracy') is not None else 101,
        ),
    )[0]

    priority_reason_map = {
        'due': f"有 {priority_dimension.get('due_words', 0)} 个到期复习节点",
        'strengthen': '当前正确率和错词热度提示需要优先补弱',
        'needs_setup': '这个维度还没有稳定证据，不能算完全掌握',
        'not_started': '这个维度还没开始系统训练',
        'building': '这个维度还在巩固期，需要继续按节点复现',
        'mastered': '当前阶段最稳定，但仍要保持整词四维均衡',
    }
    speaking_dimension = next(
        (item for item in memory_dimensions if item.get('key') == 'speaking'),
        None,
    )
    speaking_note = (
        '口语维度已开始按发音检查与造句事件跟踪。'
        if speaking_dimension and speaking_dimension.get('tracked')
        else '口语维度还需要补持久化记录。'
    )
    listening_dimension = next((item for item in memory_dimensions if item.get('key') == 'listening'), None)
    writing_dimension = next((item for item in memory_dimensions if item.get('key') == 'writing'), None)
    listening_note = (
        '听力维度已开始按逐词事件跟踪。'
        if listening_dimension and listening_dimension.get('tracking_level') == 'full'
        else '听力维度暂时仍按累计正确率估算。'
    )
    writing_note = (
        '书写维度已开始按逐词事件跟踪。'
        if writing_dimension and writing_dimension.get('tracking_level') == 'full'
        else '书写维度暂时仍按累计正确率估算。'
    )

    return {
        'label': '单词四维度记忆系统',
        'mastery_rule': '认读、听力、口语、书写四个维度全部达标，才算一个单词完全掌握。',
        'tracking_note': f'当前认读维度有较明确的逐词时间证据；{listening_note}{writing_note}{speaking_note}',
        'priority_dimension': priority_dimension['key'],
        'priority_dimension_label': priority_dimension['label'],
        'priority_reason': priority_reason_map.get(priority_dimension['status'], ''),
        'priority_action': priority_dimension.get('next_action'),
        'dimensions': memory_dimensions,
    }


def _build_mode_summary(all_sessions) -> tuple[list[dict], dict | None]:
    mode_map: dict[str, dict] = {}
    for session in all_sessions:
        mode = (session.mode or '').strip()
        if not mode:
            continue
        bucket = mode_map.setdefault(mode, {
            'mode': mode,
            'label': MODE_LABELS.get(mode, mode),
            'correct': 0,
            'wrong': 0,
            'words': 0,
            'sessions': 0,
        })
        bucket['correct'] += session.correct_count or 0
        bucket['wrong'] += session.wrong_count or 0
        bucket['words'] += session.words_studied or 0
        bucket['sessions'] += 1

    modes = []
    weakest_mode = None
    for bucket in mode_map.values():
        attempts = bucket['correct'] + bucket['wrong']
        accuracy = round(bucket['correct'] / attempts * 100) if attempts > 0 else None
        item = {
            **bucket,
            'attempts': attempts,
            'accuracy': accuracy,
        }
        modes.append(item)
        if accuracy is not None and attempts >= 5:
            if weakest_mode is None or accuracy < weakest_mode['accuracy']:
                weakest_mode = item

    modes.sort(key=lambda item: item['words'], reverse=True)
    return modes, weakest_mode


def _build_trend_direction(all_sessions) -> str:
    scored = [
        round((session.correct_count or 0) / max((session.correct_count or 0) + (session.wrong_count or 0), 1) * 100)
        for session in all_sessions
        if (session.correct_count or 0) + (session.wrong_count or 0) > 0
    ]
    if len(scored) < 4:
        return 'stable' if scored else 'new'

    window = min(7, len(scored) // 2)
    newer = scored[-window:]
    older = scored[-window * 2:-window]
    if not older:
        return 'stable'

    avg_newer = sum(newer) / len(newer)
    avg_older = sum(older) / len(older)
    if avg_newer >= avg_older + 5:
        return 'improving'
    if avg_newer <= avg_older - 5:
        return 'declining'
    return 'stable'


def _build_next_actions(
    *,
    memory_system: dict | None,
    weakest_mode: dict | None,
    weak_dimensions: list[dict],
    focus_words: list[dict],
    due_reviews: int,
) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()

    def add_action(text: str | None):
        normalized = (text or '').strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        actions.append(normalized)

    if memory_system:
        add_action(memory_system.get('priority_action'))
        for item in memory_system.get('dimensions') or []:
            if item.get('key') == memory_system.get('priority_dimension'):
                continue
            if item.get('status') in {'due', 'strengthen', 'needs_setup'}:
                add_action(item.get('next_action'))

    if due_reviews > 0:
        add_action(f"优先复习 {due_reviews} 个已到期的速记单词，先清理短期遗忘。")

    if weakest_mode:
        add_action(
            f"下一轮先做 {weakest_mode['label']} 10-15 分钟，优先修复当前最低准确率模式。"
        )

    if weak_dimensions:
        add_action(
            f"围绕 {weak_dimensions[0]['label']} 设计辨析/陷阱题，而不是继续平均铺题。"
        )

    if focus_words:
        focus_word_text = '、'.join(item['word'] for item in focus_words[:3])
        add_action(f"把 {focus_word_text} 放进同组复习，做易混辨析和反向提问。")

    return actions[:4]


def build_learner_profile(user_id: int, target_date: str | None = None) -> dict:
    date_str, start_dt, end_dt = _resolve_target_date(target_date)
    now_utc = utc_now_naive()

    day_sessions = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(
            UserStudySession.started_at >= start_dt,
            UserStudySession.started_at < end_dt,
            UserStudySession.analytics_clause(),
        )
        .order_by(UserStudySession.started_at.asc())
        .all()
    )
    all_sessions = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(
            UserStudySession.started_at < end_dt,
            UserStudySession.analytics_clause(),
        )
        .order_by(UserStudySession.started_at.asc())
        .all()
    )
    smart_rows = UserSmartWordStat.query.filter_by(user_id=user_id).all()
    wrong_words = (
        UserWrongWord.query
        .filter_by(user_id=user_id)
        .order_by(UserWrongWord.wrong_count.desc(), UserWrongWord.updated_at.desc())
        .limit(20)
        .all()
    )
    qm_rows = UserQuickMemoryRecord.query.filter_by(user_id=user_id).all()
    dimension_events = (
        UserLearningEvent.query
        .filter_by(user_id=user_id)
        .filter(
            UserLearningEvent.occurred_at < end_dt,
            UserLearningEvent.event_type.in_((
                'listening_review',
                'writing_review',
                'pronunciation_check',
                'speaking_simulation',
            )),
        )
        .order_by(UserLearningEvent.occurred_at.asc(), UserLearningEvent.id.asc())
        .all()
    )
    notes = (
        UserLearningNote.query
        .filter_by(user_id=user_id)
        .filter(UserLearningNote.created_at < end_dt)
        .order_by(UserLearningNote.created_at.desc())
        .limit(80)
        .all()
    )

    now_ms = utc_naive_to_epoch_ms(now_utc)
    due_reviews = UserQuickMemoryRecord.query.filter_by(user_id=user_id).filter(
        UserQuickMemoryRecord.next_review > 0,
        UserQuickMemoryRecord.next_review <= now_ms,
    ).count()

    today_words = sum(item.words_studied or 0 for item in day_sessions)
    today_correct = sum(item.correct_count or 0 for item in day_sessions)
    today_wrong = sum(item.wrong_count or 0 for item in day_sessions)
    today_attempts = today_correct + today_wrong
    today_accuracy = round(today_correct / today_attempts * 100) if today_attempts > 0 else 0
    today_duration = sum(item.duration_seconds or 0 for item in day_sessions)
    if start_dt <= now_utc < end_dt:
        live_pending = get_live_pending_session_snapshot(
            user_id,
            since=start_dt,
            now=now_utc,
        )
        if live_pending:
            live_session = live_pending['session']
            if live_session.started_at and live_session.started_at < end_dt:
                today_duration += live_pending['elapsed_seconds']

    modes, weakest_mode = _build_mode_summary(all_sessions)
    dimensions = _build_dimension_breakdown(smart_rows, wrong_words)
    focus_words = _build_focus_words(wrong_words)
    memory_system = _build_memory_system(
        smart_rows=smart_rows,
        wrong_words=wrong_words,
        focus_words=focus_words,
        qm_rows=qm_rows,
        dimension_events=dimension_events,
        now_ms=now_ms,
        now_utc=now_utc,
    )
    repeated_topics = build_memory_topics(notes, limit=5, include_singletons=False)
    next_actions = _build_next_actions(
        memory_system=memory_system,
        weakest_mode=weakest_mode,
        weak_dimensions=dimensions,
        focus_words=focus_words,
        due_reviews=due_reviews,
    )
    activity_timeline = build_learning_activity_timeline(user_id, date_str)

    summary = {
        'date': date_str,
        'today_words': today_words,
        'today_accuracy': today_accuracy,
        'today_duration_seconds': today_duration,
        'today_sessions': len(day_sessions),
        'streak_days': _calc_streak_days(user_id, date_str),
        'weakest_mode': weakest_mode['mode'] if weakest_mode else None,
        'weakest_mode_label': weakest_mode['label'] if weakest_mode else None,
        'weakest_mode_accuracy': weakest_mode['accuracy'] if weakest_mode else None,
        'due_reviews': due_reviews,
        'trend_direction': _build_trend_direction(all_sessions),
    }

    return {
        'date': date_str,
        'summary': summary,
        'dimensions': dimensions,
        'focus_words': focus_words,
        'memory_system': memory_system,
        'repeated_topics': repeated_topics,
        'next_actions': next_actions,
        'mode_breakdown': modes,
        'activity_summary': activity_timeline.get('summary') or {},
        'activity_source_breakdown': activity_timeline.get('source_breakdown') or [],
        'activity_event_breakdown': activity_timeline.get('event_breakdown') or [],
        'recent_activity': activity_timeline.get('recent_events') or [],
    }
