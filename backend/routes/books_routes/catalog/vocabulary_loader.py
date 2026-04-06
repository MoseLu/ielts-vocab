from models import WordCatalogEntry

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
    """Load examples from the unified word catalog once per process."""
    global _catalog_examples_cache
    if _catalog_examples_cache is not None:
        return _catalog_examples_cache

    loaded_examples = {}
    try:
        rows = WordCatalogEntry.query.all()
        for row in rows:
            normalized_word = str(row.normalized_word or '').strip().lower()
            examples = row.get_examples()
            if normalized_word and examples:
                loaded_examples[normalized_word] = examples
    except Exception:
        return {}

    _catalog_examples_cache = loaded_examples
    return _catalog_examples_cache


def _load_examples():
    """Load example sentences from vocabulary_examples.json once."""
    global _examples_cache
    if _examples_cache is not None:
        return _examples_cache

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, 'vocabulary_examples.json')
    _examples_cache = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        examples_map = data.get('examples', {})
        # Normalise: support both string keys and store lowercase keys for fast lookup
        for word, ex_list in examples_map.items():
            if ex_list:
                _examples_cache[word.lower()] = ex_list
    except Exception as e:
        print(f"Warning: could not load vocabulary examples: {e}")
        _examples_cache = {}
    return _examples_cache


def _merge_examples(word_entry):
    """Add examples to a word entry, preferring unified catalog content."""
    word_text = word_entry.get('word', '').strip()
    if not word_text:
        return word_entry
    normalized_word = word_text.lower()
    examples = _load_catalog_examples().get(normalized_word) or _load_examples().get(normalized_word)
    if examples:
        return {**word_entry, 'examples': examples}
    return word_entry


def _enrich_word_entry(word_entry):
    return attach_preset_listening_confusables(_merge_examples(word_entry), limit=6)


