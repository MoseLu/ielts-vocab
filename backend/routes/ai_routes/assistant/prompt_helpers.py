def _build_context_msg(ctx: dict) -> str:
    """Build a readable context string from learning context dict."""
    parts = []
    dimension_labels = {
        'listening': '听音辨义',
        'meaning': '汉译英（会想）',
        'dictation': '拼写默写',
    }

    # Book / chapter info
    if ctx.get('currentChapterTitle'):
        parts.append(f"当前章节：{ctx['currentChapterTitle']}")
    elif ctx.get('currentChapter'):
        parts.append(f"当前章节 ID：{ctx['currentChapter']}")
    if ctx.get('currentBook'):
        parts.append(f"当前词书 ID：{ctx['currentBook']}")

    if ctx.get('practiceMode'):
        parts.append(f"练习模式：{ctx['practiceMode']}")
    if ctx.get('mode'):
        parts.append(f"学习类型：{ctx['mode']}")

    # Session progress
    session_progress = ctx.get('sessionProgress')
    total_words = ctx.get('totalWords')
    words_completed = ctx.get('wordsCompleted')
    session_completed = ctx.get('sessionCompleted')

    if session_completed:
        parts.append(f"本轮练习：已完成全部 {total_words} 个单词")
        if words_completed is not None:
            parts.append(f"本轮答题数：{words_completed} 个")
    elif session_progress is not None:
        if total_words:
            parts.append(f"本次进度：{session_progress} / {total_words} 个词")
        else:
            parts.append(f"本次进度：{session_progress} 个词")
        if words_completed is not None:
            parts.append(f"本次已答题：{words_completed} 个")

    if ctx.get('sessionAccuracy') is not None:
        parts.append(f"本次准确率：{ctx['sessionAccuracy']}%")

    # Current word being studied (only when mid-session)
    if ctx.get('currentWord') and not session_completed:
        parts.append(f"当前单词：{ctx['currentWord']}")
        if ctx.get('currentPhonetic'):
            parts.append(f"  音标：{ctx['currentPhonetic']}")
        if ctx.get('currentPos'):
            parts.append(f"  词性：{ctx['currentPos']}")
        if ctx.get('currentDefinition'):
            parts.append(f"  释义：{ctx['currentDefinition']}")

    current_focus_dimension = ctx.get('currentFocusDimension')
    if current_focus_dimension:
        parts.append(
            f"当前训练焦点：{dimension_labels.get(current_focus_dimension, current_focus_dimension)}"
        )

    weak_dimension_order = ctx.get('weakDimensionOrder')
    if isinstance(weak_dimension_order, list) and weak_dimension_order:
        labels = [
            dimension_labels.get(str(item), str(item))
            for item in weak_dimension_order[:3]
            if item
        ]
        if labels:
            parts.append(f"当前薄弱维度：{'、'.join(labels)}")
    elif ctx.get('weakestDimension'):
        weakest_dimension = ctx.get('weakestDimension')
        parts.append(
            f"当前最弱维度：{dimension_labels.get(weakest_dimension, weakest_dimension)}"
        )

    weak_focus_words = ctx.get('weakFocusWords')
    if isinstance(weak_focus_words, list) and weak_focus_words:
        parts.append(f"当前重点薄弱词：{'、'.join(str(item) for item in weak_focus_words[:5])}")

    recent_wrong_words = ctx.get('recentWrongWords')
    if isinstance(recent_wrong_words, list) and recent_wrong_words:
        parts.append(f"近期易错词：{'、'.join(str(item) for item in recent_wrong_words[:5])}")

    trap_strategy = ctx.get('trapStrategy')
    if trap_strategy:
        parts.append(f"当前出题策略：{trap_strategy}")

    priority_distractor_words = ctx.get('priorityDistractorWords')
    if isinstance(priority_distractor_words, list) and priority_distractor_words:
        parts.append(f"当前高优先干扰词：{'、'.join(str(item) for item in priority_distractor_words[:5])}")

    quick_memory_summary = ctx.get('quickMemorySummary')
    if quick_memory_summary and isinstance(quick_memory_summary, dict):
        known = quick_memory_summary.get('known')
        unknown = quick_memory_summary.get('unknown')
        due_today = quick_memory_summary.get('dueToday')
        summary_bits = []
        if isinstance(known, (int, float)):
            summary_bits.append(f"已认识 {int(known)}")
        if isinstance(unknown, (int, float)):
            summary_bits.append(f"待巩固 {int(unknown)}")
        if isinstance(due_today, (int, float)):
            summary_bits.append(f"今日到期待复习 {int(due_today)}")
        if summary_bits:
            parts.append("速记画像：" + '，'.join(summary_bits))

    mode_performance = ctx.get('modePerformance')
    if mode_performance and isinstance(mode_performance, dict):
        mode_labels = {
            'smart': '智能练习',
            'listening': '听音选义',
            'meaning': '汉译英',
            'dictation': '听写',
            'radio': '随身听',
            'quickmemory': '速记',
            'errors': '错词强化',
        }
        mode_summary = []
        for mode_key, stats in mode_performance.items():
            if not isinstance(stats, dict):
                continue
            correct = int(stats.get('correct') or 0)
            wrong = int(stats.get('wrong') or 0)
            attempts = correct + wrong
            if attempts <= 0:
                continue
            accuracy = round(correct / attempts * 100)
            label = mode_labels.get(str(mode_key), str(mode_key))
            mode_summary.append(f"{label} {accuracy}%（{attempts} 次）")
        if mode_summary:
            parts.append("本地模式表现：" + '、'.join(mode_summary[:4]))

    # Local historical summary (from localStorage)
    local = ctx.get('localHistory')
    if local and isinstance(local, dict):
        completed = local.get('chaptersCompleted', 0)
        attempted = local.get('chaptersAttempted', 0)
        accuracy = local.get('overallAccuracy', 0)
        correct = local.get('totalCorrect', 0)
        wrong = local.get('totalWrong', 0)
        if attempted > 0:
            parts.append(
                f"历史记录（本地）：已尝试 {attempted} 个章节，完成 {completed} 个，"
                f"累计答题 {correct + wrong} 次，准确率 {accuracy}%"
            )

    # Per-book breakdown from localStorage (richer than aggregate localHistory)
    local_book = ctx.get('localBookProgress')
    if local_book and isinstance(local_book, dict):
        from routes.books import VOCAB_BOOKS
        book_title_map = {b['id']: b['title'] for b in VOCAB_BOOKS}
        book_word_count_map = {b['id']: b.get('word_count', 0) for b in VOCAB_BOOKS}
        parts.append("本地各词书进度：")
        for book_id, stats in local_book.items():
            title = book_title_map.get(book_id, book_id)
            word_count = book_word_count_map.get(book_id, 0)
            ch_done = stats.get('chaptersCompleted', 0)
            ch_tried = stats.get('chaptersAttempted', 0)
            correct = stats.get('correct', 0)
            wrong = stats.get('wrong', 0)
            words_learned = stats.get('wordsLearned', 0)
            total = correct + wrong
            acc = round(correct / total * 100) if total > 0 else 0
            wc_str = f"（共{word_count}词）" if word_count else ""
            parts.append(
                f"  - {title}{wc_str}：已完成{ch_done}/{ch_tried}章，"
                f"已答{words_learned}词，正确率{acc}%"
            )

    return '\n'.join(parts) if parts else '暂无'


