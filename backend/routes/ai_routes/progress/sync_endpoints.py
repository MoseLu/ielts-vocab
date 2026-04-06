@ai_bp.route('/quick-memory/sync', methods=['POST'])
@token_required
def sync_quick_memory(current_user: User):
    """Bulk upsert quick-memory records. Accepts {records: [{word, status, firstSeen, lastSeen, knownCount, unknownCount, nextReview}]}."""
    body = request.get_json() or {}
    records_in = body.get('records', [])
    source_raw = body.get('source')
    source = source_raw.strip()[:50] if isinstance(source_raw, str) and source_raw.strip() else None
    if not isinstance(records_in, list):
        return jsonify({'error': 'records must be a list'}), 400

    for r in records_in:
        word = (r.get('word') or '').strip().lower()
        if not word:
            continue
        record_book_id = (r.get('bookId') or r.get('book_id') or '').strip() or None
        record_chapter_id = _normalize_chapter_id(r.get('chapterId', r.get('chapter_id')))
        try:
            record_last_seen = max(0, int(r.get('lastSeen', 0) or 0))
        except (TypeError, ValueError):
            record_last_seen = 0
        try:
            record_known_count = max(0, int(r.get('knownCount', 0) or 0))
        except (TypeError, ValueError):
            record_known_count = 0
        canonical_next_review = resolve_quick_memory_next_review_ms(
            record_known_count,
            record_last_seen,
            r.get('nextReview', 0),
        )
        existing = UserQuickMemoryRecord.query.filter_by(
            user_id=current_user.id, word=word
        ).first()
        previous_snapshot = None
        if existing:
            previous_snapshot = {
                'status': existing.status,
                'book_id': existing.book_id,
                'chapter_id': _normalize_chapter_id(existing.chapter_id),
                'last_seen': existing.last_seen or 0,
                'known_count': existing.known_count or 0,
                'unknown_count': existing.unknown_count or 0,
                'next_review': existing.next_review or 0,
                'fuzzy_count': existing.fuzzy_count or 0,
            }
        if existing:
            # Only overwrite if client data is newer (lastSeen is epoch ms)
            if (r.get('lastSeen') or 0) >= (existing.last_seen or 0):
                if record_book_id is not None:
                    existing.book_id = record_book_id
                if record_chapter_id is not None:
                    existing.chapter_id = record_chapter_id
                existing.status        = r.get('status', existing.status)
                existing.first_seen    = r.get('firstSeen', existing.first_seen)
                existing.last_seen     = record_last_seen if record_last_seen is not None else existing.last_seen
                existing.known_count   = record_known_count if record_known_count is not None else existing.known_count
                existing.unknown_count = r.get('unknownCount', existing.unknown_count)
                existing.next_review   = canonical_next_review
                # fuzzy_count: take the max so it never decreases
                if r.get('fuzzyCount') is not None:
                    existing.fuzzy_count = max(existing.fuzzy_count or 0, r['fuzzyCount'])
        else:
            new_rec = UserQuickMemoryRecord(
                user_id=current_user.id,
                word=word,
                book_id=record_book_id,
                chapter_id=record_chapter_id,
                status=r.get('status', 'unknown'),
                first_seen=r.get('firstSeen', 0),
                last_seen=record_last_seen,
                known_count=record_known_count,
                unknown_count=r.get('unknownCount', 0),
                next_review=canonical_next_review,
                fuzzy_count=r.get('fuzzyCount', 0),
            )
            db.session.add(new_rec)
            existing = new_rec

        if source:
            current_snapshot = {
                'status': existing.status,
                'book_id': existing.book_id,
                'chapter_id': _normalize_chapter_id(existing.chapter_id),
                'last_seen': existing.last_seen or 0,
                'known_count': existing.known_count or 0,
                'unknown_count': existing.unknown_count or 0,
                'next_review': existing.next_review or 0,
                'fuzzy_count': existing.fuzzy_count or 0,
            }
            if previous_snapshot != current_snapshot:
                status = current_snapshot['status']
                record_learning_event(
                    user_id=current_user.id,
                    event_type='quick_memory_review',
                    source=source,
                    mode='quickmemory',
                    book_id=current_snapshot['book_id'],
                    chapter_id=current_snapshot['chapter_id'],
                    word=word,
                    item_count=1,
                    correct_count=1 if status == 'known' else 0,
                    wrong_count=1 if status == 'unknown' else 0,
                    payload={
                        'status': status,
                        'known_count': current_snapshot['known_count'],
                        'unknown_count': current_snapshot['unknown_count'],
                        'next_review': current_snapshot['next_review'],
                        'fuzzy_count': current_snapshot['fuzzy_count'],
                    },
                )

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({'ok': True}), 200


