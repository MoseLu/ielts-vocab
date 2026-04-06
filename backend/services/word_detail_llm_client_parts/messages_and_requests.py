def extract_json_block(raw: str) -> str:
    text = str(raw or '').strip()
    if not text:
        raise ValueError('LLM returned empty text')

    object_start = text.find('{')
    array_start = text.find('[')
    candidates = [
        (position, opening, closing)
        for position, opening, closing in (
            (object_start, '{', '}'),
            (array_start, '[', ']'),
        )
        if position >= 0
    ]
    if not candidates:
        raise ValueError('No valid JSON block found in LLM output')

    start, opening, closing = min(candidates, key=lambda item: item[0])
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start:index + 1]

    raise ValueError('No valid JSON block found in LLM output')


def normalize_llm_items(raw_payload, normalize_word) -> dict[str, dict]:
    if isinstance(raw_payload, dict):
        items = raw_payload.get('items') or raw_payload.get('results') or raw_payload.get('words')
        if items is None and raw_payload.get('word'):
            items = [raw_payload]
    elif isinstance(raw_payload, list):
        items = raw_payload
    else:
        items = []

    normalized_items = {}
    for item in items or []:
        if not isinstance(item, dict):
            continue
        key = normalize_word(item.get('word'))
        if key:
            normalized_items[key] = item
    return normalized_items


def _build_multi_word_messages(word_seeds: list[dict]) -> list[dict]:
    system_prompt = (
        '你是雅思词汇编辑。请只返回合法 JSON，不要 markdown，不要解释。'
        '返回数组，顺序必须与输入一致，每个输入词都必须返回一个对象。'
        '每个元素都必须包含 word, english, root, derivatives, examples。'
        'word 必须原样使用输入里的小写 word 字段。'
        'english 最多返回 2 条，元素字段为 pos, definition，definition 用简洁英文。'
        'root 字段为对象，包含 segments 和 summary。'
        'segments 里的每个元素都必须包含 kind、text、meaning，kind 只能是 前缀、词根、后缀。'
        'derivatives 最多返回 3 条，元素字段为 word, phonetic, pos, definition, relation_type。'
        'examples 必须返回 2 条，元素字段为 en, zh。英文例句要自然、适合雅思学习场景，中文翻译要直白。'
        '如果某词没有明显前后缀，就只保留一个 kind=词根 的 segment。'
        '如果没有合适派生词，可以返回空数组。'
    )
    payload = [{
        'word': seed['normalized_word'],
        'display_word': seed['display_word'],
        'phonetic': seed['phonetic'],
        'pos': seed['pos'],
        'cn_definitions': seed['definitions'],
        'reference_examples': seed['examples'],
    } for seed in word_seeds]
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
    ]


def _build_single_word_messages(word_seed: dict) -> list[dict]:
    system_prompt = (
        '你是雅思词汇编辑。请只返回一个合法 JSON 对象，不要 markdown，不要解释。'
        '必须包含 word, english, root, derivatives, examples。'
        'word 必须原样返回输入里的小写 word。'
        'english 最多 2 条，每条包含 pos, definition，definition 用简洁英文。'
        'root 必须包含 segments 和 summary。'
        'segments 是数组，数组里的每一项都必须包含 kind、text、meaning。'
        'kind 只能是 前缀、词根、后缀。'
        'derivatives 最多 3 条，每条包含 word, phonetic, pos, definition, relation_type。'
        'examples 必须返回 2 条，每条包含 en, zh。'
    )
    payload = {
        'word': word_seed['normalized_word'],
        'display_word': word_seed['display_word'],
        'phonetic': word_seed['phonetic'],
        'pos': word_seed['pos'],
        'cn_definitions': word_seed['definitions'],
        'reference_examples': word_seed['examples'],
    }
    return [
        {'role': 'system', 'content': system_prompt},
        {'role': 'user', 'content': json.dumps(payload, ensure_ascii=False)},
    ]


def _request_minimax(
    messages: list[dict],
    model: str,
    max_tokens: int,
    *,
    force_secondary: bool,
) -> str:
    if force_secondary:
        api_key = _MINIMAX_SECONDARY_KEY or _MINIMAX_PRIMARY_KEY
        provider_name = MINIMAX_SECONDARY_PROVIDER
    else:
        api_key = _MINIMAX_PRIMARY_KEY or _MINIMAX_SECONDARY_KEY
        provider_name = MINIMAX_PRIMARY_PROVIDER

    if not api_key:
        raise ValueError(f'{provider_name} API key not found in backend/.env')

    payload = {
        'model': model,
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': 0.1,
    }
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json',
    }
    response = requests.post(
        f'{_MINIMAX_BASE_URL}/chat/completions',
        json=payload,
        headers=headers,
        timeout=60,
    )
    _raise_for_api_error(response, provider_name)

    data = response.json()
    choices = data.get('choices') or []
    if not choices:
        raise ValueError('MiniMax response missing choices')
    message = choices[0].get('message') or {}
    content = message.get('content', '')
    if isinstance(content, list):
        text = ''.join(
            str(item.get('text') or '')
            for item in content
            if isinstance(item, dict)
        ).strip()
    else:
        text = str(content or '').strip()
    if not text:
        raise ValueError('MiniMax response missing text content')
    return text


def _request_dashscope(messages: list[dict], model: str, max_tokens: int) -> str:
    if not _DASHSCOPE_API_KEY:
        raise ValueError('DashScope API key not found in backend/.env')

    payload = {
        'model': model,
        'messages': messages,
        'max_tokens': max_tokens,
        'temperature': 0.1,
    }
    headers = {
        'Authorization': f'Bearer {_DASHSCOPE_API_KEY}',
        'Content-Type': 'application/json',
    }
    url = f'{_DASHSCOPE_BASE_URL}/chat/completions'
    response = requests.post(url, json=payload, headers=headers, timeout=180)
    if response.status_code == 429:
        retry_after = int(response.headers.get('Retry-After', 10) or 10)
        time.sleep(max(1, retry_after))
        response = requests.post(url, json=payload, headers=headers, timeout=180)
    _raise_for_api_error(response, 'dashscope')

    data = response.json()
    choices = data.get('choices') or []
    if not choices:
        raise ValueError('DashScope response missing choices')
    message = choices[0].get('message') or {}
    content = message.get('content', '')
    if isinstance(content, list):
        return ''.join(str(item.get('text') or '') for item in content if isinstance(item, dict))
    return str(content or '')


def _request_provider_messages(
    messages: list[dict],
    *,
    provider: str,
    model: str,
    max_tokens: int,
) -> str:
    if provider == 'dashscope':
        return _request_dashscope(messages, model, max_tokens)
    if provider == MINIMAX_SECONDARY_PROVIDER:
        return _request_minimax(
            messages,
            model,
            max_tokens,
            force_secondary=True,
        )
    if provider in {DEFAULT_PROVIDER, MINIMAX_PRIMARY_PROVIDER}:
        return _request_minimax(
            messages,
            model,
            max_tokens,
            force_secondary=False,
        )
    raise ValueError(f'Unsupported LLM provider: {provider}')
