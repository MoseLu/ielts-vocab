from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'tts_routes/sentence_audio.py',
        'tts_routes/batch_and_word_audio.py',
        'tts_routes/follow_read.py',
    ),
    globals(),
)
