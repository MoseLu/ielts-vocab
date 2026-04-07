from models import WordCatalogEntry
from services.books_vocabulary_loader_service import (
    build_csv_chapters as _build_csv_chapters_service,
    build_json_chapters as _build_json_chapters_service,
    chunk_group as _chunk_group_service,
    copy_optional_word_fields as _copy_optional_word_fields_service,
    enrich_word_entry as _enrich_word_entry_service,
    get_vocab_data_path as _get_vocab_data_path_service,
    load_catalog_examples as _load_catalog_examples_service,
    load_examples as _load_examples_service,
    merge_examples as _merge_examples_service,
    normalize_chapter_title as _normalize_chapter_title_service,
    normalize_csv_word as _normalize_csv_word_service,
    resolve_unified_examples as _resolve_unified_examples_service,
)

CSV_CHAPTER_GROUPS = {
    # ── 雅思综合词汇5000+ ──────────────────────────────────────────────────
    'ielts_comprehensive': [
        # AWL学术词汇: grouped by sublist (sublist 1-4 each have 230-320 words)
        ('AWL学术词汇 Sublist 1',
            lambda r: r.get('source') == 'AWL' and r.get('sublist') == '1'),
        ('AWL学术词汇 Sublist 2',
            lambda r: r.get('source') == 'AWL' and r.get('sublist') == '2'),
        ('AWL学术词汇 Sublist 3',
            lambda r: r.get('source') == 'AWL' and r.get('sublist') == '3'),
        ('AWL学术词汇 Sublist 4',
            lambda r: r.get('source') == 'AWL' and r.get('sublist') == '4'),
        ('AWL学术词汇 其他',
            lambda r: r.get('source') == 'AWL'),

        # IELTS听力词汇: by listening topic
        ('听力词汇·住宿',
            lambda r: r.get('category') == 'listening_accommodation'),
        ('听力词汇·教育',
            lambda r: r.get('category') == 'listening_education'),
        ('听力词汇·交通',
            lambda r: r.get('category') in ('listening_travel_transport', 'listening_travel')),
        ('听力词汇·医疗',
            lambda r: r.get('category') in ('listening_medical', 'listening_medical_health')),
        ('听力词汇·银行金融',
            lambda r: r.get('category') == 'listening_banking'),
        ('听力词汇·就业职场',
            lambda r: r.get('category') == 'listening_employment'),
        ('听力词汇·购物',
            lambda r: r.get('category') == 'listening_shopping'),
        ('听力词汇·餐饮',
            lambda r: r.get('category') == 'listening_restaurant'),
        # remaining IELTS_Listening words not matched above
        ('听力词汇·综合',
            lambda r: r.get('source') == 'IELTS_Listening'),

        # IELTS写作词汇
        ('写作词汇',
            lambda r: r.get('source') == 'IELTS_Writing'),

        # IELTS口语词汇
        ('口语词汇',
            lambda r: r.get('source') == 'IELTS_Speaking'),

        # 学术短语
        ('学术短语',
            lambda r: r.get('source') == 'Academic_Phrases'),

        # Cambridge IELTS 高频词
        ('Cambridge IELTS高频词',
            lambda r: r.get('source') == 'Cambridge_IELTS'),

        # Oxford 3000核心词
        ('Oxford 3000核心词',
            lambda r: r.get('source') == 'Oxford_3000'),

        # IELTS核心词汇
        ('IELTS核心词汇',
            lambda r: r.get('source') == 'IELTS_Core'),

        # IELTS阅读词汇: by reading topic (small topic groups first)
        ('阅读词汇·科学技术',
            lambda r: r.get('category') in ('reading_science', 'reading_science_technology')),
        ('阅读词汇·环境',
            lambda r: r.get('category') == 'reading_environment'),
        ('阅读词汇·医疗健康',
            lambda r: r.get('category') in ('reading_health', 'reading_health_medicine')),
        ('阅读词汇·社会文化',
            lambda r: r.get('category') == 'reading_society_culture'),
        ('阅读词汇·心理学',
            lambda r: r.get('category') == 'reading_psychology'),

        # reading_society is the largest group (3003 words) — split into 50-word units
        ('IELTS阅读词汇',
            lambda r: r.get('source') == 'IELTS_Reading'),
    ],

    # ── 雅思终极词汇库 ──────────────────────────────────────────────────────
    'ielts_ultimate': [
        # AWL学术词汇 (1039 words, no sublist column in this CSV)
        ('AWL学术词汇',
            lambda r: r.get('category') == 'academic'),

        # 写作词汇
        ('写作词汇',
            lambda r: r.get('category') == 'writing'),

        # 听力词汇: by topic
        ('听力词汇·住宿',
            lambda r: r.get('category') == 'listening_accommodation'),
        ('听力词汇·教育',
            lambda r: r.get('category') == 'listening_education'),
        ('听力词汇·交通',
            lambda r: r.get('category') == 'listening_travel_transport'),
        ('听力词汇·医疗',
            lambda r: r.get('category') == 'listening_medical'),

        # 阅读词汇: by topic
        ('阅读词汇·科学技术',
            lambda r: r.get('category') == 'reading_science_technology'),
        ('阅读词汇·环境',
            lambda r: r.get('category') == 'reading_environment'),
        ('阅读词汇·医疗健康',
            lambda r: r.get('category') == 'reading_health_medicine'),
        ('阅读词汇·社会文化',
            lambda r: r.get('category') == 'reading_society_culture'),
        ('阅读词汇·心理学',
            lambda r: r.get('category') == 'reading_psychology'),

        # 口语词汇
        ('口语词汇',
            lambda r: r.get('category') == 'speaking'),

        # 学术短语
        ('学术短语',
            lambda r: r.get('category') == 'academic_phrases'),
    ],
}

