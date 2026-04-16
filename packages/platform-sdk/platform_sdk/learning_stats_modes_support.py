from __future__ import annotations

_STATS_MODE_ORDER = (
    'game',
    'smart',
    'quickmemory',
    'listening',
    'meaning',
    'dictation',
    'radio',
    'errors',
)
_STATS_MODE_RANK = {mode: index for index, mode in enumerate(_STATS_MODE_ORDER)}
_STATS_MODE_ALIASES = {
    'choice': 'radio',
    'select': 'radio',
    'selection': 'radio',
    'quick_memory': 'quickmemory',
    'quick-memory': 'quickmemory',
    'five-dimension-game': 'game',
}


def _raw_mode_text(value) -> str:
    if value is None:
        return ''
    if isinstance(value, str):
        return value.strip().lower()
    return str(value).strip().lower()


def normalize_stats_mode(value) -> str:
    mode = _raw_mode_text(value)
    if not mode:
        return ''
    normalized = _STATS_MODE_ALIASES.get(mode, mode)
    return normalized if normalized in _STATS_MODE_RANK else ''


def sort_stats_modes(values) -> list[str]:
    return sorted(values, key=lambda mode: (_STATS_MODE_RANK.get(mode, 999), mode))


def stats_mode_candidates(value) -> list[str]:
    normalized = normalize_stats_mode(value)
    if not normalized:
        raw_mode = _raw_mode_text(value) if isinstance(value, str) else ''
        return [raw_mode] if raw_mode else []

    candidates = {
        normalized,
        *[
            alias
            for alias, target in _STATS_MODE_ALIASES.items()
            if target == normalized
        ],
    }
    return sorted(candidate for candidate in candidates if candidate)


__all__ = [
    'normalize_stats_mode',
    'sort_stats_modes',
    'stats_mode_candidates',
]
