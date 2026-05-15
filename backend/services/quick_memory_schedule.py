from service_models.learning_core_models import UserQuickMemoryRecord
from services import ai_vocab_catalog_service, quick_memory_record_repository, scoped_quick_memory_repository
from platform_sdk.quick_memory_schedule_support import (
    QUICK_MEMORY_MASTERY_TARGET,
    QUICK_MEMORY_REVIEW_INTERVALS_DAYS,
    compute_quick_memory_next_review_ms,
    load_and_normalize_quick_memory_records,
    normalize_quick_memory_record_schedule,
    resolve_quick_memory_next_review_ms,
)


def load_user_quick_memory_records(user_id: int) -> list[UserQuickMemoryRecord]:
    return load_and_normalize_quick_memory_records(
        user_id,
        list_records=quick_memory_record_repository.list_user_quick_memory_records,
        commit=quick_memory_record_repository.commit,
        resolve_vocab_context=ai_vocab_catalog_service._resolve_unique_quick_memory_vocab_context,
    )


def load_user_scoped_quick_memory_records(user_id: int, scope_key: str):
    return load_and_normalize_quick_memory_records(
        user_id,
        list_records=lambda uid: scoped_quick_memory_repository.list_user_scoped_quick_memory_records(
            uid,
            scope_key=scope_key,
        ),
        commit=scoped_quick_memory_repository.commit,
        resolve_vocab_context=None,
    )
