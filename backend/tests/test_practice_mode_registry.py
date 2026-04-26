from platform_sdk.learning_stats_modes_support import (
    normalize_stats_mode,
    sort_stats_modes,
    stats_mode_candidates,
)
from platform_sdk.practice_mode_registry import (
    PRACTICE_MODE_KEYS,
    get_practice_mode_label,
    normalize_profile_practice_mode,
    sort_profile_practice_modes,
)
from services.learning_activity_service import normalize_learning_mode


def test_practice_mode_registry_covers_browser_modes_and_shared_aliases():
    assert PRACTICE_MODE_KEYS == (
        'game',
        'smart',
        'quickmemory',
        'listening',
        'meaning',
        'dictation',
        'radio',
        'errors',
        'speaking',
    )
    assert normalize_stats_mode('quick_memory') == 'quickmemory'
    assert normalize_stats_mode('choice') == 'radio'
    assert normalize_stats_mode('five-dimension-game') == 'game'
    assert normalize_profile_practice_mode('five-dimension-game') == 'game'
    assert normalize_learning_mode('quick-memory') == 'quickmemory'
    assert normalize_learning_mode('follow') == 'follow'


def test_practice_mode_registry_keeps_consistent_labels_candidates_and_sorting():
    assert get_practice_mode_label('smart') == '智能练习'
    assert get_practice_mode_label('smart', short=True) == '智能'
    assert get_practice_mode_label('game') == '五维闯关'
    assert get_practice_mode_label('missing', default='未知') == '未知'
    assert stats_mode_candidates('radio') == ['choice', 'radio', 'select', 'selection']
    assert stats_mode_candidates('custom-mode') == ['custom-mode']
    assert sort_stats_modes(['meaning', 'radio', 'game']) == ['game', 'meaning', 'radio']
    assert sort_profile_practice_modes(['quickmemory', 'game', 'smart']) == ['game', 'smart', 'quickmemory']
