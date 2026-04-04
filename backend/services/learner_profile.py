from services._split_loader import load_split_module_parts


load_split_module_parts(
    __file__,
    (
        'learner_profile_parts/part_01.py',
        'learner_profile_parts/part_02.py',
        'learner_profile_parts/part_03.py',
        'learner_profile_parts/part_04.py',
    ),
    globals(),
)