# ── Flat-JSON chapter grouping rules ────────────────────────────────────────
# Same structure as CSV_CHAPTER_GROUPS but applies to flat JSON list books.
# Each entry: (chapter_label, filter_fn(word_dict) -> bool)
JSON_CHAPTER_GROUPS = {
    # ── AWL学术词汇表 ──────────────────────────────────────────────────────
    'awl_academic': [
        ('Sublist 1', lambda w: w.get('sublist') == 1),
        ('Sublist 2', lambda w: w.get('sublist') == 2),
        ('Sublist 3', lambda w: w.get('sublist') == 3),
        ('其他词汇',  lambda w: True),
    ],
}

# Cache for loaded vocabulary data
_vocabulary_cache = {}
# Cache for CSV chapter structures: {book_id: {'chapters': [...], 'row_data': [...]}}
_csv_chapter_cache = {}
# Cache for flat-JSON chapter structures: {book_id: {'chapters': [...], 'words': [...]}}
_json_chapter_cache = {}
# Cache for normalized word lookup used by custom confusable groups.
_confusable_lookup_cache = None
# Cache for catalog-backed examples: {word_lower: [examples]}
_catalog_examples_cache = None
# Cache for vocabulary examples: {word_lower: [examples]}
_examples_cache = None
_CORRUPTED_CHAPTER_TITLE_RE = re.compile(r'^[?？\uFFFD]\s*(\d+)\s*[?？\uFFFD]\s+(\d{4}-\d{4})$')


def _load_catalog_examples():
    return _load_catalog_examples_service()


def _load_examples():
    return _load_examples_service()


def _merge_examples(word_entry):
    return _merge_examples_service(word_entry)


def _resolve_unified_examples(word, fallback_examples=None, limit=1):
    return _resolve_unified_examples_service(
        word,
        fallback_examples=fallback_examples,
        limit=limit,
    )


def _enrich_word_entry(word_entry):
    return _enrich_word_entry_service(word_entry)


def get_vocab_data_path():
    return _get_vocab_data_path_service()


def _normalize_chapter_title(title, chapter_id=None):
    return _normalize_chapter_title_service(title, chapter_id=chapter_id)


def _chunk_group(label, rows_with_indices, chunk_size, starting_id):
    return _chunk_group_service(label, rows_with_indices, chunk_size, starting_id)


def _build_csv_chapters(book_id):
    return _build_csv_chapters_service(book_id)


def _build_json_chapters(book_id):
    return _build_json_chapters_service(book_id)


def _normalize_csv_word(row):
    return _normalize_csv_word_service(row)


def _copy_optional_word_fields(source_word, target_word):
    return _copy_optional_word_fields_service(source_word, target_word)
