def request_llm_batch(
    word_seeds: list[dict],
    *,
    provider: str,
    model: str | None,
    fallback_provider: str | None,
    fallback_model: str | None,
    normalize_word,
) -> dict[str, dict]:
    messages = (
        _build_single_word_messages(word_seeds[0])
        if len(word_seeds) == 1
        else _build_multi_word_messages(word_seeds)
    )
    max_tokens = _recommended_max_tokens(len(word_seeds))
    errors = []

    for current_provider, current_model in request_plan(
        provider,
        model,
        fallback_provider,
        fallback_model,
    ):
        try:
            raw_text = _request_provider_messages(
                messages,
                provider=current_provider,
                model=current_model,
                max_tokens=max_tokens,
            )
            parsed = json.loads(extract_json_block(raw_text))
            normalized_items = normalize_llm_items(parsed, normalize_word)
            missing = [
                seed['word']
                for seed in word_seeds
                if seed['normalized_word'] not in normalized_items
            ]
            if missing:
                raise ValueError(f'LLM result missing words: {", ".join(missing)}')
            return normalized_items
        except Exception as exc:
            errors.append(f'{current_provider}/{current_model}: {exc}')

    raise RuntimeError(' | '.join(errors))


def _extract_error_text(response: requests.Response) -> str:
    body_text = str(response.text or '').strip()
    if not body_text:
        return ''

    try:
        payload = response.json()
    except ValueError:
        return body_text[:500]

    if isinstance(payload, dict):
        for key in ('message', 'error_msg', 'msg', 'detail'):
            value = str(payload.get(key) or '').strip()
            if value:
                return value
        error = payload.get('error')
        if isinstance(error, dict):
            for key in ('message', 'msg', 'detail', 'code'):
                value = str(error.get(key) or '').strip()
                if value:
                    return value
        if isinstance(error, str) and error.strip():
            return error.strip()

    return body_text[:500]


def _raise_for_api_error(response: requests.Response, provider: str) -> None:
    if response.status_code < 400:
        return

    detail = _extract_error_text(response)
    raise RuntimeError(
        f'{provider} http {response.status_code}'
        + (f': {detail}' if detail else '')
    )


def is_quota_exhausted_error(message: str | Exception | None) -> bool:
    text = str(message or '').lower()
    return any(re.search(pattern, text) for pattern in QUOTA_EXHAUSTED_PATTERNS)


def _recommended_max_tokens(word_count: int) -> int:
    if word_count <= 1:
        return 1200
    return min(6400, max(DEFAULT_MODEL_MAX_TOKENS, 600 + (word_count * 700)))
