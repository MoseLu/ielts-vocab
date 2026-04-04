import logging
import os
import requests
import json

# Read .env directly to bypass MCP proxy env var interception
_BACKEND_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
_ENV_FILE = os.path.join(_BACKEND_DIR, '.env')

def _load_env():
    env = {}
    if os.path.exists(_ENV_FILE):
        with open(_ENV_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, _, value = line.partition('=')
                    env[key.strip()] = value.strip()
    return env

_env = _load_env()

# MiniMax API configuration
BASE_URL = _env.get('ANTHROPIC_BASE_URL') or _env.get('MINIMAX_BASE_URL') or "https://api.minimaxi.com/anthropic"
API_KEY = _env.get('MINIMAX_API_KEY', '')
API_KEY_2 = _env.get('MINIMAX_API_KEY_2', '')

# Use MiniMax-M2.7-highspeed for primary key, M2.7 for secondary
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"
FALLBACK_MODEL = "MiniMax-M2.5"

# Track which key to use (simple round-robin for load balancing)
_use_secondary_key = False
# Track if primary key is rate-limited (429)
_primary_rate_limited = False


def _build_messages_url(base_url: str) -> str:
    normalized = base_url.rstrip('/')
    if normalized.endswith('/anthropic/v1'):
        return f"{normalized}/messages"
    if normalized.endswith('/anthropic'):
        return f"{normalized}/v1/messages"
    if normalized.endswith('/v1') and 'minimaxi.com' in normalized:
        legacy_root = normalized[:-3]
        return f"{legacy_root}/anthropic/v1/messages"
    return f"{normalized}/v1/messages"


def _build_headers(api_key: str, stream: bool = False) -> dict[str, str]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    if stream:
        headers["Accept"] = "text/event-stream"
    return headers


def _extract_error_message(resp: requests.Response) -> str:
    try:
        data = resp.json()
    except Exception:
        return resp.text
    error = data.get('error')
    if isinstance(error, dict):
        return str(error.get('message', ''))
    return str(error or data)


def _post_messages_request(
    payload: dict,
    *,
    force_secondary: bool = False,
    allow_model_fallback: bool = True,
    stream: bool = False,
):
    global _primary_rate_limited

    current_key, key_type = get_api_key_with_fallback(force_secondary=force_secondary)
    if not current_key:
        raise ValueError("MiniMax API key not found in .env file")

    resp = requests.post(
        _build_messages_url(BASE_URL),
        json=payload,
        headers=_build_headers(current_key, stream=stream),
        timeout=60,
        stream=stream,
    )

    if resp.status_code == 429:
        if key_type == 'primary' and API_KEY_2:
            print("[LLM] Primary key rate limited (429), switching to secondary key...")
            _primary_rate_limited = True
            return _post_messages_request(
                payload,
                force_secondary=True,
                allow_model_fallback=allow_model_fallback,
                stream=stream,
            )
        raise RuntimeError("Both API keys are rate limited. Please try again later.")

    if resp.status_code >= 500 and allow_model_fallback:
        error_message = _extract_error_message(resp).lower()
        if 'not support model' in error_message and payload.get('model') != FALLBACK_MODEL:
            if key_type == 'primary' and API_KEY_2 and not force_secondary:
                logging.warning(
                    "[LLM] Model %s unsupported on primary key, retrying with secondary key",
                    payload.get('model'),
                )
                return _post_messages_request(
                    payload,
                    force_secondary=True,
                    allow_model_fallback=allow_model_fallback,
                    stream=stream,
                )
            logging.warning(
                "[LLM] Model %s unsupported for current token plan, falling back to %s",
                payload.get('model'),
                FALLBACK_MODEL,
            )
            fallback_payload = dict(payload)
            fallback_payload['model'] = FALLBACK_MODEL
            return _post_messages_request(
                fallback_payload,
                force_secondary=force_secondary,
                allow_model_fallback=False,
                stream=stream,
            )

    resp.raise_for_status()
    return resp

def get_api_key():
    """Get API key with simple round-robin load balancing."""
    global _use_secondary_key
    if API_KEY_2 and _use_secondary_key:
        _use_secondary_key = not _use_secondary_key
        return API_KEY_2
    elif API_KEY:
        _use_secondary_key = not _use_secondary_key
        return API_KEY
    else:
        return API_KEY_2  # Fallback to secondary if primary is empty


def get_api_key_with_fallback(force_secondary=False):
    """Get API key, automatically falling back to secondary if primary is rate-limited."""
    if force_secondary and API_KEY_2:
        return API_KEY_2, 'secondary'
    elif _primary_rate_limited and API_KEY_2:
        return API_KEY_2, 'secondary'
    elif API_KEY:
        return API_KEY, 'primary'
    elif API_KEY_2:
        return API_KEY_2, 'secondary'
    else:
        raise ValueError("No MiniMax API key available")


# ── Web Search Tool ────────────────────────────────────────────────────────────

SEARCH_TOOL_DEF = {
    "name": "web_search",
    "description": "Search the web for information about a word, phrase, or topic. Use this when you need current, authoritative definitions, example sentences from real sources, or detailed explanations beyond your training data. Returns top search results with snippets.",
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query. For word lookups use: 'word example sentences in IELTS context' or 'word definition usage examples'"
            }
        },
        "required": ["query"]
    }
}

