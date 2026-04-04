from services._split_loader import load_split_module_parts


load_split_module_parts(
    __file__,
    (
        'test_stats_api_contract_parts/part_01.py',
        'test_stats_api_contract_parts/part_02.py',
        'test_stats_api_contract_parts/part_03.py',
    ),
    globals(),
)
