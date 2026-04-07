import routes.books as books_routes
import services.legacy_word_detail_migration as legacy_word_detail_migration
import services.word_detail_enrichment as word_detail_enrichment
from models import (
    WordCatalogBookRef,
    WordCatalogEntry,
    UserWordNote,
    WordDerivativeEntry,
    WordEnglishMeaning,
    WordExampleEntry,
    WordRootDetail,
    db,
)


def _mock_catalog():
    return [
        {
            'word': 'quit',
            'phonetic': '/kwɪt/',
            'pos': 'v.',
            'definition': '停止；离开',
            'examples': [{'en': 'He decided to quit last year.', 'zh': '他决定去年辞职。'}],
            'headword': '',
            'book_id': 'book-a',
            'book_title': 'Book A',
        },
        {
            'word': 'quits',
            'phonetic': '/kwɪts/',
            'pos': 'v.',
            'definition': '退出；辞职',
            'headword': '',
            'book_id': 'book-a',
            'book_title': 'Book A',
        },
        {
            'word': 'quitting',
            'phonetic': '/ˈkwɪtɪŋ/',
            'pos': 'n.',
            'definition': '辞职；放弃',
            'headword': '',
            'book_id': 'book-a',
            'book_title': 'Book A',
        },
        {
            'word': 'quitter',
            'phonetic': '/ˈkwɪtə(r)/',
            'pos': 'n.',
            'definition': '半途而废的人',
            'headword': '',
            'book_id': 'book-a',
            'book_title': 'Book A',
        },
        {
            'word': 'analysis',
            'phonetic': '/əˈnæləsɪs/',
            'pos': 'n.',
            'definition': '分析',
            'headword': '',
            'book_id': 'book-b',
            'book_title': 'Book B',
        },
        {
            'word': 'analyst',
            'phonetic': '/ˈænəlɪst/',
            'pos': 'n.',
            'definition': '分析师',
            'headword': 'analysis',
            'book_id': 'book-b',
            'book_title': 'Book B',
        },
        {
            'word': 'analytical',
            'phonetic': '/ˌænəˈlɪtɪk(ə)l/',
            'pos': 'adj.',
            'definition': '分析的',
            'headword': 'analysis',
            'book_id': 'book-b',
            'book_title': 'Book B',
        },
    ]


def _stub_example_caches(monkeypatch, *, short_examples=None, catalog_examples=None):
    monkeypatch.setattr(books_routes, '_examples_cache', short_examples or {})
    monkeypatch.setattr(books_routes, '_catalog_examples_cache', catalog_examples or {})


