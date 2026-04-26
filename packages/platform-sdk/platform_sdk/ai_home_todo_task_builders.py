from __future__ import annotations

from service_models.ai_execution_models import UserHomeTodoItem
from services.learner_profile import DIMENSION_LABELS


TASK_ORDER = (
    'due-review',
    'error-review',
    'continue-book',
    'add-book',
    'speaking',
)
TASK_PRIORITY = {
    'due-review': 10,
    'error-review': 20,
    'continue-book': 30,
    'add-book': 35,
    'speaking': 40,
}
SPEAKING_VARIANTS = frozenset({'needs_setup', 'due', 'strengthen'})
MAINLINE_TARGET_NORMAL = 20
MAINLINE_TARGET_LOADED = 15
MAINLINE_TARGET_HEAVY = 10


def ranked_items(items: list[UserHomeTodoItem]) -> list[UserHomeTodoItem]:
    return sorted(
        items,
        key=lambda item: (
            TASK_PRIORITY.get(item.kind, 99),
            TASK_ORDER.index(item.kind) if item.kind in TASK_ORDER else 999,
            int(item.id or 0),
        ),
    )


def _completion_source(*, completed: bool, completed_today: bool) -> str | None:
    if not completed:
        return None
    return 'completed_today' if completed_today else 'already_clear'


def _finalize_steps(raw_steps: list[dict]) -> list[dict]:
    steps: list[dict] = []
    current_marked = False
    for raw_step in raw_steps:
        if raw_step.get('done'):
            status = 'completed'
        elif not current_marked:
            status = 'current'
            current_marked = True
        else:
            status = 'pending'
        steps.append({
            'id': str(raw_step.get('id') or ''),
            'label': str(raw_step.get('label') or ''),
            'status': status,
        })
    return steps


def _task_spec(
    *,
    task_key: str,
    kind: str,
    title: str,
    description: str,
    badge: str,
    status: str,
    action: dict,
    carry_over_count: int,
    completion_source: str | None = None,
    steps: list[dict] | None = None,
    evidence: dict | None = None,
) -> dict:
    merged_evidence = dict(evidence or {})
    if completion_source:
        merged_evidence['completion_source'] = completion_source
    return {
        'task_key': task_key,
        'kind': kind,
        'priority': TASK_PRIORITY.get(kind, 100),
        'title': title,
        'description': description,
        'badge': badge,
        'status': status,
        'action': action,
        'steps': steps or [],
        'evidence': merged_evidence,
        'carry_over_count': max(0, int(carry_over_count or 0)),
    }


def _sanitize_speaking_todo_text(text: str) -> str:
    sanitized = str(text or '').strip()
    replacements = (
        ('有效证据', '练习记录'),
        ('造句证据', '主动造句'),
        ('输出证据', '输出练习'),
        ('口语证据', '口语练习'),
        ('补证据', '补练习'),
        ('有效口语输出记录', '英文输出'),
        ('有效回答', '口语回答'),
    )
    for source, target in replacements:
        sanitized = sanitized.replace(source, target)
    return sanitized


def build_due_review_task(signals: dict, *, carry_over_count: int) -> dict:
    pending_count = int(((signals.get('due_review') or {}).get('pending_count')) or 0)
    done_today = bool((signals.get('due_review') or {}).get('done_today'))
    completed = pending_count <= 0
    steps = _finalize_steps([
        {'id': 'review-due', 'label': f'完成 {pending_count} 个到期词复习', 'done': completed},
        {'id': 'clear-due', 'label': '完成标准：到期数归零，不能只打开页面。', 'done': completed},
    ])
    return _task_spec(
        task_key='due-review',
        kind='due-review',
        title='到期复习',
        description=f'还有 {pending_count} 个到期词需要先回顾。' if pending_count > 0 else '今天没有积压的到期复习。',
        badge=f'{pending_count} 词到期' if pending_count > 0 else '已清空',
        status='completed' if completed else 'pending',
        completion_source=_completion_source(completed=completed, completed_today=done_today),
        action={
            'kind': 'due-review',
            'cta_label': '进入五维复习',
            'task': 'due-review',
            'mode': None,
            'book_id': None,
            'chapter_id': None,
            'dimension': None,
        },
        carry_over_count=carry_over_count,
        steps=steps,
    )


