from services._split_loader import load_split_module_parts


load_split_module_parts(
    __file__,
    (
        'ai_parts/part_01.py',
        'ai_parts/part_02.py',
        'ai_parts/part_03.py',
        'ai_parts/part_04.py',
        'ai_parts/part_05.py',
        'ai_parts/part_06.py',
        'ai_parts/part_07.py',
        'ai_parts/part_08.py',
        'ai_parts/part_09.py',
        'ai_parts/part_10.py',
        'ai_parts/part_11.py',
        'ai_parts/part_12.py',
    ),
    globals(),
)
