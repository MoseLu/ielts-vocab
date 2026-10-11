"""AI Polish service for journal notes."""

from services.llm_service.chat_streaming import chat


class JournalPolishUnavailable(RuntimeError):
    """Raised when the journal polish provider cannot produce a result."""


def _normalize_for_compare(value: str) -> str:
    return ''.join(value.split())


def _request_polish(content: str, *, force_visible_revision: bool = False) -> str:
    extra_instruction = (
        "The previous result was identical to the input. Rewrite it visibly while preserving meaning; "
        "for example, improve colloquial phrasing, add natural diary wording, or smooth the sentence rhythm. "
        "Do not return the exact same text. "
        if force_visible_revision
        else ""
    )
    prompt = (
        "You are a writing assistant for a language learner's daily journal. "
        "Polish the following markdown journal entry to improve fluency, clarity, "
        "and organization while PRESERVING the original meaning, tone, and all markdown formatting. "
        "Do NOT add new facts or change the content substantially. "
        "Keep the language natural — the user writes in Chinese and English mixed. "
        "For short entries, still provide a visibly smoother rewrite instead of returning the input unchanged, "
        "unless the entry truly cannot be improved without changing its meaning. "
        "Fix minor grammar issues, improve sentence flow, and make wording a little more diary-like. "
        f"{extra_instruction}"
        "Return ONLY the polished markdown, no explanations."
    )

    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": content[:8000]},
    ]
    resp = chat(messages, max_tokens=4096)
    text = resp.get("text", "")
    polished = text.strip()
    if not polished:
        raise JournalPolishUnavailable("AI 润色服务没有返回内容，请稍后重试")
    return polished


def polish_text(content: str) -> str:
    """Polish the given markdown text using AI. Returns polished markdown."""
    if not content or not content.strip():
        return content

    try:
        polished = _request_polish(content)
        if _normalize_for_compare(polished) == _normalize_for_compare(content):
            polished = _request_polish(content, force_visible_revision=True)
        return polished
    except JournalPolishUnavailable:
        raise
    except Exception as exc:
        raise JournalPolishUnavailable("AI 润色服务暂不可用，请检查模型配置后重试") from exc
