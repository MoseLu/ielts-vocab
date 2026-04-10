def ensure_word_catalog_entry(
    word: str,
    *,
    book_ids: tuple[str, ...] | None = None,
) -> tuple[WordCatalogEntry, bool]:
    seed = get_word_seed(word, book_ids=book_ids)
    normalized = seed['normalized_word']
    record = word_catalog_repository.get_word_catalog_entry(normalized)
    created = record is None
    changed = created

    if not record:
        record = word_catalog_repository.create_word_catalog_entry(
            word=seed['display_word'],
            normalized_word=normalized,
        )
        word_catalog_repository.flush()

    if seed['display_word'] and record.word != seed['display_word']:
        record.word = seed['display_word']
        changed = True
    if seed['phonetic'] and record.phonetic != seed['phonetic']:
        record.phonetic = seed['phonetic']
        changed = True
    if seed['pos'] and record.pos != seed['pos']:
        record.pos = seed['pos']
        changed = True
    if seed['definition'] and record.definition != seed['definition']:
        record.definition = seed['definition']
        changed = True

    if not record.get_root_segments():
        root_payload = build_default_root_payload(record.word)
        record.set_root_segments(root_payload['segments'])
        record.root_summary = root_payload['summary']
        changed = True
    if not record.get_derivatives():
        record.set_derivatives(build_default_derivative_payload(normalized, book_ids=book_ids))
        changed = True
    if not record.get_examples() and seed['examples']:
        record.set_examples(seed['examples'])
        changed = True

    book_refs_changed = False
    if seed['book_refs']:
        current_refs = record.get_book_refs()
        if current_refs != seed['book_refs']:
            record.set_book_refs(seed['book_refs'])
            changed = True
            book_refs_changed = True

    if created and not record.source:
        record.source = 'catalog'

    word_catalog_repository.flush()
    if seed['book_refs'] and (created or book_refs_changed):
        _replace_book_refs(record, seed['book_refs'])

    return record, changed


def upsert_word_catalog_entry(
    word_seed: dict,
    *,
    root_payload: dict,
    english_entries: list[dict],
    derivative_entries: list[dict],
    example_entries: list[dict],
    source: str,
) -> WordCatalogEntry:
    normalized = word_seed['normalized_word']
    record = word_catalog_repository.get_word_catalog_entry(normalized)
    if not record:
        record = word_catalog_repository.create_word_catalog_entry(
            word=word_seed['display_word'],
            normalized_word=normalized,
        )
        word_catalog_repository.flush()

    record.word = word_seed['display_word']
    record.phonetic = word_seed.get('phonetic', '')
    record.pos = word_seed.get('pos', '')
    record.definition = word_seed.get('definition', '')
    record.set_root_segments(root_payload.get('segments', []))
    record.root_summary = root_payload.get('summary', '')
    record.set_english_entries(english_entries)
    record.set_derivatives(derivative_entries)
    record.set_examples(example_entries)
    record.set_book_refs(word_seed.get('book_refs', []))
    record.source = source
    word_catalog_repository.flush()

    _replace_book_refs(record, word_seed.get('book_refs', []))
    return record


def materialize_word_catalog(
    *,
    book_ids: tuple[str, ...] | None = None,
    limit: int | None = None,
    start_at: int = 0,
    commit_interval: int = 200,
) -> dict:
    seeds = list(build_word_seed_index(book_ids).values())
    if start_at > 0:
        seeds = seeds[start_at:]
    if limit is not None:
        seeds = seeds[:limit]

    stats = {'total': len(seeds), 'created': 0, 'updated': 0}
    for index, seed in enumerate(seeds, start=1):
        existed = word_catalog_repository.get_word_catalog_entry(seed['normalized_word']) is not None
        _record, changed = ensure_word_catalog_entry(seed['normalized_word'], book_ids=book_ids)
        if not existed:
            stats['created'] += 1
        elif changed:
            stats['updated'] += 1

        if index % commit_interval == 0:
            word_catalog_repository.commit()

    word_catalog_repository.commit()
    return stats
