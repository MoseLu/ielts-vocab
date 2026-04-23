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


def test_collect_memory_word_seeds_reads_catalog_entries(monkeypatch):
    class _FakeRecord:
        def __init__(self, word, book_refs, definition='定义'):
            self.word = word
            self.normalized_word = word.lower()
            self.phonetic = '/test/'
            self.pos = 'n.'
            self.definition = definition
            self._book_refs = book_refs

        def get_examples(self):
            return [{'en': f'{self.word} example', 'zh': '例句'}]

        def get_book_refs(self):
            return list(self._book_refs)

    monkeypatch.setattr(
        word_memory_note_enrichment.word_catalog_repository,
        'list_all_word_catalog_entries',
        lambda: [
            _FakeRecord('zeta', [{'book_id': 'ielts_reading_premium'}]),
            _FakeRecord('alpha', [{'book_id': 'ielts_listening_premium'}]),
            _FakeRecord('other', [{'book_id': 'ielts_comprehensive'}]),
        ],
    )

    seeds = word_memory_note_enrichment.collect_memory_word_seeds()

    assert [seed['normalized_word'] for seed in seeds] == ['alpha', 'zeta']
    assert seeds[0]['book_ids'] == ['ielts_listening_premium']
    assert seeds[1]['book_ids'] == ['ielts_reading_premium']


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


def test_memory_note_enrichment_retries_rate_limit_until_success(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    sleeps = []
    attempts = {'count': 0}

    def fake_request(*_args, **_kwargs):
        attempts['count'] += 1
        if attempts['count'] == 1:
            raise RuntimeError('minimax-primary http 429: usage limit exceeded (2056)')
        return {
            'stout': {
                'word': 'stout',
                'badge': '联想',
                'text': '先想一个人站得又稳又壮，再把“粗壮的；结实的”这个意思挂上去。',
            },
        }

    monkeypatch.setattr(word_memory_note_enrichment, 'request_memory_note_batch', fake_request)
    monkeypatch.setattr(word_memory_note_enrichment.time, 'sleep', lambda seconds: sleeps.append(seconds))
    monkeypatch.setattr(word_memory_note_enrichment.random, 'uniform', lambda *_args: 0.0)

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            words=['stout'],
            batch_size=1,
            overwrite=True,
            sleep_seconds=0,
            rate_limit_base_sleep_seconds=3,
            rate_limit_max_sleep_seconds=30,
        )

        assert attempts['count'] == 2
        assert stats['enriched'] == 1
        assert stats['failed'] == 0
        assert stats['rate_limit_retries'] == 1
        assert stats['rate_limit_wait_seconds'] == 3
        assert sleeps == [3]


def test_memory_note_enrichment_stops_on_real_quota_exhaustion(app, monkeypatch):
    monkeypatch.setattr(books_catalog_service, '_build_global_word_search_catalog', _seed_catalog)
    monkeypatch.setattr(
        word_memory_note_enrichment,
        'request_memory_note_batch',
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError('your current token plan not support model, MiniMax-M2.7 (2061)'),
        ),
    )

    with app.app_context():
        stats = word_memory_note_enrichment.enrich_premium_book_memory_notes(
            words=['stout'],
            batch_size=1,
            overwrite=True,
            sleep_seconds=0,
        )

        assert stats['quota_exhausted'] is True
        assert 'token plan not support model' in stats['stop_reason']
        assert stats['failed'] == 1
        assert stats['enriched'] == 0
