import os
import requests

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
BASE_URL = _env.get('MINIMAX_BASE_URL') or "https://api.minimaxi.com/v1"
API_KEY = _env.get('MINIMAX_API_KEY', '')
API_KEY_2 = _env.get('MINIMAX_API_KEY_2', '')

# Use MiniMax-M2.7-highspeed for primary key, M2.7 for secondary
DEFAULT_MODEL = "MiniMax-M2.7-highspeed"

# Track which key to use (simple round-robin for load balancing)
_use_secondary_key = False
# Track if primary key is rate-limited (429)
_primary_rate_limited = False

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

TOOLS = [SEARCH_TOOL_DEF, REMEMBER_TOOL_DEF]


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


# ── Chat with MiniMax ───────────────────────────────────────────────────────────

def chat(
    messages: list[dict],
    model: str = DEFAULT_MODEL,
    max_tokens: int = 4096,
    tools: list | None = None,
    force_secondary: bool = False,
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

    headers = {
        "Authorization": f"Bearer {current_key}",
        "Content-Type": "application/json",
    }

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
        resp = requests.post(
            f"{BASE_URL}/v1/messages",
            json=payload,
            headers=headers,
            timeout=60
        )

        # Handle 429 rate limit error - automatically switch to secondary key
        if resp.status_code == 429:
            if key_type == 'primary' and API_KEY_2:
                print("[LLM] Primary key rate limited (429), switching to secondary key...")
                _primary_rate_limited = True
                # Retry with secondary key
                return chat(messages, model, max_tokens, tools, force_secondary=True)
            else:
                raise RuntimeError(f"Both API keys are rate limited. Please try again later.")

        resp.raise_for_status()
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

    except requests.exceptions.RequestException as e:
        # Check if it's a 429 error from response
        if hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
            if key_type == 'primary' and API_KEY_2:
                print("[LLM] Primary key rate limited (429), switching to secondary key...")
                _primary_rate_limited = True
                return chat(messages, model, max_tokens, tools, force_secondary=True)
        raise
