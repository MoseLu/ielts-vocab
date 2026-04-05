def _get_summary_job(job_id: str) -> dict | None:
    _prune_summary_jobs()
    with _summary_jobs_lock:
        job = _summary_jobs.get(job_id)
        return dict(job) if job else None


def _update_summary_job(job_id: str, **fields) -> dict | None:
    with _summary_jobs_lock:
        job = _summary_jobs.get(job_id)
        if not job:
            return None
        job.update(fields)
        job['updated_at'] = _utc_now()
        return dict(job)


def _find_running_summary_job(user_id: int, target_date: str) -> dict | None:
    _prune_summary_jobs()
    with _summary_jobs_lock:
        for job in _summary_jobs.values():
            if (
                job['user_id'] == user_id and
                job['date'] == target_date and
                job['status'] in {'queued', 'running'}
            ):
                return dict(job)
    return None


def _create_summary_job(user_id: int, target_date: str) -> dict:
    job = {
        'job_id': uuid.uuid4().hex,
        'user_id': user_id,
        'date': target_date,
        'status': 'queued',
        'progress': 1,
        'message': '准备生成总结...',
        'estimated_chars': 0,
        'generated_chars': 0,
        'summary': None,
        'error': None,
        'created_at': _utc_now(),
        'updated_at': _utc_now(),
    }
    with _summary_jobs_lock:
        _summary_jobs[job['job_id']] = job
    return dict(job)


def _run_summary_job(app, job_id: str, user_id: int, target_date: str) -> None:
    try:
        with app.app_context():
            _update_summary_job(job_id, status='running', progress=8, message='正在收集学习记录...')
            existing = UserDailySummary.query.filter_by(user_id=user_id, date=target_date).first()
            notes, sessions, wrong_words = _collect_summary_source_data(user_id, target_date)
            learning_snapshot = _build_learning_snapshot(user_id, target_date, sessions, wrong_words)
            topic_insights = build_memory_topics(notes, limit=5, include_singletons=True)
            learner_profile = build_learner_profile(user_id, target_date)
            estimated_chars = _estimate_summary_target_chars(notes, sessions, wrong_words)
            _update_summary_job(
                job_id,
                progress=18,
                message='正在整理总结结构...',
                estimated_chars=estimated_chars,
            )

            user_content = _build_summary_prompt(
                target_date,
                notes,
                sessions,
                wrong_words,
                learning_snapshot=learning_snapshot,
                topic_insights=topic_insights,
                learner_profile=learner_profile,
            )
            _update_summary_job(job_id, progress=26, message='AI 正在生成正文...')

            chunks: list[str] = []
            generated_chars = 0
            for chunk in _stream_summary_text(user_content):
                if not chunk:
                    continue
                chunks.append(chunk)
                generated_chars += len(chunk)
                ratio = min(generated_chars / max(estimated_chars, 1), 1.0)
                progress = min(94, 26 + int(ratio * 64))
                _update_summary_job(
                    job_id,
                    progress=progress,
                    message='AI 正在生成正文...',
                    generated_chars=generated_chars,
                )

            summary_content = ''.join(chunks).strip() or _fallback_summary_content(target_date)
            _update_summary_job(
                job_id,
                progress=96,
                message='正在保存总结...',
                generated_chars=max(generated_chars, len(summary_content)),
            )
            saved_summary = _save_summary(existing, user_id, target_date, summary_content)
            _update_summary_job(
                job_id,
                status='completed',
                progress=100,
                message='生成完成',
                generated_chars=max(generated_chars, len(summary_content)),
                summary=saved_summary.to_dict(),
                error=None,
            )
    except Exception as exc:
        logging.exception("[Notes] Summary job failed for user=%s date=%s", user_id, target_date)
        _update_summary_job(
            job_id,
            status='failed',
            message='生成失败，请重试',
            error=str(exc) or '生成失败，请重试',
        )


