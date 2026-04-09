_TOOL_INPUT_SCHEMA: dict[str, dict[str, tuple]] = {
    "web_search": {
        "query": (str, 500),
    },
    "remember_user_note": {
        "note": (str, 500),
        "category": (str, 50),
    },
    "get_wrong_words": {
        "limit": (int, None),
        "query": (str, 100),
        "recent_first": (bool, None),
    },
    "get_chapter_words": {
        "book_id": (str, 100),
        "chapter_id": (int, None),
    },
    "get_book_chapters": {
        "book_id": (str, 100),
    },
}

_VALID_CATEGORIES = {'goal', 'habit', 'weakness', 'preference', 'achievement', 'other'}


def validate_tool_input(tool_name: str, tool_input: dict) -> dict | None:
    schema = _TOOL_INPUT_SCHEMA.get(tool_name)
    if schema is None:
        return None

    cleaned = {}
    for param, (expected_type, max_len) in schema.items():
        value = tool_input.get(param)
        if value is None:
            continue
        if not isinstance(value, expected_type):
            return None
        if max_len and isinstance(value, str):
            value = value[:max_len]
        cleaned[param] = value

    if tool_name == "remember_user_note":
        category = cleaned.get("category", "other")
        if category not in _VALID_CATEGORIES:
            cleaned["category"] = "other"
    return cleaned
