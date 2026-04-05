def _apply_wrong_word_snapshot(record: UserWrongWord, payload: dict) -> tuple[int, int]:
    previous_states = _build_wrong_word_dimension_states(record)
    previous_summary = _summarize_wrong_word_dimension_states(previous_states)
    incoming_states = _build_incoming_wrong_word_dimension_states(payload)
    merged_states = _merge_wrong_word_dimension_states(previous_states, incoming_states)
    merged_summary = _summarize_wrong_word_dimension_states(merged_states)

    phonetic = payload.get('phonetic')
    pos = payload.get('pos')
    definition = payload.get('definition')
    if isinstance(phonetic, str) and phonetic.strip():
        record.phonetic = phonetic
    if isinstance(pos, str) and pos.strip():
        record.pos = pos
    if isinstance(definition, str) and definition.strip():
        record.definition = definition

    record.wrong_count = merged_summary['wrong_count']
    record.listening_correct = _max_wrong_word_counter(
        record.listening_correct,
        payload.get('listening_correct', payload.get('listeningCorrect')),
    )
    record.meaning_correct = _max_wrong_word_counter(
        record.meaning_correct,
        payload.get('meaning_correct', payload.get('meaningCorrect')),
    )
    record.dictation_correct = _max_wrong_word_counter(
        record.dictation_correct,
        payload.get('dictation_correct', payload.get('dictationCorrect')),
    )
    record.listening_wrong = merged_states['listening']['history_wrong']
    record.meaning_wrong = merged_states['meaning']['history_wrong']
    record.dictation_wrong = merged_states['dictation']['history_wrong']
    record.dimension_state = json.dumps(merged_states, ensure_ascii=False)

    return previous_summary['wrong_count'], merged_summary['wrong_count']


def _clear_wrong_word_pending_states(states: dict) -> dict:
    now_iso = datetime.utcnow().isoformat()
    cleared = {}
    for dimension in WRONG_WORD_DIMENSIONS:
        state = _normalize_wrong_word_dimension_state(states.get(dimension))
        if _normalize_wrong_word_counter(state.get('history_wrong')) > 0:
            cleared[dimension] = {
                **state,
                'pass_streak': WRONG_WORD_PENDING_REVIEW_TARGET,
                'last_pass_at': now_iso,
            }
        else:
            cleared[dimension] = state
    return cleared

@ai_bp.route('/wrong-words', methods=['GET'])
@token_required
def get_wrong_words(current_user: User):
    """Get all wrong words for the current user from the backend."""
    words = UserWrongWord.query.filter_by(user_id=current_user.id)\
        .order_by(UserWrongWord.wrong_count.desc()).all()
    return jsonify({'words': _decorate_wrong_words_with_quick_memory_progress(current_user.id, words)}), 200


# ── POST /api/wrong-words/sync ──────────────────────────────────────────────

@ai_bp.route('/wrong-words/sync', methods=['POST'])
@token_required
def sync_wrong_words(current_user: User):
    """Sync wrong words from client localStorage to backend DB."""
    body = request.get_json() or {}
    words = body.get('words', [])
    source_mode_raw = body.get('sourceMode')
    source_mode = source_mode_raw.strip()[:30] if isinstance(source_mode_raw, str) and source_mode_raw.strip() else None
    book_id = body.get('bookId') or None
    chapter_id = _normalize_chapter_id(body.get('chapterId'))

    if not isinstance(words, list):
        return jsonify({'error': 'words must be an array'}), 400

    updated = 0
    for w in words:
        word_value = str(w.get('word') or '').strip()
        if not word_value:
            continue
        existing = UserWrongWord.query.filter_by(
            user_id=current_user.id,
            word=word_value
        ).first()
        if existing is None:
            existing = UserWrongWord(
                user_id=current_user.id,
                word=word_value,
                phonetic=w.get('phonetic'),
                pos=w.get('pos'),
                definition=w.get('definition'),
                wrong_count=0,
                listening_correct=0,
                listening_wrong=0,
                meaning_correct=0,
                meaning_wrong=0,
                dictation_correct=0,
                dictation_wrong=0,
            )
            db.session.add(existing)

        previous_wrong_count, current_wrong_count = _apply_wrong_word_snapshot(existing, w)
        wrong_delta = max(0, current_wrong_count - previous_wrong_count)
        if source_mode and wrong_delta > 0:
            record_learning_event(
                user_id=current_user.id,
                event_type='wrong_word_recorded',
                source='wrong_words',
                mode=source_mode,
                book_id=book_id,
                chapter_id=chapter_id,
                word=existing.word,
                item_count=1,
                wrong_count=wrong_delta,
                payload={
                    'wrong_count': current_wrong_count,
                    'definition': existing.definition or '',
                    'dimension_states': json.loads(existing.dimension_state or '{}'),
                },
            )
        updated += 1

    db.session.commit()
    return jsonify({'updated': updated})


@ai_bp.route('/wrong-words/<word>', methods=['DELETE'])
@token_required
def delete_wrong_word(current_user: User, word: str):
    """Clear pending status for a wrong word without deleting its history."""
    record = UserWrongWord.query.filter_by(user_id=current_user.id, word=word).first()
    if record:
        cleared_states = _clear_wrong_word_pending_states(_build_wrong_word_dimension_states(record))
        summary = _summarize_wrong_word_dimension_states(cleared_states)
        record.wrong_count = summary['wrong_count']
        record.listening_wrong = cleared_states['listening']['history_wrong']
        record.meaning_wrong = cleared_states['meaning']['history_wrong']
        record.dictation_wrong = cleared_states['dictation']['history_wrong']
        record.dimension_state = json.dumps(cleared_states, ensure_ascii=False)
        db.session.commit()
    return jsonify({'message': '已移出未过错词'}), 200


@ai_bp.route('/wrong-words', methods=['DELETE'])
@token_required
def clear_wrong_words(current_user: User):
    """Clear pending wrong-word state for all words without deleting history."""
    records = UserWrongWord.query.filter_by(user_id=current_user.id).all()
    for record in records:
        cleared_states = _clear_wrong_word_pending_states(_build_wrong_word_dimension_states(record))
        summary = _summarize_wrong_word_dimension_states(cleared_states)
        record.wrong_count = summary['wrong_count']
        record.listening_wrong = cleared_states['listening']['history_wrong']
        record.meaning_wrong = cleared_states['meaning']['history_wrong']
        record.dictation_wrong = cleared_states['dictation']['history_wrong']
        record.dimension_state = json.dumps(cleared_states, ensure_ascii=False)
    db.session.commit()
    return jsonify({'message': '已清空未过错词'}), 200


# ── POST /api/ai/log-session ─────────────────────────────────────────────────