@notes_bp.route('', methods=['GET'])
@token_required
def get_notes(current_user):
    per_page, err = _parse_int_param(request.args.get('per_page'), default=20, min_val=1, max_val=100)
    if err:
        return jsonify({'error': err}), 400

    before_id_raw = request.args.get('before_id')
    before_id: int | None = None
    if before_id_raw is not None:
        before_id, err = _parse_int_param(before_id_raw, default=0, min_val=1, max_val=2_147_483_647)
        if err:
            return jsonify({'error': f'before_id: {err}'}), 400

    start_date, err = _parse_date_param(request.args.get('start_date'), 'start_date')
    if err:
        return jsonify({'error': err}), 400
    end_date, err = _parse_date_param(request.args.get('end_date'), 'end_date')
    if err:
        return jsonify({'error': err}), 400

    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    filtered_query = UserLearningNote.query.filter_by(user_id=current_user.id)
    if start_date:
        filtered_query = filtered_query.filter(UserLearningNote.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        filtered_query = filtered_query.filter(UserLearningNote.created_at < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))

    memory_source_notes = (
        filtered_query
        .order_by(UserLearningNote.created_at.desc())
        .limit(160)
        .all()
    )
    memory_topics = build_memory_topics(memory_source_notes, limit=8, include_singletons=True)

    query = filtered_query
    if before_id:
        query = query.filter(UserLearningNote.id < before_id)

    total = filtered_query.count()
    notes = query.order_by(UserLearningNote.id.desc()).limit(per_page).all()
    has_more = len(notes) == per_page
    next_cursor = notes[-1].id if has_more else None

    return jsonify({
        'notes': [note.to_dict() for note in notes],
        'memory_topics': memory_topics,
        'total': total,
        'per_page': per_page,
        'next_cursor': next_cursor,
        'has_more': has_more,
    })


@notes_bp.route('/summaries', methods=['GET'])
@token_required
def get_summaries(current_user):
    start_date, err = _parse_date_param(request.args.get('start_date'), 'start_date')
    if err:
        return jsonify({'error': err}), 400
    end_date, err = _parse_date_param(request.args.get('end_date'), 'end_date')
    if err:
        return jsonify({'error': err}), 400

    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    query = UserDailySummary.query.filter_by(user_id=current_user.id)
    if start_date:
        query = query.filter(UserDailySummary.date >= start_date)
    if end_date:
        query = query.filter(UserDailySummary.date <= end_date)

    summaries = query.order_by(UserDailySummary.date.desc()).all()
    return jsonify({'summaries': [summary.to_dict() for summary in summaries]})


@notes_bp.route('/summaries/generate', methods=['POST'])
@token_required
def generate_summary(current_user):
    body = request.get_json() or {}
    target_date = body.get('date', date_type.today().strftime('%Y-%m-%d'))

    target_date, err = _parse_date_param(target_date, 'date')
    if err or not target_date:
        return jsonify({'error': err or '日期格式错误'}), 400
    if target_date > date_type.today().strftime('%Y-%m-%d'):
        return jsonify({'error': '不能为未来日期生成总结'}), 400

    existing, cooldown_response = _check_generate_cooldown(current_user.id, target_date)
    if cooldown_response:
        return cooldown_response

    notes, sessions, wrong_words = _collect_summary_source_data(current_user.id, target_date)
    learning_snapshot = _build_learning_snapshot(current_user.id, target_date, sessions, wrong_words)
    topic_insights = build_memory_topics(notes, limit=5, include_singletons=True)
    learner_profile = build_learner_profile(current_user.id, target_date)
    user_content = _build_summary_prompt(
        target_date,
        notes,
        sessions,
        wrong_words,
        learning_snapshot=learning_snapshot,
        topic_insights=topic_insights,
        learner_profile=learner_profile,
    )

    try:
        messages = [
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ]
        response = chat(messages, max_tokens=2000)
        summary_content = (response or {}).get('text', '').strip() or _fallback_summary_content(target_date)
    except Exception as exc:
        logging.warning("[Notes] LLM summary generation failed for user=%s: %s", current_user.id, exc)
        return jsonify({'error': 'AI 生成失败，请稍后重试'}), 500

    try:
        saved_summary = _save_summary(existing, current_user.id, target_date, summary_content)
        return jsonify({'summary': saved_summary.to_dict()})
    except Exception as exc:
        db.session.rollback()
        logging.error("[Notes] Failed to save summary for user=%s: %s", current_user.id, exc)
        return jsonify({'error': '保存失败，请重试'}), 500


