def _save_turn(user_id: int, user_message: str, assistant_reply: str):
    """Persist a user+assistant turn to DB, and prune records older than 90 days."""
    from datetime import timedelta
    import logging
    try:
        db.session.add(UserConversationHistory(
            user_id=user_id, role='user', content=user_message
        ))
        db.session.add(UserConversationHistory(
            user_id=user_id, role='assistant', content=assistant_reply
        ))
        # Prune old history rows (>90 days) to cap table growth
        cutoff = datetime.utcnow() - timedelta(days=_HISTORY_PRUNE_DAYS)
        UserConversationHistory.query.filter(
            UserConversationHistory.user_id == user_id,
            UserConversationHistory.created_at < cutoff,
        ).delete(synchronize_session=False)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        logging.warning(f"[AI] Failed to save conversation turn: {e}")


# ── User memory helpers ───────────────────────────────────────────────────────

def _get_or_create_memory(user_id: int) -> 'UserMemory':
    """Return the UserMemory row for this user, creating it if absent.
    Uses INSERT OR IGNORE to avoid UNIQUE constraint races under concurrency."""
    from sqlalchemy.exc import IntegrityError
    mem = UserMemory.query.filter_by(user_id=user_id).first()
    if not mem:
        try:
            mem = UserMemory(user_id=user_id)
            db.session.add(mem)
            db.session.flush()
        except IntegrityError:
            # Another request created it concurrently — rollback and re-fetch
            db.session.rollback()
            mem = UserMemory.query.filter_by(user_id=user_id).first()
    return mem


def _load_memory(user_id: int) -> dict:
    """Return serialisable memory dict for context injection."""
    mem = UserMemory.query.filter_by(user_id=user_id).first()
    if not mem:
        return {}
    return {
        'goals': mem.get_goals(),
        'ai_notes': mem.get_ai_notes(),
        'conversation_summary': mem.conversation_summary or '',
    }


def _add_memory_note(user_id: int, note: str, category: str) -> str:
    """Append an AI-written note to UserMemory.ai_notes. Returns confirmation."""
    from datetime import datetime as _dt
    try:
        mem = _get_or_create_memory(user_id)
        notes = mem.get_ai_notes()
        # Avoid exact duplicates
        if not any(n.get('note') == note for n in notes):
            notes.append({
                'category': category,
                'note': note,
                'created_at': _dt.utcnow().strftime('%Y-%m-%d'),
            })
            # Keep last 30 notes to avoid unbounded growth
            mem.set_ai_notes(notes[-30:])
        db.session.commit()
        return f"已记录：[{category}] {note}"
    except Exception as e:
        db.session.rollback()
        import logging
        logging.warning(f"[AI] Failed to save memory note: {e}")
        return f"记录失败：{e}"


# Threshold: when total turns exceed this, compress the oldest chunk
_SUMMARIZE_THRESHOLD = 40   # total turns before triggering compression
_SUMMARIZE_CHUNK = 20       # how many old turns to compress each time


