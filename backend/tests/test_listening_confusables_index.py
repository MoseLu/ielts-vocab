import csv
import json
from pathlib import Path

from services.listening_confusables import (
    get_listening_confusables_path,
    get_preset_listening_confusables,
    normalize_listening_confusable_key,
)


def iter_source_words(base_dir: Path, source_name: str):
    source_path = base_dir / source_name

    if source_name.endswith('.csv'):
        with source_path.open('r', encoding='utf-8-sig', newline='') as file_obj:
            for row in csv.DictReader(file_obj):
                yield row
        return

    payload = json.loads(source_path.read_text(encoding='utf-8'))
    if isinstance(payload, dict) and 'chapters' in payload:
        for chapter in payload.get('chapters', []):
            for word in chapter.get('words', []):
                yield word
        return

    if isinstance(payload, list):
        for word in payload:
            yield word


def test_listening_confusables_index_covers_all_supported_source_words():
    index_path = Path(get_listening_confusables_path())
    payload = json.loads(index_path.read_text(encoding='utf-8'))
    index = payload['words']
    minimum_candidates = int(payload['minimum_candidates'])
    candidate_limit = int(payload['candidate_limit'])

    expected_words: set[str] = set()
    for source_name in payload['sources']:
        for raw_word in iter_source_words(index_path.parent, source_name):
            word = normalize_listening_confusable_key(raw_word.get('word'))
            definition = str(raw_word.get('definition', '') or raw_word.get('translation', '')).strip()
            if not word or not definition:
                continue
            expected_words.add(word)

    assert set(index) == expected_words
    assert payload['total_words'] == len(index)

    for word, candidates in index.items():
        assert minimum_candidates <= len(candidates) <= candidate_limit

        seen_candidates: set[str] = set()
        for candidate in candidates:
            candidate_key = normalize_listening_confusable_key(candidate.get('word'))
            assert candidate_key
            assert candidate_key != word
            assert candidate_key not in seen_candidates
            seen_candidates.add(candidate_key)


def test_listening_confusables_lookup_normalizes_edge_case_words():
    assert get_preset_listening_confusables('worry n.', limit=3)
    assert get_preset_listening_confusables("students' union", limit=3)
    assert get_preset_listening_confusables('both...and', limit=3)
