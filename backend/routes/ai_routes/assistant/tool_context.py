def _chat_with_tools(
    messages: list[dict],
    tools: list | None = None,
    max_iterations: int = 5,
    extra_handlers: dict | None = None,
) -> dict:
    """
    Chat with MiniMax, automatically handling tool_use blocks.
    Appends assistant responses and tool results to messages in-place.
    Returns the final text response.

    extra_handlers: optional dict of {tool_name: callable} that extends/overrides
    TOOL_HANDLERS for this call (used to inject per-request handlers, e.g. memory writes).
    """
    handlers = {**TOOL_HANDLERS, **(extra_handlers or {})}
    for i in range(max_iterations):
        response = chat(messages, tools=tools, max_tokens=4096)

        if response.get("type") == "tool_call":
            tool_name = response.get("tool")
            raw_input = response.get("input", {})
            tool_call_id = response.get("tool_call_id", f"call_{i}")
            handler = handlers.get(tool_name)

            # Validate + sanitize tool inputs before execution
            tool_input = _validate_tool_input(tool_name, raw_input) if isinstance(raw_input, dict) else None

            if handler and tool_input is not None:
                try:
                    result = handler(**tool_input)
                except Exception as e:
                    result = f"Tool error: {e}"

                # Append assistant message with tool_use reference
                messages.append({
                    "role": "assistant",
                    "content": [{
                        "type": "tool_use",
                        "id": tool_call_id,
                        "name": tool_name,
                        "input": tool_input
                    }]
                })
                # Append tool result
                messages.append({
                    "role": "user",
                    "content": [{
                        "type": "tool_result",
                        "tool_use_id": tool_call_id,
                        "content": result
                    }]
                })
            elif handler and tool_input is None:
                # Tool input failed validation — log and continue
                import logging as _log
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
        else:
            return response

    # Max iterations reached
    return {"type": "text", "text": "[对话轮次过多，已停止]"}


GREET_SYSTEM_PROMPT = """你是一个 IELTS 英语词汇学习规划助手，名叫"雅思小助手"。请用中文回复用户。

你的任务是生成一条个性化的问候语，让用户感到被关注和激励。

## 问候规则
- 如果用户有历史学习数据（totalLearned > 0），回顾他们的进度并鼓励继续
- 如果用户正在学习中（有 [当前学习状态]），提及当前进度
- 如果用户是新用户（totalLearned=0），热情欢迎，引导开始学习
- 问候语要简洁（3-5句话），不要过长
- 可以提供 2-3 个选项让用户快速选择接下来要做什么

## 回复格式
直接输出问候内容，可在末尾加选项：
[options]
A. 选项A
B. 选项B
[/options]
"""


GREET_SYSTEM_PROMPT_V2 = """你是一个 IELTS 英语词汇学习规划助手，名叫“雅思小助手”。请用中文回复用户。

你的任务是生成一条个性化的开场问候，让用户一打开就感到“这个助手记得我、理解我现在卡在哪”。

## 问候目标
- 优先利用学习画像、重复困惑主题、薄弱模式、重点突破词来组织问候。
- 如果【四维记忆系统】已经标出当前优先维度，要直接点出这个维度，并说明今天先补它。
- 如果用户近期反复卡在某个辨析点，要主动点出来，并说明你可以换一种讲法继续讲透。
- 如果用户今天有明确的训练焦点或弱项，要顺着这个焦点自然开场，不要只说泛泛的“继续加油”。
- 如果是新用户或几乎没有学习数据，再使用简单欢迎语。

## 输出规则
- 问候语保持 3-5 句，简洁、自然、像真人老师开场，不要写成模板化播报。
- 默认输出自然问候，不要默认输出选项，也不要把问候强行写成选择题。
- 只有当用户下一步动作非常明确时，才在末尾附 1-2 个简短选项。
- 如果提供选项，选项必须紧扣用户画像，而不是通用话术。

## 允许的选项格式
[options]
A. 选项A
B. 选项B
[/options]
"""

