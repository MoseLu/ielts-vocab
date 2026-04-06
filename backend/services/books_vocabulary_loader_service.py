from __future__ import annotations

from importlib import import_module


def _books_module():
    return import_module('routes.books')


def load_catalog_examples():
    books = _books_module()
    cached_examples = getattr(books, '_catalog_examples_cache', None)
    if cached_examples is not None:
        return cached_examples

    loaded_examples = {}
    try:
        rows = books.WordCatalogEntry.query.all()
        for row in rows:
            normalized_word = str(row.normalized_word or '').strip().lower()
            examples = row.get_examples()
            if normalized_word and examples:
                loaded_examples[normalized_word] = examples
    except Exception:
        return {}

    books._catalog_examples_cache = loaded_examples
    return books._catalog_examples_cache


def load_examples():
    books = _books_module()
    cached_examples = getattr(books, '_examples_cache', None)
    if cached_examples is not None:
        return cached_examples

    file_path = books.os.path.join(get_vocab_data_path(), 'vocabulary_examples.json')
    books._examples_cache = {}
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = books.json.load(file)
        for word, example_list in data.get('examples', {}).items():
            if example_list:
                books._examples_cache[word.lower()] = example_list
    except Exception as exc:
        print(f"Warning: could not load vocabulary examples: {exc}")
        books._examples_cache = {}
    return books._examples_cache


def merge_examples(word_entry):
    word_text = word_entry.get('word', '').strip()
    if not word_text:
        return word_entry

    normalized_word = word_text.lower()
    examples = load_catalog_examples().get(normalized_word) or load_examples().get(normalized_word)
    if examples:
        return {**word_entry, 'examples': examples}
    return word_entry


def enrich_word_entry(word_entry):
    books = _books_module()
    return books.attach_preset_listening_confusables(merge_examples(word_entry), limit=6)


def get_vocab_data_path():
    books = _books_module()
    return books.os.path.join(
        books.os.path.dirname(books.os.path.abspath(books.__file__)),
        '..',
        '..',
        'vocabulary_data',
    )


def normalize_chapter_title(title, chapter_id=None):
    books = _books_module()
    if title is None:
        return f'第{chapter_id}章' if chapter_id is not None else ''

    normalized = ' '.join(str(title).split())
    match = books._CORRUPTED_CHAPTER_TITLE_RE.fullmatch(normalized)
    if match:
        chapter_number, word_range = match.groups()
        return f'第{chapter_number}章 {word_range}'
    return normalized


def chunk_group(label, rows_with_indices, chunk_size, starting_id):
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
            'row_indices': [index for index, _ in chunk],
        })
        chapter_id += 1

    return chapters, chapter_id


def build_csv_chapters(book_id):
    books = _books_module()
    if book_id in books._csv_chapter_cache:
        return

    book = next((item for item in books.VOCAB_BOOKS if item['id'] == book_id), None)
    if not book or not book['file'].endswith('.csv'):
        return

    file_path = books.os.path.join(get_vocab_data_path(), book['file'])
    try:
        with open(file_path, 'r', encoding='utf-8-sig') as file:
            raw_rows = list(books.csv_module.DictReader(file))
    except Exception as exc:
        print(f"Error reading CSV for chapters ({book_id}): {exc}")
        return

    groups = books.CSV_CHAPTER_GROUPS.get(book_id)
    if not groups:
        indexed_rows = list(enumerate(raw_rows))
        chapters, _ = chunk_group('Unit', indexed_rows, books.CSV_CHAPTER_SIZE, 1)
        books._csv_chapter_cache[book_id] = {'chapters': chapters, 'row_data': raw_rows}
        return

    assigned_indices = set()
    chapters = []
    next_id = 1
    for label, predicate in groups:
        matched = [
            (index, row)
            for index, row in enumerate(raw_rows)
            if index not in assigned_indices and predicate(row)
        ]
        if not matched:
            continue
        new_chapters, next_id = chunk_group(label, matched, books.CSV_CHAPTER_SIZE, next_id)
        chapters.extend(new_chapters)
        for index, _ in matched:
            assigned_indices.add(index)

    remaining = [(index, row) for index, row in enumerate(raw_rows) if index not in assigned_indices]
    if remaining:
        extra_chapters, _ = chunk_group('其他词汇', remaining, books.CSV_CHAPTER_SIZE, next_id)
        chapters.extend(extra_chapters)

    books._csv_chapter_cache[book_id] = {'chapters': chapters, 'row_data': raw_rows}
    print(
        f"Built {len(chapters)} chapters for '{book_id}' "
        f"covering {sum(chapter['word_count'] for chapter in chapters)} words"
    )


def build_json_chapters(book_id):
    books = _books_module()
    if book_id in books._json_chapter_cache:
        return

    book = next((item for item in books.VOCAB_BOOKS if item['id'] == book_id), None)
    if not book or not book['file'].endswith('.json'):
        return

    file_path = books.os.path.join(get_vocab_data_path(), book['file'])
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            data = books.json.load(file)
    except Exception as exc:
        print(f"Error reading JSON for chapters ({book_id}): {exc}")
        return

    if not isinstance(data, list):
        return

    groups = books.JSON_CHAPTER_GROUPS.get(book_id)
    chapters = []
    next_id = 1

    if groups:
        assigned = set()
        for label, predicate in groups:
            matched = [
                (index, word)
                for index, word in enumerate(data)
                if index not in assigned and predicate(word)
            ]
            if not matched:
                continue
            new_chapters, next_id = chunk_group(label, matched, books.CSV_CHAPTER_SIZE, next_id)
            for chapter in new_chapters:
                chapter['word_indices'] = chapter.pop('row_indices')
            chapters.extend(new_chapters)
            for index, _ in matched:
                assigned.add(index)

        remaining = [(index, word) for index, word in enumerate(data) if index not in assigned]
        if remaining:
            extra_chapters, _ = chunk_group('其他词汇', remaining, books.CSV_CHAPTER_SIZE, next_id)
            for chapter in extra_chapters:
                chapter['word_indices'] = chapter.pop('row_indices')
            chapters.extend(extra_chapters)
    else:
        indexed_words = list(enumerate(data))
        chapters, _ = chunk_group('Unit', indexed_words, books.CSV_CHAPTER_SIZE, 1)
        for chapter in chapters:
            chapter['word_indices'] = chapter.pop('row_indices')

    books._json_chapter_cache[book_id] = {'chapters': chapters, 'words': data}
    print(
        f"Built {len(chapters)} JSON chapters for '{book_id}' "
        f"covering {sum(chapter['word_count'] for chapter in chapters)} words"
    )


def normalize_csv_word(row):
    normalized = {
        'word': row.get('word', '').strip(),
        'phonetic': row.get('phonetic', ''),
        'pos': row.get('pos', 'n.'),
        'definition': row.get('translation', '') or row.get('definition', ''),
    }
    return copy_optional_word_fields(row, normalized)


def copy_optional_word_fields(source_word, target_word):
    group_key = source_word.get('group_key')
    if isinstance(group_key, str) and group_key.strip():
        target_word['group_key'] = group_key.strip()

    headword = source_word.get('headword')
    if isinstance(headword, str) and headword.strip():
        target_word['headword'] = headword.strip()
    return target_word