def build_error_review_task(signals: dict, *, carry_over_count: int) -> dict:
    error_review = signals.get('error_review') or {}
    pending_count = int(error_review.get('pending_count') or 0)
    recommended_dimension = error_review.get('recommended_dimension')
    recommended_count = int(error_review.get('recommended_count') or 0)
    done_today = bool(error_review.get('done_today'))
    completed = pending_count <= 0
    if pending_count > 0 and recommended_dimension:
        dimension_label = DIMENSION_LABELS.get(recommended_dimension, recommended_dimension)
        description = f'优先处理「{dimension_label}」，还有 {recommended_count} 个词未过。'
    elif pending_count > 0:
        description = f'还有 {pending_count} 个错词待处理。'
    else:
        description = '当前没有待清理的错词。'
    target_label = (
        f'优先清理「{DIMENSION_LABELS.get(recommended_dimension, recommended_dimension)}」{recommended_count} 个'
        if recommended_dimension and recommended_count > 0
        else f'清理 {pending_count} 个待清错词'
    )
    return _task_spec(
        task_key='error-review',
        kind='error-review',
        title='清错词',
        description=description,
        badge=f'{pending_count} 个待清' if pending_count > 0 else '已清空',
        status='completed' if completed else 'pending',
        completion_source=_completion_source(completed=completed, completed_today=done_today),
        action={
            'kind': 'error-review',
            'cta_label': '清理错维回流',
            'task': 'error-review',
            'mode': None,
            'book_id': None,
            'chapter_id': None,
            'dimension': recommended_dimension,
        },
        carry_over_count=carry_over_count,
        steps=_finalize_steps([
            {'id': 'clear-wrong', 'label': target_label, 'done': completed},
            {'id': 'clear-rule', 'label': '完成标准：待清错词数归零。', 'done': completed},
        ]),
        evidence={'recommended_dimension': recommended_dimension, 'recommended_count': recommended_count},
    )


def _mainline_target(signals: dict, focus_book: dict) -> int:
    remaining = max(0, int(focus_book.get('remaining_words') or 0))
    if remaining <= 0:
        return 0
    due_count = int(((signals.get('due_review') or {}).get('pending_count')) or 0)
    wrong_count = int(((signals.get('error_review') or {}).get('pending_count')) or 0)
    if due_count >= 50 or wrong_count >= 80:
        target = MAINLINE_TARGET_HEAVY
    elif due_count >= 20 or wrong_count >= 30:
        target = MAINLINE_TARGET_LOADED
    else:
        target = MAINLINE_TARGET_NORMAL
    return min(remaining, target)


def build_mainline_task(signals: dict, *, carry_over_by_key: dict[str, int]) -> dict:
    focus_book = signals.get('focus_book')
    if not isinstance(focus_book, dict):
        return _task_spec(
            task_key='add-book',
            kind='add-book',
            title='添加词书',
            description='添加 1 本有效词书，作为之后每天的新词主线。',
            badge='缺少词书',
            status='pending',
            steps=_finalize_steps([
                {'id': 'add-book', 'label': '添加 1 本有效词书', 'done': False},
                {'id': 'start-mainline', 'label': '添加后明天起生成主线新词任务。', 'done': False},
            ]),
            action={
                'kind': 'add-book',
                'cta_label': '去选词书',
                'task': 'add-book',
                'mode': None,
                'book_id': None,
                'chapter_id': None,
                'dimension': None,
            },
            carry_over_count=carry_over_by_key.get('add-book', 0),
        )

    is_completed = bool(focus_book.get('is_completed'))
    words_today = max(0, int(focus_book.get('words_today') or 0))
    target_words = _mainline_target(signals, focus_book)
    done_today = words_today >= target_words and target_words > 0
    completed = is_completed or done_today
    remaining_words = int(focus_book.get('remaining_words') or 0)
    title = str(focus_book.get('title') or '当前词书')
    progress_label = f'{min(words_today, target_words)}/{target_words}' if target_words > 0 else '0/0'
    steps = _finalize_steps([
        {'id': 'new-words', 'label': f'今日推进 {target_words} 个新词（已完成 {progress_label}）', 'done': completed},
        {'id': 'progress-rule', 'label': '完成标准：同一词书产生真实学习进度，不算只打开页面或纯时长。', 'done': completed},
    ])
    return _task_spec(
        task_key='continue-book',
        kind='continue-book',
        title='推进词书',
        description=(
            f'继续《{title}》，今天目标 {target_words} 个新词，还剩 {remaining_words} 词。'
            if not is_completed
            else f'《{title}》的主线已经清空。'
        ),
        badge=f'{progress_label} 今日新词' if not is_completed else '主线已清空',
        status='completed' if completed else 'pending',
        completion_source=_completion_source(completed=completed, completed_today=done_today),
        action={
            'kind': 'continue-book',
            'cta_label': '继续学习',
            'task': 'continue-book',
            'mode': None,
            'book_id': focus_book.get('book_id'),
            'chapter_id': focus_book.get('chapter_id'),
            'dimension': None,
        },
        carry_over_count=carry_over_by_key.get('continue-book', 0),
        steps=steps,
        evidence={'focus_book': focus_book, 'target_words': target_words, 'words_today': words_today},
    )


