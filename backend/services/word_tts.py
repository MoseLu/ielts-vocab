from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'word_tts_service/audio_cache.py',
        'word_tts_service/synthesis_pipeline.py',
        'word_tts_service/batch_generation.py',
    ),
    globals(),
)
