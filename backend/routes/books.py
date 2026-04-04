from services._split_loader import load_split_module_parts


load_split_module_parts(
    __file__,
    (
        'books_parts/part_01.py',
        'books_parts/part_02.py',
        'books_parts/part_03.py',
        'books_parts/part_04.py',
        'books_parts/part_05.py',
    ),
    globals(),
)