@notes_bp.route('/summaries/generate-jobs', methods=['POST'])
@token_required
def start_generate_summary_job(current_user):
    body = request.get_json() or {}
    target_date = body.get('date', date_type.today().strftime('%Y-%m-%d'))

    target_date, err = _parse_date_param(target_date, 'date')
    if err or not target_date:
        return jsonify({'error': err or '日期格式错误'}), 400
    if target_date > date_type.today().strftime('%Y-%m-%d'):
        return jsonify({'error': '不能为未来日期生成总结'}), 400

    running_job = _find_running_summary_job(current_user.id, target_date)
    if running_job:
        return jsonify(_serialize_summary_job(running_job)), 202

    _existing, cooldown_response = _check_generate_cooldown(current_user.id, target_date)
    if cooldown_response:
        return cooldown_response

    job = _create_summary_job(current_user.id, target_date)
    app = current_app._get_current_object()
    threading.Thread(
        target=_run_summary_job,
        args=(app, job['job_id'], current_user.id, target_date),
        daemon=True,
    ).start()
    return jsonify(_serialize_summary_job(job)), 202


@notes_bp.route('/summaries/generate-jobs/<job_id>', methods=['GET'])
@token_required
def get_generate_summary_job(current_user, job_id: str):
    job = _get_summary_job(job_id)
    if not job or job['user_id'] != current_user.id:
        return jsonify({'error': '任务不存在'}), 404
    return jsonify(_serialize_summary_job(job))


@notes_bp.route('/export', methods=['GET'])
@token_required
def export_notes(current_user):
    start_date, err = _parse_date_param(request.args.get('start_date'), 'start_date')
    if err:
        return jsonify({'error': err}), 400
    end_date, err = _parse_date_param(request.args.get('end_date'), 'end_date')
    if err:
        return jsonify({'error': err}), 400

    if start_date and end_date and start_date > end_date:
        return jsonify({'error': 'start_date 不能晚于 end_date'}), 400

    fmt = request.args.get('format', 'md')
    if fmt not in ('md', 'txt'):
        fmt = 'md'

    export_type = request.args.get('type', 'all')
    if export_type not in ('summaries', 'notes', 'all'):
        export_type = 'all'

    sections: list[str] = []

    if export_type in ('summaries', 'all'):
        query = UserDailySummary.query.filter_by(user_id=current_user.id)
        if start_date:
            query = query.filter(UserDailySummary.date >= start_date)
        if end_date:
            query = query.filter(UserDailySummary.date <= end_date)
        summaries = query.order_by(UserDailySummary.date.asc()).all()

        if summaries:
            sections.append("# 每日学习总结\n")
            for summary in summaries:
                sections.append(f"\n---\n\n{summary.content}\n")

    if export_type in ('notes', 'all'):
        query = UserLearningNote.query.filter_by(user_id=current_user.id)
        if start_date:
            query = query.filter(UserLearningNote.created_at >= datetime.strptime(start_date, '%Y-%m-%d'))
        if end_date:
            query = query.filter(UserLearningNote.created_at < datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1))
        notes = query.order_by(UserLearningNote.created_at.asc()).all()

        if notes:
            sections.append("\n# AI 问答笔记\n")
            current_day = None
            for note in notes:
                day = note.created_at.strftime('%Y-%m-%d') if note.created_at else '未知日期'
                if day != current_day:
                    current_day = day
                    sections.append(f"\n## {day}\n")
                word_info = f"（{note.word_context}）" if note.word_context else ""
                sections.append(f"\n**问：** {note.question}{word_info}\n\n**答：** {note.answer}\n")

    content = '\n'.join(sections) if sections else "暂无数据。"

    if fmt == 'txt':
        content = re.sub(r'#{1,6}\s*', '', content)
        content = re.sub(r'\*{1,2}(.+?)\*{1,2}', r'\1', content)
        content = re.sub(r'\n{3,}', '\n\n', content)

    date_range = f"{start_date or 'all'}_{end_date or 'all'}"
    filename = f"ielts_notes_{date_range}.{'md' if fmt != 'txt' else 'txt'}"

    return jsonify({
        'content': content,
        'filename': filename,
        'format': fmt,
    })