def _strip_options(text: str) -> str:
    """Remove [options]...[/options] blocks from text."""
    import re
    return re.sub(r'\[options\][\s\S]*?\[/options\]\s*', '', text).strip()


def _parse_options(text: str) -> list[str] | None:
    """Extract [options] blocks from text. Returns list of options or None."""
    import re
    pattern = r'\[options\]\s*([\s\S]*?)\s*\[/options\]'
    matches = re.findall(pattern, text)
    if not matches:
        return None
    # Extract individual lines
    options = []
    for block in matches:
        for line in block.strip().split('\n'):
            line = line.strip()
            if line and re.match(r'^[A-Z]\.', line):
                options.append(line)
    return options if options else None


_QUERY_STOPWORDS = {
    'the', 'and', 'for', 'with', 'that', 'this', 'have', 'what', 'when', 'where',
    'which', 'from', 'into', 'your', 'about', 'please', 'could', 'would', 'should',
    'kind',  # kept via currentWord / phrase overlap when relevant
}


def _extract_query_tokens(text: str) -> set[str]:
    english = {
        token.lower()
        for token in re.findall(r"[A-Za-z][A-Za-z'-]{1,}", text or '')
        if token.lower() not in _QUERY_STOPWORDS
    }
    chinese = {
        chunk
        for chunk in re.findall(r'[\u4e00-\u9fff]{2,}', text or '')
        if len(chunk.strip()) >= 2
    }
    return english | chinese


def _normalize_question_signature(text: str) -> str:
    lowered = (text or '').lower()
    lowered = re.sub(r'[^a-z0-9\u4e00-\u9fff]+', ' ', lowered)
    return re.sub(r'\s+', ' ', lowered).strip()