def _maybe_summarize_history(user_id: int):
    """If conversation history is long, compress old turns into UserMemory.conversation_summary."""
    with current_app.app_context():
        total = UserConversationHistory.query.filter_by(user_id=user_id).count()
        mem = UserMemory.query.filter_by(user_id=user_id).first()
        already_summarized = mem.summary_turn_count if mem else 0

        unsummarized = total - already_summarized
        if unsummarized <= _SUMMARIZE_THRESHOLD:
            return  # Not enough new turns yet

        # Fetch the oldest un-summarized chunk
        old_rows = (
            UserConversationHistory.query
            .filter_by(user_id=user_id)
            .order_by(UserConversationHistory.created_at.asc())
            .offset(already_summarized)
            .limit(_SUMMARIZE_CHUNK)
            .all()
        )
        if not old_rows:
            return

        # Build a conversation snippet for the LLM to summarize
        snippet = '\n'.join(
            f"{'用户' if r.role == 'user' else 'AI'}：{r.content[:300]}"
            for r in old_rows
        )
        existing_summary = mem.conversation_summary if mem else ''

        summary_prompt = [
            {"role": "system", "content": (
                "你是一个摘要助手，请将以下对话压缩为一段简洁的中文摘要（100-200字），"
                "重点保留：用户的学习目标、偏好、困难、AI给出的重要建议和用户的关键反应。"
                "不要编造内容，只提炼对话中已有的信息。"
            )},
            {"role": "user", "content": (
                (f"【已有摘要】\n{existing_summary}\n\n" if existing_summary else '') +
                f"【新增对话（{len(old_rows)}条）】\n{snippet}\n\n"
                "请输出更新后的完整摘要："
            )},
        ]
        try:
            resp = chat(summary_prompt, max_tokens=400)
            new_summary = resp.get('text', '').strip()
            if new_summary:
                mem = _get_or_create_memory(user_id)
                mem.conversation_summary = new_summary
                mem.summary_turn_count = already_summarized + len(old_rows)
                db.session.commit()
        except Exception as e:
            import logging
            logging.warning(f"[AI] Summarization failed for user={user_id}: {e}")


# ── Per-request tool handlers (need user_id, built inside ask()) ──────────────

def _make_get_wrong_words(user_id: int):
    def handler(limit: int = 100, book_id: str | None = None) -> str:
        limit = min(int(limit), 300)
        q = UserWrongWord.query.filter_by(user_id=user_id)
        words = q.order_by(UserWrongWord.wrong_count.desc()).limit(limit).all()
        if not words:
            return "暂无错词记录。"
        decorated = _decorate_wrong_words_with_quick_memory_progress(user_id, words)
        prefix = ''
        if book_id:
            prefix = "当前错词记录暂不支持按词书过滤，以下返回全部错词。\n"
        lines = [
            (
                f"{w['word']}（{w.get('phonetic') or ''}，{w.get('pos') or ''}）"
                f"{w.get('definition') or ''}  错误{w.get('wrong_count', 0)}次"
                f"  艾宾浩斯{w.get('ebbinghaus_streak', 0)}/{w.get('ebbinghaus_target', _QUICK_MEMORY_MASTERY_TARGET)}"
            )
            for w in decorated
        ]
        return prefix + f"共{len(lines)}个错词：\n" + "\n".join(lines)
    return handler


def _make_get_chapter_words(user_id: int):
    def handler(book_id: str, chapter_id: int) -> str:
        from routes.books import load_book_vocabulary, VOCAB_BOOKS
        book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
        if not book:
            return f"找不到词书 '{book_id}'，请检查 book_id 是否正确。"
        vocab = load_book_vocabulary(book_id)
        if not vocab:
            return f"词书 '{book['title']}' 的单词数据加载失败。"
        chapter_words = [w for w in vocab if w.get('chapter_id') == chapter_id]
        if not chapter_words:
            return f"词书 '{book['title']}' 中找不到第{chapter_id}章，或该章无单词。"
        chapter_title = chapter_words[0].get('chapter_title', f'第{chapter_id}章')
        lines = [
            f"{w['word']}  {w.get('phonetic', '')}  [{w.get('pos', '')}]  {w.get('definition', '')}"
            for w in chapter_words
        ]
        return f"{book['title']} — {chapter_title}（共{len(lines)}词）：\n" + "\n".join(lines)
    return handler


