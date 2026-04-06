@ai_bp.route('/cancel-session', methods=['POST'])
@token_required
def cancel_session(current_user: User):
    """Delete a started session when no meaningful learning interaction happened."""
    body = request.get_json() or {}
    session_id = body.get('sessionId')
    if not session_id:
        return jsonify({'error': 'sessionId is required'}), 400

    session = UserStudySession.query.filter_by(
        id=session_id,
        user_id=current_user.id,
    ).first()
    if not session:
        return jsonify({'error': 'Session not found'}), 404

    has_meaningful_data = any([
        (session.words_studied or 0) > 0,
        (session.correct_count or 0) > 0,
        (session.wrong_count or 0) > 0,
        (session.duration_seconds or 0) > 0,
    ])
    if has_meaningful_data:
        return jsonify({'error': 'Session already contains learning data'}), 409

    db.session.delete(session)
    db.session.commit()
    return jsonify({'deleted': True}), 200


def _normalize_client_duration_seconds(
    raw_duration,
    *,
    started_at: datetime | None = None,
    ended_at: datetime | None = None,
) -> int:
    try:
        duration_seconds = max(0, int(raw_duration or 0))
    except (TypeError, ValueError):
        duration_seconds = 0

    if started_at is not None and ended_at is not None and ended_at >= started_at:
        elapsed_seconds = max(0, int((ended_at - started_at).total_seconds()))
        if duration_seconds <= 0:
            return elapsed_seconds
        if duration_seconds > 86400 and elapsed_seconds <= 86400:
            return elapsed_seconds
        return max(duration_seconds, elapsed_seconds)

    # Broken clients can accidentally send epoch seconds when startedAt is missing.
    return 0 if duration_seconds > 86400 else duration_seconds


