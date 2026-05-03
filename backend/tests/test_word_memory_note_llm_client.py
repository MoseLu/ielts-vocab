import services.word_memory_note_llm_client as word_memory_note_llm_client


def _normalize_word(value: str | None) -> str:
    return str(value or '').strip().lower()


def test_memory_system_prompt_rejects_forced_phonetic_transliteration():
    prompt = word_memory_note_llm_client._memory_system_prompt()

    assert '只有谐音自然顺口时才用 谐音' in prompt
    assert '禁止使用拗口生造音译' in prompt
    assert '辨析用于近义/易混词差异' in prompt
    assert '扩展用于同根、派生、复合词或固定搭配' in prompt
    assert '类型规则：词根词缀要写真实前缀/词根/后缀' in prompt
    assert '辨析要比较近义词的使用边界' in prompt
    assert '不要补 -ain 这类假后缀' in prompt
    assert '禁止把没有真实语义关系的形近词硬连' in prompt
    assert 'certain 必须只写 cert 表确定' in prompt
    assert '每条 text 都必须有真实可回忆的钩子' in prompt
    assert '多义词要覆盖或点明核心义群' in prompt
    assert '禁止使用拗口生造音译、伪词根、假拆分或编造人名地名' in prompt
    assert '除非释义本身包含死亡、杀死、致命等义' in prompt
    assert '禁止模板句：先抓核心义、放回句子判断' in prompt
    assert '禁止只写没有中文解释的词根词缀链' in prompt
    assert '派生词、复数词、现在分词不能只写' in prompt


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
