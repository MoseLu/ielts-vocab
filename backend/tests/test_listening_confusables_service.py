import json

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


def test_get_preset_listening_confusables_filters_out_non_ielts_candidates(monkeypatch):
    monkeypatch.setattr(
        listening_service,
        'load_allowed_ielts_word_keys',
        lambda: {'quiet', 'quits'},
    )
    monkeypatch.setattr(
        listening_service,
        'load_high_value_listening_confusable_index',
        lambda: {
            'quit': [
                {'word': 'quiet', 'phonetic': '/ˈkwaɪət/', 'pos': 'adj.', 'definition': '安静的'},
                {'word': 'quota', 'phonetic': '/ˈkwəʊtə/', 'pos': 'n.', 'definition': '配额'},
            ]
        },
    )
    monkeypatch.setattr(
        listening_service,
        'load_listening_confusable_index',
        lambda: {
            'quit': [
                {'word': 'quits', 'phonetic': '/kwɪts/', 'pos': 'v.', 'definition': '退出'},
                {'word': 'quite', 'phonetic': '/kwaɪt/', 'pos': 'adv.', 'definition': '相当'},
            ]
        },
    )

    result = listening_service.get_preset_listening_confusables('quit', limit=4)

    assert [candidate['word'] for candidate in result] == ['quiet', 'quits']


def test_rank_preset_listening_confusables_prioritizes_closer_distractors():
    ranked = listening_service.rank_preset_listening_confusables(
        {
            'word': 'power',
            'phonetic': '/ˈpaʊə(r)/',
            'pos': 'n.',
            'definition': '力量；电源；权力；强国；',
        },
        [
            {'word': 'powerful', 'phonetic': '/ˈpaʊəfəl/', 'pos': 'adj.', 'definition': '强大的'},
            {'word': 'poker', 'phonetic': '/ˈpəʊkə(r)/', 'pos': 'n.', 'definition': '扑克'},
            {'word': 'powder', 'phonetic': '/ˈpaʊdə(r)/', 'pos': 'n.', 'definition': '粉末'},
            {'word': 'tower', 'phonetic': '/ˈtaʊə(r)/', 'pos': 'n.', 'definition': '塔'},
        ],
    )

    assert [candidate['word'] for candidate in ranked] == [
        'powder',
        'tower',
        'poker',
        'powerful',
    ]


def test_attach_preset_listening_confusables_ranks_before_limit(monkeypatch):
    monkeypatch.setattr(
        listening_service,
        'get_preset_listening_confusables',
        lambda word, limit=None: [
            {'word': 'powerful', 'phonetic': '/ˈpaʊəfəl/', 'pos': 'adj.', 'definition': '强大的'},
            {'word': 'poker', 'phonetic': '/ˈpəʊkə(r)/', 'pos': 'n.', 'definition': '扑克'},
            {'word': 'powder', 'phonetic': '/ˈpaʊdə(r)/', 'pos': 'n.', 'definition': '粉末'},
            {'word': 'tower', 'phonetic': '/ˈtaʊə(r)/', 'pos': 'n.', 'definition': '塔'},
        ],
    )

    entry = listening_service.attach_preset_listening_confusables(
        {'word': 'power', 'phonetic': '/ˈpaʊə(r)/', 'pos': 'n.', 'definition': '力量；电源；权力；强国；'},
        limit=3,
    )

    assert [candidate['word'] for candidate in entry['listening_confusables']] == [
        'powder',
        'tower',
        'poker',
    ]


def test_load_confusable_index_file_applies_phonetic_overrides(tmp_path, monkeypatch):
    path = tmp_path / 'confusables.json'
    path.write_text(json.dumps({
        'words': {
            'recipe': [
                {
                    'word': 'recipes',
                    'phonetic': '/ˈresɪpsiːz/',
                    'pos': 'n.',
                    'definition': '食谱；配方',
                }
            ]
        }
    }, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(
        listening_service.phonetic_lookup_service,
        'load_phonetic_overrides',
        lambda: {'recipes': '/ˈresəpiz/'},
    )

    index = listening_service._load_confusable_index_file(
        str(path),
        warning_label='test confusables index',
    )

    assert index['recipe'][0]['phonetic'] == '/ˈresəpiz/'