@ai_bp.route('/log-session', methods=['POST'])
@token_required
def log_session(current_user: User):
    """Persist a study session record to the database.

    If sessionId is provided the existing session row (created by /start-session) is
    updated and duration_seconds is calculated server-side from started_at → now.
    Otherwise a new row is inserted using the client-supplied durationSeconds.
    """
    body = request.get_json() or {}
    try:
        mode_raw = body.get('mode')
        if isinstance(mode_raw, str):
            mode = mode_raw.strip()[:30] or None
        else:
            mode = None
        book_id = body.get('bookId') or None
        chapter_id = _normalize_chapter_id(body.get('chapterId'))
        session_id = body.get('sessionId')
        client_ended_at = _parse_client_epoch_ms(body.get('endedAt'))
        if session_id:
            # Update the existing session row created by /start-session
            session = UserStudySession.query.filter_by(
                id=session_id, user_id=current_user.id
            ).first()
            if session:
                if session.ended_at is not None and session.has_activity():
                    return jsonify({'id': session.id}), 200

                ended_at = datetime.utcnow()
                if (
                    client_ended_at is not None
                    and session.started_at is not None
                    and client_ended_at >= session.started_at
                    and client_ended_at <= ended_at
                ):
                    ended_at = client_ended_at
                session.ended_at = ended_at
                computed_duration = max(0, int((ended_at - session.started_at).total_seconds()))
                if mode:
                    session.mode = mode
                if book_id is not None:
                    session.book_id = book_id
                if chapter_id is not None:
                    session.chapter_id = chapter_id
                session.words_studied = body.get('wordsStudied', 0)
                session.correct_count = body.get('correctCount', 0)
                session.wrong_count = body.get('wrongCount', 0)
                # Sessions that already contain meaningful study activity should not
                # end up recorded as 0s just because start/end landed in the same second.
                if computed_duration == 0 and (
                    (session.words_studied or 0) > 0 or
                    (session.correct_count or 0) > 0 or
                    (session.wrong_count or 0) > 0
                ):
                    session.duration_seconds = 1
                else:
                    session.duration_seconds = computed_duration
                record_learning_event(
                    user_id=current_user.id,
                    event_type='study_session',
                    source='practice',
                    mode=session.mode,
                    book_id=session.book_id,
                    chapter_id=session.chapter_id,
                    item_count=session.words_studied or 0,
                    correct_count=session.correct_count or 0,
                    wrong_count=session.wrong_count or 0,
                    duration_seconds=session.duration_seconds or 0,
                    occurred_at=session.ended_at or ended_at,
                    payload={
                        'session_id': session.id,
                        'started_at': session.started_at.isoformat() if session.started_at else None,
                        'ended_at': session.ended_at.isoformat() if session.ended_at else None,
                    },
                )
                db.session.commit()
                return jsonify({'id': session.id}), 200

        # Fallback: create a new row using client-supplied timestamps/duration
        started_at = _parse_client_epoch_ms(body.get('startedAt'))

        duration_seconds = _normalize_client_duration_seconds(
            body.get('durationSeconds', 0),
            started_at=started_at,
            ended_at=client_ended_at,
        )
        words_studied = body.get('wordsStudied', 0) or 0
        correct_count = body.get('correctCount', 0) or 0
        wrong_count = body.get('wrongCount', 0) or 0
        if duration_seconds == 0 and (words_studied > 0 or correct_count > 0 or wrong_count > 0):
            duration_seconds = 1

        pending = _find_pending_session(
            user_id=current_user.id,
            mode=mode,
            book_id=book_id,
            chapter_id=chapter_id,
            started_at=started_at,
        )
        if pending:
            pending_end = datetime.utcnow()
            if (
                client_ended_at is not None
                and pending.started_at is not None
                and client_ended_at >= pending.started_at
                and client_ended_at <= pending_end
            ):
                pending_end = client_ended_at
            pending.ended_at = pending_end
            if mode:
                pending.mode = mode
            if book_id is not None:
                pending.book_id = book_id
            if chapter_id is not None:
                pending.chapter_id = chapter_id
            pending.words_studied = words_studied
            pending.correct_count = correct_count
            pending.wrong_count = wrong_count
            computed_duration = max(0, int((pending.ended_at - pending.started_at).total_seconds()))
            pending.duration_seconds = max(duration_seconds, computed_duration)
            if pending.duration_seconds == 0 and pending.has_activity():
                pending.duration_seconds = 1
            record_learning_event(
                user_id=current_user.id,
                event_type='study_session',
                source='practice',
                mode=pending.mode,
                book_id=pending.book_id,
                chapter_id=pending.chapter_id,
                item_count=pending.words_studied or 0,
                correct_count=pending.correct_count or 0,
                wrong_count=pending.wrong_count or 0,
                duration_seconds=pending.duration_seconds or 0,
                occurred_at=pending.ended_at,
                payload={
                    'session_id': pending.id,
                    'started_at': pending.started_at.isoformat() if pending.started_at else None,
                    'ended_at': pending.ended_at.isoformat() if pending.ended_at else None,
                },
            )
            db.session.commit()
            return jsonify({'id': pending.id}), 200

        session = UserStudySession(
            user_id=current_user.id,
            mode=mode,
            book_id=book_id,
            chapter_id=chapter_id,
            words_studied=words_studied,
            correct_count=correct_count,
            wrong_count=wrong_count,
            duration_seconds=duration_seconds,
        )
        if started_at:
            session.started_at = started_at
        if duration_seconds > 0:
            session_end = datetime.utcnow()
            if (
                client_ended_at is not None
                and session.started_at is not None
                and client_ended_at >= session.started_at
                and client_ended_at <= session_end
            ):
                session_end = client_ended_at
            session.ended_at = session_end
        db.session.add(session)
        db.session.flush()
        record_learning_event(
            user_id=current_user.id,
            event_type='study_session',
            source='practice',
            mode=session.mode,
            book_id=session.book_id,
            chapter_id=session.chapter_id,
            item_count=session.words_studied or 0,
            correct_count=session.correct_count or 0,
            wrong_count=session.wrong_count or 0,
            duration_seconds=session.duration_seconds or 0,
            occurred_at=session.ended_at or session.started_at,
            payload={
                'session_id': session.id,
                'started_at': session.started_at.isoformat() if session.started_at else None,
                'ended_at': session.ended_at.isoformat() if session.ended_at else None,
            },
        )
        db.session.commit()
        return jsonify({'id': session.id}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


# ── GET /api/ai/quick-memory ──────────────────────────────────────────────────

@ai_bp.route('/quick-memory', methods=['GET'])
@token_required
def get_quick_memory(current_user: User):
    """Return all quick-memory records for the current user."""
    records = load_user_quick_memory_records(current_user.id)
    return jsonify({'records': [r.to_dict() for r in records]}), 200


# ── GET /api/ai/quick-memory/review-queue ────────────────────────────────────

@ai_bp.route('/quick-memory/review-queue', methods=['GET'])
@token_required
def get_quick_memory_review_queue(current_user: User):
    """Return the user's due/upcoming Ebbinghaus review queue with full word metadata."""
    try:
        raw_limit = int(request.args.get('limit', 20))
    except (TypeError, ValueError):
        raw_limit = 20
    # 0 means no cap — return everything after offset
    limit = raw_limit if raw_limit != 0 else None

    try:
        offset = max(0, int(request.args.get('offset', 0)))
    except (TypeError, ValueError):
        offset = 0

    try:
        within_days = max(1, min(int(request.args.get('within_days', 1)), 30))
    except (TypeError, ValueError):
        within_days = 1

    scope = (request.args.get('scope') or 'window').strip().lower()
    due_only = scope == 'due'

    book_id_filter = (request.args.get('book_id') or '').strip() or None
    chapter_id_filter = _normalize_chapter_id(request.args.get('chapter_id'))

    now_ms = int(time.time() * 1000)
    window_end_ms = now_ms + within_days * 86400000

    pool = _get_global_vocab_pool()
    pool_by_word = {
        (item.get('word') or '').strip().lower(): item
        for item in pool
        if (item.get('word') or '').strip()
    }

    due_words = []
    upcoming_words = []
    context_map: dict[tuple[str, str], dict] = {}

    rows = sorted(
        [row for row in load_user_quick_memory_records(current_user.id) if (row.next_review or 0) > 0],
        key=lambda row: row.next_review or 0,
    )

    for row in rows:
        word_key = (row.word or '').strip().lower()
        stored_book_id = (row.book_id or '').strip() or None
        stored_chapter_id = _normalize_chapter_id(row.chapter_id)
        vocab_item = _resolve_quick_memory_vocab_entry(
            word_key,
            book_id=stored_book_id,
            chapter_id=stored_chapter_id,
        )
        fallback_item = pool_by_word.get(word_key)
        if not vocab_item and not fallback_item:
            continue

        effective_book_id = stored_book_id or (vocab_item or {}).get('book_id')
        effective_chapter_id = stored_chapter_id or _normalize_chapter_id((vocab_item or {}).get('chapter_id'))

        if book_id_filter and effective_book_id != book_id_filter:
            continue
        if chapter_id_filter and effective_chapter_id != chapter_id_filter:
            continue

        next_review = row.next_review or 0
        if next_review <= now_ms:
            due_state = 'due'
        elif next_review <= window_end_ms:
            if due_only:
                continue
            due_state = 'upcoming'
        else:
            continue

        book_title = (vocab_item or {}).get('book_title') or effective_book_id or ''
        chapter_title = (vocab_item or {}).get('chapter_title') or (
            f"第{effective_chapter_id}章" if effective_chapter_id is not None else ''
        )
        item = {
            **(fallback_item or {}),
            **(vocab_item or {}),
            'status': row.status,
            'knownCount': row.known_count or 0,
            'unknownCount': row.unknown_count or 0,
            'nextReview': next_review,
            'dueState': due_state,
            'book_id': effective_book_id,
            'book_title': book_title,
            'chapter_id': effective_chapter_id,
            'chapter_title': chapter_title,
        }
        if due_state == 'due':
            due_words.append(item)
        else:
            upcoming_words.append(item)

        if effective_book_id and effective_chapter_id is not None:
            context_key = (effective_book_id, effective_chapter_id)
            context = context_map.get(context_key)
            if context is None:
                context = {
                    'book_id': effective_book_id,
                    'book_title': book_title,
                    'chapter_id': effective_chapter_id,
                    'chapter_title': chapter_title,
                    'due_count': 0,
                    'upcoming_count': 0,
                    'total_count': 0,
                    'next_review': next_review,
                }
                context_map[context_key] = context

            context['total_count'] += 1
            context['next_review'] = min(context['next_review'], next_review)
            if due_state == 'due':
                context['due_count'] += 1
            else:
                context['upcoming_count'] += 1

    combined_words = due_words + upcoming_words
    selected = combined_words[offset:offset + limit] if limit is not None else combined_words[offset:]
    total_count = len(combined_words)
    next_offset = offset + len(selected)
    has_more = next_offset < total_count
    contexts = sorted(
        context_map.values(),
        key=lambda context: (
            0 if context['due_count'] > 0 else 1,
            context['next_review'],
            context['book_title'],
            context['chapter_title'],
        ),
    )
    selected_context = None
    if book_id_filter and chapter_id_filter is not None:
        selected_context = context_map.get((book_id_filter, chapter_id_filter))
    elif book_id_filter:
        selected_context = next((context for context in contexts if context['book_id'] == book_id_filter), None)
    elif contexts:
        selected_context = contexts[0]

    return jsonify({
        'words': selected,
        'summary': {
            'due_count': len(due_words),
            'upcoming_count': len(upcoming_words),
            'returned_count': len(selected),
            'review_window_days': within_days,
            'offset': offset,
            'limit': limit,
            'total_count': total_count,
            'has_more': has_more,
            'next_offset': next_offset if has_more else None,
            'contexts': contexts,
            'selected_context': selected_context,
        },
    }), 200


# ── POST /api/ai/quick-memory/sync ───────────────────────────────────────────