def build_speaking_task(
    signals: dict,
    *,
    carry_over_count: int,
    existing_item: UserHomeTodoItem | None,
) -> dict | None:
    speaking = signals.get('speaking') or {}
    current_status = str(speaking.get('status') or '').strip() or 'needs_setup'
    existing_variant = None
    if existing_item is not None:
        existing_variant = str(existing_item.evidence_dict().get('variant') or '').strip() or None
    variant = existing_variant or (current_status if current_status in SPEAKING_VARIANTS else None)
    if variant not in SPEAKING_VARIANTS:
        return None

    has_pronunciation_today = bool(speaking.get('has_pronunciation_today'))
    has_output_today = bool(speaking.get('has_output_today'))
    has_assessment_today = bool(speaking.get('has_assessment_today'))
    due_words = int(speaking.get('due_words') or 0)
    backlog_words = int(speaking.get('backlog_words') or 0)
    speaking_activity_today = any([has_pronunciation_today, has_output_today, has_assessment_today])
    if variant == 'needs_setup':
        raw_steps = [
            {'id': 'pronunciation', 'label': '1 次发音检查', 'done': has_pronunciation_today},
            {'id': 'output', 'label': '1 句英文主动表达', 'done': has_output_today},
        ]
        badge = '开始练口语'
        description = _sanitize_speaking_todo_text(
            speaking.get('next_action') or '先做一次发音检查，再说 1 句英文。',
        )
    elif variant == 'due':
        raw_steps = [
            {'id': 'due-clear', 'label': '完成当日到期口语复现', 'done': due_words <= 0},
            {'id': 'answer', 'label': '1 次口语回答或估分', 'done': has_output_today or has_assessment_today},
        ]
        badge = f'{max(due_words, 0)} 个到期'
        description = _sanitize_speaking_todo_text(
            speaking.get('next_action') or '优先清掉今天到期的口语复现，再补 1 次口语回答。',
        )
    else:
        raw_steps = [
            {'id': 'pronunciation', 'label': '1 次发音检查', 'done': has_pronunciation_today},
            {'id': 'reinforce', 'label': '1 次造句/模拟/估分', 'done': has_output_today or has_assessment_today},
        ]
        badge = f'{max(backlog_words, 0)} 项待补'
        description = _sanitize_speaking_todo_text(
            speaking.get('next_action') or '先做一次发音检查，再补一条造句或口语模拟。',
        )

    steps = _finalize_steps(raw_steps)
    completed = all(step.get('status') == 'completed' for step in steps)
    completion_source = _completion_source(completed=completed, completed_today=speaking_activity_today)
    return _task_spec(
        task_key='speaking',
        kind='speaking',
        title='口语任务',
        description=description,
        badge='已完成' if completed else badge,
        status='completed' if completed else 'pending',
        completion_source=completion_source,
        action={
            'kind': 'speaking',
            'cta_label': '口语补练',
            'task': 'speaking',
            'mode': None,
            'book_id': None,
            'chapter_id': None,
            'dimension': 'speaking',
        },
        carry_over_count=carry_over_count,
        steps=steps,
        evidence={
            'variant': variant,
            'generated_status': current_status,
            'due_words': due_words,
            'backlog_words': backlog_words,
            'focus_words': speaking.get('focus_words') or [],
            'has_pronunciation_today': has_pronunciation_today,
            'has_output_today': has_output_today,
            'has_assessment_today': has_assessment_today,
        },
    )
