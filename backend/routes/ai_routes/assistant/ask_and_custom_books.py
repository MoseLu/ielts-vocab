@ai_bp.route('/ask', methods=['POST'])
@token_required
def ask(current_user: User):
    """
    Chat endpoint — accepts user message + optional learning context.
    Handles tool calls (web search) and returns structured response with options.
    """
    body = request.get_json() or {}
    user_message = body.get('message', '').strip()
    frontend_context = body.get('context', {})  # {currentWord, practiceMode, sessionProgress, ...}

    import logging
    logging.warning(f"[AI] ask from user={current_user.id}: msg='{user_message[:50]}' ctx={frontend_context}")

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    messages = _build_ask_messages(current_user, user_message, frontend_context)
    extra_handlers = _build_ask_extra_handlers(current_user)

    # Run chat with tool calling support — capped at 90 s total to prevent hangs
    try:
        with maybe_timeout(90, RuntimeError('LLM timeout')):
            response = _chat_with_tools(messages, tools=TOOLS, extra_handlers=extra_handlers)

        final_text = response.get("text", str(response))
        options = _parse_options(final_text)
        # Strip [options] blocks from the visible reply text
        clean_reply = _strip_options(final_text)

        _persist_ask_response(current_user, user_message, frontend_context, clean_reply)

        return jsonify({
            'reply': clean_reply,
            'options': options,
        })

    except Exception as e:
        import logging as _log
        _log.error(f"[AI] /ask error for user={current_user.id}: {e}", exc_info=True)
        return jsonify({'error': 'AI 服务暂时不可用，请稍后重试'}), 500


@ai_bp.route('/ask/stream', methods=['POST'])
@token_required
def ask_stream(current_user: User):
    body = request.get_json() or {}
    user_message = body.get('message', '').strip()
    frontend_context = body.get('context', {})

    import logging
    logging.warning(f"[AI] ask/stream from user={current_user.id}: msg='{user_message[:50]}' ctx={frontend_context}")

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    messages = _build_ask_messages(current_user, user_message, frontend_context)
    extra_handlers = _build_ask_extra_handlers(current_user)

    @stream_with_context
    def generate():
        import logging as _log

        raw_reply = ''
        visible_reply = ''
        try:
            yield _encode_sse_event({'type': 'status', 'stage': 'start', 'message': 'AI 正在思考...'})

            with maybe_timeout(90, RuntimeError('LLM timeout')):
                for event in _stream_chat_with_tools(messages, tools=TOOLS, extra_handlers=extra_handlers):
                    event_type = event.get('type')
                    if event_type == 'status':
                        yield _encode_sse_event(event)
                        continue
                    if event_type != 'text_delta':
                        continue

                    raw_reply += str(event.get('text', '') or '')
                    next_visible_reply = _strip_options_for_stream(raw_reply)
                    if next_visible_reply.startswith(visible_reply):
                        visible_delta = next_visible_reply[len(visible_reply):]
                    else:
                        visible_delta = next_visible_reply

                    if visible_delta:
                        visible_reply = next_visible_reply
                        yield _encode_sse_event({'type': 'text', 'delta': visible_delta})

            clean_reply = _strip_options(raw_reply)
            options = _parse_options(raw_reply) or []
            _persist_ask_response(current_user, user_message, frontend_context, clean_reply)

            if options:
                yield _encode_sse_event({'type': 'options', 'options': options})
            yield _encode_sse_event({'type': 'done', 'reply': clean_reply, 'options': options})
        except Exception as exc:
            _log.error(f"[AI] /ask/stream error for user={current_user.id}: {exc}", exc_info=True)
            yield _encode_sse_event({'type': 'error', 'error': 'AI 服务暂时不可用，请稍后重试'})

    response = Response(generate(), mimetype='text/event-stream')
    response.headers['Cache-Control'] = 'no-cache, no-transform'
    response.headers['X-Accel-Buffering'] = 'no'
    response.headers['Connection'] = 'keep-alive'
    return response


# ── POST /api/ai/generate-book ───────────────────────────────────────────────

GENERATE_BOOK_PROMPT = """你是一个 IELTS 词汇专家。用户希望生成一份自定义词汇书，请根据以下信息生成词表。

要求：
1. 返回 JSON 格式，包含 title、description、chapters（数组）、words（数组）
2. 每个 word 必须包含：word（单词）、phonetic（音标，如 /əˈbdev/）、pos（词性，如 n.、v.、adj.）、definition（中文释义）
3. 章节数建议 3-5 章，每章 15-30 个词
4. 词汇要真实存在，是 IELTS 考试常见词汇
5. 不要与用户已掌握的词重复
6. 如果用户指定了 focusAreas（focusAreas），优先选择对应领域的词汇
7. 如果用户指定了 userLevel，按对应难度选词：
   - beginner：大学英语四级水平词汇为主
   - intermediate：六级到雅思核心词汇
   - advanced：雅思高分段学术词汇

输出格式（只需要 JSON，不要其他文字）：
{{
  "title": "词书标题",
  "description": "词书描述（20字内）",
  "chapters": [
    {{ "id": "ch1", "title": "第一章标题", "wordCount": 25 }}
  ],
  "words": [
    {{ "chapterId": "ch1", "word": "abdicate", "phonetic": "/ˈæbdɪkeɪt/", "pos": "v.", "definition": "退位；放弃（职位）" }}
  ]
}}
"""


