import services.word_memory_note_llm_client as word_memory_note_llm_client


def _normalize_word(value: str | None) -> str:
    return str(value or '').strip().lower()


def test_normalize_memory_items_uses_default_word_for_single_payload():
    items = word_memory_note_llm_client._normalize_memory_items(
        {
            'badge': '联想',
            'text': '想一下只差一点点，就是“稍微；有点”。',
        },
        _normalize_word,
        default_word='a bit',
    )

    assert items == {
        'a bit': {
            'badge': '联想',
            'text': '想一下只差一点点，就是“稍微；有点”。',
            'word': 'a bit',
        },
    }


def test_request_memory_note_batch_retries_single_word_and_fills_missing_word(monkeypatch):
    responses = iter([
        '   ',
        '{"badge":"联想","text":"想一下只差一点点，就是“稍微；有点”。"}',
    ])

    monkeypatch.setattr(
        word_memory_note_llm_client,
        'request_plan',
        lambda *_args, **_kwargs: [('minimax-primary', 'MiniMax-M2.5')],
    )
    monkeypatch.setattr(
        word_memory_note_llm_client,
        '_request_provider_messages',
        lambda *_args, **_kwargs: next(responses),
    )

    items = word_memory_note_llm_client.request_memory_note_batch(
        [{
            'normalized_word': 'a bit',
            'display_word': 'a bit',
            'phonetic': '/ə bɪt/',
            'pos': 'adv.',
            'definitions': ['稍微；有点'],
            'examples': [],
            'is_phrase': True,
            'book_ids': ['ielts_listening_premium'],
        }],
        provider='minimax-primary',
        model=None,
        fallback_provider='none',
        fallback_model=None,
        normalize_word=_normalize_word,
    )

    assert items['a bit']['text'] == '想一下只差一点点，就是“稍微；有点”。'


def test_normalize_memory_items_rewrites_single_target_word_variants():
    items = word_memory_note_llm_client._normalize_memory_items(
        [{'word': 'abit', 'badge': '联想', 'text': '想一下只差一点点，就是“稍微；有点”。'}],
        _normalize_word,
        default_word='a bit',
    )

    assert items['a bit']['word'] == 'a bit'


def test_request_memory_note_batch_accepts_single_word_plain_text_fallback(monkeypatch):
    monkeypatch.setattr(
        word_memory_note_llm_client,
        'request_plan',
        lambda *_args, **_kwargs: [('minimax-primary', 'MiniMax-M2.5')],
    )
    monkeypatch.setattr(
        word_memory_note_llm_client,
        '_request_provider_messages',
        lambda *_args, **_kwargs: '联想：想一下只差一点点，就是“稍微；有点”。',
    )

    items = word_memory_note_llm_client.request_memory_note_batch(
        [{
            'normalized_word': 'a bit',
            'display_word': 'a bit',
            'phonetic': '/ə bɪt/',
            'pos': 'adv.',
            'definitions': ['稍微；有点'],
            'examples': [],
            'is_phrase': True,
            'book_ids': ['ielts_listening_premium'],
        }],
        provider='minimax-primary',
        model=None,
        fallback_provider='none',
        fallback_model=None,
        normalize_word=_normalize_word,
    )

    assert items['a bit']['badge'] == '联想'
    assert items['a bit']['text'] == '想一下只差一点点，就是“稍微；有点”。'
