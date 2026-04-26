from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PracticeModeDefinition:
    key: str
    label: str
    short_label: str
    aliases: tuple[str, ...] = ()
    stats_rank: int | None = None
    profile_rank: int | None = None


PRACTICE_MODE_DEFINITIONS = (
    PracticeModeDefinition(
        key='game',
        label='五维闯关',
        short_label='五维闯关',
        aliases=('five-dimension-game', 'five_dimension_game'),
        stats_rank=0,
        profile_rank=0,
    ),
    PracticeModeDefinition(
        key='smart',
        label='智能练习',
        short_label='智能',
        stats_rank=1,
        profile_rank=1,
    ),
    PracticeModeDefinition(
        key='quickmemory',
        label='速记',
        short_label='速记',
        aliases=('quick_memory', 'quick-memory'),
        stats_rank=2,
        profile_rank=2,
    ),
    PracticeModeDefinition(
        key='listening',
        label='听音选义',
        short_label='听音选义',
        stats_rank=3,
        profile_rank=3,
    ),
    PracticeModeDefinition(
        key='meaning',
        label='默写模式',
        short_label='默写模式',
        stats_rank=4,
        profile_rank=4,
    ),
    PracticeModeDefinition(
        key='dictation',
        label='听写',
        short_label='听写',
        stats_rank=5,
        profile_rank=5,
    ),
    PracticeModeDefinition(
        key='radio',
        label='随身听',
        short_label='随身听',
        aliases=('choice', 'select', 'selection'),
        stats_rank=6,
        profile_rank=6,
    ),
    PracticeModeDefinition(
        key='errors',
        label='错词强化',
        short_label='错词强化',
        stats_rank=7,
        profile_rank=7,
    ),
    PracticeModeDefinition(
        key='speaking',
        label='口语',
        short_label='口语',
    ),
)

PRACTICE_MODE_KEYS = tuple(item.key for item in PRACTICE_MODE_DEFINITIONS)
PRACTICE_MODE_BY_KEY = {item.key: item for item in PRACTICE_MODE_DEFINITIONS}
PRACTICE_MODE_ALIASES = {
    alias: item.key
    for item in PRACTICE_MODE_DEFINITIONS
    for alias in item.aliases
}
STATS_PRACTICE_MODE_RANK = {
    item.key: item.stats_rank
    for item in PRACTICE_MODE_DEFINITIONS
    if item.stats_rank is not None
}
PROFILE_PRACTICE_MODE_RANK = {
    item.key: item.profile_rank
    for item in PRACTICE_MODE_DEFINITIONS
    if item.profile_rank is not None
}


def _raw_mode_text(value) -> str:
    if not isinstance(value, str):
        return ''
    return value.strip().lower()


def normalize_practice_mode(value) -> str:
    mode = _raw_mode_text(value)
    if not mode:
        return ''
    normalized = PRACTICE_MODE_ALIASES.get(mode, mode)
    return normalized if normalized in PRACTICE_MODE_BY_KEY else ''


def normalize_practice_mode_or_custom(
    value,
    *,
    default: str | None = '',
    max_length: int = 30,
) -> str | None:
    if not isinstance(value, str):
        return default
    raw_mode = value.strip()
    if not raw_mode:
        return default
    normalized = normalize_practice_mode(raw_mode)
    return normalized or raw_mode[:max_length]


def normalize_stats_practice_mode(value) -> str:
    normalized = normalize_practice_mode(value)
    return normalized if normalized in STATS_PRACTICE_MODE_RANK else ''


def normalize_profile_practice_mode(value) -> str:
    normalized = normalize_practice_mode(value)
    return normalized if normalized in PROFILE_PRACTICE_MODE_RANK else ''


def stats_practice_mode_candidates(value) -> list[str]:
    normalized = normalize_stats_practice_mode(value)
    if not normalized:
        raw_mode = _raw_mode_text(value)
        return [raw_mode] if raw_mode else []
    candidates = {
        normalized,
        *[
            alias
            for alias, target in PRACTICE_MODE_ALIASES.items()
            if target == normalized
        ],
    }
    return sorted(candidate for candidate in candidates if candidate)


def stats_practice_mode_sort_key(mode: str) -> tuple[int, str]:
    return (STATS_PRACTICE_MODE_RANK.get(mode, 999), mode)


def profile_practice_mode_sort_key(mode: str) -> tuple[int, str]:
    return (PROFILE_PRACTICE_MODE_RANK.get(mode, 999), mode)


def sort_stats_practice_modes(values) -> list[str]:
    return sorted(values, key=stats_practice_mode_sort_key)


def sort_profile_practice_modes(values) -> list[str]:
    return sorted(values, key=profile_practice_mode_sort_key)


def get_practice_mode_label(mode: str, *, default: str | None = None, short: bool = False) -> str:
    normalized = normalize_practice_mode(mode)
    definition = PRACTICE_MODE_BY_KEY.get(normalized)
    if definition is None:
        return mode if default is None else default
    return definition.short_label if short else definition.label


def practice_mode_labels(*, short: bool = False) -> dict[str, str]:
    return {
        item.key: item.short_label if short else item.label
        for item in PRACTICE_MODE_DEFINITIONS
    }


__all__ = [
    'PRACTICE_MODE_KEYS',
    'get_practice_mode_label',
    'normalize_practice_mode',
    'normalize_practice_mode_or_custom',
    'normalize_profile_practice_mode',
    'normalize_stats_practice_mode',
    'practice_mode_labels',
    'profile_practice_mode_sort_key',
    'sort_profile_practice_modes',
    'sort_stats_practice_modes',
    'stats_practice_mode_candidates',
    'stats_practice_mode_sort_key',
]