REMEMBER_TOOL_DEF = {
    "name": "remember_user_note",
    "description": (
        "Store an important, reusable observation about this user's learning goals, habits, "
        "preferences, weaknesses, or achievements. Call this whenever the user reveals something "
        "worth remembering for future sessions (e.g. 'my exam is in June', 'I struggle with "
        "academic words', 'I prefer listening practice'). "
        "The note will be injected into every future conversation."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "note": {
                "type": "string",
                "description": "A concise observation in Chinese, max 80 characters."
            },
            "category": {
                "type": "string",
                "enum": ["goal", "habit", "weakness", "preference", "achievement", "other"],
                "description": "Category of the note."
            }
        },
        "required": ["note", "category"]
    }
}

GET_WRONG_WORDS_TOOL_DEF = {
    "name": "get_wrong_words",
    "description": (
        "Fetch the user's wrong words from the database. "
        "Use this when the user asks about their mistakes, wants to review error-prone words, "
        "or when you need to analyse which words they struggle with. "
        "Returns word, phonetic, part-of-speech, definition and wrong_count."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Maximum number of wrong words to return (default 100, max 300)."
            }
        },
        "required": []
    }
}

GET_CHAPTER_WORDS_TOOL_DEF = {
    "name": "get_chapter_words",
    "description": (
        "Fetch the full word list for a specific chapter of a vocabulary book. "
        "Use this when the user asks what words are in a chapter, wants to preview content, "
        "or when you need to build a targeted study plan for a chapter. "
        "Returns each word with its phonetic, pos, and definition."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "book_id": {
                "type": "string",
                "description": "Book ID, e.g. 'ielts_listening_premium', 'ielts_reading_premium'."
            },
            "chapter_id": {
                "type": "integer",
                "description": "Chapter number (1-based integer)."
            }
        },
        "required": ["book_id", "chapter_id"]
    }
}

GET_BOOK_CHAPTERS_TOOL_DEF = {
    "name": "get_book_chapters",
    "description": (
        "Fetch the chapter list for a vocabulary book along with the user's progress per chapter. "
        "Use this when the user asks how many chapters a book has, which chapters they've completed, "
        "or when planning a study schedule chapter by chapter."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "book_id": {
                "type": "string",
                "description": "Book ID, e.g. 'ielts_listening_premium', 'ielts_reading_premium'."
            }
        },
        "required": ["book_id"]
    }
}

