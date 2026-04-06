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
