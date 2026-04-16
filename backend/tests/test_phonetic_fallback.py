import services.books_catalog_query_service as books_catalog_query_service
import services.books_word_detail_service as books_word_detail_service
from models import WordCatalogEntry


class TestPhoneticFallback:
    def test_search_words_hydrates_missing_phonetic_from_local_lookup(self, client, monkeypatch):
        monkeypatch.setattr(books_catalog_query_service, '_global_word_search_catalog', None)
        monkeypatch.setattr(books_catalog_query_service, '_build_global_word_search_catalog', lambda: [{
            'word': 'complicate',
            'phonetic': '',
            'pos': 'v.',
            'definition': '使复杂化',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'examples': [],
        }])
        monkeypatch.setattr(
            books_catalog_query_service.phonetic_lookup_service,
            'lookup_local_phonetics',
            lambda words: {'complicate': '/ˈkɒmplɪkeɪt/'},
        )

        res = client.get('/api/books/search?q=complicate')

        assert res.status_code == 200
        data = res.get_json()
        assert data['results'][0]['phonetic'] == '/ˈkɒmplɪkeɪt/'

    def test_search_words_override_replaces_incorrect_existing_phonetic(self, client, monkeypatch):
        monkeypatch.setattr(books_catalog_query_service, '_global_word_search_catalog', None)
        monkeypatch.setattr(books_catalog_query_service, '_build_global_word_search_catalog', lambda: [{
            'word': 'recipes',
            'phonetic': '/ˈresɪpsiːz/',
            'pos': 'n.',
            'definition': '食谱；配方',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'examples': [],
        }])
        monkeypatch.setattr(
            books_catalog_query_service.phonetic_lookup_service,
            'load_phonetic_overrides',
            lambda: {'recipes': '/ˈresəpiz/'},
        )

        res = client.get('/api/books/search?q=recipes')

        assert res.status_code == 200
        data = res.get_json()
        assert data['results'][0]['phonetic'] == '/ˈresəpiz/'

    def test_word_details_resolve_remote_phonetic_and_persist_it(self, client, app, monkeypatch):
        monkeypatch.setattr(books_catalog_query_service, '_global_word_search_catalog', None)
        monkeypatch.setattr(books_catalog_query_service, '_build_global_word_search_catalog', lambda: [{
            'word': 'complicate',
            'phonetic': '',
            'pos': 'v.',
            'definition': '使复杂化',
            'book_id': 'book-a',
            'book_title': 'Book A',
            'examples': [],
        }])
        monkeypatch.setattr(
            books_word_detail_service.phonetic_lookup_service,
            'lookup_local_phonetic',
            lambda _word: '',
        )
        monkeypatch.setattr(
            books_word_detail_service.phonetic_lookup_service,
            'resolve_phonetic',
            lambda _word, allow_remote=False: '/ˈkɒmplɪkeɪt/',
        )

        res = client.get('/api/books/word-details?word=complicate')

        assert res.status_code == 200
        data = res.get_json()
        assert data['phonetic'] == '/ˈkɒmplɪkeɪt/'

        with app.app_context():
            entry = WordCatalogEntry.query.filter_by(normalized_word='complicate').first()
            assert entry is not None
            assert entry.phonetic == '/ˈkɒmplɪkeɪt/'