TOOLS = [SEARCH_TOOL_DEF, REMEMBER_TOOL_DEF, GET_WRONG_WORDS_TOOL_DEF, GET_CHAPTER_WORDS_TOOL_DEF, GET_BOOK_CHAPTERS_TOOL_DEF]


_SEARCH_CACHE_TTL_DAYS = 7


def web_search(query: str) -> str:
    """
    Perform a web search. Uses DuckDuckGo as primary (no API key needed).
    Results are cached in the database for up to 7 days.
    """
    from datetime import datetime, timedelta
    from models import db, SearchCache

    # Prune expired cache entries (opportunistic, non-blocking on failure)
    try:
        cutoff = datetime.utcnow() - timedelta(days=_SEARCH_CACHE_TTL_DAYS)
        SearchCache.query.filter(SearchCache.created_at < cutoff).delete(synchronize_session=False)
        db.session.commit()
    except Exception:
        db.session.rollback()

    # Check cache (only fresh entries remain after prune above)
    cached = SearchCache.query.filter_by(query=query).first()
    if cached:
        return f"[Cached]\n{cached.result}"

    try:
        url = f"https://api.duckduckgo.com/?q={requests.utils.quote(query)}&format=json&no_redirect=1"
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            raise RuntimeError(f"DuckDuckGo returned {resp.status_code}")

        data = resp.json()
        topics = data.get('RelatedTopics', [])
        snippets = []
        for t in topics[:6]:
            text = t.get('Text', '')
            if text:
                snippets.append(f"- {text}")

        summary = "\n".join(snippets) if snippets else "No results found."
    except Exception as e:
        summary = f"Search failed: {e}"

    # Cache result
    try:
        cache_entry = SearchCache(query=query, result=summary)
        db.session.add(cache_entry)
        db.session.commit()
    except Exception:
        pass

    return summary


TOOL_HANDLERS = {
    "web_search": web_search,
}


def _safe_json_parse(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except Exception:
        return None


def correct_text(text: str) -> dict:
    prompt = (
        "你是 IELTS Academic 写作纠错专家。请仅返回 JSON，字段为："
        "is_valid_english(boolean), grammar_ok(boolean), corrected_sentence(string), "
        "upgrades(array of {from,to,reason,example}), collocations(array of {wrong,right,reason,example}), "
        "encouragement(string), next_word(string)。"
        "若输入不是英文句子，请礼貌引导用户输入英文。"
    )
    payload = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": text[:1200]},
    ]
    resp = chat(payload, max_tokens=900)
    raw = resp.get("text", "")
    parsed = _safe_json_parse(raw)
    if parsed:
        return parsed
    # Fallback structure keeps API stable even when model does not output JSON
    return {
        "is_valid_english": True,
        "grammar_ok": False,
        "corrected_sentence": text,
        "upgrades": [],
        "collocations": [],
        "encouragement": raw[:500] if raw else "已收到你的句子，建议继续补充上下文以便更精准纠错。",
        "next_word": "crucial",
    }


def differentiate_synonyms(a: str, b: str) -> dict:
    prompt = (
        "你是 IELTS 近义词辨析专家。请仅返回 JSON："
        "summary(string), table(array of {word,cn_meaning,focus,pos,collocations,ielts_usage,example}), "
        "interchangeable(boolean), quiz({question,options,answer,explanation})."
    )
    resp = chat(
        [
            {"role": "system", "content": prompt},
            {"role": "user", "content": f"{a} vs {b}"},
        ],
        max_tokens=1200,
    )
    raw = resp.get("text", "")
    parsed = _safe_json_parse(raw)
    if parsed:
        return parsed
    return {
        "summary": raw[:500] or f"{a} 与 {b} 在 IELTS 语境有细微差异。",
        "table": [],
        "interchangeable": False,
        "quiz": {
            "question": f"在句子中应使用 {a} 还是 {b}？",
            "options": [a, b],
            "answer": a,
            "explanation": "请结合句法与语义判断。",
        },
    }


# ── Chat with MiniMax ───────────────────────────────────────────────────────────

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