def _collect_related_learning_notes(
    user_id: int,
    user_message: str,
    frontend_context: dict | None = None,
    limit: int = 3,
) -> dict | None:
    query_tokens = _extract_query_tokens(user_message)
    normalized_message = _normalize_question_signature(user_message)
    current_word = ((frontend_context or {}).get('currentWord') or '').strip().lower()

    recent_notes = (
        UserLearningNote.query
        .filter_by(user_id=user_id)
        .order_by(UserLearningNote.created_at.desc())
        .limit(80)
        .all()
    )
    if not recent_notes:
        return None

    topic_matches: list[dict] = []
    memory_topics = build_memory_topics(
        recent_notes,
        limit=12,
        include_singletons=True,
        related_note_limit=max(limit + 2, 4),
    )
    for topic in memory_topics:
        related_notes = topic.get('related_notes') or []
        topic_text = ' '.join([
            str(topic.get('title') or ''),
            ' '.join(str(item.get('question') or '') for item in related_notes),
        ]).strip()
        topic_signature = _normalize_question_signature(topic_text)
        topic_tokens = _extract_query_tokens(topic_text)
        overlap = query_tokens & topic_tokens
        topic_word = str(topic.get('word_context') or '').strip().lower()

        score = len(overlap) * 2
        if current_word and topic_word == current_word:
            score += 4
        if topic_signature and normalized_message and (
            topic_signature in normalized_message or normalized_message in topic_signature
        ):
            score += 4
        if current_word and current_word in topic_signature:
            score += 1

        if score < 3:
            continue

        items: list[dict] = []
        for item in related_notes[:limit]:
            created_at = item.get('created_at')
            created_at_dt = None
            if isinstance(created_at, datetime):
                created_at_dt = created_at
            elif isinstance(created_at, str) and created_at:
                try:
                    created_at_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except ValueError:
                    created_at_dt = None

            items.append({
                'question': item.get('question') or '',
                'answer': item.get('answer') or '',
                'word_context': item.get('word_context') or '',
                'created_at': created_at_dt or created_at,
            })

        latest_at = topic.get('latest_at')
        latest_at_dt = None
        if isinstance(latest_at, datetime):
            latest_at_dt = latest_at
        elif isinstance(latest_at, str) and latest_at:
            try:
                latest_at_dt = datetime.fromisoformat(latest_at.replace('Z', '+00:00'))
            except ValueError:
                latest_at_dt = None

        topic_matches.append({
            'score': score,
            'repeat_count': int(topic.get('count') or len(items)),
            'items': items,
            'follow_up_hint': topic.get('follow_up_hint') or '',
            'latest_at': latest_at_dt or datetime.min,
        })

    if not topic_matches:
        return None

    topic_matches.sort(
        key=lambda item: (item['score'], item['repeat_count'], item['latest_at']),
        reverse=True,
    )
    best = topic_matches[0]
    return {
        'repeat_count': best['repeat_count'],
        'items': best['items'][:limit],
        'follow_up_hint': best['follow_up_hint'],
    }


def _build_related_notes_msg(related_notes: dict | None) -> str | None:
    if not related_notes:
        return None

    repeat_count = int(related_notes.get('repeat_count') or 0)
    items = related_notes.get('items') or []
    follow_up_hint = str(related_notes.get('follow_up_hint') or '').strip()
    if not items:
        return None

    lines = ['[相关历史问答]']
    if repeat_count >= 2:
        lines.append(f"这个主题用户已重复询问 {repeat_count} 次，说明这里可能还没有真正吃透。")
    else:
        lines.append("下面是和当前问题最相关的历史问答，请优先利用。")

    for index, item in enumerate(items, start=1):
        created_at = item.get('created_at')
        date_text = created_at.strftime('%Y-%m-%d') if isinstance(created_at, datetime) else '最近'
        question = str(item.get('question') or '').strip()[:180]
        answer = str(item.get('answer') or '').strip().replace('\n', ' ')[:220]
        word_context = str(item.get('word_context') or '').strip()
        suffix = f"（关联单词：{word_context}）" if word_context else ''
        lines.append(f"{index}. {date_text} | 问：{question}{suffix}")
        lines.append(f"   答：{answer}")

    if repeat_count >= 2:
        lines.append("回答要求：先承认用户之前问过这个点，换一种解释角度，并主动询问是否需要进一步辨析、例句或小测。")

    if follow_up_hint:
        lines.append(f"[Follow-up hint] {follow_up_hint}")

    return '\n'.join(lines)


# ── Tool input schemas (whitelist validation) ─────────────────────────────────
# Maps tool_name → {param: (type, max_len_or_None)}
_TOOL_INPUT_SCHEMA: dict[str, dict[str, tuple]] = {
    "web_search": {
        "query": (str, 500),
    },
    "remember_user_note": {
        "note":     (str, 500),
        "category": (str, 50),
    },
    "get_wrong_words": {
        "limit": (int, None),
    },
    "get_chapter_words": {
        "book_id": (str, 100),
        "chapter_id": (int, None),
    },
    "get_book_chapters": {
        "book_id": (str, 100),
    },
}

_VALID_CATEGORIES = {'goal', 'habit', 'weakness', 'preference', 'achievement', 'other'}


def _validate_tool_input(tool_name: str, tool_input: dict) -> dict | None:
    """
    Validate and sanitize tool inputs against the whitelist schema.
    Returns a cleaned dict, or None if validation fails.
    """
    schema = _TOOL_INPUT_SCHEMA.get(tool_name)
    if schema is None:
        return None   # Unknown tool — reject

    cleaned = {}
    for param, (expected_type, max_len) in schema.items():
        val = tool_input.get(param)
        if val is None:
            continue
        if not isinstance(val, expected_type):
            return None
        if max_len and isinstance(val, str):
            val = val[:max_len]
        cleaned[param] = val

    # Extra whitelist check for category
    if tool_name == "remember_user_note":
        cat = cleaned.get("category", "other")
        if cat not in _VALID_CATEGORIES:
            cleaned["category"] = "other"

    return cleaned
