import json

from services import premium_word_mnemonic_catalog


def test_premium_mnemonic_catalog_rejects_low_quality_templates(monkeypatch, tmp_path):
    data_path = tmp_path / 'premium_word_mnemonics.json'
    data_path.write_text(json.dumps({
        'manifest_version': 1,
        'book_ids': ['ielts_reading_premium'],
        'generated_at': '2026-05-09T00:00:00Z',
        'items': {
            'racism': {
                'word': 'racism',
                'badge': '词根词缀',
                'text': '先抓 racism 的词形尾巴，再把它落到“种族主义”这个意思上。',
                'book_ids': ['ielts_reading_premium'],
                'source': 'premium_word_mnemonics',
            },
        },
    }, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(premium_word_mnemonic_catalog, 'PREMIUM_WORD_MNEMONICS_PATH', data_path)
    premium_word_mnemonic_catalog.clear_premium_mnemonic_cache()

    assert premium_word_mnemonic_catalog.get_premium_word_mnemonic('racism') is None


def test_premium_mnemonic_catalog_keeps_specific_root_notes(monkeypatch, tmp_path):
    data_path = tmp_path / 'premium_word_mnemonics.json'
    data_path.write_text(json.dumps({
        'manifest_version': 1,
        'book_ids': ['ielts_reading_premium'],
        'generated_at': '2026-05-09T00:00:00Z',
        'items': {
            'racism': {
                'word': 'racism',
                'badge': '词根词缀',
                'text': 'race 表“种族”，-ism 表“主义/观念”；racism 就是种族主义或种族歧视。',
                'book_ids': ['ielts_reading_premium'],
                'source': 'premium_word_mnemonics',
            },
        },
    }, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(premium_word_mnemonic_catalog, 'PREMIUM_WORD_MNEMONICS_PATH', data_path)
    premium_word_mnemonic_catalog.clear_premium_mnemonic_cache()

    note = premium_word_mnemonic_catalog.get_premium_word_mnemonic('racism')

    assert note is not None
    assert note['text'].startswith('race 表“种族”')