class TestWordDetails:
    def test_word_details_requires_word(self, client):
        res = client.get('/api/books/word-details')
        assert res.status_code == 400

    def test_word_details_bootstrap_root_and_derivatives(self, client, app, monkeypatch):
        monkeypatch.setattr(books_routes, '_build_global_word_search_catalog', _mock_catalog)
        _stub_example_caches(monkeypatch, short_examples={
            'quit': [{'en': 'Quit the course before the deadline.', 'zh': '在截止前退出课程。'}],
        })

        res = client.get('/api/books/word-details?word=quit')

        assert res.status_code == 200
        data = res.get_json()
        assert data['word'] == 'quit'
        assert data['phonetic'] == '/kwɪt/'
        assert data['pos'] == 'v.'
        assert data['definition'] == '停止；离开'
        assert data['root']['segments'][0]['text'] == 'quit'
        assert data['english']['entries'] == []
        assert [item['word'] for item in data['derivatives']] == ['quits', 'quitting', 'quitter']
        assert data['examples'][0]['en'] == 'Quit the course before the deadline.'
        assert data['books'][0]['book_id'] == 'book-a'
        assert data['note']['content'] == ''

        with app.app_context():
            catalog_entry = WordCatalogEntry.query.filter_by(normalized_word='quit').first()
            assert catalog_entry is not None
            assert catalog_entry.definition == '停止；离开'
            assert catalog_entry.get_root_segments()[0]['text'] == 'quit'
            assert WordCatalogBookRef.query.filter_by(catalog_entry_id=catalog_entry.id).count() == 1
            derivative_words = [item['word'] for item in catalog_entry.get_derivatives()]
            assert derivative_words == ['quits', 'quitting', 'quitter']
            assert catalog_entry.get_examples()[0]['en'] == 'He decided to quit last year.'

    def test_word_details_fall_back_to_catalog_examples_when_short_examples_missing(self, client, monkeypatch):
        monkeypatch.setattr(books_routes, '_build_global_word_search_catalog', _mock_catalog)
        _stub_example_caches(monkeypatch, short_examples={})

        res = client.get('/api/books/word-details?word=quit')

        assert res.status_code == 200
        data = res.get_json()
        assert data['examples'][0]['en'] == 'He decided to quit last year.'

    def test_word_details_include_headword_family(self, client, monkeypatch):
        monkeypatch.setattr(books_routes, '_build_global_word_search_catalog', _mock_catalog)

        res = client.get('/api/books/word-details?word=analysis')

        assert res.status_code == 200
        data = res.get_json()
        derivative_words = [item['word'] for item in data['derivatives']]
        assert 'analyst' in derivative_words
        assert 'analytical' in derivative_words

    def test_word_details_fall_back_to_placeholder_derivatives(self, client, monkeypatch):
        monkeypatch.setattr(books_routes, '_build_global_word_search_catalog', lambda: [])
        _stub_example_caches(monkeypatch, short_examples={})

        res = client.get('/api/books/word-details?word=quit')

        assert res.status_code == 200
        data = res.get_json()
        assert [item['word'] for item in data['derivatives']] == ['quits', 'quitting', 'quitter']
        assert all(item['source'] == 'placeholder' for item in data['derivatives'])
        assert data['examples'] == []

    def test_word_details_ignore_legacy_tables_during_runtime_reads(self, client, app, monkeypatch):
        monkeypatch.setattr(books_routes, '_build_global_word_search_catalog', _mock_catalog)

        with app.app_context():
            root = WordRootDetail(
                word='quit',
                normalized_word='quit',
                segments_json='[]',
                summary='legacy summary',
            )
            root.set_segments([{
                'kind': '词根',
                'text': 'legacyquit',
                'meaning': '旧表里的遗留词根',
            }])
            db.session.add(root)
            db.session.commit()

        res = client.get('/api/books/word-details?word=quit')

        assert res.status_code == 200
        data = res.get_json()
        assert data['root']['segments'][0]['text'] == 'quit'
        assert data['root']['segments'][0]['text'] != 'legacyquit'

    def test_llm_enrichment_persists_english_and_examples(self, client, app, monkeypatch):
        monkeypatch.setattr(books_routes, '_build_global_word_search_catalog', lambda: [{
            'word': 'quit',
            'book_id': 'ielts_listening_premium',
            'book_title': 'Listening Premium',
            'phonetic': '/kwɪt/',
            'pos': 'v.',
            'definition': '停止；离开',
            'examples': [{'en': 'He decided to quit last year.', 'zh': '他决定去年辞职。'}],
        }])
        _stub_example_caches(monkeypatch, short_examples={
            'quit': [{'en': 'Quit before the deadline if needed.', 'zh': '如果有需要，就在截止前退出。'}],
        })
        monkeypatch.setattr(word_detail_enrichment, 'request_llm_batch', lambda *_args, **_kwargs: {
            'quit': {
                'word': 'quit',
                'english': [
                    {'pos': 'v.', 'definition': 'to stop doing something'},
                    {'pos': 'v.', 'definition': 'to leave a job, school, or place'},
                ],
                'root': {
                    'segments': [{'kind': '词根', 'text': 'quit', 'meaning': '把 quit 直接当作核心词形记忆'}],
                    'summary': 'quit 本身就是核心记忆单元。',
                },
                'derivatives': [
                    {'word': 'quitter', 'phonetic': '/ˈkwɪtə(r)/', 'pos': 'n.', 'definition': 'a person who gives up easily', 'relation_type': 'person'},
                    {'word': 'quitting', 'phonetic': '/ˈkwɪtɪŋ/', 'pos': 'n.', 'definition': 'the act of leaving or stopping', 'relation_type': 'action'},
                ],
                'examples': [
                    {'en': 'She decided to quit her job before the exam season.', 'zh': '她决定在考试季前辞职。'},
                    {'en': 'Many students quit the course when the workload became too heavy.', 'zh': '当课业负担太重时，很多学生退出了课程。'},
                ],
            },
        })

        with app.app_context():
            stats = word_detail_enrichment.enrich_premium_books(
                book_ids=('ielts_listening_premium',),
                words=['quit'],
                batch_size=1,
                overwrite=True,
                sleep_seconds=0,
            )
            assert stats['enriched'] == 1
            assert stats['failed'] == 0
            catalog_entry = WordCatalogEntry.query.filter_by(normalized_word='quit').first()
            assert catalog_entry is not None
            assert catalog_entry.source == 'llm'
            assert len(catalog_entry.get_book_refs()) == 1
            assert len(catalog_entry.get_english_entries()) == 2
            assert len(catalog_entry.get_examples()) == 2

        res = client.get('/api/books/word-details?word=quit')
        assert res.status_code == 200
        data = res.get_json()
        assert data['phonetic'] == '/kwɪt/'
        assert data['english']['entries'][0]['definition'] == 'to stop doing something'
        assert data['examples'][0]['en'] == 'Quit before the deadline if needed.'
        assert data['derivatives'][0]['word'] == 'quitter'
        assert 'ielts_listening_premium' in {item['book_id'] for item in data['books']}

    def test_explicit_legacy_migration_backfills_catalog(self, app, monkeypatch):
        monkeypatch.setattr(books_routes, '_build_global_word_search_catalog', lambda: [{
            'word': 'quit',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'phonetic': '/kwɪt/',
            'pos': 'v.',
            'definition': '停止；离开',
            'examples': [],
        }])

        with app.app_context():
            root = WordRootDetail(
                word='quit',
                normalized_word='quit',
                segments_json='[]',
                summary='legacy root summary',
            )
            root.set_segments([{
                'kind': '词根',
                'text': 'legacyquit',
                'meaning': '旧表词根',
            }])
            english = WordEnglishMeaning(
                word='quit',
                normalized_word='quit',
                entries_json='[]',
                source='legacy',
            )
            english.set_entries([{'pos': 'v.', 'definition': 'to stop doing something'}])
            derivative = WordDerivativeEntry(
                base_word='quit',
                normalized_base_word='quit',
                derivative_word='quitter',
                derivative_phonetic='/ˈkwɪtə(r)/',
                derivative_pos='n.',
                derivative_definition='a person who gives up easily',
                relation_type='legacy',
                sort_order=0,
                source='legacy',
            )
            example = WordExampleEntry(
                word='quit',
                normalized_word='quit',
                sentence_en='He decided to quit last year.',
                sentence_zh='他决定去年辞职。',
                source='legacy',
                sort_order=0,
            )
            db.session.add_all([root, english, derivative, example])
            db.session.commit()

            stats = legacy_word_detail_migration.migrate_legacy_word_details(words=['quit'])

            assert stats['migrated'] == 1
            catalog_entry = WordCatalogEntry.query.filter_by(normalized_word='quit').first()
            assert catalog_entry is not None
            assert catalog_entry.source == 'legacy_migration'
            assert catalog_entry.get_root_segments()[0]['text'] == 'legacyquit'
            assert catalog_entry.get_english_entries()[0]['definition'] == 'to stop doing something'
            assert catalog_entry.get_derivatives()[0]['word'] == 'quitter'
            assert catalog_entry.get_examples()[0]['en'] == 'He decided to quit last year.'

    def test_word_notes_save_and_clear(self, client, app, monkeypatch):
        monkeypatch.setattr(books_routes, '_build_global_word_search_catalog', _mock_catalog)
        client.post('/api/auth/register', json={
            'username': 'word-note-user',
            'password': 'password123',
        })

        save = client.put('/api/books/word-details/note', json={
            'word': 'quit',
            'content': '记住 quit 和 quiet 的区别',
        })
        assert save.status_code == 200
        assert save.get_json()['note']['content'] == '记住 quit 和 quiet 的区别'

        detail = client.get('/api/books/word-details?word=quit')
        assert detail.status_code == 200
        assert detail.get_json()['note']['content'] == '记住 quit 和 quiet 的区别'

        clear = client.put('/api/books/word-details/note', json={
            'word': 'quit',
            'content': '',
        })
        assert clear.status_code == 200
        assert clear.get_json()['note']['content'] == ''

        with app.app_context():
            assert UserWordNote.query.count() == 0

    def test_llm_enrichment_stops_fast_on_quota_exhausted(self, app, monkeypatch):
        monkeypatch.setattr(books_routes, '_build_global_word_search_catalog', lambda: [
            {
                'word': 'quit',
                'book_id': 'book-a',
                'book_title': 'Book A',
                'phonetic': '/kwɪt/',
                'pos': 'v.',
                'definition': '停止；离开',
                'examples': [],
            },
            {
                'word': 'analysis',
                'book_id': 'book-a',
                'book_title': 'Book A',
                'phonetic': '/əˈnæləsɪs/',
                'pos': 'n.',
                'definition': '分析',
                'examples': [],
            },
        ])
        monkeypatch.setattr(
            word_detail_enrichment,
            'request_llm_batch',
            lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError('quota exhausted')),
        )

        with app.app_context():
            stats = word_detail_enrichment.enrich_catalog_words(
                words=['quit', 'analysis'],
                batch_size=2,
                overwrite=True,
                sleep_seconds=0,
            )

        assert stats['quota_exhausted'] is True
        assert 'quota exhausted' in stats['stop_reason']
        assert stats['failed'] == 2
        assert stats['enriched'] == 0
