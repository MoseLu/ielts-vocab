from services._module_loader import load_split_module_files


load_split_module_files(
    __file__,
    (
        'word_detail_enrichment_parts/sanitizers_and_seeds.py',
    'word_detail_enrichment_parts/batch_enrichment.py',
    'word_detail_enrichment_parts/entrypoints.py',
    ),
    globals(),
)
