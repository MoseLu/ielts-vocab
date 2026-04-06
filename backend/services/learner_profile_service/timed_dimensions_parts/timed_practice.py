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
