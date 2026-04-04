def _build_greet_fallback(current_user: User, ctx_data: dict | None = None) -> str:
    """Return a stable local greeting when the AI provider is unavailable."""
    name = (getattr(current_user, 'username', None) or '同学').strip() or '同学'
    ctx_data = ctx_data or {}

    total_learned = int(ctx_data.get('totalLearned') or 0)
    accuracy_rate = ctx_data.get('accuracyRate')
    wrong_words = ctx_data.get('wrongWords') or []
    recent_sessions = ctx_data.get('recentSessions') or []
    learner_profile = ctx_data.get('learnerProfile') or {}
    dimensions = learner_profile.get('dimensions') or []
    focus_words = learner_profile.get('focus_words') or []
    memory_system = learner_profile.get('memory_system') or {}
    repeated_topics = learner_profile.get('repeated_topics') or []
    next_actions = learner_profile.get('next_actions') or []

    if total_learned <= 0 and not recent_sessions and not repeated_topics and not focus_words and not dimensions:
        return f"你好，{name}！我是雅思小助手。你可以告诉我今天想学哪本词书，或者直接开始一章练习。"

    parts = [f"你好，{name}！我是雅思小助手。"]

    if repeated_topics:
        topic = repeated_topics[0] or {}
        topic_title = str(topic.get('title') or '').strip()
        topic_count = int(topic.get('count') or 0)
        if topic_title:
            repeat_text = f"这个点你已经反复问过 {topic_count} 次" if topic_count > 1 else "这个点你最近又问到了"
            parts.append(f"我注意到你最近在“{topic_title}”上有些卡住，{repeat_text}，这次我可以换个更容易抓住差别的讲法。")
    elif focus_words:
        focus_text = '、'.join(item.get('word', '') for item in focus_words[:3] if item.get('word'))
        if focus_text:
            parts.append(f"你这阶段的重点突破词主要集中在 {focus_text}，我可以顺着这些词继续帮你拆开辨析。")

    if total_learned > 0:
        summary = f"你已经累计学习了 {total_learned} 个词"
        if isinstance(accuracy_rate, (int, float)):
            summary += f"，整体正确率约 {int(accuracy_rate)}%"
        parts.append(summary + "。")

    priority_dimension_label = str(memory_system.get('priority_dimension_label') or '').strip()
    priority_reason = str(memory_system.get('priority_reason') or '').strip()
    if priority_dimension_label:
        reason_suffix = f"，原因是{priority_reason}" if priority_reason else ''
        parts.append(f"按四维记忆节奏，你现在最该先补的是“{priority_dimension_label}”{reason_suffix}。")
    elif dimensions:
        dimension = dimensions[0] or {}
        label = str(dimension.get('label') or dimension.get('dimension') or '').strip()
        accuracy = dimension.get('accuracy')
        if label:
            accuracy_suffix = f"，目前准确率大约 {int(accuracy)}%" if isinstance(accuracy, (int, float)) else ''
            parts.append(f"当前最值得优先补的是“{label}”{accuracy_suffix}。")
    elif wrong_words:
        focus_text = '、'.join(w.get('word', '') for w in wrong_words[:3] if w.get('word'))
        if focus_text:
            parts.append(f"近期可以优先复习：{focus_text}。")

    speaking_state = next(
        (item for item in (memory_system.get('dimensions') or []) if item.get('key') == 'speaking'),
        None,
    )
    if speaking_state and speaking_state.get('status') == 'needs_setup':
        parts.append("另外，口语维度目前还没有稳定记录，后面要补一轮跟读和造句。")

    if next_actions:
        first_action = str(next_actions[0]).strip()
        if first_action:
            parts.append(f"如果你愿意，我们可以先从“{first_action}”开始。")
    elif recent_sessions:
        latest = recent_sessions[0]
        book_title = latest.get('book_title') or latest.get('book_id') or '当前词书'
        chapter_id = latest.get('chapter_id')
        chapter_label = f"第{chapter_id}章" if chapter_id else '当前章节'
        parts.append(f"如果你愿意，我可以继续围绕 {book_title} {chapter_label} 帮你安排复习。")
    else:
        parts.append("如果你愿意，我可以根据你最近的学习情况帮你安排下一步复习。")

    return ''.join(parts)


