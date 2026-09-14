import json
from pathlib import Path

from services.books_registry_service import get_vocab_book


VOCAB_ROOT = Path(__file__).resolve().parents[2] / 'vocabulary_data'


def test_ielts_vocab_supplements_merge_into_existing_books():
    extended = json.loads((VOCAB_ROOT / 'ielts_9400_extended.json').read_text(encoding='utf-8'))
    awl = json.loads((VOCAB_ROOT / 'ielts_vocabulary_awl_extended.json').read_text(encoding='utf-8'))

    assert get_vocab_book('ielts_vocab_master') is None
    assert get_vocab_book('ielts_9400_extended')['word_count'] == extended['total_words']
    assert get_vocab_book('awl_academic')['word_count'] == len(awl)


def test_ielts_vocab_supplements_include_cross_source_gap_fillers():
    extended = json.loads((VOCAB_ROOT / 'ielts_9400_extended.json').read_text(encoding='utf-8'))
    awl = json.loads((VOCAB_ROOT / 'ielts_vocabulary_awl_extended.json').read_text(encoding='utf-8'))
    extended_words = {row['word'] for chapter in extended['chapters'] for row in chapter['words']}
    awl_words = {row['word'] for row in awl}

    assert {'albeit', 'append', 'invoke', 'utilise'} <= awl_words
    assert {'artificial intelligence', 'single-use plastic', 'come to a conclusion', 'look into'} <= extended_words
