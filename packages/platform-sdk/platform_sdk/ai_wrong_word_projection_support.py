from __future__ import annotations

from sqlalchemy import func, or_

from platform_sdk.ai_projection_bootstrap import ai_projection_bootstrap_ready
from platform_sdk.ai_vocab_catalog_application import (
    get_global_vocab_pool,
    resolve_quick_memory_vocab_entry,
)
from platform_sdk.ai_wrong_word_projection_application import (
    AI_WRONG_WORD_CONTEXT_PROJECTION,
)
from platform_sdk.learning_core_learning_summary_support import (
    decorate_wrong_words_with_quick_memory_progress,
)
from service_models.ai_execution_models import AIProjectedWrongWord


def projected_wrong_words_ready(user_id: int) -> bool:
    return ai_projection_bootstrap_ready(AI_WRONG_WORD_CONTEXT_PROJECTION)


def list_projected_wrong_words_for_ai(
    user_id: int,
    *,
    limit: int | None = None,
    query: str | None = None,
    recent_first: bool = True,
    decorate: bool = True,
) -> tuple[bool, list[dict]]:
    if not projected_wrong_words_ready(user_id):
        return False, []

    normalized_query = ' '.join(str(query or '').strip().lower().split())
    query_builder = AIProjectedWrongWord.query.filter_by(user_id=user_id)
    if normalized_query:
        pattern = f'%{normalized_query}%'
        query_builder = query_builder.filter(or_(
            func.lower(func.coalesce(AIProjectedWrongWord.word, '')).like(pattern),
            func.lower(func.coalesce(AIProjectedWrongWord.phonetic, '')).like(pattern),
            func.lower(func.coalesce(AIProjectedWrongWord.pos, '')).like(pattern),
            func.lower(func.coalesce(AIProjectedWrongWord.definition, '')).like(pattern),
        ))

    if recent_first:
        query_builder = query_builder.order_by(
            AIProjectedWrongWord.updated_at.desc(),
            AIProjectedWrongWord.wrong_count.desc(),
            AIProjectedWrongWord.word.asc(),
        )
    else:
        query_builder = query_builder.order_by(
            AIProjectedWrongWord.wrong_count.desc(),
            AIProjectedWrongWord.updated_at.desc(),
            AIProjectedWrongWord.word.asc(),
        )

    if limit is not None:
        query_builder = query_builder.limit(limit)
    rows = query_builder.all()
    if not decorate:
        return True, [row.to_dict() for row in rows]

    return True, decorate_wrong_words_with_quick_memory_progress(
        user_id,
        rows,
        get_global_vocab_pool=get_global_vocab_pool,
        resolve_quick_memory_vocab_entry=resolve_quick_memory_vocab_entry,
    )
