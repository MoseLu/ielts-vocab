from routes import books as books_routes


def test_merge_examples_prefers_unified_short_examples_over_catalog_cache(monkeypatch):
    monkeypatch.setattr(books_routes, '_catalog_examples_cache', {
        'quit': [{'en': 'She quit the course early.', 'zh': '她提前退课了。'}],
    })
    monkeypatch.setattr(books_routes, '_examples_cache', {
        'quit': [{'en': 'He quit last year.', 'zh': '他去年辞职了。'}],
    })

    enriched = books_routes._merge_examples({'word': 'quit'})

    assert enriched['examples'] == [{'en': 'He quit last year.', 'zh': '他去年辞职了。'}]


def test_merge_examples_falls_back_to_catalog_examples_when_short_examples_missing(monkeypatch):
    monkeypatch.setattr(books_routes, '_catalog_examples_cache', {
        'quit': [{'en': 'She quit the course early.', 'zh': '她提前退课了。'}],
    })
    monkeypatch.setattr(books_routes, '_examples_cache', {
        'quit': [],
    })

    enriched = books_routes._merge_examples({'word': 'quit'})

    assert enriched['examples'] == [{'en': 'She quit the course early.', 'zh': '她提前退课了。'}]


def test_merge_examples_normalizes_and_caps_examples_to_one(monkeypatch):
    monkeypatch.setattr(books_routes, '_catalog_examples_cache', {})
    monkeypatch.setattr(books_routes, '_examples_cache', {
        'quit': [
            {'en': '  He   quit   last year.  ', 'zh': ' 他去年辞职了。 '},
            {'en': 'He quit last year.', 'zh': '重复例句会被去重。'},
            {'en': 'She quit the course early.', 'zh': '她提前退课了。'},
        ],
    })

    enriched = books_routes._merge_examples({'word': 'quit'})

    assert enriched['examples'] == [{'en': 'He quit last year.', 'zh': '他去年辞职了。'}]
