from __future__ import annotations

from platform_sdk.ai_listening_confusables_application import get_preset_listening_confusables
from platform_sdk.ai_vocab_catalog_application import get_global_vocab_pool as build_global_vocab_pool


def get_global_vocab_pool() -> list:
    return build_global_vocab_pool()


def list_preset_listening_confusables(target_word: str, *, limit: int) -> list[dict]:
    return get_preset_listening_confusables(target_word, limit=limit)