def _build_learning_context_msg(ctx_data: dict, frontend_context: dict) -> str:
    """Build a combined context message from server data + frontend state."""
    from datetime import datetime
    parts = []

    # ── Current date (so AI can make accurate plans) ──────────────────────────
    import calendar
    weekday_zh = ['一', '二', '三', '四', '五', '六', '日']
    now = datetime.now()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_left = days_in_month - now.day
    parts.append(
        f"【今日日期】{now.strftime('%Y年%m月%d日')}，"
        f"星期{weekday_zh[now.weekday()]}，本月还剩{days_left}天"
    )

    # ── Persistent AI memory (goals, notes, compressed history) ──────────────
    memory = ctx_data.get('memory', {})
    goals = memory.get('goals', {})
    ai_notes = memory.get('ai_notes', [])
    conv_summary = memory.get('conversation_summary', '')

    if goals or ai_notes or conv_summary:
        parts.append("【AI记忆（跨会话持久）】")
        if goals:
            goal_parts = []
            if goals.get('target_band'):
                goal_parts.append(f"目标分数：{goals['target_band']}")
            if goals.get('exam_date'):
                goal_parts.append(f"考试日期：{goals['exam_date']}")
            if goals.get('daily_minutes'):
                goal_parts.append(f"每日学习：{goals['daily_minutes']}分钟")
            if goals.get('focus'):
                goal_parts.append(f"重点方向：{goals['focus']}")
            if goal_parts:
                parts.append("  用户目标：" + "，".join(goal_parts))
        if ai_notes:
            cat_zh = {'goal': '目标', 'habit': '习惯', 'weakness': '薄弱', 'preference': '偏好', 'achievement': '成就', 'other': '其他'}
            for n in ai_notes[-10:]:  # last 10 notes
                cat = cat_zh.get(n.get('category', 'other'), n.get('category', ''))
                parts.append(f"  [{cat}] {n.get('note', '')}（{n.get('created_at', '')}）")
        if conv_summary:
            parts.append(f"\n【历史对话摘要】\n{conv_summary}")

    # Server-side learning summary
    total_learned = ctx_data.get('totalLearned', 0)
    total_correct = ctx_data.get('totalCorrect', 0)
    total_wrong = ctx_data.get('totalWrong', 0)
    accuracy = ctx_data.get('accuracyRate', 0)
    trend = ctx_data.get('recentTrend', 'new')
    books = ctx_data.get('books', [])
    wrong_words = ctx_data.get('wrongWords', [])
    recent_sessions = ctx_data.get('recentSessions', [])
    chapter_stats = ctx_data.get('chapterSessionStats', [])
    learner_profile = ctx_data.get('learnerProfile', {})
    memory_system = learner_profile.get('memory_system') or {}

    trend_zh = {'improving': '上升', 'declining': '下滑', 'stable': '平稳', 'new': '刚开始'}.get(trend, trend)

    parts.append(
        f"【用户学习数据摘要】\n"
        f"总学习词数：{total_learned}\n"
        f"总正确数：{total_correct}  总错误数：{total_wrong}\n"
        f"整体准确率：{accuracy}%\n"
        f"近期趋势：{trend_zh}\n"
        f"正在学习的词书：{len(books)} 本"
    )
    for b in books:
        word_count = b.get('wordCount', 0)
        correct = b.get('correctCount', 0)
        wc_str = f"共{word_count}词、" if word_count else ""
        parts.append(
            f"  - {b.get('title', b.get('id'))} "
            f"({wc_str}已答对{correct}词、准确率{b.get('accuracy', 0)}%、错词数{b.get('wrongCount', 0)})"
        )

    memory_dimensions = memory_system.get('dimensions') or []
    if memory_dimensions:
        parts.append("\n【四维记忆系统】")
        mastery_rule = memory_system.get('mastery_rule')
        tracking_note = memory_system.get('tracking_note')
        priority_label = memory_system.get('priority_dimension_label')
        priority_reason = memory_system.get('priority_reason')
        if mastery_rule:
            parts.append(f"总规则：{mastery_rule}")
        if priority_label:
            if priority_reason:
                parts.append(f"当前优先维度：{priority_label}（{priority_reason}）")
            else:
                parts.append(f"当前优先维度：{priority_label}")
        if tracking_note:
            parts.append(f"跟踪说明：{tracking_note}")
        for item in memory_dimensions:
            stats = [
                f"周期 {item.get('schedule_label')}",
                f"状态 {item.get('status_label', item.get('status'))}",
            ]
            if item.get('tracked_words'):
                stats.append(f"跟踪词 {item.get('tracked_words', 0)}")
            if item.get('stable_words'):
                stats.append(f"稳定词 {item.get('stable_words', 0)}")
            if item.get('accuracy') is not None:
                stats.append(f"准确率 {item.get('accuracy')}%")
            if item.get('due_words'):
                stats.append(f"到期 {item.get('due_words', 0)}")
            parts.append(f"  - {item.get('label', item.get('key'))}：{'，'.join(stats)}")
            focus_words = item.get('focus_words') or []
            if focus_words:
                parts.append(f"    重点词：{'、'.join(str(word) for word in focus_words[:3])}")
            next_action = str(item.get('next_action') or '').strip()
            if next_action:
                parts.append(f"    下一步：{next_action}")

    # ── Recent sessions (最近练习记录) ────────────────────────────────────────
    if recent_sessions:
        parts.append("\n【最近练习记录（最新10条）】")
        mode_zh = {
            'smart': '智能', 'listening': '听音选义', 'meaning': '汉译英',
            'dictation': '听写', 'radio': '随身听', 'quickmemory': '速记',
        }
        for s in recent_sessions:
            date_str = (s.get('started_at') or '')[:10]
            mode_label = mode_zh.get(s.get('mode', ''), s.get('mode', '未知'))
            chapter_label = f"第{s.get('chapter_id', '?')}章" if s.get('chapter_id') else '全书'
            book_label = s.get('book_title') or s.get('book_id') or '?'
            dur = s.get('duration_seconds', 0) or 0
            dur_str = f"{dur // 60}分{dur % 60}秒" if dur >= 60 else f"{dur}秒"
            parts.append(
                f"  {date_str} | {book_label} {chapter_label} | {mode_label} | "
                f"{s.get('words_studied', 0)}词 | 正确率{s.get('accuracy', 0)}% | 用时{dur_str}"
            )
    else:
        parts.append("\n【最近练习记录】暂无")

    # ── Per-chapter repeated practice stats ───────────────────────────────────
    repeated = [c for c in chapter_stats if c.get('session_count', 0) >= 2]
    if repeated:
        # Sort by session count desc, show top 5
        repeated.sort(key=lambda c: c.get('session_count', 0), reverse=True)
        parts.append("\n【多次练习章节（练了2次以上的）】")
        for c in repeated[:5]:
            acc_list = c.get('accuracies', [])
            acc_str = ' → '.join(f"{a}%" for a in acc_list[-5:])  # last 5 sessions
            modes_str = '、'.join(c.get('modes', []))
            parts.append(
                f"  {c.get('book_title', c.get('book_id', '?'))} 第{c.get('chapter_id', '?')}章："
                f"共练 {c.get('session_count')} 次，"
                f"平均正确率 {c.get('avg_accuracy')}%，"
                f"趋势 {c.get('trend', '—')}，"
                f"各次正确率 [{acc_str}]，"
                f"使用模式：{modes_str}"
            )

    if wrong_words:
        words_list = '、'.join([w['word'] for w in wrong_words[:20]])
        parts.append(f"\n错词列表（最近50条）：{words_list}")
    else:
        parts.append("\n错词列表：暂无")

    if learner_profile and isinstance(learner_profile, dict):
        summary = learner_profile.get('summary') or {}
        dimensions = learner_profile.get('dimensions') or []
        focus_words = learner_profile.get('focus_words') or []
        repeated_topics = learner_profile.get('repeated_topics') or []
        next_actions = learner_profile.get('next_actions') or []
        mode_breakdown = learner_profile.get('mode_breakdown') or []
        activity_summary = learner_profile.get('activity_summary') or {}
        activity_sources = learner_profile.get('activity_source_breakdown') or []
        activity_event_breakdown = learner_profile.get('activity_event_breakdown') or []
        recent_activity = learner_profile.get('recent_activity') or []

        parts.append("\n[统一学习画像]")
        weakest_mode_label = summary.get('weakest_mode_label') or summary.get('weakest_mode')
        weakest_mode_accuracy = summary.get('weakest_mode_accuracy')
        if weakest_mode_label:
            suffix = f"（准确率 {weakest_mode_accuracy}%）" if weakest_mode_accuracy is not None else ''
            parts.append(f"当前最弱模式：{weakest_mode_label}{suffix}")
        if dimensions:
            dimension_text = '、'.join(
                f"{item.get('label', item.get('dimension'))} {item.get('accuracy')}%"
                for item in dimensions[:3]
            )
            parts.append(f"薄弱维度排序：{dimension_text}")
        if focus_words:
            focus_text = '、'.join(item.get('word', '') for item in focus_words[:5] if item.get('word'))
            if focus_text:
                parts.append(f"重点突破词：{focus_text}")
        if mode_breakdown:
            mode_text = '、'.join(
                f"{item.get('label', item.get('mode'))} {item.get('words', 0)} 词/{item.get('sessions', 0)} 次"
                for item in mode_breakdown[:3]
            )
            if mode_text:
                parts.append(f"模式投入分布：{mode_text}")
        if repeated_topics:
            parts.append("重复困惑主题：")
            for topic in repeated_topics[:3]:
                parts.append(f"  - {topic.get('title', '')}（重复 {topic.get('count', 0)} 次）")
        if next_actions:
            parts.append("建议动作：")
            for action in next_actions[:3]:
                parts.append(f"  - {action}")
        if activity_summary.get('total_events'):
            parts.append("今日行为时间线：")
            parts.append(
                "  - "
                f"已记录 {activity_summary.get('total_events', 0)} 个行为，"
                f"涉及 {activity_summary.get('books_touched', 0)} 本词书、"
                f"{activity_summary.get('chapters_touched', 0)} 个章节、"
                f"{activity_summary.get('words_touched', 0)} 个单词"
            )
            if activity_summary.get('assistant_tool_uses'):
                parts.append(f"  - AI 工具动作：{activity_summary.get('assistant_tool_uses', 0)} 次")
            if activity_sources:
                source_text = '、'.join(
                    f"{item.get('label', item.get('source'))} {item.get('count', 0)} 次"
                    for item in activity_sources[:4]
                )
                if source_text:
                    parts.append(f"  - 来源分布：{source_text}")
            if activity_event_breakdown:
                event_text = '、'.join(
                    f"{item.get('label', item.get('event_type'))} {item.get('count', 0)} 次"
                    for item in activity_event_breakdown[:6]
                )
                if event_text:
                    parts.append(f"  - 行为类型：{event_text}")
            if recent_activity:
                parts.append("  - 最近关键动作：")
                for item in recent_activity[:6]:
                    stamp = str(item.get('occurred_at') or '')[11:16]
                    title = item.get('title') or item.get('label') or '学习行为'
                    if stamp:
                        parts.append(f"    {stamp} {title}")
                    else:
                        parts.append(f"    {title}")

    # Frontend session context
    if frontend_context:
        ctx_str = _build_context_msg(frontend_context)
        if ctx_str and ctx_str != '暂无':
            parts.append(f"\n[当前学习状态]\n{ctx_str}")

    return '\n'.join(parts)
