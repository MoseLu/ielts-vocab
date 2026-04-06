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
