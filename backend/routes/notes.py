from services._split_loader import load_split_module_parts


load_split_module_parts(
    __file__,
    (
        'notes_parts/part_01.py',
        'notes_parts/part_02.py',
    ),
    globals(),
)
