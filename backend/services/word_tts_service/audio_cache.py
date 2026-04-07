from pathlib import Path

from services._module_loader import load_split_module_files


_MODULE_FILE = Path(__file__).resolve().parent / 'word_tts_service' / 'audio_cache.py'


load_split_module_files(
    str(_MODULE_FILE),
    (
        'audio_cache_parts/identity_and_fetch.py',
        'audio_cache_parts/providers_azure.py',
        'audio_cache_parts/providers_volcengine.py',
    'audio_cache_parts/audio_bytes.py',
    'audio_cache_parts/cache_policies.py',
    ),
    globals(),
)
