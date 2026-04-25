from __future__ import annotations


CURRENT_WORD_CACHE_TAG = 'azure-word-v6-ielts-rp-female-onset-buffer'
SEGMENTED_WORD_CACHE_TAG = 'azure-word-segmented-v2'
LEGACY_WORD_CACHE_TAG = 'azure-word-v5-ielts-rp-female-onset-buffer'
RYAN_WORD_AUDIO_VOICE = 'en-GB-RyanNeural'
LEGACY_NORMAL_WORD_VOICES = ('en-GB-LibbyNeural',)
LEGACY_SEGMENTED_WORD_VOICES = ('en-GB-LibbyNeural',)
RYAN_WORD_AUDIO_OVERRIDES = frozenset({
    'brag', 'branch', 'brash', 'brass', 'brave', 'breach', 'bread', 'breadth',
    'breed', 'breeding', 'brew', 'brewery', 'brick', 'bridle', 'brim',
    'brochure', 'broker', 'broom', 'brought', 'brute',
})
