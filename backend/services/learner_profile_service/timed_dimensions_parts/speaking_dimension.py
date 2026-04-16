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

        response_text = str(payload.get('response_text') or payload.get('transcript_excerpt') or '').strip()
        sentence = str(payload.get('sentence') or '').strip()
        score = int(payload.get('score') or 0)
        overall_band = float(payload.get('overall_band') or 0)
        passed = (
            bool(payload.get('passed'))
            or bool(payload.get('passed_threshold'))
            or (event.correct_count or 0) > 0
            or score >= 80
            or overall_band >= 6
        )

        for word in target_words:
            word_key = word.lower()
            bucket = word_map.setdefault(word_key, {
                'word': word,
                'attempts': 0,
                'correct': 0,
                'wrong': 0,
                'sentence_uses': 0,
                'simulation_uses': 0,
                'assessment_uses': 0,
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
            elif event.event_type == 'speaking_assessment_completed':
                bucket['attempts'] += 1
                bucket['assessment_uses'] += 1
                if passed:
                    bucket['correct'] += 1
                    if bucket['last_pass_at'] is None or (event.occurred_at and event.occurred_at > bucket['last_pass_at']):
                        bucket['last_pass_at'] = event.occurred_at
                else:
                    bucket['wrong'] += 1
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
            'assessment_uses': bucket['assessment_uses'],
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
        '当前口语维度依据发音检查、带回应的口语模拟和口语估分事件跟踪，发音通过后仍需补主动造句证据。'
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
