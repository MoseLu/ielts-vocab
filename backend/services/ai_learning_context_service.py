from __future__ import annotations

import calendar

from platform_sdk.practice_mode_registry import get_practice_mode_label
from services.ai_prompt_context_service import build_context_msg
from services.local_time import current_local_datetime, format_event_time_for_ai


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
- 不要臆造具体钟点、分钟或次数；如果上下文没有明确给出，就只说“今天”“刚才”“最近”。
- 不要每次都重复同一个开场模板；同样的画像也要尽量换切入口，只抓最强的 1-2 个信号。

## 允许的选项格式
[options]
A. 选项A
B. 选项B
[/options]
"""


def build_learning_context_msg(ctx_data: dict, frontend_context: dict) -> str:
    parts = []
    weekday_zh = ['一', '二', '三', '四', '五', '六', '日']
    now = current_local_datetime()
    days_in_month = calendar.monthrange(now.year, now.month)[1]
    days_left = days_in_month - now.day
    parts.append(
        f"【今日日期】{now.strftime('%Y年%m月%d日')}，"
        f"星期{weekday_zh[now.weekday()]}，本月还剩{days_left}天"
    )

    memory = ctx_data.get('memory', {})
    goals = memory.get('goals', {})
    ai_notes = memory.get('ai_notes', [])
    conversation_summary = memory.get('conversation_summary', '')
    if goals or ai_notes or conversation_summary:
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
            category_labels = {
                'goal': '目标',
                'habit': '习惯',
                'weakness': '薄弱',
                'preference': '偏好',
                'achievement': '成就',
                'other': '其他',
            }
            for note in ai_notes[-10:]:
                category = category_labels.get(note.get('category', 'other'), note.get('category', ''))
                parts.append(f"  [{category}] {note.get('note', '')}（{note.get('created_at', '')}）")
        if conversation_summary:
            parts.append(f"\n【历史对话摘要】\n{conversation_summary}")

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
    for book in books:
        word_count = book.get('wordCount', 0)
        correct = book.get('correctCount', 0)
        word_count_text = f"共{word_count}词、" if word_count else ""
        parts.append(
            f"  - {book.get('title', book.get('id'))} "
            f"({word_count_text}已答对{correct}词、准确率{book.get('accuracy', 0)}%、错词数{book.get('wrongCount', 0)})"
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

    if recent_sessions:
        parts.append("\n【最近练习记录（最新10条）】")
        for session in recent_sessions:
            date_str = (session.get('started_at') or '')[:10]
            mode = session.get('mode', '')
            mode_label = get_practice_mode_label(mode, default=mode or '未知', short=True)
            chapter_label = f"第{session.get('chapter_id', '?')}章" if session.get('chapter_id') else '全书'
            book_label = session.get('book_title') or session.get('book_id') or '?'
            duration_seconds = session.get('duration_seconds', 0) or 0
            duration_text = (
                f"{duration_seconds // 60}分{duration_seconds % 60}秒"
                if duration_seconds >= 60 else
                f"{duration_seconds}秒"
            )
            parts.append(
                f"  {date_str} | {book_label} {chapter_label} | {mode_label} | "
                f"{session.get('words_studied', 0)}词 | 正确率{session.get('accuracy', 0)}% | 用时{duration_text}"
            )
    else:
        parts.append("\n【最近练习记录】暂无")

    repeated = [item for item in chapter_stats if item.get('session_count', 0) >= 2]
    if repeated:
        repeated.sort(key=lambda item: item.get('session_count', 0), reverse=True)
        parts.append("\n【多次练习章节（练了2次以上的）】")
        for item in repeated[:5]:
            accuracies = item.get('accuracies', [])
            accuracy_text = ' → '.join(f"{accuracy_item}%" for accuracy_item in accuracies[-5:])
            modes_text = '、'.join(item.get('modes', []))
            parts.append(
                f"  {item.get('book_title', item.get('book_id', '?'))} 第{item.get('chapter_id', '?')}章："
                f"共练 {item.get('session_count')} 次，"
                f"平均正确率 {item.get('avg_accuracy')}%，"
                f"趋势 {item.get('trend', '—')}，"
                f"各次正确率 [{accuracy_text}]，"
                f"使用模式：{modes_text}"
            )

    if wrong_words:
        words_list = '、'.join(word['word'] for word in wrong_words[:8])
        parts.append(f"\n近期错词提示（最近更新优先，仅展示少量）：{words_list}")
    else:
        parts.append("\n近期错词提示：暂无")

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
                    stamp = format_event_time_for_ai(item.get('occurred_at'))
                    title = item.get('title') or item.get('label') or '学习行为'
                    if stamp:
                        parts.append(f"    {stamp} {title}")
                    else:
                        parts.append(f"    {title}")

    if frontend_context:
        context_text = build_context_msg(frontend_context)
        if context_text and context_text != '暂无':
            parts.append(f"\n[当前学习状态]\n{context_text}")

    return '\n'.join(parts)
