from __future__ import annotations

import re
from services import books_registry_service


def build_context_msg(ctx: dict) -> str:
    parts = []
    dimension_labels = {
        'listening': '听音辨义',
        'meaning': '默写模式',
        'dictation': '拼写默写',
    }

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

    session_progress = ctx.get('sessionProgress')
    total_words = ctx.get('totalWords')
    words_completed = ctx.get('wordsCompleted')
    session_completed = ctx.get('sessionCompleted')
    if session_completed:
        parts.append(f"本轮练习：已完成全部 {total_words} 个单词")
        if words_completed is not None:
            parts.append(f"本轮答题数：{words_completed} 个")
    elif session_progress is not None:
        parts.append(
            f"本次进度：{session_progress} / {total_words} 个词"
            if total_words else
            f"本次进度：{session_progress} 个词"
        )
        if words_completed is not None:
            parts.append(f"本次已答题：{words_completed} 个")

    if ctx.get('sessionAccuracy') is not None:
        parts.append(f"本次准确率：{ctx['sessionAccuracy']}%")

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
        parts.append(f"当前最弱维度：{dimension_labels.get(weakest_dimension, weakest_dimension)}")

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
        summary_bits = []
        for key, label in (('known', '已认识'), ('unknown', '待巩固'), ('dueToday', '今日到期待复习')):
            value = quick_memory_summary.get(key)
            if isinstance(value, (int, float)):
                summary_bits.append(f"{label} {int(value)}")
        if summary_bits:
            parts.append("速记画像：" + '，'.join(summary_bits))

    mode_performance = ctx.get('modePerformance')
    if mode_performance and isinstance(mode_performance, dict):
        mode_labels = {
            'smart': '智能练习',
            'listening': '听音选义',
            'meaning': '默写模式',
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

    local = ctx.get('localHistory')
    if local and isinstance(local, dict):
        attempted = local.get('chaptersAttempted', 0)
        completed = local.get('chaptersCompleted', 0)
        accuracy = local.get('overallAccuracy', 0)
        correct = local.get('totalCorrect', 0)
        wrong = local.get('totalWrong', 0)
        if attempted > 0:
            parts.append(
                f"历史记录（本地）：已尝试 {attempted} 个章节，完成 {completed} 个，"
                f"累计答题 {correct + wrong} 次，准确率 {accuracy}%"
            )

    local_book = ctx.get('localBookProgress')
    if local_book and isinstance(local_book, dict):
        book_title_map = books_registry_service.get_vocab_book_title_map()
        book_word_count_map = books_registry_service.get_vocab_book_word_count_map()
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


def strip_options(text: str) -> str:
    return re.sub(r'\[options\][\s\S]*?\[/options\]\s*', '', text).strip()


def parse_options(text: str) -> list[str] | None:
    matches = re.findall(r'\[options\]\s*([\s\S]*?)\s*\[/options\]', text)
    if not matches:
        return None

    options = []
    for block in matches:
        for line in block.strip().split('\n'):
            line = line.strip()
            if line and re.match(r'^[A-Z]\.', line):
                options.append(line)
    return options if options else None
