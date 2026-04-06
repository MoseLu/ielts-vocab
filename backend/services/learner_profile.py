from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'learner_profile_service/core_dimensions.py',
        'learner_profile_service/timed_dimensions.py',
        'learner_profile_service/recommendations.py',
        'learner_profile_service/profile_builder.py',
    ),
    globals(),
)
