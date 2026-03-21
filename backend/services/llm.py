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

BASE_URL = _env.get('ANTHROPIC_BASE_URL') or "https://api.minimaxi.com/anthropic"
API_KEY = _env.get('ANTHROPIC_AUTH_TOKEN', '')

# Use MiniMax-M2.7 for tool calling support (not highspeed)
DEFAULT_MODEL = "MiniMax-M2.7"


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

TOOLS = [SEARCH_TOOL_DEF]


def web_search(query: str) -> str:
    """
    Perform a web search. Uses DuckDuckGo as primary (no API key needed).
    Results are cached in the database.
    """
    from models import db, SearchCache

    # Check cache first
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
) -> dict:
    """
    Send a chat request to MiniMax with OpenAI-compatible tool calling.

    Returns:
        {"type": "text", "text": "...", "reasoning": "..."}
        {"type": "tool_call", "tool": "name", "input": {...}, "reasoning": "..."}
    """
    if not API_KEY:
        raise ValueError("MiniMax API key not found in .env file")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
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

    resp = requests.post(
        f"{BASE_URL}/v1/messages",
        json=payload,
        headers=headers,
        timeout=60
    )
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