@ai_bp.route('/greet', methods=['POST'])
@token_required
def greet(current_user: User):
    """
    Personalized greeting — called when user opens the AI chat panel.
    Returns a greeting based on the user's real learning progress.
    """
    body = request.get_json(silent=True) or {}
    frontend_context = body.get('context') or {}

    messages = [{"role": "system", "content": GREET_SYSTEM_PROMPT_V2}]

    ctx_data = {}
    try:
        ctx_data = _get_context_data(current_user.id)
        context_msg = _build_learning_context_msg(ctx_data, frontend_context)
        messages.append({
            "role": "user",
            "content": (
                "补充要求：如果画像已经显示明显弱点、重复困惑主题或重点突破词，优先围绕这些点自然开场。"
                "不要默认输出选项；只有当下一步动作非常明确时，才补 1-2 个简短选项。"
            ),
        })
        messages.append({"role": "user", "content": f"[学习数据]\n{context_msg}\n\n请根据以上数据，生成一条个性化的问候。"})
    except Exception as e:
        import logging
        logging.warning(f"[AI] greet context load failed for user={current_user.id}: {e}")
        messages.append({
            "role": "user",
            "content": "补充要求：默认自然开场，不要默认输出选项。",
        })
        messages.append({"role": "user", "content": "请生成一条欢迎问候语，用户可能刚开始学习。"})

    try:
        response = _chat_with_tools(messages, tools=None)
        final_text = response.get("text", str(response))
        options = _parse_options(final_text) or []
        clean_reply = _strip_options(final_text).strip()
        # Save greeting as the opening assistant turn so /ask can reference it
        _save_turn(current_user.id, '[用户打开了AI助手]', clean_reply)
        return jsonify({'reply': clean_reply, 'options': options})
    except Exception as e:
        import logging
        logging.warning(f"[AI] greet failed for user={current_user.id}: {e}")
        fallback_reply = _build_greet_fallback(current_user, ctx_data)
        _save_turn(current_user.id, '[用户打开了AI助手]', fallback_reply)
        return jsonify({'reply': fallback_reply, 'options': []}), 200


# ── Feature APIs (PRD Phase 1-4) ─────────────────────────────────────────────

@ai_bp.route('/correct-text', methods=['POST'])
@token_required
def correct_text_api(current_user: User):
    body = request.get_json() or {}
    text_in = (body.get('text') or '').strip()
    if not text_in:
        return jsonify({
            'is_valid_english': False,
            'message': '请输入英文句子（建议 1-50 词）。',
        }), 200
    if len(text_in.split()) > 80:
        return jsonify({'error': '句子过长，请控制在 80 词内'}), 400

    result = correct_text(text_in)
    _track_metric(current_user.id, 'writing_correction_used', {'length': len(text_in.split())})
    return jsonify(result), 200


@ai_bp.route('/correction-feedback', methods=['POST'])
@token_required
def correction_feedback(current_user: User):
    body = request.get_json() or {}
    adopted = bool(body.get('adopted'))
    _track_metric(current_user.id, 'writing_correction_adoption', {'adopted': adopted})
    return jsonify({'ok': True}), 200


@ai_bp.route('/ielts-example', methods=['GET'])
@token_required
def ielts_example(current_user: User):
    word = (request.args.get('word') or '').strip().lower()
    if not word:
        return jsonify({'error': 'word is required'}), 400

    corpus = _load_json_data('ielts-reading-corpus.json', {})
    topic_map = _load_json_data('ielts-topics.json', {})
    items = corpus.get(word, [])
    if items:
        _track_metric(current_user.id, 'ielts_example_hit', {'word': word, 'count': len(items)})
        return jsonify({'word': word, 'source': 'ielts-corpus', 'examples': items[:5]}), 200

    # 降级：web_search
    summary = web_search(f"{word} IELTS reading sentence examples")
    fallback = [{
        'sentence': summary.split('\n')[0][:220],
        'source': 'web_search',
        'topic': topic_map.get(word, 'general'),
        'is_real_exam': False,
    }]
    _track_metric(current_user.id, 'ielts_example_fallback', {'word': word})
    return jsonify({'word': word, 'source': 'fallback', 'examples': fallback}), 200


