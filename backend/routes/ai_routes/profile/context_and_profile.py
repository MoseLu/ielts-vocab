def _get_context_data(user_id: int) -> dict:
    """Return structured learning summary dict for a given user_id."""
    # Book progress
    book_progress = UserBookProgress.query.filter_by(user_id=user_id).all()
    chapter_progress = UserChapterProgress.query.filter_by(user_id=user_id).all()
    wrong_words = UserWrongWord.query.filter_by(user_id=user_id).order_by(
        UserWrongWord.wrong_count.desc()
    ).limit(50).all()

    # ── Recent study sessions (last 20) for AI context ────────────────────────
    recent_sessions = (
        UserStudySession.query
        .filter_by(user_id=user_id)
        .filter(UserStudySession.words_studied > 0)
        .order_by(UserStudySession.started_at.desc())
        .limit(20)
        .all()
    )

    # Per-chapter session stats: session count + accuracy trend (last 5 sessions per chapter)
    from collections import defaultdict
    chapter_sessions: dict = defaultdict(list)
    for s in UserStudySession.query.filter_by(user_id=user_id).filter(UserStudySession.words_studied > 0).order_by(UserStudySession.started_at.desc()).limit(200).all():
        key = f"{s.book_id}__{s.chapter_id}"
        chapter_sessions[key].append(s)

    chapter_session_stats = {}
    from routes.books import VOCAB_BOOKS
    book_title_map = {b['id']: b['title'] for b in VOCAB_BOOKS}

    for key, sessions in chapter_sessions.items():
        book_id, chapter_id = key.split('__', 1)
        # Accuracy per session (oldest → newest)
        ordered = sorted(sessions, key=lambda s: s.started_at or 0)
        accuracies = [
            round(s.correct_count / s.words_studied * 100)
            for s in ordered if s.words_studied > 0
        ]
        # Trend: compare average of first half vs last half
        if len(accuracies) >= 2:
            mid = max(1, len(accuracies) // 2)
            early_avg = sum(accuracies[:mid]) / mid
            late_avg = sum(accuracies[mid:]) / max(len(accuracies) - mid, 1)
            trend = "↑进步" if late_avg - early_avg >= 5 else "↓下滑" if early_avg - late_avg >= 5 else "→稳定"
        else:
            trend = "—"
        total_words = sum(s.words_studied for s in sessions)
        avg_acc = round(sum(accuracies) / len(accuracies)) if accuracies else 0
        chapter_session_stats[key] = {
            'book_id': book_id,
            'chapter_id': chapter_id,
            'book_title': book_title_map.get(book_id, book_id),
            'session_count': len(sessions),
            'total_words': total_words,
            'avg_accuracy': avg_acc,
            'accuracies': accuracies,
            'trend': trend,
            'modes': list({s.mode for s in sessions if s.mode}),
        }

    # Aggregate per-book stats with the same effective-progress rules used by
    # the books API. Book-level current_index can mirror a chapter offset, so
    # summing it together with chapter words_learned double-counts the same work.
    from routes.books import _serialize_effective_book_progress

    books = []
    total_effective_words = 0
    total_correct = 0
    total_wrong = 0

    book_progress_by_id = {
        bp.book_id: bp
        for bp in book_progress
        if bp.book_id
    }
    chapter_progress_by_book: dict[str, list[UserChapterProgress]] = defaultdict(list)
    for cp in chapter_progress:
        if cp.book_id:
            chapter_progress_by_book[cp.book_id].append(cp)

    book_word_count_map = {b['id']: b.get('word_count', 0) for b in VOCAB_BOOKS}
    all_book_ids = sorted(set(book_progress_by_id) | set(chapter_progress_by_book))

    for book_id in all_book_ids:
        effective = _serialize_effective_book_progress(
            book_id,
            progress_record=book_progress_by_id.get(book_id),
            chapter_records=chapter_progress_by_book.get(book_id, []),
        )
        if not effective:
            continue

        correct_count = int(effective.get('correct_count') or 0)
        wrong_count = int(effective.get('wrong_count') or 0)
        attempted = correct_count + wrong_count
        word_count = int(book_word_count_map.get(book_id, 0) or 0)
        current_index = int(effective.get('current_index') or 0)

        total_effective_words += current_index
        total_correct += correct_count
        total_wrong += wrong_count

        books.append({
            'id': book_id,
            'title': book_title_map.get(book_id, book_id),
            'wordCount': word_count,
            'progress': round(current_index / word_count * 100) if word_count > 0 else 0,
            'accuracy': round(correct_count / attempted * 100) if attempted > 0 else 0,
            'wrongCount': wrong_count,
            'correctCount': correct_count,
        })

    total_learned = _alltime_words_display(user_id, total_effective_words)
    total_attempted = total_correct + total_wrong
    accuracy_rate = round(total_correct / total_attempted * 100) if total_attempted > 0 else 0

    # Recent trend: use actual study sessions (more reliable than chapter progress timestamps)
    if len(recent_sessions) >= 4:
        mid = len(recent_sessions) // 2
        # recent_sessions is newest-first; older sessions = second half
        newer = recent_sessions[:mid]
        older = recent_sessions[mid:]
        def _avg_acc(sessions):
            items = [s for s in sessions if s.words_studied > 0]
            if not items:
                return 0
            return sum(s.correct_count / s.words_studied for s in items) / len(items)
        trend = "improving" if _avg_acc(newer) > _avg_acc(older) + 0.05 else \
                "declining" if _avg_acc(newer) < _avg_acc(older) - 0.05 else "stable"
    elif recent_sessions:
        trend = "stable"
    else:
        # Fall back to chapter progress trend
        recent_cp = UserChapterProgress.query.filter_by(user_id=user_id).order_by(
            UserChapterProgress.updated_at.desc()
        ).limit(5).all()
        if len(recent_cp) >= 2:
            first_half = sum(r.correct_count / max(r.correct_count + r.wrong_count, 1) for r in recent_cp[len(recent_cp)//2:])
            second_half = sum(r.correct_count / max(r.correct_count + r.wrong_count, 1) for r in recent_cp[:len(recent_cp)//2])
            trend = "improving" if second_half > first_half else "declining" if second_half < first_half else "stable"
        else:
            trend = "new"

    # Build serialisable recent-session list
    recent_sessions_data = []
    for s in recent_sessions[:10]:
        acc = round(s.correct_count / s.words_studied * 100) if s.words_studied else 0
        recent_sessions_data.append({
            'mode': s.mode,
            'book_id': s.book_id,
            'chapter_id': s.chapter_id,
            'book_title': book_title_map.get(s.book_id or '', s.book_id or ''),
            'words_studied': s.words_studied,
            'correct_count': s.correct_count,
            'wrong_count': s.wrong_count,
            'accuracy': acc,
            'duration_seconds': s.duration_seconds,
            'started_at': s.started_at.isoformat() if s.started_at else None,
        })

    # Load persistent AI memory for this user
    memory = _load_memory(user_id)
    learner_profile = build_learner_profile(user_id)

    return {
        'totalBooks': len(books),
        'totalLearned': total_learned,
        'totalCorrect': total_correct,
        'totalWrong': total_wrong,
        'accuracyRate': accuracy_rate,
        'books': books,
        'wrongWords': [
            {
                'word': w.word,
                'phonetic': w.phonetic,
                'pos': w.pos,
                'definition': w.definition,
                'wrongCount': w.wrong_count
            }
            for w in wrong_words
        ],
        'recentTrend': trend,
        'recentSessions': recent_sessions_data,
        'chapterSessionStats': list(chapter_session_stats.values()),
        'totalSessions': len(recent_sessions),
        'learnerProfile': learner_profile,
        'activityTimeline': {
            'summary': learner_profile.get('activity_summary') or {},
            'source_breakdown': learner_profile.get('activity_source_breakdown') or [],
            'event_breakdown': learner_profile.get('activity_event_breakdown') or [],
            'recent_events': learner_profile.get('recent_activity') or [],
        },
        'memory': memory,
    }


@ai_bp.route('/context', methods=['GET'])
@token_required
def get_context(current_user: User):
    """Return structured learning summary for AI context."""
    return jsonify(_get_context_data(current_user.id))


@ai_bp.route('/learner-profile', methods=['GET'])
@token_required
def get_learner_profile(current_user: User):
    target_date = request.args.get('date') or None
    try:
        profile = build_learner_profile(current_user.id, target_date)
    except ValueError:
        return jsonify({'error': 'date must be YYYY-MM-DD'}), 400
    return jsonify(profile)


# ── POST /api/ai/ask ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """你是一个 IELTS 英语词汇学习规划助手，名叫"雅思小助手"。请用中文回复用户。

你具备以下能力：
1. 分析用户的学习数据（进度、准确率、错词分布、当前学习状态、历史练习记录）
2. 给出学习计划建议（每日学习量、复习节奏），提供可操作的选项让用户选择
3. 激励用户保持学习习惯，结合用户目标和进步趋势给出针对性反馈
4. 解释英文单词的用法，通过网络搜索获取权威例句
5. 记住用户的目标、习惯、偏好，在未来对话中持续引用

## 四维记忆系统（必须遵守）
- 单词掌握必须拆成 4 个独立维度：认读、听力、口语、书写。
- 四个维度独立达标、独立复习，全部达标后，才能把一个单词称为“完全掌握”。
- 认读周期：第 1 / 3 / 7 / 30 天，目标是看到英文后 1 秒内说出核心中文义。
- 听力周期：第 1 / 2 / 4 / 7 / 14 天，目标是听到发音立刻反应词义。
- 口语周期：第 1 / 3 / 7 / 15 / 30 天，目标是发音正确并能主动造句。
- 书写周期：第 1 / 2 / 5 / 9 / 21 天，目标是看到中文能零错误拼写英文。
- 当上下文里出现【四维记忆系统】时，优先按这个区块决定今日复习顺序和计划，而不是只看总正确率。
- 如果口语维度显示“证据不足”或“尚未开始”，要明确指出这一点，并安排发音 + 造句任务，不要假装已经掌握。
- 不要把某一个维度达标说成整个单词已经永久掌握。

## 工具使用指南

### remember_user_note — 持久化用户信息
当对话中出现以下信息时，**主动调用** 将其持久化（无需问用户）：
- 考试目标（如"目标7分"、"6月考试"）
- 每日学习计划（如"每天学30分钟"）
- 学习偏好、薄弱点、重要成就

### get_wrong_words — 获取错词列表
当用户问"我哪些词错得多"、"帮我复习错词"、"我的薄弱词汇"时调用。
参数：limit（数量，默认100）

### get_chapter_words — 获取章节单词
当用户问"第X章有哪些词"、"帮我看看这章内容"、"制定某章学习计划"时调用。
参数：book_id（词书ID）、chapter_id（章节号，整数）

### get_book_chapters — 获取词书章节结构
当用户问"这本书有几章"、"我完成了哪些章节"、"制定全书学习计划"时调用。
参数：book_id（词书ID）

**book_id 对照表：**
- 雅思听力高频词汇 → ielts_listening_premium
- 雅思阅读高频词汇 → ielts_reading_premium
- 雅思综合词汇5000+ → ielts_comprehensive
- 雅思终极词汇库 → ielts_ultimate
- AWL学术词汇表 → awl_academic

## 上下文优先级（从高到低）
1. 【AI记忆】— 跨会话持久的用户目标和 AI 笔记（最重要，始终优先引用）
2. 【历史对话摘要】— 压缩的旧会话上下文
3. 【最近练习记录】— 实际练习行为数据
4. 【当前学习状态】— 当前正在做什么
5. 【用户学习数据摘要】— 整体统计数字

## 最重要的原则：优先使用用户的真实数据
- 引用【AI记忆】中的内容时，要自然融入回复（"我记得你说过目标是7分…"）
- 如果用户问你记住了哪些单词，要明确说出具体单词名称，而不是泛泛而谈
- 如果用户在学习过程中问你当前单词的例句，先用 web_search 搜索真实例句
- 绝对不要在用户询问个人学习情况时给出通用词汇表

## 当用户没有历史数据时（totalLearned=0 或 [当前学习状态] 为空）
- 说明用户刚开始，先询问他们的目标：每天多少时间、目标分数等
- 获取到目标后立即用 remember_user_note 记录
- 不要给通用词汇表，而是制定第一阶段学习计划，提供选项让用户选择

## 回复格式规范

### 普通回复
直接用中文回复，内容清晰有条理。

### 建议型回复（需要用户确认）
在回复末尾用以下格式提供选项：
[options]
A. 选项A描述
B. 选项B描述
[/options]

示例（用户问今日计划）：
"根据你的数据，你今日可以学习50个新词，重点复习听力场景词汇。你想："
[options]
A. 好的，开始学习
B. 调整一下数量
C. 换个复习方向
[/options]

### 选项处理规则
- 用户可能只回复 "A" 或 "B" 等，识别并继续执行
- 回复选项时选项要有实际意义，每个选项要有明确的差异化

## 重要原则
- 如果看到【相关历史问答】，说明用户在同一主题反复卡住。要明确承认这一点，换一种解释方式，并主动追问是否需要更深入辨析、例句或小测。
- 不要编造例句，尽量通过网络搜索获取真实、地道的例句
- 建议要具体可执行（具体词数、时间安排）
- 语言要友好鼓励，不要过于严肃
- 如果用户还没有学习数据，鼓励他们开始学习
"""