def _make_get_book_chapters(user_id: int):
    def handler(book_id: str) -> str:
        from routes.books import load_book_chapters, VOCAB_BOOKS
        book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
        if not book:
            return f"找不到词书 '{book_id}'，请检查 book_id 是否正确。"
        structure = load_book_chapters(book_id)
        if not structure:
            return f"词书 '{book['title']}' 的章节数据加载失败。"
        # Fetch user chapter progress for this book
        ch_progress = {
            str(cp.chapter_id): cp
            for cp in UserChapterProgress.query.filter_by(user_id=user_id, book_id=book_id).all()
        }
        lines = []
        for ch in structure.get('chapters', []):
            cid = str(ch.get('id', ''))
            cp = ch_progress.get(cid)
            if cp:
                total = cp.correct_count + cp.wrong_count
                acc = round(cp.correct_count / total * 100) if total > 0 else 0
                status = f"已完成 正确率{acc}%" if cp.is_completed else f"进行中 已答{total}题 正确率{acc}%"
            else:
                status = "未开始"
            lines.append(f"  第{ch['id']}章《{ch.get('title', '')}》 {ch.get('word_count', '?')}词 — {status}")
        total_w = structure.get('total_words', 0)
        total_c = structure.get('total_chapters', len(lines))
        done_c = sum(1 for cp in ch_progress.values() if cp.is_completed)
        return (
            f"{book['title']}（共{total_c}章、{total_w}词，已完成{done_c}章）：\n"
            + "\n".join(lines)
        )
    return handler


def _build_ask_messages(current_user: User, user_message: str, frontend_context: dict) -> list[dict]:
    import logging

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    try:
        ctx_data = _get_context_data(current_user.id)
        context_msg = _build_learning_context_msg(ctx_data, frontend_context)
        messages.append({"role": "user", "content": f"[学习数据]\n{context_msg}"})
    except Exception as exc:
        logging.warning(f"[AI] Failed to fetch user context: {exc}")
        messages.append({"role": "user", "content": "[学习数据]\n数据加载失败，请根据用户当前状态回复。"})
        if frontend_context:
            ctx_str = _build_context_msg(frontend_context)
            messages.append({"role": "user", "content": f"[当前学习状态]\n{ctx_str}"})

    messages.extend(_load_history(current_user.id))

    related_notes_msg = _build_related_notes_msg(
        _collect_related_learning_notes(current_user.id, user_message, frontend_context)
    )
    if related_notes_msg:
        messages.append({"role": "user", "content": related_notes_msg})

    search_trigger_keywords = ['例句', '例 子', 'example', '怎么 用', '用法', '这个词', '这个词的', '这个单词']
    needs_search = any(keyword in user_message for keyword in search_trigger_keywords)

    if needs_search and frontend_context.get('currentWord'):
        word = frontend_context['currentWord']
        search_query = f"{word} example sentences IELTS context"
        try:
            search_results = web_search(search_query)
            messages.append({"role": "user", "content": (
                f"[网页搜索结果 for '{word}']\n{search_results}\n\n"
                "请根据搜索结果，为用户解释这个单词的用法并给出例句。"
            )})
        except Exception:
            messages.append({"role": "user", "content": user_message})
    else:
        messages.append({"role": "user", "content": user_message})

    return messages


def _build_ask_extra_handlers(current_user: User) -> dict[str, callable]:
    def _handle_remember(note: str, category: str = 'other') -> str:
        return _add_memory_note(current_user.id, note, category)

    return {
        'remember_user_note': _handle_remember,
        'get_wrong_words': _make_get_wrong_words(current_user.id),
        'get_chapter_words': _make_get_chapter_words(current_user.id),
        'get_book_chapters': _make_get_book_chapters(current_user.id),
    }


def _persist_ask_response(current_user: User, user_message: str, frontend_context: dict, clean_reply: str) -> None:
    import logging

    _save_turn(current_user.id, user_message, clean_reply)

    try:
        word_ctx = frontend_context.get('currentWord') if frontend_context else None
        note = UserLearningNote(
            user_id=current_user.id,
            question=user_message,
            answer=clean_reply,
            word_context=word_ctx,
        )
        db.session.add(note)
        record_learning_event(
            user_id=current_user.id,
            event_type='assistant_question',
            source='assistant',
            mode=(frontend_context.get('practiceMode') if isinstance(frontend_context, dict) else None),
            word=word_ctx,
            payload={
                'question': user_message[:500],
                'answer_excerpt': clean_reply[:500],
            },
        )
        db.session.commit()
    except Exception as note_err:
        db.session.rollback()
        logging.warning(f"[AI] Failed to save learning note: {note_err}")

    try:
        spawn_background(_maybe_summarize_history, current_user.id)
    except Exception:
        pass