@ai_bp.route('/generate-book', methods=['POST'])
@token_required
def generate_book(current_user: User):
    """Generate a custom vocabulary book based on user's learning profile."""
    body = request.get_json() or {}
    target_words = body.get('targetWords', 100)
    user_level = body.get('userLevel', 'intermediate')
    focus_areas = body.get('focusAreas', [])
    exclude_words = body.get('excludeWords', [])

    # Build context
    try:
        ctx = _get_context_data(current_user.id)
        wrong_words = ctx.get('wrongWords', [])
        wrong_word_list = [w['word'] for w in wrong_words[:30]]
        all_exclude = list(set(exclude_words + wrong_word_list))
    except Exception:
        all_exclude = exclude_words

    user_message = (
        f"请生成一份约 {target_words} 词的自定义词书。\n"
        f"用户水平：{user_level}\n"
        f"重点领域：{', '.join(focus_areas) if focus_areas else '综合'}"
    )
    if all_exclude:
        user_message += f"\n以下词汇已掌握，请排除：{', '.join(all_exclude[:50])}"

    messages = [
        {"role": "system", "content": GENERATE_BOOK_PROMPT},
        {"role": "user", "content": user_message}
    ]

    try:
        raw = chat(messages, max_tokens=8192)
        raw_text = raw.get('text', '') if isinstance(raw, dict) else str(raw)

        # Parse JSON from response (may be wrapped in markdown code blocks)
        import re
        json_str = re.search(r'\{[\s\S]*\}', raw_text)
        if not json_str:
            return jsonify({'error': 'Failed to parse generated book data'}), 500

        data = json.loads(json_str.group())

        # Persist to DB
        book_id = f"custom_{uuid.uuid4().hex[:12]}"
        book = CustomBook(
            id=book_id,
            user_id=current_user.id,
            title=data.get('title', '自定义词书'),
            description=data.get('description', ''),
            word_count=len(data.get('words', []))
        )
        db.session.add(book)

        chapter_map = {}
        for ch in data.get('chapters', []):
            chapter = CustomBookChapter(
                id=ch.get('id', f"ch_{uuid.uuid4().hex[:6]}"),
                book_id=book_id,
                title=ch.get('title', '未命名章节'),
                word_count=ch.get('wordCount', 0),
                sort_order=data.get('chapters', []).index(ch)
            )
            db.session.add(chapter)
            chapter_map[chapter.id] = chapter

        for w in data.get('words', []):
            word = CustomBookWord(
                chapter_id=w.get('chapterId', list(chapter_map.keys())[0] if chapter_map else 'ch1'),
                word=w.get('word', ''),
                phonetic=w.get('phonetic', ''),
                pos=w.get('pos', ''),
                definition=w.get('definition', '')
            )
            db.session.add(word)

        db.session.commit()

        return jsonify({
            'bookId': book_id,
            'title': book.title,
            'description': book.description,
            'chapters': [c.to_dict() for c in book.chapters],
            'words': [w.to_dict() for w in CustomBookWord.query.filter(
                CustomBookWord.chapter_id.in_([c.id for c in book.chapters])
            ).all()]
        })

    except json.JSONDecodeError as e:
        return jsonify({'error': f'Failed to parse generated book: {str(e)}'}), 500
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': f'Book generation failed: {str(e)}'}), 500


# ── GET /api/ai/custom-books ────────────────────────────────────────────────

@ai_bp.route('/custom-books', methods=['GET'])
@token_required
def list_custom_books(current_user: User):
    """List all AI-generated custom books for the current user."""
    books = CustomBook.query.filter_by(user_id=current_user.id).order_by(
        CustomBook.created_at.desc()
    ).all()
    return jsonify({'books': [b.to_dict() for b in books]})


# ── GET /api/ai/custom-books/<book_id> ───────────────────────────────────────

@ai_bp.route('/custom-books/<book_id>', methods=['GET'])
@token_required
def get_custom_book(current_user: User, book_id: str):
    """Get a single custom book with its chapters and words."""
    book = CustomBook.query.filter_by(id=book_id, user_id=current_user.id).first()
    if not book:
        return jsonify({'error': 'Book not found'}), 404
    return jsonify(book.to_dict())


# ── GET /api/wrong-words ─────────────────────────────────────────────────────

def _normalize_wrong_word_counter(value, default: int = 0) -> int:
    try:
        return max(0, int(value or default))
    except Exception:
        return default


def _clamp_wrong_word_pass_streak(value) -> int:
    return min(_normalize_wrong_word_counter(value), WRONG_WORD_PENDING_REVIEW_TARGET)


def _normalize_wrong_word_iso(value) -> str | None:
    if not isinstance(value, str):
        return None

    text_value = value.strip()
    if not text_value:
        return None

    try:
        return datetime.fromisoformat(text_value.replace('Z', '+00:00')).isoformat()
    except Exception:
        return None


