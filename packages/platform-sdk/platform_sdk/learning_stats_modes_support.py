from __future__ import annotations

from platform_sdk.practice_mode_registry import (
    normalize_stats_practice_mode,
    sort_stats_practice_modes,
    stats_practice_mode_candidates,
)


def normalize_stats_mode(value) -> str:
    return normalize_stats_practice_mode(value)


def sort_stats_modes(values) -> list[str]:
    return sort_stats_practice_modes(values)


def stats_mode_candidates(value) -> list[str]:
    return stats_practice_mode_candidates(value)


__all__ = [
    'normalize_stats_mode',
    'sort_stats_modes',
    'stats_mode_candidates',
]