@ai_bp.route('/synonyms-diff', methods=['POST'])
@token_required
def synonyms_diff(current_user: User):
    body = request.get_json() or {}
    a = (body.get('a') or '').strip()
    b = (body.get('b') or '').strip()
    if not a or not b:
        return jsonify({'error': 'a and b are required'}), 400
    result = differentiate_synonyms(a, b)
    _track_metric(current_user.id, 'synonyms_diff_used', {'pair': f'{a}-{b}'})
    return jsonify(result), 200


@ai_bp.route('/word-family', methods=['GET'])
@token_required
def word_family(current_user: User):
    word = (request.args.get('word') or '').strip().lower()
    if not word:
        return jsonify({'error': 'word is required'}), 400
    db_json = _load_json_data('word-families.json', {})
    data = db_json.get(word)
    if not data:
        return jsonify({
            'word': word,
            'message': '暂未收录该词族，建议查询实义词（如 establish / analyze / regulate）。',
        }), 200
    _track_metric(current_user.id, 'word_family_used', {'word': word})
    return jsonify(data), 200


@ai_bp.route('/word-family/quiz', methods=['GET'])
@token_required
def word_family_quiz(current_user: User):
    word = (request.args.get('word') or '').strip().lower()
    db_json = _load_json_data('word-families.json', {})
    data = db_json.get(word, {})
    variants = data.get('variants', [])
    if len(variants) < 2:
        return jsonify({'error': 'not enough variants'}), 400
    picked = random.choice(variants)
    others = [v.get('word') for v in variants if v.get('word') and v.get('word') != picked.get('word')]
    return jsonify({
        'prompt': f"请说出与 {picked.get('word')} 同词族的另外两个词",
        'answer_candidates': others[:4],
        'analysis': f"{picked.get('word')} 属于 {word} 词族，注意词性转换。",
    }), 200


@ai_bp.route('/collocations/practice', methods=['GET'])
@token_required
def collocation_practice(current_user: User):
    topic = (request.args.get('topic') or 'general').strip().lower()
    mode = (request.args.get('mode') or 'mcq').strip().lower()
    count = min(max(int(request.args.get('count', 5)), 1), 20)
    pool = _load_json_data('ielts-collocations.json', [])
    filtered = [x for x in pool if x.get('topic', 'general') in (topic, 'general')] or pool
    random.shuffle(filtered)
    _track_metric(current_user.id, 'collocation_practice_used', {'topic': topic, 'mode': mode, 'count': count})
    return jsonify({'topic': topic, 'mode': mode, 'items': filtered[:count]}), 200


@ai_bp.route('/pronunciation-check', methods=['POST'])
@token_required
def pronunciation_check(current_user: User):
    body = request.get_json() or {}
    word = (body.get('word') or '').strip()
    transcript = (body.get('transcript') or '').strip()
    sentence = (body.get('sentence') or '').strip()
    book_id = (body.get('bookId') or '').strip() or None
    chapter_id = _normalize_chapter_id(body.get('chapterId'))
    if not word:
        return jsonify({'error': 'word is required'}), 400
    # 规则兜底：后续可接 MiniMax 语音识别
    score = 85 if transcript.lower() == word.lower() else 65
    passed = score >= 80
    result = {
        'word': word,
        'score': score,
        'passed': passed,
        'stress_feedback': '重音位置基本正确，建议再拉长重读音节。',
        'vowel_feedback': '元音饱满度中等，可再放慢语速。',
        'speed_feedback': '语速可接受，注意词尾清晰度。',
    }
    try:
        record_learning_event(
            user_id=current_user.id,
            event_type='pronunciation_check',
            source='assistant',
            mode='speaking',
            book_id=book_id,
            chapter_id=chapter_id,
            word=word,
            item_count=1,
            correct_count=1 if passed else 0,
            wrong_count=0 if passed else 1,
            payload={
                'score': score,
                'passed': passed,
                'transcript': transcript[:160],
                'sentence': sentence[:300] if sentence else None,
            },
        )
        db.session.commit()
    except Exception as event_err:
        db.session.rollback()
        import logging
        logging.warning(f"[AI] Failed to record pronunciation check: {event_err}")
    _track_metric(current_user.id, 'pronunciation_check_used', {'word': word, 'score': score})
    return jsonify(result), 200


