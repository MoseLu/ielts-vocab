from __future__ import annotations

from services import legacy_word_detail_repository, word_catalog_repository
from services.word_catalog_service import (
    build_default_derivative_payload,
    build_default_root_payload,
    get_word_seed,
    normalize_word_key,
    upsert_word_catalog_entry,
)


LEGACY_SOURCE = 'legacy_migration'


def _collect_query_words(query, attr_name: str) -> set[str]:
    words = set()
    for item in query:
        key = normalize_word_key(getattr(item, attr_name, ''))
        if key:
            words.add(key)
    return words


def collect_legacy_normalized_words(words: list[str] | None = None) -> list[str]:
    if words:
        return sorted({normalize_word_key(word) for word in words if normalize_word_key(word)})

    normalized_words = set()
    normalized_words |= _collect_query_words(
        legacy_word_detail_repository.list_root_details(),
        'normalized_word',
    )
    normalized_words |= _collect_query_words(
        legacy_word_detail_repository.list_english_meanings(),
        'normalized_word',
    )
    normalized_words |= _collect_query_words(
        legacy_word_detail_repository.list_example_entries(),
        'normalized_word',
    )
    normalized_words |= _collect_query_words(
        legacy_word_detail_repository.list_derivative_entries(),
        'normalized_base_word',
    )
    return sorted(normalized_words)


def _legacy_root_payload(normalized_word: str, display_word: str) -> dict:
    record = legacy_word_detail_repository.get_root_detail(normalized_word)
    if record and record.get_segments():
        return {
            'segments': record.get_segments(),
            'summary': record.summary or '',
        }
    return build_default_root_payload(display_word)


def _legacy_english_entries(normalized_word: str) -> list[dict]:
    record = legacy_word_detail_repository.get_english_meaning(normalized_word)
    return record.get_entries() if record else []


def _legacy_derivatives(normalized_word: str) -> list[dict]:
    records = legacy_word_detail_repository.list_derivatives(normalized_word)
    return [record.to_dict() for record in records]


def _legacy_examples(normalized_word: str) -> list[dict]:
    records = legacy_word_detail_repository.list_examples(normalized_word)
    return [record.to_dict() for record in records]


def _current_root_payload(record) -> dict:
    return {
        'segments': record.get_root_segments(),
        'summary': record.root_summary or '',
    }


def migrate_legacy_word_details(
    *,
    words: list[str] | None = None,
    limit: int | None = None,
    start_at: int = 0,
    overwrite: bool = False,
    commit_interval: int = 200,
) -> dict:
    candidates = collect_legacy_normalized_words(words)
    if start_at > 0:
        candidates = candidates[start_at:]
    if limit is not None:
        candidates = candidates[:limit]

    stats = {'total': len(candidates), 'migrated': 0, 'skipped': 0}
    for index, normalized_word in enumerate(candidates, start=1):
        seed = get_word_seed(normalized_word)
        record = word_catalog_repository.get_word_catalog_entry(normalized_word)

        legacy_root = _legacy_root_payload(normalized_word, seed['display_word'])
        legacy_english = _legacy_english_entries(normalized_word)
        legacy_derivatives = _legacy_derivatives(normalized_word)
        legacy_examples = _legacy_examples(normalized_word)

        needs_root = overwrite or not record or not record.get_root_segments()
        needs_english = overwrite or not record or not record.get_english_entries()
        needs_derivatives = overwrite or not record or not record.get_derivatives()
        needs_examples = overwrite or not record or not record.get_examples()

        if not any((needs_root, needs_english, needs_derivatives, needs_examples)):
            stats['skipped'] += 1
            continue

        root_payload = legacy_root if needs_root else _current_root_payload(record)
        english_entries = legacy_english if needs_english else record.get_english_entries()
        derivative_entries = legacy_derivatives if needs_derivatives else record.get_derivatives()
        example_entries = legacy_examples if needs_examples else record.get_examples()

        if not root_payload.get('segments'):
            root_payload = build_default_root_payload(seed['display_word'])
        if not derivative_entries:
            derivative_entries = build_default_derivative_payload(seed['normalized_word'])
        if not example_entries:
            example_entries = seed['examples']

        source = LEGACY_SOURCE
        if record and record.source == 'llm' and not overwrite:
            source = 'llm'

        upsert_word_catalog_entry(
            seed,
            root_payload=root_payload,
            english_entries=english_entries,
            derivative_entries=derivative_entries,
            example_entries=example_entries,
            source=source,
        )
        stats['migrated'] += 1

        if index % commit_interval == 0:
            word_catalog_repository.commit()

    word_catalog_repository.commit()
    return stats
