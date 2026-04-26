from platform_sdk.practice_mode_registry import (
    get_practice_mode_label,
    normalize_profile_practice_mode,
    profile_practice_mode_sort_key,
)


def _normalize_profile_mode(value) -> str:
    return normalize_profile_practice_mode(value)


def _build_mode_summary(all_sessions) -> tuple[list[dict], dict | None]:
    mode_map: dict[str, dict] = {}
    for session in all_sessions:
        mode = _normalize_profile_mode(session.mode)
        if not mode:
            continue
        bucket = mode_map.setdefault(mode, {
            'mode': mode,
            'label': get_practice_mode_label(mode, default=mode),
            'correct': 0,
            'wrong': 0,
            'words': 0,
            'sessions': 0,
        })
        bucket['correct'] += session.correct_count or 0
        bucket['wrong'] += session.wrong_count or 0
        bucket['words'] += session.words_studied or 0
        bucket['sessions'] += 1

    modes = []
    weakest_mode = None
    for bucket in mode_map.values():
        attempts = bucket['correct'] + bucket['wrong']
        accuracy = round(bucket['correct'] / attempts * 100) if attempts > 0 else None
        item = {
            **bucket,
            'attempts': attempts,
            'accuracy': accuracy,
        }
        modes.append(item)
        if accuracy is not None and attempts >= 5:
            if weakest_mode is None or accuracy < weakest_mode['accuracy']:
                weakest_mode = item

    modes.sort(key=lambda item: profile_practice_mode_sort_key(item['mode']))
    return modes, weakest_mode


def _build_trend_direction(all_sessions) -> str:
    scored = [
        round((session.correct_count or 0) / max((session.correct_count or 0) + (session.wrong_count or 0), 1) * 100)
        for session in all_sessions
        if (session.correct_count or 0) + (session.wrong_count or 0) > 0
    ]
    if len(scored) < 4:
        return 'stable' if scored else 'new'

    window = min(7, len(scored) // 2)
    newer = scored[-window:]
    older = scored[-window * 2:-window]
    if not older:
        return 'stable'

    avg_newer = sum(newer) / len(newer)
    avg_older = sum(older) / len(older)
    if avg_newer >= avg_older + 5:
        return 'improving'
    if avg_newer <= avg_older - 5:
        return 'declining'
    return 'stable'


def _build_next_actions(
    *,
    memory_system: dict | None,
    weakest_mode: dict | None,
    weak_dimensions: list[dict],
    focus_words: list[dict],
    due_reviews: int,
) -> list[str]:
    actions: list[str] = []
    seen: set[str] = set()

    def add_action(text: str | None):
        normalized = (text or '').strip()
        if not normalized or normalized in seen:
            return
        seen.add(normalized)
        actions.append(normalized)

    if memory_system:
        add_action(memory_system.get('priority_action'))
        for item in memory_system.get('dimensions') or []:
            if item.get('key') == memory_system.get('priority_dimension'):
                continue
            if item.get('status') in {'due', 'strengthen', 'needs_setup'}:
                add_action(item.get('next_action'))

    if due_reviews > 0:
        add_action(f"优先复习 {due_reviews} 个已到期的速记单词，先清理短期遗忘。")

    if weakest_mode:
        add_action(
            f"下一轮先做 {weakest_mode['label']} 10-15 分钟，优先修复当前最低准确率模式。"
        )

    if weak_dimensions:
        add_action(
            f"围绕 {weak_dimensions[0]['label']} 设计辨析/陷阱题，而不是继续平均铺题。"
        )

    if focus_words:
        focus_word_text = '、'.join(item['word'] for item in focus_words[:3])
        add_action(f"把 {focus_word_text} 放进同组复习，做易混辨析和反向提问。")

    return actions[:4]
