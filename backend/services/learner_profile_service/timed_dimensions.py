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