def _strip_options_for_stream(text: str) -> str:
    stripped = re.sub(r'\[options\][\s\S]*?\[/options\]\s*', '', text)
    open_tag_index = stripped.find('[options]')
    if open_tag_index >= 0:
        stripped = stripped[:open_tag_index]
    return stripped.rstrip()


def _encode_sse_event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _build_tool_status_message(tool_name: str, tool_input: dict | None = None) -> str:
    safe_input = tool_input if isinstance(tool_input, dict) else {}

    if tool_name == 'web_search':
        return 'AI 正在检索相关资料...'

    if tool_name == 'remember_user_note':
        category = str(safe_input.get('category', '') or '').strip()
        if category == 'goal':
            return 'AI 正在记录你的学习目标...'
        if category == 'habit':
            return 'AI 正在记录你的学习习惯...'
        if category == 'weakness':
            return 'AI 正在记录你的薄弱点...'
        if category == 'preference':
            return 'AI 正在记录你的学习偏好...'
        if category == 'achievement':
            return 'AI 正在记录你的学习进展...'
        return 'AI 正在记录你的学习信息...'

    if tool_name == 'get_wrong_words':
        return 'AI 正在分析你的错词记录...'

    if tool_name == 'get_chapter_words':
        chapter_id = safe_input.get('chapter_id')
        if chapter_id not in (None, ''):
            return f'AI 正在读取第 {chapter_id} 章词表...'
        return 'AI 正在读取章节词表...'

    if tool_name == 'get_book_chapters':
        return 'AI 正在读取词书章节结构...'

    return 'AI 正在处理学习数据...'


def _stream_chat_with_tools(
    messages: list[dict],
    *,
    tools: list | None = None,
    max_iterations: int = 5,
    extra_handlers: dict | None = None,
):
    import logging as _log

    handlers = {**TOOL_HANDLERS, **(extra_handlers or {})}

    for i in range(max_iterations):
        tool_called = False
        for event in stream_chat_events(messages, tools=tools, max_tokens=4096):
            event_type = event.get('type')
            if event_type == 'text_delta':
                yield {'type': 'text_delta', 'text': str(event.get('text', '') or '')}
                continue
            if event_type != 'tool_call':
                continue

            tool_called = True
            tool_name = str(event.get('tool', '') or '')
            raw_input = event.get('input', {})
            tool_call_id = str(event.get('tool_call_id', f"call_{i}") or f"call_{i}")
            handler = handlers.get(tool_name)
            tool_input = _validate_tool_input(tool_name, raw_input) if isinstance(raw_input, dict) else None

            if handler and tool_input is not None:
                status_message = _build_tool_status_message(tool_name, tool_input)
                yield {'type': 'status', 'stage': 'tool', 'tool': tool_name, 'message': status_message}
                try:
                    result = handler(**tool_input)
                except Exception as exc:
                    result = f"Tool error: {exc}"

                messages.append({
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": tool_call_id,
                        "name": tool_name,
                        "input": tool_input
                    }]
                })
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": result
                    }]
                })
            elif handler and tool_input is None:
                _log.warning(f"[AI] Tool '{tool_name}' input validation failed: {raw_input!r}")
                messages.append({
                    "role": "assistant",
                    "content": f"[Tool '{tool_name}' input validation failed]"
                })
            else:
                messages.append({
                    "role": "assistant",
                    "content": f"[Tool '{tool_name}' not available]"
                })

        if not tool_called:
            return

    yield {'type': 'text_delta', 'text': '[对话轮次过多，已停止]'}