# ── GET /api/ai/smart-stats ───────────────────────────────────────────────────

@ai_bp.route('/smart-stats', methods=['GET'])
@token_required
def get_smart_stats(current_user: User):
    """Return all smart-mode word stats for the current user."""
    stats = UserSmartWordStat.query.filter_by(user_id=current_user.id).all()
    return jsonify({'stats': [s.to_dict() for s in stats]}), 200


# ── POST /api/ai/smart-stats/sync ─────────────────────────────────────────────

@ai_bp.route('/smart-stats/sync', methods=['POST'])
@token_required
def sync_smart_stats(current_user: User):
    """Bulk upsert smart-mode word stats. Accepts {stats: [{word, listening, meaning, dictation}]}."""
    body = request.get_json() or {}
    stats_in = body.get('stats', [])
    context = body.get('context') or {}
    if not isinstance(stats_in, list):
        return jsonify({'error': 'stats must be a list'}), 400

    record_book_id = (context.get('bookId') or context.get('book_id') or '').strip() or None if isinstance(context, dict) else None
    record_chapter_id = _normalize_chapter_id(context.get('chapterId', context.get('chapter_id'))) if isinstance(context, dict) else None
    source_mode = (context.get('mode') or '').strip() or None if isinstance(context, dict) else None

    for s in stats_in:
        word = (s.get('word') or '').strip().lower()
        if not word:
            continue
        listening = s.get('listening') or {}
        meaning   = s.get('meaning')   or {}
        dictation = s.get('dictation') or {}

        existing = UserSmartWordStat.query.filter_by(
            user_id=current_user.id, word=word
        ).first()
        previous_listening_correct = int(existing.listening_correct or 0) if existing else 0
        previous_listening_wrong = int(existing.listening_wrong or 0) if existing else 0
        previous_dictation_correct = int(existing.dictation_correct or 0) if existing else 0
        previous_dictation_wrong = int(existing.dictation_wrong or 0) if existing else 0

        listening_correct = int(listening.get('correct', previous_listening_correct) or 0)
        listening_wrong = int(listening.get('wrong', previous_listening_wrong) or 0)
        meaning_correct = int(meaning.get('correct', int(existing.meaning_correct or 0) if existing else 0) or 0)
        meaning_wrong = int(meaning.get('wrong', int(existing.meaning_wrong or 0) if existing else 0) or 0)
        dictation_correct = int(dictation.get('correct', previous_dictation_correct) or 0)
        dictation_wrong = int(dictation.get('wrong', previous_dictation_wrong) or 0)

        if existing:
            existing.listening_correct = listening_correct
            existing.listening_wrong   = listening_wrong
            existing.meaning_correct   = meaning_correct
            existing.meaning_wrong     = meaning_wrong
            existing.dictation_correct = dictation_correct
            existing.dictation_wrong   = dictation_wrong
        else:
            new_stat = UserSmartWordStat(
                user_id=current_user.id,
                word=word,
                listening_correct=listening_correct,
                listening_wrong=listening_wrong,
                meaning_correct=meaning_correct,
                meaning_wrong=meaning_wrong,
                dictation_correct=dictation_correct,
                dictation_wrong=dictation_wrong,
            )
            db.session.add(new_stat)

        _record_smart_dimension_delta_event(
            user_id=current_user.id,
            event_type='listening_review',
            mode='listening',
            word=word,
            book_id=record_book_id,
            chapter_id=record_chapter_id,
            source_mode=source_mode,
            previous_correct=previous_listening_correct,
            previous_wrong=previous_listening_wrong,
            current_correct=listening_correct,
            current_wrong=listening_wrong,
        )
        _record_smart_dimension_delta_event(
            user_id=current_user.id,
            event_type='writing_review',
            mode='dictation',
            word=word,
            book_id=record_book_id,
            chapter_id=record_chapter_id,
            source_mode=source_mode,
            previous_correct=previous_dictation_correct,
            previous_wrong=previous_dictation_wrong,
            current_correct=dictation_correct,
            current_wrong=dictation_wrong,
        )

    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({'ok': True}), 200
