from services._split_loader import load_split_module_parts


load_split_module_parts(
    __file__,
    (
        'models_parts/part_01.py',
        'models_parts/part_02.py',
        'models_parts/part_03.py',
    ),
    globals(),
)
