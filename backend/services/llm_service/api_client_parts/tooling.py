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
    from services import search_cache_repository

    # Prune expired cache entries (opportunistic, non-blocking on failure)
    try:
        cutoff = datetime.utcnow() - timedelta(days=_SEARCH_CACHE_TTL_DAYS)
        search_cache_repository.prune_search_cache_older_than(cutoff)
        search_cache_repository.commit()
    except Exception:
        search_cache_repository.rollback()

    # Check cache (only fresh entries remain after prune above)
    cached = search_cache_repository.get_search_cache(query)
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
        search_cache_repository.create_search_cache(query, summary)
        search_cache_repository.commit()
    except Exception:
        search_cache_repository.rollback()

    return summary


TOOL_HANDLERS = {
    "web_search": web_search,
}
