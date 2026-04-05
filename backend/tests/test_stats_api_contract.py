from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'test_stats_api_contract_cases/helpers.py',
        'test_stats_api_contract_cases/fixtures.py',
        'test_stats_api_contract_cases/contracts.py',
    ),
    globals(),
)
