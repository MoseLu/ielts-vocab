from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'test_learner_profile_cases/profile_dimensions.py',
        'test_learner_profile_cases/daily_plan.py',
    ),
    globals(),
)
