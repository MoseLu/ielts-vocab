def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
    tools: list | None = None,
    force_secondary: bool = False,
    allow_model_fallback: bool = True,
) -> dict:
    """
    Send a chat request to MiniMax with OpenAI-compatible tool calling.
    Automatically falls back to secondary API key if primary returns 429.

    Returns:
        {"type": "text", "text": "...", "reasoning": "..."}
        {"type": "tool_call", "tool": "name", "input": {...}, "reasoning": "..."}
    """
    global _primary_rate_limited

    current_key, key_type = get_api_key_with_fallback(force_secondary=force_secondary)
    if not current_key:
        raise ValueError("MiniMax API key not found in .env file")

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        # Request reasoning details separately
        "extra_body": {"reasoning_split": True},
    }

    if tools:
        payload["tools"] = [{
            "name": f.get("name", ""),
            "description": f.get("description", ""),
            "input_schema": f.get("parameters", {})
        } for f in tools]

    try:
        resp = _post_messages_request(
            payload,
            force_secondary=force_secondary,
            allow_model_fallback=allow_model_fallback,
            stream=False,
        )
        data = resp.json()

        # MiniMax uses Anthropic format: content is at top level, not in choices
        content = data.get("content", [])

        # Check content blocks for tool_use (MiniMax format)
        if isinstance(content, list):
            for block in content:
                if block.get("type") == "tool_use":
                    return {
                        "type": "tool_call",
                        "tool": block.get("name", ""),
                        "input": block.get("input", {}),
                        "tool_call_id": block.get("id", ""),
                        "reasoning": "",
                    }

            # Collect text blocks
            text_parts = [b.get("text", "") for b in content if b.get("type") == "text"]
            return {"type": "text", "text": "".join(text_parts), "reasoning": ""}

        logging.warning(
            "[LLM] Unexpected messages response shape (content type=%s)",
            type(content).__name__,
        )
        return {"type": "text", "text": "", "reasoning": ""}

    except requests.exceptions.RequestException as e:
        raise


def stream_text(
    messages: list[dict],
    *,
    system: str | None = None,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
    force_secondary: bool = False,
    allow_model_fallback: bool = True,
):
    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
    }
    if system:
        payload["system"] = system

    resp = _post_messages_request(
        payload,
        force_secondary=force_secondary,
        allow_model_fallback=allow_model_fallback,
        stream=True,
    )

    for raw_line in resp.iter_lines(decode_unicode=True):
        if not raw_line or not raw_line.startswith('data: '):
            continue

        data = _safe_json_parse(raw_line[6:])
        if not data:
            continue

        if data.get('type') == 'content_block_delta':
            delta = data.get('delta', {})
            if delta.get('type') == 'text_delta':
                text = delta.get('text', '')
                if text:
                    yield text
        elif data.get('type') == 'error':
            message = str(data.get('error', {}).get('message', 'Streaming generation failed'))
            raise RuntimeError(message)
        elif data.get('type') == 'message_stop':
            break


def stream_chat_events(
    messages: list[dict],
    *,
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
    tools: list | None = None,
    force_secondary: bool = False,
    allow_model_fallback: bool = True,
):
    payload: dict = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "stream": True,
        "extra_body": {"reasoning_split": True},
    }

    if tools:
        payload["tools"] = [{
            "name": f.get("name", ""),
            "description": f.get("description", ""),
            "input_schema": f.get("parameters", {})
        } for f in tools]

    resp = _post_messages_request(
        payload,
        force_secondary=force_secondary,
        allow_model_fallback=allow_model_fallback,
        stream=True,
    )

    tool_blocks: dict[int, dict[str, str]] = {}

    for raw_line in resp.iter_lines(decode_unicode=True):
        if not raw_line:
            continue
        if raw_line == 'data: [DONE]':
            break
        if not raw_line.startswith('data: '):
            continue

        data = _safe_json_parse(raw_line[6:])
        if not data:
            continue

        event_type = data.get('type')

        if event_type == 'content_block_start':
            index = int(data.get('index', 0) or 0)
            block = data.get('content_block') or {}
            block_type = block.get('type')
            if block_type == 'text':
                text = block.get('text', '')
                if text:
                    yield {'type': 'text_delta', 'text': text}
            elif block_type == 'tool_use':
                existing_input = block.get('input')
                tool_blocks[index] = {
                    'id': str(block.get('id', '') or ''),
                    'name': str(block.get('name', '') or ''),
                    'input_json': json.dumps(existing_input, ensure_ascii=False) if isinstance(existing_input, dict) and existing_input else '',
                }
        elif event_type == 'content_block_delta':
            index = int(data.get('index', 0) or 0)
            delta = data.get('delta', {}) or {}
            delta_type = delta.get('type')
            if delta_type == 'text_delta':
                text = delta.get('text', '')
                if text:
                    yield {'type': 'text_delta', 'text': text}
            elif delta_type == 'input_json_delta':
                partial_json = str(delta.get('partial_json', '') or '')
                block = tool_blocks.setdefault(index, {'id': '', 'name': '', 'input_json': ''})
                block['input_json'] += partial_json
        elif event_type == 'content_block_stop':
            index = int(data.get('index', 0) or 0)
            block = tool_blocks.pop(index, None)
            if block is not None:
                parsed_input = _safe_json_parse(block.get('input_json', '')) or {}
                yield {
                    'type': 'tool_call',
                    'tool': block.get('name', ''),
                    'input': parsed_input,
                    'tool_call_id': block.get('id', ''),
                }
        elif event_type == 'error':
            message = str(data.get('error', {}).get('message', 'Streaming generation failed'))
            raise RuntimeError(message)
        elif event_type == 'message_stop':
            break