def _pick_later_wrong_word_iso(*values) -> str | None:
    picked = None
    for value in values:
        normalized = _normalize_wrong_word_iso(value)
        if normalized is None:
            continue
        if picked is None or normalized > picked:
            picked = normalized
    return picked


def _build_incoming_wrong_word_dimension_states(payload: dict) -> dict:
    states = {
        dimension: _empty_wrong_word_dimension_state()
        for dimension in WRONG_WORD_DIMENSIONS
    }

    raw_dimension_state = payload.get('dimension_states') or payload.get('dimensionStates')
    if isinstance(raw_dimension_state, str):
        try:
            raw_dimension_state = json.loads(raw_dimension_state)
        except Exception:
            raw_dimension_state = {}
    if not isinstance(raw_dimension_state, dict):
        raw_dimension_state = {}

    for dimension in WRONG_WORD_DIMENSIONS:
        states[dimension] = _normalize_wrong_word_dimension_state(raw_dimension_state.get(dimension))

    recognition_wrong = _normalize_wrong_word_counter(
        payload.get('recognition_wrong', payload.get('recognitionWrong'))
    )
    if recognition_wrong > states['recognition']['history_wrong']:
        states['recognition']['history_wrong'] = recognition_wrong
    states['recognition']['pass_streak'] = max(
        states['recognition']['pass_streak'],
        _clamp_wrong_word_pass_streak(
            payload.get('recognition_pass_streak', payload.get('recognitionPassStreak', payload.get('ebbinghaus_streak', payload.get('ebbinghausStreak'))))
        ),
    )

    for dimension in ('meaning', 'listening', 'dictation'):
        history_wrong = _normalize_wrong_word_counter(
            payload.get(f'{dimension}_wrong', payload.get(f'{dimension}Wrong'))
        )
        if history_wrong > states[dimension]['history_wrong']:
            states[dimension]['history_wrong'] = history_wrong
        states[dimension]['pass_streak'] = max(
            states[dimension]['pass_streak'],
            _clamp_wrong_word_pass_streak(
                payload.get(
                    f'{dimension}_pass_streak',
                    payload.get(
                        f'{dimension}PassStreak',
                        payload.get(f'{dimension}_review_streak', payload.get(f'{dimension}ReviewStreak')),
                    ),
                )
            ),
        )

    fallback_wrong_count = _normalize_wrong_word_counter(
        payload.get('wrong_count', payload.get('wrongCount'))
    )
    total_history_wrong = sum(states[dimension]['history_wrong'] for dimension in WRONG_WORD_DIMENSIONS)
    if fallback_wrong_count > 0 and total_history_wrong == 0:
        states['recognition']['history_wrong'] = fallback_wrong_count
    elif fallback_wrong_count > total_history_wrong:
        states['recognition']['history_wrong'] += fallback_wrong_count - total_history_wrong

    normalized_total = sum(states[dimension]['history_wrong'] for dimension in WRONG_WORD_DIMENSIONS)
    word_value = str(payload.get('word') or '').strip()
    if normalized_total == 0 and word_value:
        # Legacy client snapshots could contain only the word payload itself.
        states['recognition']['history_wrong'] = 1

    return states


def _merge_wrong_word_dimension_states(existing_states: dict, incoming_states: dict) -> dict:
    merged = {}

    for dimension in WRONG_WORD_DIMENSIONS:
        base_state = _normalize_wrong_word_dimension_state(existing_states.get(dimension))
        incoming_state = _normalize_wrong_word_dimension_state(incoming_states.get(dimension))
        latest_wrong_at = _pick_later_wrong_word_iso(
            base_state.get('last_wrong_at'),
            incoming_state.get('last_wrong_at'),
        )
        latest_pass_at = _pick_later_wrong_word_iso(
            base_state.get('last_pass_at'),
            incoming_state.get('last_pass_at'),
        )
        if latest_pass_at and (latest_wrong_at is None or latest_pass_at > latest_wrong_at):
            pass_source = incoming_state if latest_pass_at == incoming_state.get('last_pass_at') else base_state
            pass_streak = _clamp_wrong_word_pass_streak(pass_source.get('pass_streak'))
            if pass_streak <= 0:
                pass_streak = max(
                    _clamp_wrong_word_pass_streak(base_state.get('pass_streak')),
                    _clamp_wrong_word_pass_streak(incoming_state.get('pass_streak')),
                )
        elif latest_wrong_at:
            pass_streak = 0
        else:
            pass_streak = max(
                _clamp_wrong_word_pass_streak(base_state.get('pass_streak')),
                _clamp_wrong_word_pass_streak(incoming_state.get('pass_streak')),
            )

        merged[dimension] = {
            'history_wrong': max(
                _normalize_wrong_word_counter(base_state.get('history_wrong')),
                _normalize_wrong_word_counter(incoming_state.get('history_wrong')),
            ),
            'pass_streak': pass_streak,
            'last_wrong_at': latest_wrong_at,
            'last_pass_at': latest_pass_at,
        }

    return merged


def _max_wrong_word_counter(*values) -> int:
    return max(_normalize_wrong_word_counter(value) for value in values)
