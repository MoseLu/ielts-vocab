from services._split_loader import load_split_module_parts


load_split_module_parts(
    __file__,
    (
        'test_learner_profile_parts/part_01.py',
        'test_learner_profile_parts/part_02.py',
    ),
    globals(),
)
