from services import listening_confusables as listening_service


def test_get_preset_listening_confusables_prefers_high_value_then_legacy(monkeypatch):
    monkeypatch.setattr(
        listening_service,
        'load_high_value_listening_confusable_index',
        lambda: {
            'strict': [
                {'word': 'strike', 'phonetic': '/straɪk/', 'pos': 'v.', 'definition': '打；撞击'},
                {'word': 'string', 'phonetic': '/strɪŋ/', 'pos': 'n.', 'definition': '线；细绳'},
            ]
        },
    )
    monkeypatch.setattr(
        listening_service,
        'load_listening_confusable_index',
        lambda: {
            'strict': [
                {'word': 'string', 'phonetic': '/strɪŋ/', 'pos': 'n.', 'definition': '线；细绳'},
                {'word': 'stock', 'phonetic': '/stɒk/', 'pos': 'n.', 'definition': '库存；股票'},
                {'word': 'street', 'phonetic': '/striːt/', 'pos': 'n.', 'definition': '街道'},
            ]
        },
    )

    result = listening_service.get_preset_listening_confusables('strict', limit=4)

    assert [candidate['word'] for candidate in result] == [
        'strike',
        'string',
        'stock',
        'street',
    ]


def test_attach_preset_listening_confusables_uses_merged_candidates(monkeypatch):
    monkeypatch.setattr(
        listening_service,
        'get_preset_listening_confusables',
        lambda word, limit=None: [
            {'word': 'seminar', 'phonetic': '/ˈsemɪnɑː(r)/', 'pos': 'n.', 'definition': '研讨会'},
            {'word': 'segment', 'phonetic': '/ˈseɡmənt/', 'pos': 'n.', 'definition': '部分；片段'},
        ],
    )

    entry = listening_service.attach_preset_listening_confusables(
        {'word': 'semester', 'phonetic': '/səˈmestə(r)/', 'pos': 'n.', 'definition': '学期'},
        limit=4,
    )

    assert [candidate['word'] for candidate in entry['listening_confusables']] == [
        'seminar',
        'segment',
    ]


def test_get_preset_listening_confusables_skips_legacy_when_high_value_is_complete(monkeypatch):
    monkeypatch.setattr(
        listening_service,
        'load_high_value_listening_confusable_index',
        lambda: {
            'semester': [
                {'word': 'seminar', 'phonetic': '/ˈsemɪnɑː(r)/', 'pos': 'n.', 'definition': '研讨会'},
                {'word': 'seminars', 'phonetic': '/ˈsemɪnɑːz/', 'pos': 'n.', 'definition': '研讨会（复数）'},
                {'word': 'segment', 'phonetic': '/ˈseɡmənt/', 'pos': 'n.', 'definition': '部分；片段'},
            ]
        },
    )
    monkeypatch.setattr(
        listening_service,
        'load_listening_confusable_index',
        lambda: {
            'semester': [
                {'word': 'seawater', 'phonetic': '/ˈsiːwɔːtə(r)/', 'pos': 'n.', 'definition': '海水'},
                {'word': 'signature', 'phonetic': '/ˈsɪɡnətʃə(r)/', 'pos': 'n.', 'definition': '签名'},
            ]
        },
    )

    result = listening_service.get_preset_listening_confusables('semester', limit=5)

    assert [candidate['word'] for candidate in result] == [
        'seminar',
        'seminars',
        'segment',
    ]
