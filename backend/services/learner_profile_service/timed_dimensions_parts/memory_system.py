def _build_memory_system(*, smart_rows, wrong_words, focus_words, qm_rows, dimension_events, now_ms: int, now_utc: datetime) -> dict:
    primary_dimension_rows = smart_rows if smart_rows else wrong_words
    meaning_fallback = _build_practice_dimension(
        key='meaning',
        rows=primary_dimension_rows,
        correct_attr='meaning_correct',
        wrong_attr='meaning_wrong',
        stable_threshold=5,
        stable_accuracy=85,
    )
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
    meaning_events = [event for event in dimension_events if event.event_type == 'meaning_review']
    listening_events = [event for event in dimension_events if event.event_type == 'listening_review']
    writing_events = [event for event in dimension_events if event.event_type == 'writing_review']
    speaking_events = [
        event
        for event in dimension_events
        if event.event_type in {
            'pronunciation_check',
            'speaking_simulation',
            'speaking_assessment_completed',
        }
    ]
    memory_dimensions = [
        _build_recognition_dimension(primary_dimension_rows, qm_rows, now_ms),
        _build_timed_practice_dimension(
            key='meaning',
            events=meaning_events,
            now_utc=now_utc,
            focus_words=focus_words,
            fallback_dimension=meaning_fallback,
            stable_accuracy=85,
        ),
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
        'mastered': '当前阶段最稳定，但仍要保持整词五维均衡',
    }
    speaking_dimension = next(
        (item for item in memory_dimensions if item.get('key') == 'speaking'),
        None,
    )
    speaking_note = (
        '口语维度已开始按发音检查、口语模拟与口语估分事件跟踪。'
        if speaking_dimension and speaking_dimension.get('tracked')
        else '口语维度还需要补持久化记录。'
    )
    meaning_dimension = next((item for item in memory_dimensions if item.get('key') == 'meaning'), None)
    listening_dimension = next((item for item in memory_dimensions if item.get('key') == 'listening'), None)
    writing_dimension = next((item for item in memory_dimensions if item.get('key') == 'writing'), None)
    meaning_note = (
        '释义维度已开始按逐词事件跟踪。'
        if meaning_dimension and meaning_dimension.get('tracking_level') == 'full'
        else '释义维度暂时仍按累计正确率估算。'
    )
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
        'label': '单词五维度记忆系统',
        'mastery_rule': '认读、释义、听力、口语、书写五个维度全部达标，才算一个单词完全掌握。',
        'tracking_note': f'当前认读维度有较明确的逐词时间证据；{meaning_note}{listening_note}{writing_note}{speaking_note}',
        'priority_dimension': priority_dimension['key'],
        'priority_dimension_label': priority_dimension['label'],
        'priority_reason': priority_reason_map.get(priority_dimension['status'], ''),
        'priority_action': priority_dimension.get('next_action'),
        'dimensions': memory_dimensions,
    }
