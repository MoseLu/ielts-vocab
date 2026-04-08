from services.notes_summary_service_parts.base import format_duration
from services.notes_summary_runtime import SUMMARY_MODE_LABELS


def build_summary_prompt(
    target_date: str,
    notes_list,
    sessions,
    wrong_words,
    learning_snapshot: dict | None = None,
    topic_insights: list[dict] | None = None,
    learner_profile: dict | None = None,
) -> str:
    prompt_parts = [f"请为 {target_date} 生成学习总结。", ""]

    if learning_snapshot:
        prompt_parts.append("### 学习指标总览")
        prompt_parts.append(f"- 今日学习词数：{learning_snapshot['today_words']}")
        prompt_parts.append(f"- 今日练习次数：{learning_snapshot['today_sessions']}")
        prompt_parts.append(f"- 今日用时：{format_duration(learning_snapshot['today_duration'])}")
        prompt_parts.append(f"- 今日准确率：{learning_snapshot['today_accuracy']}%")
        prompt_parts.append(f"- 连续学习：{learning_snapshot['streak_days']} 天")

        weakest_mode = learning_snapshot.get('weakest_mode')
        if weakest_mode:
            prompt_parts.append(
                f"- 最弱模式：{weakest_mode['label']}（累计准确率 {weakest_mode['accuracy']}%，样本 {weakest_mode['attempts']} 题）"
            )
        else:
            prompt_parts.append("- 最弱模式：样本不足，暂不判断")

        if learning_snapshot.get('today_mode_breakdown'):
            mode_summary = '；'.join(
                f"{item['label']} {item['accuracy']}% / {item['words']}词 / {format_duration(item['duration_seconds'])}"
                for item in learning_snapshot['today_mode_breakdown']
            )
            prompt_parts.append(f"- 今日模式表现：{mode_summary}")

    if sessions:
        prompt_parts.append("### 当天练习记录")
        for session in sessions:
            mode_label = SUMMARY_MODE_LABELS.get(session.mode or '', session.mode or '未知模式')
            duration_text = format_duration(session.duration_seconds or 0)
            correct = session.correct_count or 0
            wrong = session.wrong_count or 0
            total = correct + wrong
            accuracy = round(correct / total * 100) if total > 0 else 0
            prompt_parts.append(
                f"- {mode_label}：学习 {session.words_studied or 0} 词，准确率 {accuracy}%，用时 {duration_text}"
            )
    else:
        prompt_parts.append("### 当天练习记录")
        prompt_parts.append("- 暂无练习记录。")

    if notes_list:
        prompt_parts.append("")
        prompt_parts.append("### 当天 AI 问答记录")
        for index, note in enumerate(notes_list, start=1):
            word_info = f"（关联单词：{note.word_context}）" if note.word_context else ""
            prompt_parts.append(f"{index}. 问题{word_info}：{note.question[:200]}")
            prompt_parts.append(f"   回答要点：{note.answer[:500]}")
    else:
        prompt_parts.append("")
        prompt_parts.append("### 当天 AI 问答记录")
        prompt_parts.append("- 暂无提问记录。")

    if topic_insights:
        prompt_parts.append("")
        prompt_parts.append("### AI 对话主题洞察")
        for topic in topic_insights[:5]:
            prompt_parts.append(
                f"- {topic['title']}：今天相关提问 {topic['count']} 次；最近一次回答重点：{topic['latest_answer']}"
            )

    if wrong_words:
        prompt_parts.append("")
        prompt_parts.append("### 近期易错词")
        prompt_parts.append("- " + "、".join(word.word for word in wrong_words[:20]))

    prompt_parts.append("")
    prompt_parts.append("### 生成要求")
    prompt_parts.append("- 请把当天学习内容、学习指标、重复提问主题和易错词联系起来分析。")
    prompt_parts.append("- 后续建议必须具体到下一步动作，优先结合最弱模式、重复困惑点和错词。")

    if learner_profile:
        prompt_parts.append("")
        prompt_parts.append("### 统一学习画像")
        profile_summary = learner_profile.get('summary') or {}
        dimensions = learner_profile.get('dimensions') or []
        focus_words = learner_profile.get('focus_words') or []
        repeated_topics = learner_profile.get('repeated_topics') or []
        next_actions = learner_profile.get('next_actions') or []
        activity_summary = learner_profile.get('activity_summary') or {}
        activity_sources = learner_profile.get('activity_source_breakdown') or []
        recent_activity = learner_profile.get('recent_activity') or []

        weakest_mode_label = profile_summary.get('weakest_mode_label') or profile_summary.get('weakest_mode')
        weakest_mode_accuracy = profile_summary.get('weakest_mode_accuracy')
        if weakest_mode_label:
            accuracy_suffix = f"（{weakest_mode_accuracy}%）" if weakest_mode_accuracy is not None else ""
            prompt_parts.append(f"- 最弱模式：{weakest_mode_label}{accuracy_suffix}")
        if dimensions:
            dimension_text = '、'.join(
                f"{item.get('label', item.get('dimension'))} {item.get('accuracy')}%"
                for item in dimensions[:3]
            )
            prompt_parts.append(f"- 薄弱维度：{dimension_text}")
        if focus_words:
            focus_text = '、'.join(item.get('word', '') for item in focus_words[:5] if item.get('word'))
            if focus_text:
                prompt_parts.append(f"- 重点突破词：{focus_text}")
        if repeated_topics:
            topic_text = '；'.join(
                f"{topic.get('title', '')}（{topic.get('count', 0)}次）"
                for topic in repeated_topics[:3]
            )
            prompt_parts.append(f"- 重复困惑主题：{topic_text}")
        if next_actions:
            prompt_parts.append("- 建议动作：")
            for action in next_actions[:4]:
                prompt_parts.append(f"  - {action}")
        if activity_summary.get('total_events'):
            prompt_parts.append(
                "- 今日统一行为流："
                f"记录了 {activity_summary.get('total_events', 0)} 个事件，"
                f"涉及 {activity_summary.get('books_touched', 0)} 本词书、"
                f"{activity_summary.get('chapters_touched', 0)} 个章节、"
                f"{activity_summary.get('words_touched', 0)} 个单词"
            )
            if activity_sources:
                source_text = '；'.join(
                    f"{item.get('label', item.get('source'))} {item.get('count', 0)} 次"
                    for item in activity_sources[:5]
                )
                if source_text:
                    prompt_parts.append(f"- 行为来源分布：{source_text}")
            if recent_activity:
                prompt_parts.append("- 近期关键动作：")
                for item in recent_activity[:8]:
                    stamp = str(item.get('occurred_at') or '')[11:16]
                    title = item.get('title') or item.get('label') or '学习行为'
                    prompt_parts.append(f"  - {stamp} {title}".strip())

    return '\n'.join(prompt_parts)
