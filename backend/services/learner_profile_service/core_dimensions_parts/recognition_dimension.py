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
        'evidence_note': '当前认读维度优先依据速记复习状态与释义拼词（会想）记录判断。',
    }