@ai_bp.route('/speaking-simulate', methods=['POST'])
@token_required
def speaking_simulate(current_user: User):
    body = request.get_json() or {}
    part = int(body.get('part', 1))
    topic = (body.get('topic') or 'education').strip()
    target_words = _normalize_word_list(
        body.get('targetWords')
        or body.get('target_words')
        or body.get('words')
        or body.get('word')
    )
    response_text = (body.get('responseText') or body.get('response_text') or body.get('transcript') or '').strip()
    book_id = (body.get('bookId') or '').strip() or None
    chapter_id = _normalize_chapter_id(body.get('chapterId'))
    qmap = {
        1: f"Part 1: Do you enjoy learning vocabulary about {topic}?",
        2: f"Part 2: Describe a time when {topic} vocabulary helped your IELTS performance.",
        3: f"Part 3: How can schools improve students' {topic} related lexical resources?",
    }
    question = qmap.get(part, qmap[1])
    try:
        record_learning_event(
            user_id=current_user.id,
            event_type='speaking_simulation',
            source='assistant',
            mode='speaking',
            book_id=book_id,
            chapter_id=chapter_id,
            word=target_words[0] if len(target_words) == 1 else None,
            item_count=max(1, len(target_words)),
            correct_count=1 if response_text else 0,
            wrong_count=0,
            payload={
                'part': part,
                'topic': topic,
                'question': question,
                'target_words': target_words,
                'response_text': response_text[:500] if response_text else None,
            },
        )
        db.session.commit()
    except Exception as event_err:
        db.session.rollback()
        import logging
        logging.warning(f"[AI] Failed to record speaking simulation: {event_err}")
    _track_metric(current_user.id, 'speaking_simulation_used', {'part': part, 'topic': topic})
    return jsonify({
        'part': part,
        'topic': topic,
        'question': question,
        'follow_ups': ['请给出一个具体例子。', '能否用更学术的表达重述？'],
    }), 200


@ai_bp.route('/review-plan', methods=['GET'])
@token_required
def review_plan(current_user: User):
    profile = build_learner_profile(current_user.id)
    memory_system = profile.get('memory_system') or {}
    dimensions = memory_system.get('dimensions') or []
    plan = profile.get('next_actions') or []

    if not plan:
        plan = ['先补当前优先维度 10 分钟，再安排错词辨析和巩固复现。']

    wrong_count = UserWrongWord.query.filter_by(user_id=current_user.id).count()
    level = 'four-dimensional'

    response = {
        'level': level,
        'wrong_words': wrong_count,
        'mastery_rule': memory_system.get('mastery_rule'),
        'priority_dimension': memory_system.get('priority_dimension_label'),
        'priority_reason': memory_system.get('priority_reason'),
        'plan': plan[:4],
        'dimensions': [
            {
                'key': item.get('key'),
                'label': item.get('label'),
                'status': item.get('status'),
                'status_label': item.get('status_label'),
                'schedule_label': item.get('schedule_label'),
                'next_action': item.get('next_action'),
            }
            for item in dimensions
        ],
    }
    _track_metric(
        current_user.id,
        'adaptive_plan_generated',
        {
            'level': level,
            'priority_dimension': memory_system.get('priority_dimension'),
        },
    )
    return jsonify(response), 200


@ai_bp.route('/vocab-assessment', methods=['GET'])
@token_required
def vocab_assessment(current_user: User):
    count = min(max(int(request.args.get('count', 20)), 5), 50)
    pool = _get_global_vocab_pool()
    random.shuffle(pool)
    questions = []
    for w in pool[:count]:
        questions.append({
            'word': w.get('word'),
            'definition': w.get('definition'),
            'pos': w.get('pos'),
        })
    _track_metric(current_user.id, 'vocab_assessment_generated', {'count': count})
    return jsonify({'count': len(questions), 'questions': questions}), 200


# ── Conversation history helpers ──────────────────────────────────────────────

_HISTORY_LIMIT = 20  # max past turns to include in context


def _load_history(user_id: int) -> list[dict]:
    """Load last N conversation turns from DB as LLM-ready message dicts."""
    rows = (
        UserConversationHistory.query
        .filter_by(user_id=user_id)
        .order_by(UserConversationHistory.created_at.desc())
        .limit(_HISTORY_LIMIT)
        .all()
    )
    # Reverse so oldest first
    return [{"role": r.role, "content": r.content} for r in reversed(rows)]


_HISTORY_PRUNE_DAYS = 90   # delete conversation records older than this
