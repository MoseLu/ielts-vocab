import services.books_catalog_service as books_catalog_service
import services.word_memory_note_enrichment as word_memory_note_enrichment
from models import WordCatalogEntry


def _seed_catalog():
    return [
        {
            'word': 'stout',
            'phonetic': '/staʊt/',
            'pos': 'adj.',
            'definition': '粗壮的；结实的',
            'examples': [{'en': 'The old oak tree remained stout in the storm.', 'zh': '老橡树在风暴里依旧粗壮坚挺。'}],
            'book_id': 'ielts_reading_premium',
            'book_title': 'Reading Premium',
        },
        {
            'word': 'a bit',
            'phonetic': '/ə bɪt/',
            'pos': 'adv.',
            'definition': '稍微；有点',
            'examples': [{'en': 'I am a bit tired after the lecture.', 'zh': '讲座结束后我有点累。'}],
            'book_id': 'ielts_listening_premium',
            'book_title': 'Listening Premium',
        },
    ]


def test_memory_note_enrichment_persists_server_notes(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    monkeypatch.setattr(word_memory_note_enrichment, 'request_memory_note_batch', lambda *_args, **_kwargs: {
        'stout': {
            'word': 'stout',
            'badge': '联想',
            'text': '先想一个人站得又稳又壮，再把“粗壮的；结实的”这个意思挂上去。',
        },
        'a bit': {
            'word': 'a bit',
            'badge': '联想',
            'text': '想象老师说再等一小会儿，就是“稍微；有点”这么一点点。',
        },
    })

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            batch_size=2,
            overwrite=True,
            sleep_seconds=0,
        )

        assert stats['enriched'] == 2
        assert stats['failed'] == 0

        stout = WordCatalogEntry.query.filter_by(normalized_word='stout').first()
        phrase = WordCatalogEntry.query.filter_by(normalized_word='a bit').first()
        assert stout.get_memory_note()['source'] == 'llm_memory'
        assert '粗壮的' in stout.get_memory_note()['text']
        assert '稍微' in phrase.get_memory_note()['text']


def test_memory_note_enrichment_rejects_formulaic_phrase_output(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    monkeypatch.setattr(word_memory_note_enrichment, 'request_memory_note_batch', lambda *_args, **_kwargs: {
        'a bit': {
            'word': 'a bit',
            'badge': '联想',
            'text': 'a + bit',
        },
    })

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            words=['a bit'],
            batch_size=1,
            overwrite=True,
            sleep_seconds=0,
        )

        assert stats['enriched'] == 0
        assert stats['failed'] == 1
        assert stats['failed_words'] == ['a bit']

        phrase = WordCatalogEntry.query.filter_by(normalized_word='a bit').first()
        assert phrase is None or phrase.get_memory_note() is None


def test_memory_note_enrichment_rejects_missing_definition_anchor(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    monkeypatch.setattr(word_memory_note_enrichment, 'request_memory_note_batch', lambda *_args, **_kwargs: {
        'stout': {
            'word': 'stout',
            'badge': '联想',
            'text': '想象一个人站得特别稳，整个人看起来很有力量。',
        },
    })

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            words=['stout'],
            batch_size=1,
            overwrite=True,
            sleep_seconds=0,
        )

        assert stats['enriched'] == 0
        assert stats['failed'] == 1
        assert stats['failed_words'] == ['stout']


def test_memory_note_enrichment_emits_progress_updates(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    monkeypatch.setattr(word_memory_note_enrichment, 'request_memory_note_batch', lambda *_args, **_kwargs: {
        'stout': {
            'word': 'stout',
            'badge': '联想',
            'text': '先想一个人站得又稳又壮，再把“粗壮的；结实的”这个意思挂上去。',
        },
        'a bit': {
            'word': 'a bit',
            'badge': '联想',
            'text': '想象老师说再等一小会儿，就是“稍微；有点”这么一点点。',
        },
    })
    snapshots = []

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            batch_size=1,
            overwrite=True,
            sleep_seconds=0,
            progress_callback=lambda current: snapshots.append(current),
        )

        assert stats['enriched'] == 2
        assert snapshots
        assert snapshots[-1]['enriched'] == 2
        assert snapshots[-1]['completed_batches'] == snapshots[-1]['total_batches'] == 2