def get_vocab_data_path():
    """Get the path to vocabulary_data directory"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'vocabulary_data')


def _normalize_chapter_title(title, chapter_id=None):
    """Repair known mojibake placeholders in chapter titles before returning them to clients."""
    if title is None:
        return f'第{chapter_id}章' if chapter_id is not None else ''

    normalized = ' '.join(str(title).split())
    match = _CORRUPTED_CHAPTER_TITLE_RE.fullmatch(normalized)
    if match:
        chapter_number, word_range = match.groups()
        return f'第{chapter_number}章 {word_range}'

    return normalized


def _chunk_group(label, rows_with_indices, chunk_size, starting_id):
    """
    Split a group of (original_index, row) tuples into chunk_size chapters.
    Returns list of chapter dicts and the next available chapter id.
    """
    chapters = []
    total_chunks = (len(rows_with_indices) + chunk_size - 1) // chunk_size
    chapter_id = starting_id

    for chunk_num, offset in enumerate(range(0, len(rows_with_indices), chunk_size), start=1):
        chunk = rows_with_indices[offset:offset + chunk_size]
        title = label if total_chunks == 1 else f'{label} · Part {chunk_num}'
        chapters.append({
            'id': chapter_id,
            'title': title,
            'word_count': len(chunk),
            'row_indices': [i for i, _ in chunk],
        })
        chapter_id += 1

    return chapters, chapter_id


def _build_csv_chapters(book_id):
    """
    Read the CSV file for book_id and build a list of chapter dicts.
    Each chapter: {id, title, word_count, row_indices: [int, ...]}.
    Results are stored in _csv_chapter_cache[book_id].
    """
    if book_id in _csv_chapter_cache:
        return

    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book or not book['file'].endswith('.csv'):
        return

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, book['file'])

    try:
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            raw_rows = list(csv_module.DictReader(f))
    except Exception as e:
        print(f"Error reading CSV for chapters ({book_id}): {e}")
        return

    groups = CSV_CHAPTER_GROUPS.get(book_id)
    if not groups:
        # No grouping defined → single sequential chunking
        indexed = list(enumerate(raw_rows))
        chapters, _ = _chunk_group('Unit', indexed, CSV_CHAPTER_SIZE, 1)
        _csv_chapter_cache[book_id] = {'chapters': chapters, 'row_data': raw_rows}
        return

    assigned_indices = set()
    chapters = []
    next_id = 1

    for (label, predicate) in groups:
        matched = [
            (i, r) for i, r in enumerate(raw_rows)
            if i not in assigned_indices and predicate(r)
        ]
        if not matched:
            continue
        new_chapters, next_id = _chunk_group(label, matched, CSV_CHAPTER_SIZE, next_id)
        chapters.extend(new_chapters)
        for i, _ in matched:
            assigned_indices.add(i)

    # Remaining unassigned rows → catch-all
    remaining = [(i, r) for i, r in enumerate(raw_rows) if i not in assigned_indices]
    if remaining:
        extra, _ = _chunk_group('其他词汇', remaining, CSV_CHAPTER_SIZE, next_id)
        chapters.extend(extra)

    _csv_chapter_cache[book_id] = {'chapters': chapters, 'row_data': raw_rows}
    print(f"Built {len(chapters)} chapters for '{book_id}' "
          f"covering {sum(c['word_count'] for c in chapters)} words")


def _build_json_chapters(book_id):
    """
    Read a flat-JSON file for book_id and build chapter dicts using JSON_CHAPTER_GROUPS.
    Each chapter: {id, title, word_count, word_indices: [int, ...]}.
    Results stored in _json_chapter_cache[book_id].
    """
    if book_id in _json_chapter_cache:
        return

    book = next((b for b in VOCAB_BOOKS if b['id'] == book_id), None)
    if not book or not book['file'].endswith('.json'):
        return

    vocab_path = get_vocab_data_path()
    file_path = os.path.join(vocab_path, book['file'])

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except Exception as e:
        print(f"Error reading JSON for chapters ({book_id}): {e}")
        return

    # Only handle flat list JSON here; structured JSON is handled inline
    if not isinstance(data, list):
        return

    groups = JSON_CHAPTER_GROUPS.get(book_id)
    chapters = []
    next_id = 1

    if groups:
        assigned = set()
        for (label, predicate) in groups:
            matched = [(i, w) for i, w in enumerate(data) if i not in assigned and predicate(w)]
            if not matched:
                continue
            new_chapters, next_id = _chunk_group(label, matched, CSV_CHAPTER_SIZE, next_id)
            # Rename row_indices → word_indices for clarity
            for ch in new_chapters:
                ch['word_indices'] = ch.pop('row_indices')
            chapters.extend(new_chapters)
            for i, _ in matched:
                assigned.add(i)
        remaining = [(i, w) for i, w in enumerate(data) if i not in assigned]
        if remaining:
            extra, _ = _chunk_group('其他词汇', remaining, CSV_CHAPTER_SIZE, next_id)
            for ch in extra:
                ch['word_indices'] = ch.pop('row_indices')
            chapters.extend(extra)
    else:
        indexed = list(enumerate(data))
        chapters, _ = _chunk_group('Unit', indexed, CSV_CHAPTER_SIZE, 1)
        for ch in chapters:
            ch['word_indices'] = ch.pop('row_indices')

    _json_chapter_cache[book_id] = {'chapters': chapters, 'words': data}
    print(f"Built {len(chapters)} JSON chapters for '{book_id}' "
          f"covering {sum(c['word_count'] for c in chapters)} words")


def _normalize_csv_word(row):
    """Convert a CSV row dict to a normalized word dict."""
    normalized = {
        'word': row.get('word', '').strip(),
        'phonetic': row.get('phonetic', ''),
        'pos': row.get('pos', 'n.'),
        'definition': row.get('translation', '') or row.get('definition', ''),
    }
    return _copy_optional_word_fields(row, normalized)


def _copy_optional_word_fields(source_word, target_word):
    """Preserve optional metadata fields used by specialized practice modes."""
    group_key = source_word.get('group_key')
    if isinstance(group_key, str) and group_key.strip():
        target_word['group_key'] = group_key.strip()
    headword = source_word.get('headword')
    if isinstance(headword, str) and headword.strip():
        target_word['headword'] = headword.strip()
    return target_word
