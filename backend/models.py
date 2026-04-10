from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'model_definitions/core_models.py',
        'model_definitions/word_preference_models.py',
        'model_definitions/word_detail_models.py',
        'model_definitions/study_models.py',
        'model_definitions/note_models.py',
        'model_definitions/eventing_models.py',
    ),
    globals(),
)
